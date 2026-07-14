from __future__ import annotations

import json
import math
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

try:  # Package imports for the Worker runtime.
    from .common import (
        POLICY_CASE_COMPARISON_PATH,
        POLICY_COMPARISON_MANIFEST_PATH,
        POLICY_DECISION_SUMMARY_PATH,
        POLICY_SEGMENT_DIAGNOSTICS_PATH,
        POLICY_UNCERTAINTY_SUMMARY_PATH,
        RECOVERY_CASE_MART_PATH,
        REPORT_DIR,
        ensure_dirs,
        read_csv_rows,
        utc_now_iso,
        write_csv,
        write_json,
    )
    from .policy_config import comp_catalog, load_policy_config, load_policy_scenarios
    from .policy_engine import (
        as_bool,
        as_float,
        clamp,
        comp_value_for_tier,
        recommend_comp,
        recovery_need_score,
        score_to_tier,
    )
    from .scenario_contract import ScenarioInput
except ImportError:  # Direct script and existing local-test compatibility.
    from common import (
        POLICY_CASE_COMPARISON_PATH,
        POLICY_COMPARISON_MANIFEST_PATH,
        POLICY_DECISION_SUMMARY_PATH,
        POLICY_SEGMENT_DIAGNOSTICS_PATH,
        POLICY_UNCERTAINTY_SUMMARY_PATH,
        RECOVERY_CASE_MART_PATH,
        REPORT_DIR,
        ensure_dirs,
        read_csv_rows,
        utc_now_iso,
        write_csv,
        write_json,
    )
    from policy_config import comp_catalog, load_policy_config, load_policy_scenarios
    from policy_engine import (
        as_bool,
        as_float,
        clamp,
        comp_value_for_tier,
        recommend_comp,
        recovery_need_score,
        score_to_tier,
    )
    from scenario_contract import ScenarioInput


REPORT_PATH = REPORT_DIR / "policy-decision-analysis.md"

PROPERTY_ALIGNED_CODES = {
    "amenity_gesture",
    "late_checkout",
    "parking_fee_waiver",
    "lobby_lounge_credit",
    "rooftop_f_and_b_credit",
    "spa_wellness_credit",
    "room_upgrade",
}
ROOM_BASED_CODES = {"late_checkout", "room_upgrade"}
DIRECT_REFUND_CODES = {"partial_room_refund"}


def available_comp_codes(row: dict[str, Any]) -> set[str] | None:
    raw = row.get("available_comp_codes")
    if raw in (None, ""):
        return None
    if isinstance(raw, str):
        values = [value.strip() for value in raw.replace(";", ",").split(",")]
    else:
        values = [str(value).strip() for value in raw]
    return {value for value in values if value}


def truth(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def percentile(values: list[float], probability: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def triangular_quantile(low: float, mode: float, high: float, probability: float) -> float:
    """Return a triangular-distribution quantile without consuming policy-specific RNG state."""
    low, mode, high = min(low, mode, high), mode, max(low, mode, high)
    mode = clamp(mode, low, high)
    probability = clamp(probability, 0, 1)
    if high <= low:
        return low
    mode_probability = (mode - low) / (high - low)
    if probability < mode_probability:
        return low + math.sqrt(probability * (high - low) * (mode - low))
    return high - math.sqrt((1 - probability) * (high - low) * (high - mode))


def money(value: float | int) -> str:
    return f"${float(value):,.0f}"


def raw_issue_fit(comp: dict[str, Any], row: dict[str, str], policy: dict[str, Any]) -> float:
    fit_map = policy["comp_fit"].get(str(comp["comp_code"]), {})
    category = str(row.get("failure_category", ""))
    guest_tier = str(row.get("guest_tier", ""))
    return as_float(fit_map.get(category, fit_map.get(guest_tier, fit_map.get("default", 0.5))), 0.5)


def data_hold_case(row: dict[str, str], evaluation: dict[str, Any]) -> bool:
    return (
        as_float(row.get("reservation_match_confidence"), 0) < as_float(evaluation["reservation_match_minimum"])
        or as_float(row.get("crm_match_confidence"), 0) < as_float(evaluation["crm_match_minimum"])
    )


def high_risk_case(row: dict[str, str], tier: int, evaluation: dict[str, Any]) -> bool:
    return tier >= int(evaluation["high_risk_tier_minimum"]) or (
        as_float(row.get("severity"), 0) >= as_float(evaluation["high_risk_severity_minimum"])
        and as_float(row.get("hotel_responsibility_score"), 0)
        >= as_float(evaluation["high_risk_responsibility_minimum"])
    )


def operational_infeasible(
    codes: list[str],
    row: dict[str, str],
    evaluation: dict[str, Any],
    occupancy_multiplier: float = 1.0,
) -> bool:
    if not codes:
        return False
    return not as_bool(row.get("reported_in_stay")) and any(code in ROOM_BASED_CODES for code in codes)


def operational_pressure_review(
    codes: list[str],
    row: dict[str, Any],
    evaluation: dict[str, Any],
    occupancy_multiplier: float = 1.0,
) -> bool:
    occupancy = clamp(as_float(row.get("occupancy_pressure"), 0) * occupancy_multiplier, 0, 1)
    high_demand = truth(row.get("high_demand_rate_flag")) or truth(row.get("high_local_demand_flag"))
    return any(code in ROOM_BASED_CODES for code in codes) and (
        occupancy >= as_float(evaluation["high_occupancy_threshold"]) or high_demand
    )


def candidate_metrics(comp: dict[str, Any], row: dict[str, str], tier: int, policy: dict[str, Any]) -> dict[str, Any]:
    value = comp_value_for_tier(comp, tier, row)
    midpoint_rate = as_float(comp.get("estimated_internal_cost_rate"), 0.5)
    low_rate = as_float(comp.get("internal_cost_rate_low"), midpoint_rate)
    high_rate = as_float(comp.get("internal_cost_rate_high"), midpoint_rate)
    fit = raw_issue_fit(comp, row, policy)
    perceived_value = value * as_float(comp.get("guest_perceived_value_multiplier"), 1)
    return {
        "comp_code": str(comp["comp_code"]),
        "comp_label": str(comp["comp_label"]),
        "recommended_value": value,
        "internal_cost_low": round(value * min(low_rate, midpoint_rate, high_rate)),
        "internal_cost_mid": round(value * midpoint_rate),
        "internal_cost_high": round(value * max(low_rate, midpoint_rate, high_rate)),
        "issue_fit_score": fit,
        "perceived_value": perceived_value,
        "min_tier_fit": int(as_float(comp.get("min_tier_fit"), 1)),
        "max_tier_fit": int(as_float(comp.get("max_tier_fit"), 5)),
    }


def feasible_candidates(
    row: dict[str, str],
    tier: int,
    catalog: list[dict[str, Any]],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    candidates = []
    available = available_comp_codes(row)
    for comp in catalog:
        metrics = candidate_metrics(comp, row, tier, policy)
        if available is not None and metrics["comp_code"] not in available:
            continue
        if tier < metrics["min_tier_fit"]:
            continue
        if not as_bool(row.get("reported_in_stay")) and metrics["comp_code"] in ROOM_BASED_CODES:
            continue
        candidates.append(metrics)
    return candidates


def rank_simple_strategy(
    strategy: str,
    row: dict[str, str],
    tier: int,
    catalog: list[dict[str, Any]],
    policy: dict[str, Any],
    evaluation: dict[str, Any],
    sensitivity_low: float = 0.8,
) -> list[dict[str, Any]]:
    candidates = feasible_candidates(row, tier, catalog, policy)
    if not candidates:
        candidates = [candidate_metrics(next(comp for comp in catalog if comp["comp_code"] == "manager_note"), row, tier, policy)]

    if strategy == "highest_issue_fit":
        return sorted(
            candidates,
            key=lambda item: (-item["issue_fit_score"], -item["perceived_value"], item["internal_cost_mid"]),
        )
    if strategy == "lowest_cost_adequate":
        robust_fit_minimum = as_float(evaluation["adequate_fit_minimum"]) / max(sensitivity_low, 0.01)
        adequate = [
            item
            for item in candidates
            if item["issue_fit_score"] >= robust_fit_minimum
            and item["max_tier_fit"] >= tier
        ]
        if not adequate:
            adequate = [
                item
                for item in candidates
                if item["issue_fit_score"] >= as_float(evaluation["adequate_fit_minimum"])
                and item["max_tier_fit"] >= tier
            ] or candidates
        non_refunds = [item for item in adequate if item["comp_code"] not in DIRECT_REFUND_CODES]
        if non_refunds:
            adequate = non_refunds
        return sorted(
            adequate,
            key=lambda item: (item["internal_cost_mid"], -item["issue_fit_score"], -item["perceived_value"]),
        )
    if strategy == "highest_perceived_recovery":
        return sorted(
            candidates,
            key=lambda item: (
                -(item["issue_fit_score"] * item["perceived_value"]),
                -item["issue_fit_score"],
                item["internal_cost_mid"],
            ),
        )
    raise ValueError(f"Unknown simple policy strategy: {strategy}")


def select_simple_strategy(
    strategy: str,
    row: dict[str, str],
    tier: int,
    catalog: list[dict[str, Any]],
    policy: dict[str, Any],
    evaluation: dict[str, Any],
    sensitivity_low: float = 0.8,
) -> dict[str, Any]:
    return rank_simple_strategy(strategy, row, tier, catalog, policy, evaluation, sensitivity_low)[0]


def recommend_policy_strategy(
    mapping: dict[str, Any],
    policy_id: str,
    policy: dict[str, Any] | None = None,
    scenario_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    policy = policy or load_policy_config()
    scenario_config = scenario_config or load_policy_scenarios()
    policy_spec = next(
        (row for row in scenario_config["policies"] if row["policy_id"] == policy_id),
        None,
    )
    if policy_spec is None or not policy_spec["selection_eligible"]:
        raise ValueError(f"Policy is not available for manager scenarios: {policy_id}")

    scenario = ScenarioInput.from_mapping(mapping)
    stay, failure = scenario.to_engine_inputs()
    row = {**mapping, **stay, **failure}
    selected_policy = {**policy, "policy_id": policy_id}
    catalog = comp_catalog(selected_policy)
    catalog_by_code = {str(comp["comp_code"]): comp for comp in catalog}
    need = recovery_need_score(row, row, selected_policy)
    tier = score_to_tier(need, selected_policy)
    strategy = str(policy_spec["strategy"])

    if strategy == "context_aware_policy_engine":
        recommendation = recommend_comp(row, row, catalog, selected_policy)
        selected = intelligent_selection(row, tier, catalog_by_code, selected_policy)
        alternatives = recommendation.alternatives
    else:
        ranked = rank_simple_strategy(
            strategy,
            row,
            tier,
            catalog,
            selected_policy,
            scenario_config["evaluation"],
            as_float(scenario_config["probabilistic_sensitivity"]["multiplier_low"], 0.8),
        )
        selected = ranked[0]
        if len(ranked) < 3:
            fallback = sorted(
                (
                    item
                    for item in feasible_candidates(row, tier, catalog, selected_policy)
                    if item["comp_code"] != selected["comp_code"]
                ),
                key=lambda item: (
                    -item["issue_fit_score"],
                    item["internal_cost_mid"],
                    -item["perceived_value"],
                ),
            )
            ranked = [selected, *fallback]
        alternatives = [
            {
                "comp_code": item["comp_code"],
                "comp_label": item["comp_label"],
                "guest_facing_value": item["recommended_value"],
                "internal_cost_low": item["internal_cost_low"],
                "internal_cost_expected": item["internal_cost_mid"],
                "internal_cost_high": item["internal_cost_high"],
            }
            for item in ranked[1:3]
        ]

    evaluation = scenario_config["evaluation"]
    sensitivity_low = as_float(scenario_config["probabilistic_sensitivity"]["multiplier_low"])
    robust_fit_minimum = as_float(evaluation["adequate_fit_minimum"]) / max(sensitivity_low, 0.01)
    codes = [str(selected["comp_code"])]
    fit_uncertainty_review = as_float(selected["issue_fit_score"]) < robust_fit_minimum
    pressure_review = operational_pressure_review(codes, row, evaluation)
    review_config = selected_policy["manager_review"]
    manager_review = (
        pressure_review
        or fit_uncertainty_review
        or tier >= int(review_config["minimum_tier"])
        or as_float(selected["recommended_value"]) >= as_float(review_config["minimum_guest_facing_value"])
        or as_float(row.get("repeat_comp_review_risk"), 0)
        >= as_float(review_config["repeat_comp_review_threshold"])
    )
    return {
        **selected,
        "policy_id": policy_id,
        "policy_label": policy_spec["label"],
        "reference_recovery_need_score": need,
        "reference_recovery_tier": tier,
        "manager_review_required": manager_review,
        "fit_uncertainty_review": fit_uncertainty_review,
        "operational_pressure_review": pressure_review,
        "alternatives": alternatives,
    }


def baseline_selection(
    row: dict[str, str],
    tier: int,
    catalog_by_code: dict[str, dict[str, Any]],
    policy: dict[str, Any],
) -> dict[str, Any]:
    codes = [code for code in str(row.get("actual_comp_codes_normalized", "")).split(";") if code]
    matched = [candidate_metrics(catalog_by_code[code], row, tier, policy) for code in codes if code in catalog_by_code]
    if not matched:
        return {
            "comp_code": "no_matched_comp_record",
            "comp_label": "No matched synthetic comp record",
            "recommended_value": 0,
            "internal_cost_low": 0,
            "internal_cost_mid": 0,
            "internal_cost_high": 0,
            "issue_fit_score": 0,
            "perceived_value": 0,
            "min_tier_fit": 0,
            "max_tier_fit": 0,
            "selected_codes": [],
            "adequacy_evaluable": False,
        }
    best = max(matched, key=lambda item: (item["issue_fit_score"], item["max_tier_fit"]))
    return {
        **best,
        "comp_code": ";".join(codes),
        "comp_label": "; ".join(str(catalog_by_code[code]["comp_label"]) for code in codes if code in catalog_by_code),
        "recommended_value": int(as_float(row.get("actual_comp_face_value"), 0)),
        "internal_cost_low": int(as_float(row.get("actual_comp_internal_cost"), 0)),
        "internal_cost_mid": int(as_float(row.get("actual_comp_internal_cost"), 0)),
        "internal_cost_high": int(as_float(row.get("actual_comp_internal_cost"), 0)),
        "selected_codes": codes,
        "adequacy_evaluable": True,
    }


def intelligent_selection(
    row: dict[str, str],
    tier: int,
    catalog_by_code: dict[str, dict[str, Any]],
    policy: dict[str, Any],
) -> dict[str, Any]:
    recommendation = recommend_comp(row, row, list(catalog_by_code.values()), policy)
    comp = catalog_by_code[recommendation.comp_code]
    return {
        "comp_code": recommendation.comp_code,
        "comp_label": recommendation.comp_label,
        "recommended_value": recommendation.recommended_value,
        "internal_cost_low": recommendation.internal_cost_low,
        "internal_cost_mid": recommendation.estimated_internal_cost,
        "internal_cost_high": recommendation.internal_cost_high,
        "issue_fit_score": raw_issue_fit(comp, row, policy),
        "perceived_value": recommendation.recommended_value * as_float(comp.get("guest_perceived_value_multiplier"), 1),
        "min_tier_fit": int(as_float(comp.get("min_tier_fit"), 1)),
        "max_tier_fit": int(as_float(comp.get("max_tier_fit"), 5)),
        "selected_codes": [recommendation.comp_code],
        "adequacy_evaluable": True,
        "recommendation_stability": recommendation.recommendation_stability,
    }


def build_case_policy_rows(
    recovery_cases: list[dict[str, str]],
    scenario_config: dict[str, Any],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    catalog = comp_catalog(policy)
    catalog_by_code = {str(comp["comp_code"]): comp for comp in catalog}
    evaluation = scenario_config["evaluation"]
    review_config = policy["manager_review"]
    rows: list[dict[str, Any]] = []

    for case in recovery_cases:
        need = recovery_need_score(case, case, policy)
        tier = score_to_tier(need, policy)
        hold = data_hold_case(case, evaluation)
        high_risk = high_risk_case(case, tier, evaluation)

        for policy_spec in scenario_config["policies"]:
            strategy = str(policy_spec["strategy"])
            baseline_reference = strategy == "replay_synthetic_history"
            if strategy == "replay_synthetic_history":
                selected = baseline_selection(case, tier, catalog_by_code, policy)
                status = "reference_action" if selected["adequacy_evaluable"] else "reference_unknown"
            elif hold:
                selected = {
                    "comp_code": "data_quality_hold",
                    "comp_label": "Data-quality hold",
                    "recommended_value": 0,
                    "internal_cost_low": 0,
                    "internal_cost_mid": 0,
                    "internal_cost_high": 0,
                    "issue_fit_score": 0,
                    "perceived_value": 0,
                    "min_tier_fit": 0,
                    "max_tier_fit": 0,
                    "selected_codes": [],
                    "adequacy_evaluable": False,
                }
                status = "data_quality_hold"
            elif strategy == "context_aware_policy_engine":
                selected = intelligent_selection(case, tier, catalog_by_code, policy)
                status = "recommendation"
            else:
                selected = select_simple_strategy(strategy, case, tier, catalog, policy, evaluation)
                selected["selected_codes"] = [selected["comp_code"]]
                selected["adequacy_evaluable"] = True
                status = "recommendation"

            selected_codes = list(selected.get("selected_codes", []))
            evaluable = bool(selected.get("adequacy_evaluable"))
            adequate = (
                evaluable
                and as_float(selected.get("issue_fit_score"), 0) >= as_float(evaluation["adequate_fit_minimum"])
                and int(selected.get("max_tier_fit", 0)) >= tier
            )
            infeasible = operational_infeasible(selected_codes, case, evaluation)
            pressure_review = operational_pressure_review(selected_codes, case, evaluation)
            robust_fit_minimum = as_float(evaluation["adequate_fit_minimum"]) / max(
                as_float(scenario_config["probabilistic_sensitivity"]["multiplier_low"]), 0.01
            )
            fit_uncertainty_review = (
                not baseline_reference
                and evaluable
                and as_float(selected.get("issue_fit_score"), 0) < robust_fit_minimum
            )
            manager_review_evaluable = not baseline_reference
            manager_review = manager_review_evaluable and (
                hold
                or pressure_review
                or fit_uncertainty_review
                or tier >= int(review_config["minimum_tier"])
                or as_float(selected.get("recommended_value"), 0) >= as_float(review_config["minimum_guest_facing_value"])
                or as_float(case.get("repeat_comp_review_risk"), 0)
                >= as_float(review_config["repeat_comp_review_threshold"])
            )
            safe_recovery_path = evaluable and (adequate or manager_review)
            data_hold_compliant = (not hold) or status == "data_quality_hold"
            tier_five_review_compliant = tier < 5 or manager_review

            rows.append(
                {
                    "comparison_version": scenario_config["comparison_version"],
                    "policy_id": policy_spec["policy_id"],
                    "policy_label": policy_spec["label"],
                    "policy_strategy": strategy,
                    "selection_eligible": str(bool(policy_spec["selection_eligible"])).lower(),
                    "recovery_case_id": case["recovery_case_id"],
                    "guest_tier": case["guest_tier"],
                    "failure_category": case["failure_category"],
                    "severity": int(as_float(case.get("severity"), 0)),
                    "hotel_responsibility_score": as_float(case.get("hotel_responsibility_score"), 0),
                    "reported_in_stay": str(case.get("reported_in_stay", "false")).lower(),
                    "occupancy_pressure": as_float(case.get("occupancy_pressure"), 0),
                    "high_demand_rate_flag": str(case.get("high_demand_rate_flag", "false")).lower(),
                    "high_local_demand_flag": str(case.get("high_local_demand_flag", "false")).lower(),
                    "reservation_match_confidence": as_float(case.get("reservation_match_confidence"), 0),
                    "crm_match_confidence": as_float(case.get("crm_match_confidence"), 0),
                    "reference_recovery_need_score": need,
                    "reference_recovery_tier": tier,
                    "recommendation_status": status,
                    "selected_comp_code": selected["comp_code"],
                    "selected_comp_label": selected["comp_label"],
                    "selected_guest_facing_value": int(as_float(selected.get("recommended_value"), 0)),
                    "internal_cost_low": int(as_float(selected.get("internal_cost_low"), 0)),
                    "internal_cost_mid": int(as_float(selected.get("internal_cost_mid"), 0)),
                    "internal_cost_high": int(as_float(selected.get("internal_cost_high"), 0)),
                    "issue_fit_score": round(as_float(selected.get("issue_fit_score"), 0), 3),
                    "selected_min_tier_fit": int(selected.get("min_tier_fit", 0)),
                    "selected_max_tier_fit": int(selected.get("max_tier_fit", 0)),
                    "adequacy_evaluable": str(evaluable).lower(),
                    "recovery_adequate": str(adequate).lower(),
                    "safe_recovery_path": str(safe_recovery_path).lower(),
                    "high_risk_case": str(high_risk).lower(),
                    "high_risk_under_recovery": str(
                        high_risk and evaluable and not adequate and not manager_review
                    ).lower(),
                    "operational_infeasible": str(infeasible).lower(),
                    "operational_pressure_review": str(pressure_review).lower(),
                    "fit_uncertainty_review": str(fit_uncertainty_review).lower(),
                    "property_aligned_gesture": str(any(code in PROPERTY_ALIGNED_CODES for code in selected_codes)).lower(),
                    "direct_room_refund": str(any(code in DIRECT_REFUND_CODES for code in selected_codes)).lower(),
                    "manager_review_required": str(manager_review).lower(),
                    "manager_review_evaluable": str(manager_review_evaluable).lower(),
                    "data_hold_case": str(hold).lower(),
                    "data_hold_compliant": str(data_hold_compliant).lower(),
                    "tier_five_review_compliant": str(tier_five_review_compliant).lower(),
                    "evaluation_provenance": "synthetic_case_policy_assumption",
                }
            )
    return rows


def safe_rate(numerator: float, denominator: float, default: float = 0.0) -> float:
    return numerator / denominator if denominator else default


def point_metrics(rows: list[dict[str, Any]]) -> dict[str, float]:
    evaluable = [row for row in rows if truth(row["adequacy_evaluable"])]
    high_risk = [row for row in evaluable if truth(row["high_risk_case"])]
    review_evaluable = [row for row in rows if truth(row["manager_review_evaluable"])]
    hold_cases = [row for row in rows if truth(row["data_hold_case"])]
    tier_five = [row for row in rows if int(row["reference_recovery_tier"]) >= 5]
    return {
        "cases": len(rows),
        "evaluable_cases": len(evaluable),
        "unknown_or_hold_cases": len(rows) - len(evaluable),
        "gesture_adequacy_rate": safe_rate(
            sum(truth(row["recovery_adequate"]) for row in evaluable), len(evaluable)
        ),
        "adequacy_rate": safe_rate(
            sum(truth(row["safe_recovery_path"]) for row in evaluable), len(evaluable)
        ),
        "high_risk_cases": len(high_risk),
        "high_risk_under_recovery_rate": safe_rate(
            sum(truth(row["high_risk_under_recovery"]) for row in high_risk), len(high_risk)
        ),
        "operational_infeasibility_rate": safe_rate(
            sum(truth(row["operational_infeasible"]) for row in rows), len(rows)
        ),
        "data_hold_compliance_rate": safe_rate(
            sum(truth(row["data_hold_compliant"]) for row in hold_cases), len(hold_cases), 1.0
        ),
        "tier_five_review_compliance_rate": safe_rate(
            sum(truth(row["tier_five_review_compliant"]) for row in tier_five), len(tier_five), 1.0
        ),
        "manager_review_evaluable_cases": len(review_evaluable),
        "manager_review_rate": safe_rate(
            sum(truth(row["manager_review_required"]) for row in review_evaluable),
            len(review_evaluable),
        ),
        "property_aligned_gesture_rate": safe_rate(
            sum(truth(row["property_aligned_gesture"]) for row in rows), len(rows)
        ),
        "direct_room_refund_cases": sum(truth(row["direct_room_refund"]) for row in rows),
        "direct_room_refund_value": sum(
            as_float(row["selected_guest_facing_value"]) for row in rows if truth(row["direct_room_refund"])
        ),
        "guest_facing_value": sum(as_float(row["selected_guest_facing_value"]) for row in rows),
        "internal_cost_low": sum(as_float(row["internal_cost_low"]) for row in rows),
        "internal_cost_mid": sum(as_float(row["internal_cost_mid"]) for row in rows),
        "internal_cost_high": sum(as_float(row["internal_cost_high"]) for row in rows),
    }


def bootstrap_metrics(
    rows_by_policy: dict[str, list[dict[str, Any]]],
    case_ids: list[str],
    config: dict[str, Any],
) -> dict[str, dict[str, tuple[float, float]]]:
    rng = random.Random(int(config["bootstrap"]["seed"]))
    draws = int(config["bootstrap"]["draws"])
    aligned = {
        policy_id: {str(row["recovery_case_id"]): row for row in rows}
        for policy_id, rows in rows_by_policy.items()
    }
    sampled: dict[str, dict[str, list[float]]] = {
        policy_id: defaultdict(list) for policy_id in rows_by_policy
    }
    for _ in range(draws):
        sample_ids = [case_ids[rng.randrange(len(case_ids))] for _ in case_ids]
        for policy_id in rows_by_policy:
            metrics = point_metrics([aligned[policy_id][case_id] for case_id in sample_ids])
            for name in (
                "adequacy_rate",
                "high_risk_under_recovery_rate",
                "internal_cost_mid",
                "direct_room_refund_value",
                "manager_review_rate",
            ):
                sampled[policy_id][name].append(metrics[name])
    return {
        policy_id: {
            name: (percentile(values, 0.025), percentile(values, 0.975))
            for name, values in metrics.items()
        }
        for policy_id, metrics in sampled.items()
    }


def varied_reference_tiers(
    cases_by_id: dict[str, dict[str, str]],
    policy: dict[str, Any],
    rng: random.Random,
    low: float,
    mode: float,
    high: float,
) -> dict[str, int]:
    varied_weights = {
        name: as_float(value) * rng.triangular(low, high, mode)
        for name, value in policy["recovery_need_weights"].items()
    }
    original_total = sum(as_float(value) for value in policy["recovery_need_weights"].values())
    varied_total = sum(varied_weights.values()) or 1
    varied_weights = {name: value * original_total / varied_total for name, value in varied_weights.items()}
    varied_policy = {**policy, "recovery_need_weights": varied_weights}
    return {
        case_id: score_to_tier(recovery_need_score(case, case, varied_policy), policy)
        for case_id, case in cases_by_id.items()
    }


def fit_uncertainty_key(row: dict[str, Any]) -> str:
    return f"{row['selected_comp_code']}|{row['failure_category']}"


def build_shared_sensitivity_draw(
    rows_by_policy: dict[str, list[dict[str, Any]]],
    rng: random.Random,
    low: float,
    mode: float,
    high: float,
) -> dict[str, Any]:
    rows = [row for policy_rows in rows_by_policy.values() for row in policy_rows]
    fit_keys = sorted({fit_uncertainty_key(row) for row in rows})
    cost_keys = sorted({str(row["selected_comp_code"]) for row in rows})
    return {
        "fit_multipliers": {
            key: rng.triangular(low, high, mode)
            for key in fit_keys
        },
        "occupancy_multiplier": rng.triangular(low, high, mode),
        "cost_quantiles": {key: rng.random() for key in cost_keys},
    }


def sensitivity_metrics_for_policy(
    rows: list[dict[str, Any]],
    varied_tiers: dict[str, int],
    evaluation: dict[str, Any],
    shared_draw: dict[str, Any],
) -> dict[str, float]:
    fit_multipliers = shared_draw["fit_multipliers"]
    occupancy_multiplier = as_float(shared_draw["occupancy_multiplier"], 1.0)
    cost_quantiles = shared_draw["cost_quantiles"]
    evaluable = 0
    adequate_count = 0
    high_risk_count = 0
    high_risk_under = 0
    operational_infeasible_count = 0
    hold_count = 0
    hold_compliant = 0
    tier_five_count = 0
    tier_five_review = 0
    total_cost = 0.0
    refund_value = 0.0
    manager_review_count = 0

    for row in rows:
        tier = varied_tiers[str(row["recovery_case_id"])]
        is_evaluable = truth(row["adequacy_evaluable"])
        fit = as_float(row["issue_fit_score"]) * as_float(
            fit_multipliers[fit_uncertainty_key(row)], 1.0
        )
        adequate = is_evaluable and fit >= as_float(evaluation["adequate_fit_minimum"]) and int(row["selected_max_tier_fit"]) >= tier
        high_risk = high_risk_case(row, tier, evaluation)
        review_evaluable = truth(row["manager_review_evaluable"])
        manager_review = review_evaluable and (truth(row["manager_review_required"]) or tier >= 5)
        codes = [code for code in str(row["selected_comp_code"]).split(";") if code]
        infeasible = operational_infeasible(codes, row, evaluation, occupancy_multiplier)
        manager_review = manager_review or operational_pressure_review(
            codes, row, evaluation, occupancy_multiplier
        ) if review_evaluable else False
        safe_path = is_evaluable and (adequate or manager_review)

        cost_low = as_float(row["internal_cost_low"])
        cost_mid = as_float(row["internal_cost_mid"])
        cost_high = as_float(row["internal_cost_high"])
        total_cost += triangular_quantile(
            min(cost_low, cost_mid, cost_high),
            cost_mid,
            max(cost_low, cost_mid, cost_high),
            as_float(cost_quantiles[str(row["selected_comp_code"])]),
        )
        if truth(row["direct_room_refund"]):
            refund_value += as_float(row["selected_guest_facing_value"])
        if is_evaluable:
            evaluable += 1
            adequate_count += int(safe_path)
            if high_risk:
                high_risk_count += 1
                high_risk_under += int(not adequate and not manager_review)
        operational_infeasible_count += int(infeasible)
        if truth(row["data_hold_case"]):
            hold_count += 1
            hold_compliant += int(truth(row["data_hold_compliant"]))
        if tier >= 5:
            tier_five_count += 1
            tier_five_review += int(manager_review)
        manager_review_count += int(manager_review)

    return {
        "adequacy_rate": safe_rate(adequate_count, evaluable),
        "high_risk_under_recovery_rate": safe_rate(high_risk_under, high_risk_count),
        "operational_infeasibility_rate": safe_rate(operational_infeasible_count, len(rows)),
        "data_hold_compliance_rate": safe_rate(hold_compliant, hold_count, 1.0),
        "tier_five_review_compliance_rate": safe_rate(tier_five_review, tier_five_count, 1.0),
        "manager_review_rate": safe_rate(
            manager_review_count,
            sum(truth(row["manager_review_evaluable"]) for row in rows),
        ),
        "internal_cost": total_cost,
        "direct_room_refund_value": refund_value,
    }


def passes_guardrails(metrics: dict[str, float], guardrails: dict[str, Any]) -> bool:
    return (
        metrics["adequacy_rate"] >= as_float(guardrails["minimum_overall_adequacy"])
        and metrics["high_risk_under_recovery_rate"]
        <= as_float(guardrails["maximum_high_risk_under_recovery"])
        and metrics["operational_infeasibility_rate"]
        <= as_float(guardrails["maximum_operational_infeasibility"])
        and metrics["data_hold_compliance_rate"] >= as_float(guardrails["minimum_data_hold_compliance"])
        and metrics["tier_five_review_compliance_rate"]
        >= as_float(guardrails["minimum_tier_five_review_compliance"])
    )


def probabilistic_sensitivity(
    rows_by_policy: dict[str, list[dict[str, Any]]],
    cases_by_id: dict[str, dict[str, str]],
    scenario_config: dict[str, Any],
    policy: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, float]]]]:
    sensitivity = scenario_config["probabilistic_sensitivity"]
    draws = int(sensitivity["draws"])
    rng = random.Random(int(sensitivity["seed"]))
    low = as_float(sensitivity["multiplier_low"])
    mode = as_float(sensitivity["multiplier_mode"])
    high = as_float(sensitivity["multiplier_high"])
    evaluation = scenario_config["evaluation"]
    guardrails = scenario_config["shadow_guardrails"]
    policy_specs = {str(row["policy_id"]): row for row in scenario_config["policies"]}
    draw_metrics: dict[str, list[dict[str, float]]] = {policy_id: [] for policy_id in rows_by_policy}
    draw_selection_counts: Counter[str] = Counter()

    for _ in range(draws):
        varied_tiers = varied_reference_tiers(cases_by_id, policy, rng, low, mode, high)
        shared_draw = build_shared_sensitivity_draw(rows_by_policy, rng, low, mode, high)
        current_draw: dict[str, dict[str, float]] = {}
        for policy_id, rows in rows_by_policy.items():
            metrics = sensitivity_metrics_for_policy(rows, varied_tiers, evaluation, shared_draw)
            metrics["guardrails_passed"] = float(passes_guardrails(metrics, guardrails))
            draw_metrics[policy_id].append(metrics)
            current_draw[policy_id] = metrics
        candidates = [
            policy_id
            for policy_id, metrics in current_draw.items()
            if policy_specs[policy_id]["selection_eligible"] and metrics["guardrails_passed"] == 1
        ]
        if candidates:
            winner = min(
                candidates,
                key=lambda policy_id: (
                    current_draw[policy_id]["internal_cost"],
                    current_draw[policy_id]["direct_room_refund_value"],
                    current_draw[policy_id]["manager_review_rate"],
                    policy_id,
                ),
            )
            draw_selection_counts[winner] += 1

    uncertainty_rows: list[dict[str, Any]] = []
    for policy_id, metrics_rows in draw_metrics.items():
        def values(name: str) -> list[float]:
            return [row[name] for row in metrics_rows]

        uncertainty_rows.append(
            {
                "comparison_version": scenario_config["comparison_version"],
                "policy_id": policy_id,
                "policy_label": policy_specs[policy_id]["label"],
                "sensitivity_draws": draws,
                "joint_guardrail_pass_probability": statistics.mean(values("guardrails_passed")),
                "adequacy_guardrail_pass_probability": statistics.mean(
                    value >= as_float(guardrails["minimum_overall_adequacy"])
                    for value in values("adequacy_rate")
                ),
                "high_risk_guardrail_pass_probability": statistics.mean(
                    value <= as_float(guardrails["maximum_high_risk_under_recovery"])
                    for value in values("high_risk_under_recovery_rate")
                ),
                "operational_guardrail_pass_probability": statistics.mean(
                    value <= as_float(guardrails["maximum_operational_infeasibility"])
                    for value in values("operational_infeasibility_rate")
                ),
                "data_hold_guardrail_pass_probability": statistics.mean(
                    value >= as_float(guardrails["minimum_data_hold_compliance"])
                    for value in values("data_hold_compliance_rate")
                ),
                "tier_five_review_guardrail_pass_probability": statistics.mean(
                    value >= as_float(guardrails["minimum_tier_five_review_compliance"])
                    for value in values("tier_five_review_compliance_rate")
                ),
                "internal_cost_p05": round(percentile(values("internal_cost"), 0.05)),
                "internal_cost_p50": round(percentile(values("internal_cost"), 0.5)),
                "internal_cost_p95": round(percentile(values("internal_cost"), 0.95)),
                "policy_selection_probability": draw_selection_counts[policy_id] / draws,
                "uncertainty_provenance": "synthetic_case_mix_and_policy_assumptions",
            }
        )
    return uncertainty_rows, draw_metrics


def select_shadow_candidate(
    summary_metrics: dict[str, dict[str, float]],
    uncertainty_rows: list[dict[str, Any]],
    scenario_config: dict[str, Any],
) -> tuple[str, str]:
    guardrails = scenario_config["shadow_guardrails"]
    specs = {str(row["policy_id"]): row for row in scenario_config["policies"]}
    uncertainty = {str(row["policy_id"]): row for row in uncertainty_rows}
    eligible = [
        policy_id
        for policy_id, spec in specs.items()
        if spec["selection_eligible"]
        and as_float(uncertainty[policy_id]["joint_guardrail_pass_probability"])
        >= as_float(guardrails["minimum_guardrail_pass_probability"])
    ]
    if not eligible:
        return "", "Do not advance a policy; no candidate cleared the declared shadow-validation guardrails reliably."

    minimum_cost = min(as_float(uncertainty[policy_id]["internal_cost_p50"]) for policy_id in eligible)
    tie_limit = minimum_cost * (1 + as_float(guardrails["cost_tie_fraction"]))
    finalists = [
        policy_id
        for policy_id in eligible
        if as_float(uncertainty[policy_id]["internal_cost_p50"]) <= tie_limit
    ]
    selected = min(
        finalists,
        key=lambda policy_id: (
            summary_metrics[policy_id]["direct_room_refund_value"],
            summary_metrics[policy_id]["manager_review_rate"],
            policy_id,
        ),
    )
    return selected, (
        f"Approve a four-week, minimum-50-case shadow validation of {specs[selected]['label']} as the leading candidate. "
        "Under the declared synthetic case mix and policy assumptions, it cleared the guest-protection, data-quality, "
        "escalation, and operational guardrails with the lowest modeled cost among eligible policies."
    )


def build_summary_rows(
    rows_by_policy: dict[str, list[dict[str, Any]]],
    scenario_config: dict[str, Any],
    bootstrap: dict[str, dict[str, tuple[float, float]]],
    uncertainty_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], str, str]:
    specs = {str(row["policy_id"]): row for row in scenario_config["policies"]}
    uncertainty = {str(row["policy_id"]): row for row in uncertainty_rows}
    metrics_by_policy = {policy_id: point_metrics(rows) for policy_id, rows in rows_by_policy.items()}
    selected_id, recommendation = select_shadow_candidate(metrics_by_policy, uncertainty_rows, scenario_config)
    selected_metrics = metrics_by_policy.get(selected_id, {})
    rows: list[dict[str, Any]] = []
    for policy_id, metrics in metrics_by_policy.items():
        intervals = bootstrap[policy_id]
        selected_cost = as_float(selected_metrics.get("internal_cost_mid"), 0)
        rows.append(
            {
                "comparison_version": scenario_config["comparison_version"],
                "policy_id": policy_id,
                "policy_label": specs[policy_id]["label"],
                "policy_strategy": specs[policy_id]["strategy"],
                "selection_eligible": str(bool(specs[policy_id]["selection_eligible"])).lower(),
                "cases": int(metrics["cases"]),
                "evaluable_cases": int(metrics["evaluable_cases"]),
                "unknown_or_hold_cases": int(metrics["unknown_or_hold_cases"]),
                "adequacy_rate": round(metrics["adequacy_rate"], 4),
                "gesture_adequacy_rate": round(metrics["gesture_adequacy_rate"], 4),
                "adequacy_rate_ci_low": round(intervals["adequacy_rate"][0], 4),
                "adequacy_rate_ci_high": round(intervals["adequacy_rate"][1], 4),
                "high_risk_cases": int(metrics["high_risk_cases"]),
                "high_risk_under_recovery_rate": round(metrics["high_risk_under_recovery_rate"], 4),
                "high_risk_under_recovery_ci_low": round(intervals["high_risk_under_recovery_rate"][0], 4),
                "high_risk_under_recovery_ci_high": round(intervals["high_risk_under_recovery_rate"][1], 4),
                "operational_infeasibility_rate": round(metrics["operational_infeasibility_rate"], 4),
                "data_hold_compliance_rate": round(metrics["data_hold_compliance_rate"], 4),
                "tier_five_review_compliance_rate": round(metrics["tier_five_review_compliance_rate"], 4),
                "manager_review_rate": round(metrics["manager_review_rate"], 4),
                "manager_review_evaluable_cases": int(metrics["manager_review_evaluable_cases"]),
                "manager_review_rate_ci_low": round(intervals["manager_review_rate"][0], 4),
                "manager_review_rate_ci_high": round(intervals["manager_review_rate"][1], 4),
                "property_aligned_gesture_rate": round(metrics["property_aligned_gesture_rate"], 4),
                "direct_room_refund_cases": int(metrics["direct_room_refund_cases"]),
                "direct_room_refund_value": round(metrics["direct_room_refund_value"]),
                "guest_facing_value": round(metrics["guest_facing_value"]),
                "internal_cost_low": round(metrics["internal_cost_low"]),
                "internal_cost_mid": round(metrics["internal_cost_mid"]),
                "internal_cost_high": round(metrics["internal_cost_high"]),
                "internal_cost_bootstrap_ci_low": round(intervals["internal_cost_mid"][0]),
                "internal_cost_bootstrap_ci_high": round(intervals["internal_cost_mid"][1]),
                "joint_guardrail_pass_probability": round(
                    as_float(uncertainty[policy_id]["joint_guardrail_pass_probability"]), 4
                ),
                "policy_selection_probability": round(
                    as_float(uncertainty[policy_id]["policy_selection_probability"]), 4
                ),
                "selected_for_shadow_evaluation": str(policy_id == selected_id).lower(),
                "midpoint_cost_delta_vs_selected": round(metrics["internal_cost_mid"] - selected_cost) if selected_id else "",
                "executive_recommendation": recommendation if policy_id == selected_id else "",
                "evidence_boundary": "synthetic_policy_comparison_not_observed_hotel_performance",
            }
        )
    return rows, selected_id, recommendation


def occupancy_band(value: Any) -> str:
    occupancy = as_float(value)
    if occupancy < 0.65:
        return "low"
    if occupancy < 0.85:
        return "moderate"
    return "high"


def build_segment_rows(
    rows: list[dict[str, Any]],
    scenario_config: dict[str, Any],
) -> list[dict[str, Any]]:
    minimum = int(scenario_config["evaluation"]["minimum_segment_size"])
    dimensions: dict[str, Callable[[dict[str, Any]], str]] = {
        "severity": lambda row: str(row["severity"]),
        "failure_category": lambda row: str(row["failure_category"]),
        "guest_tier": lambda row: str(row["guest_tier"]),
        "occupancy_band": lambda row: occupancy_band(row["occupancy_pressure"]),
        "recovery_timing": lambda row: "in_stay" if truth(row["reported_in_stay"]) else "after_checkout",
    }
    output: list[dict[str, Any]] = []
    by_policy: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_policy[str(row["policy_id"])].append(row)
    for policy_id, policy_rows in by_policy.items():
        for dimension, value_fn in dimensions.items():
            groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for row in policy_rows:
                groups[value_fn(row)].append(row)
            for value, group in sorted(groups.items()):
                suppressed = len(group) < minimum
                metrics = point_metrics(group) if not suppressed else {}
                output.append(
                    {
                        "comparison_version": scenario_config["comparison_version"],
                        "policy_id": policy_id,
                        "policy_label": group[0]["policy_label"],
                        "segment_dimension": dimension,
                        "segment_value": value,
                        "cases": len(group),
                        "suppressed_small_group": str(suppressed).lower(),
                        "adequacy_rate": "" if suppressed else round(metrics["adequacy_rate"], 4),
                        "high_risk_under_recovery_rate": ""
                        if suppressed
                        else round(metrics["high_risk_under_recovery_rate"], 4),
                        "operational_infeasibility_rate": ""
                        if suppressed
                        else round(metrics["operational_infeasibility_rate"], 4),
                        "manager_review_rate": "" if suppressed else round(metrics["manager_review_rate"], 4),
                        "internal_cost_mid": "" if suppressed else round(metrics["internal_cost_mid"]),
                    }
                )
    return output


def render_report(
    summary_rows: list[dict[str, Any]],
    uncertainty_rows: list[dict[str, Any]],
    selected_id: str,
    recommendation: str,
    scenario_config: dict[str, Any],
) -> str:
    selected = next((row for row in summary_rows if row["policy_id"] == selected_id), None)
    lines = [
        "# Comp Policy Decision Analysis",
        "",
        "## Executive Decision",
        "",
        recommendation,
        "",
        "> **Evidence boundary:** this is constrained optimization over synthetic hotel operations and declared policy assumptions. It supports selecting a candidate for shadow validation, not manager-facing use, permanent adoption, actual savings, or claims about Proper Hotels performance.",
        "",
        "## Policy Comparison",
        "",
        "| Policy | Safe recovery path | Gesture fit | High-risk under-recovery | Midpoint cost | Direct refund face value | Manager review | Assumption-stress pass rate | Decision |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in summary_rows:
        adequacy = "unknown" if not int(row["evaluable_cases"]) else f"{as_float(row['adequacy_rate']):.1%}"
        manager_review = (
            "unknown"
            if not int(row["manager_review_evaluable_cases"])
            else f"{as_float(row['manager_review_rate']):.1%}"
        )
        lines.append(
            f"| {row['policy_label']} | {adequacy} | {as_float(row['gesture_adequacy_rate']):.1%} | {as_float(row['high_risk_under_recovery_rate']):.1%} | "
            f"{money(row['internal_cost_mid'])} | {money(row['direct_room_refund_value'])} | "
            f"{manager_review} | {as_float(row['joint_guardrail_pass_probability']):.1%} | "
            f"{'Shadow-validation candidate' if truth(row['selected_for_shadow_evaluation']) else 'Comparator'} |"
        )
    lines.extend(
        [
            "",
            "## Decision Rule",
            "",
            "A policy can advance to shadow validation only when at least 80% of assumption-stress draws satisfy all declared guardrails: at least 90% of evaluable cases receive either an adequate gesture or explicit manager review, no more than 5% of high-risk cases are both inadequate and unreviewed, no more than 2% operational infeasibility, complete data-hold compliance, and complete tier-5 manager review.",
            "",
            "Safe recovery path counts an adequate gesture or an explicit manager-review path. Gesture fit evaluates the proposed gesture alone.",
            "",
            "Guardrailed recovery is deliberately an adequacy-constrained cost optimizer. Its advantage is therefore a decision-analysis result under the declared fit and cost assumptions, not independent evidence of superior guest outcomes.",
            "",
            "Among qualifying policies, the decision rule selects the lowest median modeled internal cost. Policies within 1% are resolved by lower direct-refund exposure and then lower manager-review burden.",
            "",
            "## Statistical Evidence",
            "",
            f"- Paired case bootstrap draws: `{scenario_config['bootstrap']['draws']}`",
            f"- Shared-world assumption-stress draws: `{scenario_config['probabilistic_sensitivity']['draws']}`",
            "- Bootstrap intervals describe synthetic case-mix variability, not sampling uncertainty for Proper Hotels.",
            "- Each stress draw applies the same recovery-weight, gesture-fit, occupancy-pressure, and comp-cost realization to every policy before comparison.",
            "- Synthetic post-stay scores are excluded because their generator does not include a comp-treatment effect.",
            "",
            "## Selected Policy Tradeoff",
            "",
        ]
    )
    if selected:
        uncertainty = next(row for row in uncertainty_rows if row["policy_id"] == selected_id)
        lines.extend(
            [
                f"- Selected policy: **{selected['policy_label']}**",
                f"- Safe recovery-path coverage: `{as_float(selected['adequacy_rate']):.1%}`",
                f"- Strict gesture adequacy before manager review: `{as_float(selected['gesture_adequacy_rate']):.1%}`",
                f"- High-risk under-recovery: `{as_float(selected['high_risk_under_recovery_rate']):.1%}`",
                f"- Modeled midpoint internal cost: `{money(selected['internal_cost_mid'])}`",
                f"- Cost uncertainty range (5th-95th percentile): `{money(uncertainty['internal_cost_p05'])}-{money(uncertainty['internal_cost_p95'])}`",
                f"- Direct room-refund face-value exposure: `{money(selected['direct_room_refund_value'])}`",
                f"- Manager-review rate: `{as_float(selected['manager_review_rate']):.1%}`",
                f"- Assumption-stress guardrail pass rate: `{as_float(selected['joint_guardrail_pass_probability']):.1%}`",
            ]
        )
    else:
        lines.append("No policy qualified for manager-facing testing. Continue in shadow mode and revise the policy assumptions.")
    lines.extend(
        [
            "",
            "## Proposed Shadow Validation",
            "",
            "1. Run shadow mode for four weeks or 50 eligible cases, whichever is later.",
            "2. Validate reservation and CRM matching, property-reviewed marginal-cost ranges, manager override capture, and complete outcome instrumentation.",
            "3. Calculate the controlled-phase sample requirement from shadow event volume, outcome variance, baseline recovery, and a pre-specified minimum detectable effect.",
            "4. Randomize policy-eligible cases between usual manager judgment and decision support. Tier-5 and low-confidence cases always remain manager-controlled.",
            "5. Measure post-recovery satisfaction, resolution time, actual marginal cost, room refunds, overrides, reviews, and repeat stays before any permanent policy decision.",
            "",
            "## Model Improvement After Controlled-Test Data",
            "",
            "Fit a Bayesian hierarchical recovery-outcome model with partial pooling by issue type, manager, guest segment, and operating conditions. Use posterior probabilities to evaluate whether decision support preserves guest recovery while reducing cost or room-rate erosion. Until those outcomes exist, the project remains a robust policy simulation rather than an empirically optimized comp model.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    ensure_dirs()
    if not RECOVERY_CASE_MART_PATH.exists():
        print("Missing recovery-case mart. Run `make mart` first.")
        return 1
    policy = load_policy_config()
    scenario_config = load_policy_scenarios()
    _, cases = read_csv_rows(RECOVERY_CASE_MART_PATH)
    case_ids = [row["recovery_case_id"] for row in cases]
    cases_by_id = {row["recovery_case_id"]: row for row in cases}

    case_policy_rows = build_case_policy_rows(cases, scenario_config, policy)
    rows_by_policy: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in case_policy_rows:
        rows_by_policy[str(row["policy_id"])].append(row)

    bootstrap = bootstrap_metrics(rows_by_policy, case_ids, scenario_config)
    uncertainty_rows, _draw_metrics = probabilistic_sensitivity(
        rows_by_policy, cases_by_id, scenario_config, policy
    )
    summary_rows, selected_id, recommendation = build_summary_rows(
        rows_by_policy, scenario_config, bootstrap, uncertainty_rows
    )
    segment_rows = build_segment_rows(case_policy_rows, scenario_config)

    write_csv(POLICY_CASE_COMPARISON_PATH, list(case_policy_rows[0].keys()), case_policy_rows)
    write_csv(POLICY_DECISION_SUMMARY_PATH, list(summary_rows[0].keys()), summary_rows)
    write_csv(POLICY_SEGMENT_DIAGNOSTICS_PATH, list(segment_rows[0].keys()), segment_rows)
    write_csv(POLICY_UNCERTAINTY_SUMMARY_PATH, list(uncertainty_rows[0].keys()), uncertainty_rows)
    REPORT_PATH.write_text(
        render_report(summary_rows, uncertainty_rows, selected_id, recommendation, scenario_config),
        encoding="utf-8",
    )
    write_json(
        POLICY_COMPARISON_MANIFEST_PATH,
        {
            "generated_at": utc_now_iso(),
            "comparison_version": scenario_config["comparison_version"],
            "reference_policy_id": scenario_config["reference_policy_id"],
            "case_count": len(cases),
            "policy_count": len(rows_by_policy),
            "case_policy_row_count": len(case_policy_rows),
            "bootstrap_draws": scenario_config["bootstrap"]["draws"],
            "bootstrap_seed": scenario_config["bootstrap"]["seed"],
            "sensitivity_draws": scenario_config["probabilistic_sensitivity"]["draws"],
            "sensitivity_seed": scenario_config["probabilistic_sensitivity"]["seed"],
            "selected_policy_id": selected_id,
            "executive_recommendation": recommendation,
            "outcome_boundary": "Synthetic post-stay scores are excluded from policy selection because no comp-treatment effect was generated.",
            "public_safety_note": "All operating cases and policy comparisons are synthetic; official public context does not reveal internal hotel performance or policy.",
        },
    )
    print(f"Wrote {len(case_policy_rows)} case-policy rows across {len(rows_by_policy)} policies")
    print(f"Selected policy: {selected_id or 'shadow_validation_only'}")
    print(f"Wrote policy decision report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
