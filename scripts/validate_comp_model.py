from __future__ import annotations

from pathlib import Path

from common import (
    COMP_CATALOG_PATH,
    COMP_POLICY_AUDIT_PATH,
    COMP_RECOMMENDATIONS_PATH,
    EXTERNAL_CONTEXT_MODEL_IMPACT_PATH,
    PROJECT_ROOT,
    PROPER_PUBLIC_CONTEXT_PATH,
    RECOVERY_CASE_MART_PATH,
    REPORT_DIR,
    ensure_dirs,
    read_csv_rows,
)
from generate_synthetic_comp_data import comp_catalog
from generate_synthetic_source_systems import (
    COMP_LEDGER_PATH,
    CRM_PROFILES_PATH,
    PMS_RESERVATIONS_PATH,
    REVIEWS_SURVEYS_PATH,
    SERVICE_TICKETS_PATH,
)
from policy_engine import as_float, recommend_comp


VALIDATION_REPORT_PATH = REPORT_DIR / "comp-model-validation.md"
DEMO_SCENARIO_CATALOG_PATH = PROJECT_ROOT / "data" / "sample" / "scenarios" / "manager_scenarios.csv"
DEMO_SCENARIO_REPORT_PATH = REPORT_DIR / "demo-scenario-recommendations.md"
METHODOLOGY_REPORT_PATH = REPORT_DIR / "methodology-and-assumptions.md"
MANAGER_DEMO_GUIDE_PATH = REPORT_DIR / "manager-demo-guide.md"
MANAGER_APP_SCRIPT_PATH = PROJECT_ROOT / "scripts" / "manager_app.py"


def add_check(checks: list[dict[str, str]], name: str, passed: bool, detail: str) -> None:
    checks.append({"name": name, "status": "PASS" if passed else "FAIL", "detail": detail})


def file_rows(path: Path) -> tuple[bool, list[dict[str, str]]]:
    if not path.exists():
        return False, []
    _, rows = read_csv_rows(path)
    return True, rows


def render_report(checks: list[dict[str, str]]) -> str:
    lines = [
        "# Comp Model Validation",
        "",
        "| Check | Status | Detail |",
        "| --- | --- | --- |",
    ]
    for check in checks:
        lines.append(f"| {check['name']} | {check['status']} | {check['detail'].replace('|', '\\|')} |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Validation intentionally checks both model behavior and realistic source-system messiness. A fully clean source layer would be less credible for the hotel comp-optimization problem.",
            "",
        ]
    )
    return "\n".join(lines)


def monotonic_checks() -> tuple[bool, str]:
    catalog = comp_catalog()
    stay = {
        "guest_tier": "loyalty_guest",
        "traveler_segment": "wellness_getaway",
        "stay_value": 2600,
        "estimated_lifetime_value": 12500,
        "guest_value_score": 0.72,
        "repeat_comp_review_risk": 0.08,
        "nightly_rate": 650,
    }
    low_failure = {
        "failure_category": "room_readiness_delay",
        "severity": 2,
        "hotel_responsibility_score": 0.55,
        "reported_in_stay": "true",
        "resolution_delay_minutes": 25,
        "complaint_sentiment_intensity": 0.35,
        "review_risk_score": 0.4,
        "occupancy_pressure": 0.65,
    }
    high_failure = dict(low_failure)
    high_failure.update(
        {
            "severity": 5,
            "hotel_responsibility_score": 0.9,
            "resolution_delay_minutes": 180,
            "complaint_sentiment_intensity": 0.9,
            "review_risk_score": 0.88,
        }
    )
    low = recommend_comp(stay, low_failure, catalog)
    high = recommend_comp(stay, high_failure, catalog)
    passed = high.recovery_need_score >= low.recovery_need_score and high.recommended_tier >= low.recommended_tier
    detail = f"low tier={low.recommended_tier}, score={low.recovery_need_score}; high tier={high.recommended_tier}, score={high.recovery_need_score}"
    return passed, detail


def pricing_sensitivity_checks() -> tuple[bool, str]:
    catalog = comp_catalog()
    stay = {
        "guest_tier": "loyalty_guest",
        "traveler_segment": "coastal_weekend",
        "stay_value": 2800,
        "estimated_lifetime_value": 14000,
        "guest_value_score": 0.74,
        "repeat_comp_review_risk": 0.04,
        "nightly_rate": 700,
    }
    base_failure = {
        "failure_category": "room_assignment_expectation_gap",
        "severity": 4,
        "hotel_responsibility_score": 0.82,
        "reported_in_stay": "true",
        "resolution_delay_minutes": 75,
        "complaint_sentiment_intensity": 0.72,
        "review_risk_score": 0.74,
        "occupancy_pressure": 0.64,
        "public_rate_pressure_index": 0.25,
        "high_demand_rate_flag": "false",
        "upgrade_opportunity_cost_proxy": 70,
        "refund_cost_pressure": 0.95,
        "rate_context_confidence": 0.82,
        "pricing_provenance": "sample_seed_public_rate_shape",
    }
    high_pressure_failure = dict(base_failure)
    high_pressure_failure.update(
        {
            "occupancy_pressure": 0.84,
            "public_rate_pressure_index": 0.92,
            "high_demand_rate_flag": "true",
            "upgrade_opportunity_cost_proxy": 290,
            "refund_cost_pressure": 1.28,
        }
    )
    low = recommend_comp(stay, base_failure, catalog)
    high = recommend_comp(stay, high_pressure_failure, catalog)
    high_has_context = "public_rate_pressure_changed_recovery" in high.reason_codes
    recommendation_changed = low.comp_code != high.comp_code or high.recommended_value != low.recommended_value
    room_comp_constrained = high.comp_code not in {"room_upgrade", "late_checkout"} or high.estimated_internal_cost <= low.estimated_internal_cost
    passed = high_has_context and recommendation_changed and room_comp_constrained
    detail = f"low={low.comp_code}/${low.recommended_value}; high={high.comp_code}/${high.recommended_value}; high reasons={','.join(high.reason_codes)}"
    return passed, detail


def main() -> int:
    ensure_dirs()
    checks: list[dict[str, str]] = []

    source_paths = [
        PMS_RESERVATIONS_PATH,
        CRM_PROFILES_PATH,
        SERVICE_TICKETS_PATH,
        COMP_LEDGER_PATH,
        REVIEWS_SURVEYS_PATH,
        RECOVERY_CASE_MART_PATH,
        COMP_RECOMMENDATIONS_PATH,
        COMP_POLICY_AUDIT_PATH,
        COMP_CATALOG_PATH,
        PROPER_PUBLIC_CONTEXT_PATH,
    ]
    for path in source_paths:
        exists, rows = file_rows(path)
        add_check(checks, f"exists: {path.name}", exists and len(rows) > 0, f"{len(rows)} rows" if exists else "missing")

    demo_catalog_exists, demo_scenarios = file_rows(DEMO_SCENARIO_CATALOG_PATH)
    add_check(
        checks,
        "demo scenario catalog exists",
        demo_catalog_exists and len(demo_scenarios) >= 8,
        f"{len(demo_scenarios)} scenarios" if demo_catalog_exists else "missing",
    )
    demo_report_text = DEMO_SCENARIO_REPORT_PATH.read_text(encoding="utf-8") if DEMO_SCENARIO_REPORT_PATH.exists() else ""
    add_check(
        checks,
        "demo scenario report generated",
        "Recommended comp:" in demo_report_text and "No Proper Hotels data" in demo_report_text,
        "contains recommendations and public-safety note" if demo_report_text else "missing",
    )
    methodology_text = METHODOLOGY_REPORT_PATH.read_text(encoding="utf-8").lower() if METHODOLOGY_REPORT_PATH.exists() else ""
    add_check(
        checks,
        "methodology report exists",
        "policy simulation" in methodology_text or "policy-simulation" in methodology_text,
        "methodology explains policy simulation" if methodology_text else "missing",
    )
    add_check(
        checks,
        "manager demo assets exist",
        MANAGER_APP_SCRIPT_PATH.exists() and MANAGER_DEMO_GUIDE_PATH.exists(),
        "manager app and guide present" if MANAGER_APP_SCRIPT_PATH.exists() and MANAGER_DEMO_GUIDE_PATH.exists() else "missing",
    )

    _, tickets = read_csv_rows(SERVICE_TICKETS_PATH) if SERVICE_TICKETS_PATH.exists() else ([], [])
    _, crm = read_csv_rows(CRM_PROFILES_PATH) if CRM_PROFILES_PATH.exists() else ([], [])
    _, ledger = read_csv_rows(COMP_LEDGER_PATH) if COMP_LEDGER_PATH.exists() else ([], [])
    _, reviews = read_csv_rows(REVIEWS_SURVEYS_PATH) if REVIEWS_SURVEYS_PATH.exists() else ([], [])
    _, mart = read_csv_rows(RECOVERY_CASE_MART_PATH) if RECOVERY_CASE_MART_PATH.exists() else ([], [])
    _, recs = read_csv_rows(COMP_RECOMMENDATIONS_PATH) if COMP_RECOMMENDATIONS_PATH.exists() else ([], [])
    _, audit = read_csv_rows(COMP_POLICY_AUDIT_PATH) if COMP_POLICY_AUDIT_PATH.exists() else ([], [])
    _, impact = read_csv_rows(EXTERNAL_CONTEXT_MODEL_IMPACT_PATH) if EXTERNAL_CONTEXT_MODEL_IMPACT_PATH.exists() else ([], [])

    add_check(
        checks,
        "tickets include missing reservation IDs",
        any(not row.get("pms_reservation_id") for row in tickets),
        f"{sum(1 for row in tickets if not row.get('pms_reservation_id'))} missing",
    )
    add_check(
        checks,
        "tickets include missing severity",
        any(not row.get("severity_raw") for row in tickets),
        f"{sum(1 for row in tickets if not row.get('severity_raw'))} missing",
    )
    add_check(
        checks,
        "CRM includes duplicate profiles",
        any(row.get("duplicate_profile_flag") == "true" for row in crm),
        f"{sum(1 for row in crm if row.get('duplicate_profile_flag') == 'true')} duplicate profiles",
    )
    add_check(
        checks,
        "comp ledger includes orphan records",
        any(not row.get("service_ticket_id") for row in ledger),
        f"{sum(1 for row in ledger if not row.get('service_ticket_id'))} without ticket ID",
    )
    add_check(
        checks,
        "comp ledger has dirty label variants",
        len(set(row.get("comp_action_raw", "") for row in ledger)) >= 10,
        f"{len(set(row.get('comp_action_raw', '') for row in ledger))} raw comp labels",
    )
    add_check(
        checks,
        "reviews are delayed after review date",
        any(row.get("review_loaded_at", "") > row.get("review_date", "") for row in reviews),
        f"{sum(1 for row in reviews if row.get('review_loaded_at', '') > row.get('review_date', ''))} delayed",
    )
    add_check(
        checks,
        "mart preserves match confidence",
        "reservation_match_confidence" in mart[0] if mart else False,
        "reservation_match_confidence present" if mart else "mart missing",
    )
    add_check(
        checks,
        "mart includes low-confidence cases",
        any(0 < as_float(row.get("reservation_match_confidence"), 0) < 0.75 for row in mart),
        f"{sum(1 for row in mart if 0 < as_float(row.get('reservation_match_confidence'), 0) < 0.75)} low-confidence matches",
    )
    add_check(
        checks,
        "recommendations include several comp types",
        len(set(row.get("comp_code", "") for row in recs)) >= 5,
        f"{len(set(row.get('comp_code', '') for row in recs))} comp types",
    )
    refund_count = sum(1 for row in recs if row.get("comp_code") == "partial_room_refund")
    add_check(
        checks,
        "partial refunds are rare but present",
        0 < refund_count <= max(25, int(len(recs) * 0.08)),
        f"{refund_count} partial-refund recommendations",
    )
    late_checkout_count = sum(1 for row in recs if row.get("comp_code") == "late_checkout")
    add_check(
        checks,
        "late checkout appears for eligible recovery",
        late_checkout_count >= 5,
        f"{late_checkout_count} late-checkout recommendations",
    )
    high_occ_rows = [row for row in recs if as_float(row.get("occupancy_pressure"), 0) >= 0.85]
    high_occ_upgrade_count = sum(1 for row in high_occ_rows if row.get("comp_code") == "room_upgrade")
    high_occ_upgrade_rate = high_occ_upgrade_count / len(high_occ_rows) if high_occ_rows else 0
    add_check(
        checks,
        "room upgrades constrained under high occupancy",
        high_occ_upgrade_rate <= 0.35,
        f"{high_occ_upgrade_count}/{len(high_occ_rows)} high-occupancy cases use room upgrades",
    )
    add_check(
        checks,
        "recommendations include manager-review cases",
        any(row.get("manager_review_flag") == "true" for row in recs),
        f"{sum(1 for row in recs if row.get('manager_review_flag') == 'true')} manager-review cases",
    )
    required_audit_classes = {
        "aligned_recovery",
        "under_recovered",
        "over_comped",
        "manager_review_required",
        "data_quality_hold",
    }
    observed_audit_classes = {row.get("audit_class", "") for row in audit}
    missing_audit_classes = sorted(required_audit_classes - observed_audit_classes)
    add_check(
        checks,
        "comp audit includes required classes",
        not missing_audit_classes,
        "all audit classes present" if not missing_audit_classes else f"missing: {missing_audit_classes}",
    )
    monotonic_passed, monotonic_detail = monotonic_checks()
    add_check(checks, "recommendation severity monotonicity", monotonic_passed, monotonic_detail)
    pricing_passed, pricing_detail = pricing_sensitivity_checks()
    add_check(checks, "public pricing changes controlled recommendation", pricing_passed, pricing_detail)

    add_check(
        checks,
        "mart carries public pricing fields",
        "public_rate_pressure_index" in mart[0] and "target_public_rate" in mart[0] if mart else False,
        "public pricing fields present" if mart else "mart missing",
    )
    add_check(
        checks,
        "mart carries external context fields",
        (
            "property_context_confidence" in mart[0]
            and "review_context_confidence" in mart[0]
            and "local_demand_pressure_index" in mart[0]
        )
        if mart
        else False,
        "property, review, and demand context fields present" if mart else "mart missing",
    )
    add_check(
        checks,
        "recommendations carry external context fields",
        (
            "property_context_confidence" in recs[0]
            and "review_context_confidence" in recs[0]
            and "local_demand_pressure_index" in recs[0]
        )
        if recs
        else False,
        "external context fields present" if recs else "recommendations missing",
    )
    required_decision_fields = {
        "internal_cost_low",
        "internal_cost_high",
        "recommendation_stability",
        "decision_confidence",
        "policy_version",
        "recommendation_counterfactuals",
        "recommendation_alternatives_json",
    }
    missing_decision_fields = sorted(required_decision_fields - set(recs[0])) if recs else sorted(required_decision_fields)
    add_check(
        checks,
        "recommendations expose trust and uncertainty fields",
        not missing_decision_fields,
        "all trust fields present" if not missing_decision_fields else f"missing: {missing_decision_fields}",
    )
    invalid_stability = [
        row for row in recs if not 0 <= as_float(row.get("recommendation_stability"), -1) <= 1
    ]
    add_check(
        checks,
        "recommendation stability is bounded",
        not invalid_stability,
        f"{len(recs) - len(invalid_stability)}/{len(recs)} rows bounded",
    )
    high_pressure_recs = [row for row in recs if as_float(row.get("public_rate_pressure_index"), 0) >= 0.72]
    contextual_reason_count = sum(
        1
        for row in high_pressure_recs
        if "public_rate_pressure_changed_recovery" in row.get("recommendation_reason_codes", "")
    )
    add_check(
        checks,
        "recommendations expose pricing context reasons",
        contextual_reason_count > 0,
        f"{contextual_reason_count}/{len(high_pressure_recs)} high-pressure recommendations changed under the rate counterfactual",
    )
    property_reason_count = sum(1 for row in recs if "property_fit_changed_recovery" in row.get("recommendation_reason_codes", ""))
    operational_reason_count = sum(1 for row in recs if "operational_pressure_changed_recovery" in row.get("recommendation_reason_codes", ""))
    add_check(
        checks,
        "property reasons require a changed counterfactual",
        property_reason_count > 0,
        f"{property_reason_count} recommendations changed without property-fit context",
    )
    add_check(
        checks,
        "operational reasons require a changed counterfactual",
        operational_reason_count > 0,
        f"{operational_reason_count} recommendations changed under the availability counterfactual",
    )
    changed_impact = sum(1 for row in impact if row.get("recommendation_changed") == "true")
    add_check(
        checks,
        "external context model impact report has changed decisions",
        changed_impact >= 3,
        f"{changed_impact} controlled comparisons changed recommendation",
    )

    VALIDATION_REPORT_PATH.write_text(render_report(checks), encoding="utf-8")
    failed = [check for check in checks if check["status"] != "PASS"]
    print(f"Wrote comp validation report: {VALIDATION_REPORT_PATH.relative_to(VALIDATION_REPORT_PATH.parents[1])}")
    if failed:
        for check in failed:
            print(f"FAIL: {check['name']} - {check['detail']}")
        return 1
    print(f"Comp model validation passed: {len(checks)} checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
