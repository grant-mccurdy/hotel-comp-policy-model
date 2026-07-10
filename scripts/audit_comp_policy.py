from __future__ import annotations

from collections import Counter, defaultdict

from common import (
    COMP_POLICY_AUDIT_PATH,
    COMP_RECOMMENDATIONS_PATH,
    REPORT_DIR,
    ensure_dirs,
    read_csv_rows,
    write_csv,
)
from policy_engine import as_float


AUDIT_REPORT_PATH = REPORT_DIR / "comp-policy-audit.md"


def money(value: float | int | str) -> str:
    try:
        return f"${float(value):,.0f}"
    except (TypeError, ValueError):
        return "$0"


def classify_case(row: dict[str, str]) -> tuple[str, list[str], str]:
    recovery_need = as_float(row.get("recovery_need_score"), 0)
    review_risk = as_float(row.get("review_risk_score"), 0)
    severity = as_float(row.get("severity"), 0)
    actual_value = as_float(row.get("actual_comp_face_value"), 0)
    recommended_value = as_float(row.get("recommended_comp_value"), 0)
    delta = recommended_value - actual_value
    reservation_confidence = as_float(row.get("reservation_match_confidence"), 0)
    crm_confidence = as_float(row.get("crm_match_confidence"), 0)
    manager_review = row.get("manager_review_flag") == "true"
    decision_confidence = row.get("decision_confidence", "unknown")
    stability = as_float(row.get("recommendation_stability"), 0)
    data_flags = row.get("data_quality_flags", "")

    flags: list[str] = []
    if reservation_confidence < 0.75 or crm_confidence < 0.65:
        flags.append("weak_identity_or_reservation_match")
    if "severity_inferred" in data_flags:
        flags.append("severity_inferred")
    if "no_comp_record" in data_flags:
        flags.append("no_historical_comp_record")
    if manager_review:
        flags.append("manager_review_model_flag")
    if decision_confidence == "low":
        flags.append("low_decision_confidence")
    if stability < 0.6:
        flags.append("unstable_policy_recommendation")
    if review_risk >= 0.7:
        flags.append("high_review_risk")
    if severity >= 4:
        flags.append("high_severity")

    if "weak_identity_or_reservation_match" in flags or "low_decision_confidence" in flags:
        return "data_quality_hold", flags, "Resolve identity/reservation match before auditing or automating the comp decision."

    if manager_review or "unstable_policy_recommendation" in flags or (severity >= 5 and recommended_value >= 400) or abs(delta) >= 500:
        return "manager_review_required", flags, "Route to manager because severity, guest value, spend, or policy variance is high."

    if delta >= 100 and recovery_need >= 55:
        return "under_recovered", flags, "Increase or improve recovery; historical/synthetic comp appears below modeled relationship and brand risk."

    if delta <= -75 and (recovery_need < 62 or review_risk < 0.55):
        return "over_comped", flags, "Review for profit leakage; historical/synthetic comp appears high relative to modeled recovery need."

    return "aligned_recovery", flags, "Current comp level appears broadly aligned with modeled recovery need."


def audit_rows(recommendations: list[dict[str, str]]) -> list[dict[str, object]]:
    audited = []
    for row in recommendations:
        audit_class, flags, action = classify_case(row)
        actual_value = as_float(row.get("actual_comp_face_value"), 0)
        recommended_value = as_float(row.get("recommended_comp_value"), 0)
        actual_cost = as_float(row.get("actual_comp_internal_cost"), 0)
        recommended_cost = as_float(row.get("estimated_internal_cost"), 0)
        audited.append(
            {
                "audit_id": f"audit_{len(audited) + 1:05d}",
                "recovery_case_id": row["recovery_case_id"],
                "service_ticket_id": row["service_ticket_id"],
                "pms_reservation_id": row["pms_reservation_id"],
                "audit_class": audit_class,
                "audit_flags": ";".join(flags),
                "recommended_action": action,
                "guest_tier": row["guest_tier"],
                "traveler_segment": row["traveler_segment"],
                "failure_category": row["failure_category"],
                "severity": row["severity"],
                "recovery_need_score": row["recovery_need_score"],
                "review_risk_score": row["review_risk_score"],
                "stay_value": row["stay_value"],
                "estimated_lifetime_value": row["estimated_lifetime_value"],
                "public_rate_pressure_index": row.get("public_rate_pressure_index", "0.5"),
                "high_demand_rate_flag": row.get("high_demand_rate_flag", "false"),
                "target_public_rate": row.get("target_public_rate", "0"),
                "comp_set_median_rate": row.get("comp_set_median_rate", "0"),
                "rate_context_confidence": row.get("rate_context_confidence", "0"),
                "pricing_provenance": row.get("pricing_provenance", "missing_public_pricing_context"),
                "actual_comp_codes_normalized": row["actual_comp_codes_normalized"],
                "actual_comp_face_value": int(actual_value),
                "actual_comp_internal_cost": int(actual_cost),
                "recommended_comp_code": row["comp_code"],
                "recommended_comp_label": row["comp_label"],
                "recommended_comp_value": int(recommended_value),
                "recommended_internal_cost": int(recommended_cost),
                "recommended_internal_cost_low": int(as_float(row.get("internal_cost_low"), recommended_cost)),
                "recommended_internal_cost_high": int(as_float(row.get("internal_cost_high"), recommended_cost)),
                "recommended_minus_actual_value": int(recommended_value - actual_value),
                "internal_cost_delta": int(recommended_cost - actual_cost),
                "manager_review_flag": row["manager_review_flag"],
                "decision_confidence": row.get("decision_confidence", "unknown"),
                "recommendation_stability": row.get("recommendation_stability", "0"),
                "policy_version": row.get("policy_version", "unknown"),
                "reservation_match_confidence": row["reservation_match_confidence"],
                "crm_match_confidence": row["crm_match_confidence"],
                "data_quality_flags": row["data_quality_flags"],
                "recommendation_reason_codes": row["recommendation_reason_codes"],
            }
        )
    return audited


def top_cases(rows: list[dict[str, object]], audit_class: str, metric: str, limit: int = 8) -> list[dict[str, object]]:
    filtered = [row for row in rows if row["audit_class"] == audit_class]
    return sorted(filtered, key=lambda row: abs(as_float(row.get(metric), 0)), reverse=True)[:limit]


def render_report(rows: list[dict[str, object]]) -> str:
    class_counts = Counter(str(row["audit_class"]) for row in rows)
    value_by_class: dict[str, float] = defaultdict(float)
    recommended_by_class: dict[str, float] = defaultdict(float)
    for row in rows:
        value_by_class[str(row["audit_class"])] += as_float(row.get("actual_comp_face_value"), 0)
        recommended_by_class[str(row["audit_class"])] += as_float(row.get("recommended_comp_value"), 0)

    lines = [
        "# Comp Policy Audit",
        "",
        "This audit compares synthetic historical comp actions against the modeled intelligent-generosity recommendation.",
        "",
        "The point is not to minimize comp spend. The point is to identify where generosity protects guest value and where compensation leaks profit without proportional recovery benefit.",
        "",
        "## Audit Summary",
        "",
        "| Audit class | Cases | Historical comp value | Recommended comp value |",
        "| --- | ---: | ---: | ---: |",
    ]
    for audit_class in [
        "under_recovered",
        "over_comped",
        "aligned_recovery",
        "manager_review_required",
        "data_quality_hold",
    ]:
        lines.append(
            f"| {audit_class.replace('_', ' ')} | {class_counts[audit_class]} | "
            f"{money(value_by_class[audit_class])} | {money(recommended_by_class[audit_class])} |"
        )

    lines.extend(
        [
            "",
            "## Decision Matrix",
            "",
            "| Case type | Meaning | Management action |",
            "| --- | --- | --- |",
            "| Under-recovered high-value cases | Guest relationship or review risk is not sufficiently protected | Increase generosity or act faster |",
            "| Over-comped low-risk cases | Comp spend may exceed modeled recovery value | Tighten approval policy or route for review |",
            "| Correctly generous cases | Spend appears aligned to recovery need | Preserve policy |",
            "| Manager-review cases | High severity, high value, high spend, or unusual variance | Human review before final action |",
            "| Data-quality holds | Weak match confidence or incomplete source context | Fix source reconciliation before auditing behavior |",
            "",
            "## Largest Under-Recovery Opportunities",
            "",
            "| Case | Guest tier | Issue | Recommended delta | Action |",
            "| --- | --- | --- | ---: | --- |",
        ]
    )
    for row in top_cases(rows, "under_recovered", "recommended_minus_actual_value"):
        lines.append(
            f"| {row['recovery_case_id']} | {row['guest_tier']} | {str(row['failure_category']).replace('_', ' ')} | "
            f"{money(row['recommended_minus_actual_value'])} | {row['recommended_action']} |"
        )

    lines.extend(
        [
            "",
            "## Largest Potential Profit-Leakage Cases",
            "",
            "| Case | Guest tier | Issue | Over-comp value | Action |",
            "| --- | --- | --- | ---: | --- |",
        ]
    )
    for row in top_cases(rows, "over_comped", "recommended_minus_actual_value"):
        lines.append(
            f"| {row['recovery_case_id']} | {row['guest_tier']} | {str(row['failure_category']).replace('_', ' ')} | "
            f"{money(abs(as_float(row['recommended_minus_actual_value'])))} | {row['recommended_action']} |"
        )

    lines.extend(
        [
            "",
            "## Public-Safety Note",
            "",
            "All rows are synthetic. This is not an analysis of actual Proper Hotels data, guest records, comp history, or internal policy.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    ensure_dirs()
    if not COMP_RECOMMENDATIONS_PATH.exists():
        print("Missing comp recommendations. Run scripts/generate_synthetic_comp_data.py first.")
        return 1
    _, recommendations = read_csv_rows(COMP_RECOMMENDATIONS_PATH)
    audited = audit_rows(recommendations)
    write_csv(COMP_POLICY_AUDIT_PATH, list(audited[0].keys()), audited)
    AUDIT_REPORT_PATH.write_text(render_report(audited), encoding="utf-8")
    print(f"Wrote comp policy audit: {COMP_POLICY_AUDIT_PATH.relative_to(COMP_POLICY_AUDIT_PATH.parents[1])}")
    print(f"Wrote comp policy audit report: {AUDIT_REPORT_PATH.relative_to(AUDIT_REPORT_PATH.parents[1])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
