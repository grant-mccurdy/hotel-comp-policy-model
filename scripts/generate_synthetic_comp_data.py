from __future__ import annotations

import json
import random
from datetime import date, timedelta

from common import (
    BOOKING_SAMPLE_PATH,
    COMP_CATALOG_PATH,
    COMP_RECOMMENDATIONS_PATH,
    RECOVERY_CASE_MART_PATH,
    SAMPLE_DIR,
    SYNTHETIC_GENERATION_MANIFEST_PATH,
    SYNTHETIC_GUEST_STAYS_PATH,
    SYNTHETIC_SERVICE_FAILURES_PATH,
    ensure_dirs,
    read_csv_rows,
    read_json,
    utc_now_iso,
    write_csv,
    write_json,
)
from policy_config import comp_catalog as configured_comp_catalog
from policy_config import load_policy_config
from policy_engine import as_float, clamp, recommend_comp
from scenario_contract import GUEST_TIER_SCORE


RANDOM_SEED = 20260704
TARGET_STAYS = 1600
TARGET_FAILURES = 430


def weighted_choice(rng: random.Random, choices: list[tuple[str, float]]) -> str:
    total = sum(weight for _, weight in choices)
    pick = rng.uniform(0, total)
    cumulative = 0.0
    for value, weight in choices:
        cumulative += weight
        if pick <= cumulative:
            return value
    return choices[-1][0]


def comp_catalog() -> list[dict[str, object]]:
    return configured_comp_catalog()


def guest_tier(rng: random.Random, booking_row: dict[str, str]) -> str:
    repeated = booking_row.get("is_repeated_guest") == "1"
    previous_stays = as_float(booking_row.get("previous_bookings_not_canceled"), 0)
    if repeated or previous_stays > 0:
        return weighted_choice(
            rng,
            [
                ("returning_guest", 0.45),
                ("loyalty_guest", 0.34),
                ("vip_guest", 0.14),
                ("event_or_suite_guest", 0.07),
            ],
        )
    return weighted_choice(
        rng,
        [
            ("new_guest", 0.57),
            ("returning_guest", 0.23),
            ("loyalty_guest", 0.13),
            ("vip_guest", 0.05),
            ("event_or_suite_guest", 0.02),
        ],
    )


def luxury_rate_from_public_row(rng: random.Random, booking_row: dict[str, str], tier: str, month: int) -> int:
    public_adr = max(as_float(booking_row.get("adr"), 95), 45)
    public_component = clamp(public_adr, 55, 350) / 350
    seasonal = 1.13 if month in {5, 6, 7, 8, 9} else 1.0
    tier_multiplier = {
        "new_guest": 1.0,
        "returning_guest": 1.08,
        "loyalty_guest": 1.15,
        "vip_guest": 1.32,
        "event_or_suite_guest": 1.55,
    }[tier]
    rate = (430 + public_component * 590 + rng.gauss(0, 70)) * seasonal * tier_multiplier
    return int(round(clamp(rate, 390, 1850) / 10) * 10)


def generate_stays(booking_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    rng = random.Random(RANDOM_SEED)
    start_date = date(2026, 1, 1)
    stays: list[dict[str, object]] = []
    segments = [
        ("coastal_weekend", 0.25),
        ("wellness_getaway", 0.17),
        ("business_traveler", 0.18),
        ("design_leisure", 0.18),
        ("event_or_wedding", 0.08),
        ("local_staycation", 0.09),
        ("family_beach_trip", 0.05),
    ]
    channels = [
        ("direct", 0.38),
        ("ota", 0.32),
        ("corporate", 0.11),
        ("group_or_event", 0.08),
        ("travel_advisor", 0.11),
    ]

    for index in range(1, TARGET_STAYS + 1):
        booking_row = rng.choice(booking_rows)
        arrival = start_date + timedelta(days=rng.randrange(365))
        tier = guest_tier(rng, booking_row)
        stay_nights = int(clamp(as_float(booking_row.get("stay_nights"), 2), 1, 7))
        nightly_rate = luxury_rate_from_public_row(rng, booking_row, tier, arrival.month)
        stay_value = nightly_rate * stay_nights
        tier_score = GUEST_TIER_SCORE[tier]
        ltv_multiplier = {
            "new_guest": rng.uniform(1.1, 2.2),
            "returning_guest": rng.uniform(2.0, 4.2),
            "loyalty_guest": rng.uniform(3.5, 6.5),
            "vip_guest": rng.uniform(5.0, 9.0),
            "event_or_suite_guest": rng.uniform(4.5, 8.5),
        }[tier]
        occupancy_pressure = round(clamp(rng.betavariate(5, 2) if arrival.month in {5, 6, 7, 8, 9} else rng.betavariate(3, 3), 0, 1), 3)
        special_requests = int(clamp(as_float(booking_row.get("total_of_special_requests"), 0), 0, 5))
        room_mismatch = booking_row.get("room_type_mismatch") == "true"
        guest_value_score = round(
            clamp(tier_score * 0.48 + min(stay_value / 5000, 1) * 0.32 + min(special_requests / 5, 1) * 0.2, 0, 1),
            3,
        )
        review_risk = round(
            clamp(rng.betavariate(1.3, 12) + (0.18 if booking_row.get("previous_cancellations", "0") not in {"0", ""} else 0), 0, 0.95),
            3,
        )

        stays.append(
            {
                "stay_id": f"stay_{index:05d}",
                "guest_id": f"synthetic_guest_{rng.randrange(100000, 999999)}",
                "guest_tier": tier,
                "traveler_segment": weighted_choice(rng, segments),
                "arrival_date": arrival.isoformat(),
                "stay_nights": stay_nights,
                "nightly_rate": nightly_rate,
                "stay_value": stay_value,
                "estimated_lifetime_value": int(round(stay_value * ltv_multiplier / 10) * 10),
                "special_requests_count": special_requests,
                "repeat_guest_flag": str(tier != "new_guest").lower(),
                "reserved_room_type_proxy": booking_row.get("reserved_room_type", "A"),
                "assigned_room_type_proxy": booking_row.get("assigned_room_type", "A"),
                "room_type_mismatch": str(room_mismatch).lower(),
                "occupancy_pressure": occupancy_pressure,
                "guest_value_score": guest_value_score,
                "repeat_comp_review_risk": review_risk,
                "booking_channel_proxy": weighted_choice(rng, channels),
            }
        )
    return stays


FAILURE_CATEGORY_WEIGHTS = [
    ("room_readiness_delay", 0.17),
    ("room_assignment_expectation_gap", 0.1),
    ("housekeeping_miss", 0.13),
    ("maintenance_issue", 0.11),
    ("noise_disruption", 0.08),
    ("billing_or_fee_dispute", 0.09),
    ("f_and_b_service_lapse", 0.12),
    ("rooftop_pool_access_issue", 0.07),
    ("spa_wellness_service_issue", 0.06),
    ("valet_or_parking_delay", 0.07),
]

FAILURE_TEXT = {
    "room_readiness_delay": "Guest waited past arrival time and felt the welcome experience did not match the rate.",
    "room_assignment_expectation_gap": "Guest expected a more desirable room configuration and felt the assignment missed the occasion.",
    "housekeeping_miss": "Guest reported a housekeeping miss that made the room feel below luxury standard.",
    "maintenance_issue": "Guest experienced a room maintenance problem requiring staff response.",
    "noise_disruption": "Guest reported disrupted rest and expected a more serene stay.",
    "billing_or_fee_dispute": "Guest questioned a charge and felt the explanation was not clear enough.",
    "f_and_b_service_lapse": "Guest had a dining or service lapse during an on-property food and beverage experience.",
    "rooftop_pool_access_issue": "Guest expected a signature rooftop/pool experience but encountered access friction.",
    "spa_wellness_service_issue": "Guest reported that a wellness or spa experience did not meet expectations.",
    "valet_or_parking_delay": "Guest experienced valet or parking delay at a high-friction arrival or departure moment.",
}


def generate_failures(stays: list[dict[str, object]]) -> list[dict[str, object]]:
    rng = random.Random(RANDOM_SEED + 1)
    weighted_stays = []
    for stay in stays:
        weight = (
            1
            + as_float(stay["occupancy_pressure"]) * 1.0
            + as_float(stay["special_requests_count"]) * 0.18
            + (0.65 if stay["room_type_mismatch"] == "true" else 0)
            + (0.35 if stay["guest_tier"] in {"vip_guest", "event_or_suite_guest"} else 0)
        )
        weighted_stays.append((stay, weight))

    failures: list[dict[str, object]] = []
    seen_stays: set[str] = set()
    while len(failures) < TARGET_FAILURES:
        stay = weighted_choice_obj(rng, weighted_stays)
        if stay["stay_id"] in seen_stays and rng.random() < 0.85:
            continue
        seen_stays.add(str(stay["stay_id"]))
        category = weighted_choice(rng, FAILURE_CATEGORY_WEIGHTS)
        if stay["room_type_mismatch"] == "true" and rng.random() < 0.38:
            category = "room_assignment_expectation_gap"

        base_severity = {
            "room_readiness_delay": 3,
            "room_assignment_expectation_gap": 3,
            "housekeeping_miss": 3,
            "maintenance_issue": 3,
            "noise_disruption": 2,
            "billing_or_fee_dispute": 2,
            "f_and_b_service_lapse": 2,
            "rooftop_pool_access_issue": 2,
            "spa_wellness_service_issue": 3,
            "valet_or_parking_delay": 2,
        }[category]
        severity = int(clamp(round(base_severity + rng.gauss(0, 1.0) + as_float(stay["occupancy_pressure"]) * 0.65), 1, 5))
        failure_type = "outcome" if category in {"room_readiness_delay", "room_assignment_expectation_gap", "housekeeping_miss", "maintenance_issue"} else "process"
        preventability = weighted_choice(rng, [("low", 0.14), ("medium", 0.38), ("high", 0.48)])
        hotel_responsibility = round(
            clamp(
                {"low": 0.35, "medium": 0.62, "high": 0.86}[preventability]
                + (0.08 if failure_type == "outcome" else 0)
                + rng.gauss(0, 0.08),
                0,
                1,
            ),
            3,
        )
        reported_in_stay = rng.random() < (0.75 if category != "billing_or_fee_dispute" else 0.48)
        resolution_delay = int(clamp(rng.lognormvariate(3.25, 0.75), 5, 720))
        sentiment = round(clamp(severity / 5 * 0.55 + rng.betavariate(2, 4) * 0.45, 0, 1), 3)
        review_risk = round(
            clamp(
                severity / 5 * 0.36
                + as_float(stay["guest_value_score"]) * 0.21
                + sentiment * 0.26
                + hotel_responsibility * 0.12
                + (0.08 if not reported_in_stay else 0),
                0,
                1,
            ),
            3,
        )
        failures.append(
            {
                "failure_id": f"failure_{len(failures) + 1:05d}",
                "stay_id": stay["stay_id"],
                "failure_category": category,
                "failure_type": failure_type,
                "severity": severity,
                "preventability": preventability,
                "hotel_responsibility_score": hotel_responsibility,
                "reported_in_stay": str(reported_in_stay).lower(),
                "resolution_delay_minutes": resolution_delay,
                "complaint_sentiment_intensity": sentiment,
                "review_risk_score": review_risk,
                "brand_impact_context": weighted_choice(
                    rng,
                    [
                        ("standard_guest_recovery", 0.54),
                        ("high_visibility_review_risk", 0.22),
                        ("special_occasion", 0.14),
                        ("event_or_group_relationship", 0.06),
                        ("travel_advisor_relationship", 0.04),
                    ],
                ),
                "occupancy_pressure": stay["occupancy_pressure"],
                "ops_capacity_constraint": weighted_choice(
                    rng,
                    [
                        ("none", 0.45),
                        ("housekeeping", 0.18),
                        ("maintenance", 0.13),
                        ("front_desk", 0.14),
                        ("food_beverage", 0.1),
                    ],
                ),
                "guest_complaint_text": FAILURE_TEXT[category],
            }
        )
    return failures


def weighted_choice_obj(rng: random.Random, choices: list[tuple[dict[str, object], float]]) -> dict[str, object]:
    total = sum(weight for _, weight in choices)
    pick = rng.uniform(0, total)
    cumulative = 0.0
    for value, weight in choices:
        cumulative += weight
        if pick <= cumulative:
            return value
    return choices[-1][0]


def generate_recommendations(
    stays: list[dict[str, object]],
    failures: list[dict[str, object]],
    catalog: list[dict[str, object]],
) -> list[dict[str, object]]:
    stays_by_id = {str(stay["stay_id"]): stay for stay in stays}
    recommendations: list[dict[str, object]] = []
    for failure in failures:
        stay = stays_by_id[str(failure["stay_id"])]
        recommendation = recommend_comp(stay, failure, catalog)
        recommendations.append(
            {
                "recommendation_id": f"rec_{len(recommendations) + 1:05d}",
                "stay_id": stay["stay_id"],
                "failure_id": failure["failure_id"],
                "guest_tier": stay["guest_tier"],
                "traveler_segment": stay["traveler_segment"],
                "stay_value": stay["stay_value"],
                "estimated_lifetime_value": stay["estimated_lifetime_value"],
                "failure_category": failure["failure_category"],
                "failure_type": failure["failure_type"],
                "severity": failure["severity"],
                "hotel_responsibility_score": failure["hotel_responsibility_score"],
                "reported_in_stay": failure["reported_in_stay"],
                "comp_code": recommendation.comp_code,
                "comp_label": recommendation.comp_label,
                "recommended_comp_value": recommendation.recommended_value,
                "estimated_internal_cost": recommendation.estimated_internal_cost,
                "internal_cost_low": recommendation.internal_cost_low,
                "internal_cost_high": recommendation.internal_cost_high,
                "recommended_tier": recommendation.recommended_tier,
                "recovery_need_score": recommendation.recovery_need_score,
                "profit_leakage_risk": recommendation.profit_leakage_risk,
                "review_risk_score": recommendation.review_risk_score,
                "brand_impact_risk": recommendation.brand_impact_risk,
                "expected_recovery_value": recommendation.expected_recovery_value,
                "manager_review_flag": str(recommendation.manager_review_flag).lower(),
                "recommendation_stability": recommendation.recommendation_stability,
                "decision_confidence": recommendation.decision_confidence,
                "policy_version": recommendation.policy_version,
                "recommendation_reason_codes": ";".join(recommendation.reason_codes),
                "recommendation_counterfactuals": " | ".join(recommendation.counterfactuals),
                "recommendation_alternatives_json": json.dumps(recommendation.alternatives, sort_keys=True),
                "recommendation_score_components_json": json.dumps(recommendation.score_components, sort_keys=True),
                "recommendation_assumptions": " | ".join(recommendation.assumptions),
                "recommendation_explanation": recommendation.explanation,
            }
        )
    return recommendations


def generate_recommendations_from_mart(
    mart_rows: list[dict[str, str]],
    catalog: list[dict[str, object]],
) -> list[dict[str, object]]:
    recommendations: list[dict[str, object]] = []
    for row in mart_rows:
        recommendation = recommend_comp(row, row, catalog)
        actual_face_value = int(as_float(row.get("actual_comp_face_value"), 0))
        recommendations.append(
            {
                "recommendation_id": f"rec_{len(recommendations) + 1:05d}",
                "recovery_case_id": row["recovery_case_id"],
                "service_ticket_id": row["service_ticket_id"],
                "pms_reservation_id": row["pms_reservation_id"],
                "guest_tier": row["guest_tier"],
                "traveler_segment": row["traveler_segment"],
                "stay_value": row["stay_value"],
                "estimated_lifetime_value": row["estimated_lifetime_value"],
                "reservation_match_confidence": row["reservation_match_confidence"],
                "crm_match_confidence": row["crm_match_confidence"],
                "data_quality_flags": row["data_quality_flags"],
                "failure_category": row["failure_category"],
                "failure_type": row["failure_type"],
                "severity": row["severity"],
                "hotel_responsibility_score": row["hotel_responsibility_score"],
                "reported_in_stay": row["reported_in_stay"],
                "occupancy_pressure": row["occupancy_pressure"],
                "target_property_name": row.get("target_property_name", ""),
                "has_rooftop_f_and_b": row.get("has_rooftop_f_and_b", "false"),
                "has_lobby_lounge": row.get("has_lobby_lounge", "false"),
                "has_spa_wellness": row.get("has_spa_wellness", "false"),
                "has_pool_or_rooftop": row.get("has_pool_or_rooftop", "false"),
                "has_parking_or_fee_recovery_context": row.get("has_parking_or_fee_recovery_context", "false"),
                "property_context_confidence": row.get("property_context_confidence", "0"),
                "property_context_provenance": row.get("property_context_provenance", "missing_public_property_context"),
                "public_review_risk_prior": row.get("public_review_risk_prior", "0.55"),
                "review_context_confidence": row.get("review_context_confidence", "0"),
                "review_context_provenance": row.get("review_context_provenance", "missing_public_review_context"),
                "event_pressure_index": row.get("event_pressure_index", "0"),
                "weather_disruption_index": row.get("weather_disruption_index", "0"),
                "local_demand_pressure_index": row.get("local_demand_pressure_index", "0.35"),
                "high_local_demand_flag": row.get("high_local_demand_flag", "false"),
                "demand_context_confidence": row.get("demand_context_confidence", "0"),
                "demand_context_provenance": row.get("demand_context_provenance", "missing_local_demand_context"),
                "public_rate_pressure_index": row.get("public_rate_pressure_index", "0.5"),
                "high_demand_rate_flag": row.get("high_demand_rate_flag", "false"),
                "target_public_rate": row.get("target_public_rate", "0"),
                "comp_set_median_rate": row.get("comp_set_median_rate", "0"),
                "proper_vs_comp_set_index": row.get("proper_vs_comp_set_index", "1"),
                "upgrade_opportunity_cost_proxy": row.get("upgrade_opportunity_cost_proxy", "0"),
                "refund_cost_pressure": row.get("refund_cost_pressure", "1"),
                "rate_context_confidence": row.get("rate_context_confidence", "0"),
                "pricing_provenance": row.get("pricing_provenance", "missing_public_pricing_context"),
                "repeat_comp_review_risk": row.get("repeat_comp_review_risk", row.get("repeat_comp_abuse_risk", "0")),
                "room_type_mismatch": row["room_type_mismatch"],
                "actual_comp_codes_normalized": row["actual_comp_codes_normalized"],
                "actual_comp_face_value": actual_face_value,
                "actual_comp_internal_cost": row["actual_comp_internal_cost"],
                "comp_code": recommendation.comp_code,
                "comp_label": recommendation.comp_label,
                "recommended_comp_value": recommendation.recommended_value,
                "estimated_internal_cost": recommendation.estimated_internal_cost,
                "internal_cost_low": recommendation.internal_cost_low,
                "internal_cost_high": recommendation.internal_cost_high,
                "recommended_minus_actual_value": recommendation.recommended_value - actual_face_value,
                "recommended_tier": recommendation.recommended_tier,
                "recovery_need_score": recommendation.recovery_need_score,
                "profit_leakage_risk": recommendation.profit_leakage_risk,
                "review_risk_score": recommendation.review_risk_score,
                "brand_impact_risk": recommendation.brand_impact_risk,
                "expected_recovery_value": recommendation.expected_recovery_value,
                "manager_review_flag": str(recommendation.manager_review_flag).lower(),
                "recommendation_stability": recommendation.recommendation_stability,
                "decision_confidence": recommendation.decision_confidence,
                "policy_version": recommendation.policy_version,
                "recommendation_reason_codes": ";".join(recommendation.reason_codes),
                "recommendation_counterfactuals": " | ".join(recommendation.counterfactuals),
                "recommendation_alternatives_json": json.dumps(recommendation.alternatives, sort_keys=True),
                "recommendation_score_components_json": json.dumps(recommendation.score_components, sort_keys=True),
                "recommendation_assumptions": " | ".join(recommendation.assumptions),
                "recommendation_explanation": recommendation.explanation,
            }
        )
    return recommendations


def write_outputs(
    stays: list[dict[str, object]],
    failures: list[dict[str, object]],
    catalog: list[dict[str, object]],
    recommendations: list[dict[str, object]],
) -> None:
    write_csv(COMP_CATALOG_PATH, list(catalog[0].keys()), catalog)
    write_csv(SYNTHETIC_GUEST_STAYS_PATH, list(stays[0].keys()), stays)
    write_csv(SYNTHETIC_SERVICE_FAILURES_PATH, list(failures[0].keys()), failures)
    write_csv(COMP_RECOMMENDATIONS_PATH, list(recommendations[0].keys()), recommendations)
    write_json(
        SYNTHETIC_GENERATION_MANIFEST_PATH,
        {
            "generated_at": utc_now_iso(),
            "random_seed": RANDOM_SEED,
            "guest_stays_path": "data/sample/synthetic_guest_stays.csv",
            "service_failures_path": "data/sample/synthetic_service_failures.csv",
            "comp_catalog_path": "data/sample/comp_catalog.csv",
            "comp_recommendations_path": "data/sample/comp_recommendations.csv",
            "guest_stays": len(stays),
            "service_failures": len(failures),
            "recommendations": len(recommendations),
            "public_safety_note": "All guest, failure, and compensation records are synthetic. No Proper Hotels or internal hotel data is used.",
            "calibration_note": "Public booking data informs distribution shape for stay context; luxury rates, failures, and compensation labels are synthetic policy simulation.",
        },
    )


def main() -> int:
    ensure_dirs()
    if not RECOVERY_CASE_MART_PATH.exists():
        print("Missing recovery-case mart. Run scripts/build_recovery_case_mart.py first.")
        return 1
    catalog = comp_catalog()
    _, mart_rows = read_csv_rows(RECOVERY_CASE_MART_PATH)
    recommendations = generate_recommendations_from_mart(mart_rows, catalog)
    write_csv(COMP_CATALOG_PATH, list(catalog[0].keys()), catalog)
    write_csv(COMP_RECOMMENDATIONS_PATH, list(recommendations[0].keys()), recommendations)
    manifest = read_json(SYNTHETIC_GENERATION_MANIFEST_PATH) if SYNTHETIC_GENERATION_MANIFEST_PATH.exists() else {}
    manifest.update(
        {
            "generated_at": utc_now_iso(),
            "policy_version": load_policy_config()["policy_version"],
            "recommendation_count": len(recommendations),
            "recommendation_contract": "data/contracts/comp_recommendation.schema.json",
            "cost_boundary": "low/mid/high internal-cost values are policy assumptions, not observed property margins",
            "public_safety_note": "All operating rows and historical comp actions are synthetic. Public property anchors are recorded separately with provenance.",
        }
    )
    write_json(SYNTHETIC_GENERATION_MANIFEST_PATH, manifest)
    print(f"Wrote comp recommendations: {COMP_RECOMMENDATIONS_PATH.relative_to(COMP_RECOMMENDATIONS_PATH.parents[1])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
