from __future__ import annotations

from common import (
    EXTERNAL_CONTEXT_MODEL_IMPACT_PATH,
    REPORT_DIR,
    ensure_dirs,
    write_csv,
)
from generate_synthetic_comp_data import comp_catalog
from policy_engine import recommend_comp
from recommend_scenario import money


MODEL_IMPACT_REPORT = REPORT_DIR / "external-context-model-impact.md"

FIELDNAMES = [
    "comparison_id",
    "decision_signal",
    "control_comp_code",
    "context_comp_code",
    "control_recommended_value",
    "context_recommended_value",
    "recommended_value_delta",
    "control_internal_cost",
    "context_internal_cost",
    "internal_cost_delta",
    "control_tier",
    "context_tier",
    "recommendation_changed",
    "context_reason_codes",
    "interpretation",
]


TARGET_PROPERTY_CONTEXT = {
    "has_rooftop_f_and_b": "true",
    "has_lobby_lounge": "true",
    "has_spa_wellness": "true",
    "has_pool_or_rooftop": "true",
    "has_parking_or_fee_recovery_context": "true",
    "property_context_confidence": 0.88,
    "rooftop_f_and_b_fit_modifier": 1.22,
    "spa_wellness_fit_modifier": 1.18,
    "lobby_lounge_fit_modifier": 1.12,
    "parking_fee_fit_modifier": 1.04,
    "late_checkout_fit_modifier": 1.04,
    "room_upgrade_fit_modifier": 1.08,
}

NEUTRAL_PROPERTY_CONTEXT = {
    "has_rooftop_f_and_b": "false",
    "has_lobby_lounge": "false",
    "has_spa_wellness": "false",
    "has_pool_or_rooftop": "false",
    "has_parking_or_fee_recovery_context": "false",
    "property_context_confidence": 0.0,
    "rooftop_f_and_b_fit_modifier": 1.0,
    "spa_wellness_fit_modifier": 1.0,
    "lobby_lounge_fit_modifier": 1.0,
    "parking_fee_fit_modifier": 1.0,
    "late_checkout_fit_modifier": 1.0,
    "room_upgrade_fit_modifier": 1.0,
}


def base_stay(**overrides: object) -> dict[str, object]:
    stay = {
        "guest_tier": "loyalty_guest",
        "traveler_segment": "coastal_weekend",
        "stay_value": 2800,
        "estimated_lifetime_value": 14000,
        "guest_value_score": 0.74,
        "repeat_comp_review_risk": 0.04,
        "nightly_rate": 700,
    }
    stay.update(overrides)
    return stay


def base_failure(**overrides: object) -> dict[str, object]:
    failure = {
        "failure_category": "room_readiness_delay",
        "failure_type": "outcome",
        "severity": 4,
        "hotel_responsibility_score": 0.82,
        "reported_in_stay": "true",
        "resolution_delay_minutes": 90,
        "complaint_sentiment_intensity": 0.72,
        "review_risk_score": 0.68,
        "occupancy_pressure": 0.62,
        "public_rate_pressure_index": 0.35,
        "high_demand_rate_flag": "false",
        "upgrade_opportunity_cost_proxy": 70,
        "refund_cost_pressure": 0.95,
        "rate_context_confidence": 0.0,
        "review_context_confidence": 0.0,
        "local_demand_pressure_index": 0.35,
        "high_local_demand_flag": "false",
        "demand_context_confidence": 0.0,
        **NEUTRAL_PROPERTY_CONTEXT,
    }
    failure.update(overrides)
    return failure


def compare(
    comparison_id: str,
    decision_signal: str,
    control_failure: dict[str, object],
    context_failure: dict[str, object],
    interpretation: str,
    stay: dict[str, object] | None = None,
) -> dict[str, object]:
    catalog = comp_catalog()
    stay_inputs = stay or base_stay()
    control = recommend_comp(stay_inputs, control_failure, catalog)
    context = recommend_comp(stay_inputs, context_failure, catalog)
    changed = (
        control.comp_code != context.comp_code
        or control.recommended_value != context.recommended_value
        or control.recommended_tier != context.recommended_tier
    )
    return {
        "comparison_id": comparison_id,
        "decision_signal": decision_signal,
        "control_comp_code": control.comp_code,
        "context_comp_code": context.comp_code,
        "control_recommended_value": control.recommended_value,
        "context_recommended_value": context.recommended_value,
        "recommended_value_delta": context.recommended_value - control.recommended_value,
        "control_internal_cost": control.estimated_internal_cost,
        "context_internal_cost": context.estimated_internal_cost,
        "internal_cost_delta": context.estimated_internal_cost - control.estimated_internal_cost,
        "control_tier": control.recommended_tier,
        "context_tier": context.recommended_tier,
        "recommendation_changed": str(changed).lower(),
        "context_reason_codes": ";".join(context.reason_codes),
        "interpretation": interpretation,
    }


def build_rows() -> list[dict[str, object]]:
    return [
        compare(
            "impact_001",
            "public_rate_pressure",
            base_failure(
                failure_category="room_assignment_expectation_gap",
                severity=4,
                hotel_responsibility_score=0.82,
                review_risk_score=0.74,
                occupancy_pressure=0.64,
                public_rate_pressure_index=0.25,
                upgrade_opportunity_cost_proxy=70,
            ),
            base_failure(
                failure_category="room_assignment_expectation_gap",
                severity=4,
                hotel_responsibility_score=0.82,
                review_risk_score=0.74,
                occupancy_pressure=0.84,
                public_rate_pressure_index=0.92,
                high_demand_rate_flag="true",
                upgrade_opportunity_cost_proxy=290,
                refund_cost_pressure=1.28,
                rate_context_confidence=0.82,
                **TARGET_PROPERTY_CONTEXT,
            ),
            "High public rate pressure should protect room inventory value and can shift recovery away from upgrades.",
        ),
        compare(
            "impact_002",
            "property_fit",
            base_failure(
                failure_category="room_readiness_delay",
                severity=2,
                hotel_responsibility_score=0.6,
                review_risk_score=0.35,
                occupancy_pressure=0.45,
            ),
            base_failure(
                failure_category="room_readiness_delay",
                severity=2,
                hotel_responsibility_score=0.6,
                review_risk_score=0.35,
                occupancy_pressure=0.45,
                **TARGET_PROPERTY_CONTEXT,
            ),
            "Public property context should strengthen room/experience gestures when demand pressure is low enough to make them operationally plausible.",
        ),
        compare(
            "impact_003",
            "review_risk_prior",
            base_failure(
                failure_category="housekeeping_miss",
                severity=2,
                hotel_responsibility_score=0.72,
                review_risk_score=0.25,
                complaint_sentiment_intensity=0.35,
                occupancy_pressure=0.45,
            ),
            base_failure(
                failure_category="housekeeping_miss",
                severity=2,
                hotel_responsibility_score=0.72,
                review_risk_score=0.86,
                complaint_sentiment_intensity=0.86,
                review_context_confidence=0.4,
                occupancy_pressure=0.45,
                **TARGET_PROPERTY_CONTEXT,
            ),
            "Issue categories with higher reputation sensitivity should increase recovery strength.",
        ),
        compare(
            "impact_004",
            "local_demand_pressure",
            base_failure(
                failure_category="room_readiness_delay",
                severity=4,
                hotel_responsibility_score=0.86,
                review_risk_score=0.66,
                occupancy_pressure=0.58,
            ),
            base_failure(
                failure_category="room_readiness_delay",
                severity=4,
                hotel_responsibility_score=0.86,
                review_risk_score=0.66,
                occupancy_pressure=0.58,
                local_demand_pressure_index=0.86,
                high_local_demand_flag="true",
                demand_context_confidence=0.32,
                **TARGET_PROPERTY_CONTEXT,
            ),
            "External demand pressure should make room-based gestures more expensive and strengthen lower-margin alternatives.",
        ),
        compare(
            "impact_005",
            "spa_wellness_fit",
            base_failure(
                failure_category="spa_wellness_service_issue",
                severity=3,
                hotel_responsibility_score=0.74,
                review_risk_score=0.6,
                occupancy_pressure=0.52,
            ),
            base_failure(
                failure_category="spa_wellness_service_issue",
                severity=3,
                hotel_responsibility_score=0.74,
                review_risk_score=0.6,
                occupancy_pressure=0.52,
                **TARGET_PROPERTY_CONTEXT,
            ),
            "A property with strong wellness context should make spa/wellness recovery more defensible.",
            stay=base_stay(traveler_segment="wellness_getaway"),
        ),
    ]


def render_report(rows: list[dict[str, object]]) -> str:
    changed = [row for row in rows if row["recommendation_changed"] == "true"]
    lines = [
        "# External Context Model Impact",
        "",
        "This report tests whether public context changes recommendations in controlled scenarios.",
        "",
        "The goal is bounded decision usefulness: public context should influence recommendations when it maps to comp fit, opportunity cost, reputation risk, or local demand pressure.",
        "",
        f"- Comparisons tested: `{len(rows)}`",
        f"- Recommendations changed by context: `{len(changed)}`",
        "",
        "| Signal | Control recommendation | Context recommendation | Value delta | Interpretation |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            "| "
            f"{row['decision_signal']} | "
            f"{row['control_comp_code']} ({money(row['control_recommended_value'])}) | "
            f"{row['context_comp_code']} ({money(row['context_recommended_value'])}) | "
            f"{money(row['recommended_value_delta'])} | "
            f"{row['interpretation']} |"
        )
    lines.extend(
        [
            "",
            "## Decision Standard",
            "",
            "- Public context should never replace internal hotel data.",
            "- Public context should be visible in reason codes when it affects a recommendation.",
            "- If context is weak or sample-seed only, confidence should be lower and the model should remain conservative.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    ensure_dirs()
    rows = build_rows()
    write_csv(EXTERNAL_CONTEXT_MODEL_IMPACT_PATH, FIELDNAMES, rows)
    MODEL_IMPACT_REPORT.write_text(render_report(rows), encoding="utf-8")
    print(f"Wrote external context model impact: {EXTERNAL_CONTEXT_MODEL_IMPACT_PATH.relative_to(EXTERNAL_CONTEXT_MODEL_IMPACT_PATH.parents[1])}")
    print(f"Wrote external context impact report: {MODEL_IMPACT_REPORT.relative_to(MODEL_IMPACT_REPORT.parents[1])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
