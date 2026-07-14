from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

try:  # Package imports for the Worker runtime.
    from .policy_config import comp_catalog as configured_comp_catalog
    from .policy_config import load_policy_config
    from .scenario_contract import GUEST_TIER_SCORE, ScenarioInput
except ImportError:  # Direct script and existing local-test compatibility.
    from policy_config import comp_catalog as configured_comp_catalog
    from policy_config import load_policy_config
    from scenario_contract import GUEST_TIER_SCORE, ScenarioInput


@dataclass(frozen=True)
class CandidateEvaluation:
    comp_code: str
    comp_label: str
    score: float
    guest_facing_value: int
    internal_cost_low: int
    internal_cost_expected: int
    internal_cost_high: int
    fit_score: float
    perceived_value: float
    leakage_penalty: float
    operational_penalty: float

    def as_public_dict(self) -> dict[str, Any]:
        return {
            "comp_code": self.comp_code,
            "comp_label": self.comp_label,
            "guest_facing_value": self.guest_facing_value,
            "internal_cost_low": self.internal_cost_low,
            "internal_cost_expected": self.internal_cost_expected,
            "internal_cost_high": self.internal_cost_high,
            "policy_score": round(self.score, 2),
        }


@dataclass(frozen=True)
class Recommendation:
    comp_code: str
    comp_label: str
    recommended_value: int
    estimated_internal_cost: int
    internal_cost_low: int
    internal_cost_high: int
    recommended_tier: int
    recovery_need_score: float
    profit_leakage_risk: float
    review_risk_score: float
    brand_impact_risk: float
    expected_recovery_value: int
    manager_review_flag: bool
    recommendation_stability: float
    decision_confidence: str
    policy_id: str
    policy_version: str
    reason_codes: list[str]
    counterfactuals: list[str]
    alternatives: list[dict[str, Any]]
    score_components: dict[str, float]
    assumptions: list[str]
    explanation: str


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def recovery_need_score(
    stay: dict[str, Any],
    failure: dict[str, Any],
    policy: dict[str, Any] | None = None,
    weight_scale: float = 1.0,
) -> float:
    selected_policy = policy or load_policy_config()
    weights = selected_policy["recovery_need_weights"]
    severity = as_float(failure.get("severity"), 1.0)
    delay = as_float(failure.get("resolution_delay_minutes"), 0.0)
    hotel_responsibility = as_float(failure.get("hotel_responsibility_score"), 0.0)
    sentiment = as_float(failure.get("complaint_sentiment_intensity"), 0.0)
    review_risk = as_float(failure.get("review_risk_score"), 0.0)
    guest_value = as_float(stay.get("guest_value_score"), 0.0)
    timing_risk = 0.55 if as_bool(failure.get("reported_in_stay")) else 1.0
    category = str(failure.get("failure_category"))
    base = as_float(selected_policy["failure_base_risk"].get(category), 0.5)
    delay_component = clamp(math.log1p(delay) / math.log1p(360), 0.0, 1.0)
    score = (
        severity / 5 * as_float(weights["severity"])
        + hotel_responsibility * as_float(weights["hotel_responsibility"])
        + review_risk * as_float(weights["review_risk"])
        + guest_value * as_float(weights["guest_value"])
        + sentiment * as_float(weights["sentiment"])
        + delay_component * as_float(weights["resolution_delay"])
        + timing_risk * as_float(weights["timing_risk"])
        + base * as_float(weights["failure_category"])
    ) * weight_scale
    return round(clamp(score, 0, 100), 2)


def service_recovery_floor_score(
    stay: dict[str, Any],
    failure: dict[str, Any],
    policy: dict[str, Any] | None = None,
) -> float:
    """Score the failure itself before any relationship-value adjustment."""
    floor_stay = {**stay, "guest_value_score": 0.0}
    return recovery_need_score(floor_stay, failure, policy)


def score_to_tier(score: float, policy: dict[str, Any] | None = None) -> int:
    thresholds = list((policy or load_policy_config())["tier_thresholds"])
    for tier, threshold in enumerate(thresholds, start=1):
        if score < as_float(threshold):
            return tier
    return 5


def comp_value_for_tier(comp: dict[str, Any], tier: int, stay: dict[str, Any]) -> int:
    face_min = int(as_float(comp.get("face_value_min"), 0))
    face_default = int(as_float(comp.get("face_value_default"), 0))
    face_max = int(as_float(comp.get("face_value_max"), face_default))
    nightly_rate = as_float(stay.get("nightly_rate"), 500)
    if comp["comp_code"] == "partial_room_refund":
        target = min(face_max, max(face_min, round(nightly_rate * (0.18 + 0.08 * max(0, tier - 3)))))
    elif comp["comp_code"] == "future_stay_credit":
        target = min(face_max, max(face_min, round(nightly_rate * 0.35)))
    else:
        multiplier = {1: 0.7, 2: 0.9, 3: 1.0, 4: 1.2, 5: 1.45}.get(tier, 1.0)
        target = round(face_default * multiplier)
    if face_max > 0:
        target = int(clamp(target, face_min, face_max))
    return int(round(target / 5) * 5)


def property_fit_modifier(comp_code: str, failure: dict[str, Any]) -> float:
    field_by_comp = {
        "rooftop_f_and_b_credit": "rooftop_f_and_b_fit_modifier",
        "spa_wellness_credit": "spa_wellness_fit_modifier",
        "lobby_lounge_credit": "lobby_lounge_fit_modifier",
        "parking_fee_waiver": "parking_fee_fit_modifier",
        "late_checkout": "late_checkout_fit_modifier",
        "room_upgrade": "room_upgrade_fit_modifier",
    }
    field = field_by_comp.get(comp_code)
    return as_float(failure.get(field), 1.0) if field else 1.0


def evaluate_candidate(
    comp: dict[str, Any],
    stay: dict[str, Any],
    failure: dict[str, Any],
    tier: int,
    need: float,
    policy: dict[str, Any],
    scales: dict[str, float] | None = None,
) -> CandidateEvaluation:
    scales = scales or {}
    fit_scale = as_float(scales.get("fit"), 1.0)
    cost_scale = as_float(scales.get("cost"), 1.0)
    occupancy_scale = as_float(scales.get("occupancy"), 1.0)
    context_scale = as_float(scales.get("context"), 1.0)
    comp_code = str(comp["comp_code"])
    failure_category = str(failure.get("failure_category"))
    guest_tier = str(stay.get("guest_tier"))
    occupancy = clamp(as_float(failure.get("occupancy_pressure"), 0.5) * occupancy_scale, 0, 1)
    review_risk = as_float(stay.get("repeat_comp_review_risk"), 0.0)
    severity = as_float(failure.get("severity"), 0.0)
    responsibility = as_float(failure.get("hotel_responsibility_score"), 0.0)
    reputation_risk = as_float(failure.get("review_risk_score"), 0.0)
    public_rate_pressure = as_float(failure.get("public_rate_pressure_index"), 0.5)
    rate_context_confidence = as_float(failure.get("rate_context_confidence"), 0.0) * context_scale
    high_demand_rate = as_bool(failure.get("high_demand_rate_flag")) or public_rate_pressure >= 0.72
    upgrade_opportunity_cost = as_float(failure.get("upgrade_opportunity_cost_proxy"), 0.0)
    refund_cost_pressure = as_float(failure.get("refund_cost_pressure"), 1.0)
    property_context_confidence = as_float(failure.get("property_context_confidence"), 0.0) * context_scale
    local_demand_pressure = as_float(failure.get("local_demand_pressure_index"), 0.35)
    demand_context_confidence = as_float(failure.get("demand_context_confidence"), 0.0) * context_scale
    high_local_demand = as_bool(failure.get("high_local_demand_flag")) or local_demand_pressure >= 0.68
    effective_occupancy = max(
        occupancy,
        occupancy * 0.82 + local_demand_pressure * min(demand_context_confidence, 0.45),
    )

    value = comp_value_for_tier(comp, tier, stay)
    cost_low = int(round(value * as_float(comp.get("internal_cost_rate_low"), comp.get("estimated_internal_cost_rate", 0.5)) * cost_scale))
    cost_expected = int(round(value * as_float(comp.get("estimated_internal_cost_rate"), 0.5) * cost_scale))
    cost_high = int(round(value * as_float(comp.get("internal_cost_rate_high"), comp.get("estimated_internal_cost_rate", 0.5)) * cost_scale))
    perceived = value * as_float(comp.get("guest_perceived_value_multiplier"), 1.0)
    comp_fit = policy["comp_fit"].get(comp_code, {})
    fit = as_float(comp_fit.get(failure_category, comp_fit.get(guest_tier, comp_fit.get("default", 0.5))))
    property_modifier = property_fit_modifier(comp_code, failure)
    if property_context_confidence:
        fit *= 1 + (property_modifier - 1) * min(property_context_confidence, 0.9)
    fit *= fit_scale

    leakage_penalty = cost_expected * (0.25 + review_risk * 0.75)
    refund_penalty = 0.0
    if comp_code == "partial_room_refund":
        refund_penalty = cost_expected * (0.22 if severity >= 5 and responsibility >= 0.88 and reputation_risk >= 0.72 else 0.95)
        refund_penalty += cost_expected * max(0, refund_cost_pressure - 1) * (0.45 + rate_context_confidence * 0.35)

    operational_penalty = 0.0
    if not as_bool(failure.get("reported_in_stay")) and comp_code in {"room_upgrade", "late_checkout"}:
        operational_penalty += 10000
    if comp_code == "room_upgrade":
        operational_penalty += 165 * effective_occupancy if effective_occupancy >= 0.72 else 55 * effective_occupancy
        if high_demand_rate or high_local_demand:
            operational_penalty += max(upgrade_opportunity_cost, value * 0.18) * (0.85 + rate_context_confidence * 0.75)
    elif comp_code == "late_checkout":
        operational_penalty += 95 * effective_occupancy if effective_occupancy >= 0.86 else 18 * effective_occupancy
        if high_demand_rate or high_local_demand:
            operational_penalty += 55 * public_rate_pressure * (0.5 + rate_context_confidence)

    insufficient_penalty = max(0, tier - int(as_float(comp.get("max_tier_fit"), 5))) * 60
    score = fit * perceived * (0.7 + need / 160) - leakage_penalty - refund_penalty - operational_penalty - insufficient_penalty
    if comp_code == "late_checkout" and failure_category in {"room_readiness_delay", "noise_disruption"} and occupancy < 0.78:
        score += 70
    if comp_code == "parking_fee_waiver" and failure_category in {"valet_or_parking_delay", "billing_or_fee_dispute"}:
        score += 45
    if comp_code == "partial_room_refund" and severity >= 5 and responsibility >= 0.9 and reputation_risk >= 0.76:
        score += 240
    if high_demand_rate and comp_code in {"rooftop_f_and_b_credit", "spa_wellness_credit", "lobby_lounge_credit", "amenity_gesture"}:
        score += 58 * public_rate_pressure * (0.6 + rate_context_confidence)
    if high_local_demand and comp_code in {"rooftop_f_and_b_credit", "spa_wellness_credit", "lobby_lounge_credit", "amenity_gesture"}:
        score += 34 * local_demand_pressure * (0.5 + demand_context_confidence)
    if property_context_confidence and comp_code in {"rooftop_f_and_b_credit", "spa_wellness_credit", "lobby_lounge_credit"}:
        score += 24 * max(property_modifier - 1, 0) * (0.6 + property_context_confidence)

    return CandidateEvaluation(
        comp_code=comp_code,
        comp_label=str(comp["comp_label"]),
        score=score,
        guest_facing_value=value,
        internal_cost_low=min(cost_low, cost_expected, cost_high),
        internal_cost_expected=cost_expected,
        internal_cost_high=max(cost_low, cost_expected, cost_high),
        fit_score=fit,
        perceived_value=perceived,
        leakage_penalty=leakage_penalty + refund_penalty,
        operational_penalty=operational_penalty,
    )


def should_force_partial_refund(stay: dict[str, Any], failure: dict[str, Any], tier: int) -> bool:
    category = str(failure.get("failure_category"))
    severity = as_float(failure.get("severity"), 0)
    responsibility = as_float(failure.get("hotel_responsibility_score"), 0)
    review_risk = as_float(failure.get("review_risk_score"), 0)
    occupancy = as_float(failure.get("occupancy_pressure"), 0.5)
    guest_tier = str(stay.get("guest_tier"))
    after_checkout = not as_bool(failure.get("reported_in_stay"))
    high_guest_value = guest_tier in {"loyalty_guest", "vip_guest", "event_or_suite_guest"}
    severe_room_failure = category in {"room_readiness_delay", "housekeeping_miss"}
    constrained_recovery = occupancy >= 0.72 or after_checkout or high_guest_value
    return tier >= 5 and severe_room_failure and severity >= 5 and responsibility >= 0.93 and review_risk >= 0.72 and constrained_recovery


def _rank_candidates(
    stay: dict[str, Any],
    failure: dict[str, Any],
    catalog: list[dict[str, Any]],
    policy: dict[str, Any],
    scales: dict[str, float] | None = None,
) -> tuple[float, int, list[CandidateEvaluation]]:
    need = recovery_need_score(stay, failure, policy, as_float((scales or {}).get("need"), 1.0))
    tier = score_to_tier(need, policy)
    candidates = []
    raw_available = failure.get("available_comp_codes")
    if isinstance(raw_available, str):
        available = {value.strip() for value in raw_available.replace(";", ",").split(",") if value.strip()}
    elif raw_available:
        available = {str(value) for value in raw_available}
    else:
        available = None
    for comp in catalog:
        if available is not None and str(comp["comp_code"]) not in available:
            continue
        if tier < int(as_float(comp.get("min_tier_fit"), 1)):
            continue
        candidates.append(evaluate_candidate(comp, stay, failure, tier, need, policy, scales))
    candidates.sort(key=lambda item: item.score, reverse=True)
    if not candidates:
        manager_note = next(row for row in configured_comp_catalog(policy) if row["comp_code"] == "manager_note")
        candidates = [evaluate_candidate(manager_note, stay, failure, tier, need, policy, scales)]
    if should_force_partial_refund(stay, failure, tier):
        refund = next((item for item in candidates if item.comp_code == "partial_room_refund"), None)
        if refund is not None:
            candidates = [refund, *[item for item in candidates if item.comp_code != "partial_room_refund"]]
    return need, tier, candidates


def _counterfactuals(
    stay: dict[str, Any],
    failure: dict[str, Any],
    selected_code: str,
    catalog: list[dict[str, Any]],
    policy: dict[str, Any],
) -> tuple[list[str], list[str]]:
    messages: list[str] = []
    reason_codes: list[str] = []

    def compare(label: str, code: str, modified_stay: dict[str, Any], modified_failure: dict[str, Any]) -> None:
        _, _, ranked = _rank_candidates(modified_stay, modified_failure, catalog, policy)
        alternative = ranked[0]
        if alternative.comp_code != selected_code:
            messages.append(
                f"{label}: without this signal, the model would prefer {alternative.comp_label} at ${alternative.guest_facing_value}."
            )
            reason_codes.append(code)

    if as_float(failure.get("occupancy_pressure"), 0) >= 0.72 or as_bool(failure.get("high_local_demand_flag")):
        modified = dict(failure)
        modified.update({"occupancy_pressure": 0.45, "local_demand_pressure_index": 0.35, "high_local_demand_flag": False})
        compare("Operational availability changed the recommendation", "operational_pressure_changed_recovery", stay, modified)
    if as_float(failure.get("rate_context_confidence"), 0) > 0 and as_float(failure.get("public_rate_pressure_index"), 0.5) >= 0.72:
        modified = dict(failure)
        modified.update(
            {
                "public_rate_pressure_index": 0.5,
                "high_demand_rate_flag": False,
                "upgrade_opportunity_cost_proxy": 0,
                "refund_cost_pressure": 1,
                "rate_context_confidence": 0,
            }
        )
        compare("Public rate pressure changed the recommendation", "public_rate_pressure_changed_recovery", stay, modified)
    if as_float(failure.get("property_context_confidence"), 0) > 0:
        modified = dict(failure)
        modified.update(
            {
                "property_context_confidence": 0,
                "rooftop_f_and_b_fit_modifier": 1,
                "spa_wellness_fit_modifier": 1,
                "lobby_lounge_fit_modifier": 1,
                "parking_fee_fit_modifier": 1,
                "late_checkout_fit_modifier": 1,
                "room_upgrade_fit_modifier": 1,
            }
        )
        compare("Property fit changed the recommendation", "property_fit_changed_recovery", stay, modified)
    if as_float(stay.get("guest_value_score"), 0) >= 0.65:
        modified_stay = dict(stay)
        modified_stay["guest_value_score"] = 0.3
        compare("Guest relationship value changed the recommendation", "guest_value_changed_recovery", modified_stay, failure)
    return messages, reason_codes


def _stability(
    stay: dict[str, Any],
    failure: dict[str, Any],
    selected_code: str,
    catalog: list[dict[str, Any]],
    policy: dict[str, Any],
) -> float:
    fraction = as_float(policy.get("sensitivity", {}).get("perturbation_fraction"), 0.2)
    low = 1 - fraction
    high = 1 + fraction
    perturbations = [
        {},
        {"fit": low},
        {"fit": high},
        {"cost": low},
        {"cost": high},
        {"occupancy": low},
        {"occupancy": high},
        {"context": low},
        {"context": high},
        {"need": low},
        {"need": high},
    ]
    winners = []
    for scales in perturbations:
        _, _, ranked = _rank_candidates(stay, failure, catalog, policy, scales)
        winners.append(ranked[0].comp_code)
    for weight_name, weight_value in policy["recovery_need_weights"].items():
        for multiplier in (low, high):
            varied_weights = dict(policy["recovery_need_weights"])
            varied_weights[weight_name] = as_float(weight_value) * multiplier
            varied_policy = {**policy, "recovery_need_weights": varied_weights}
            _, _, ranked = _rank_candidates(stay, failure, catalog, varied_policy)
            winners.append(ranked[0].comp_code)
    return round(sum(code == selected_code for code in winners) / len(winners), 3)


def _confidence(stability: float, source_flags: str, policy: dict[str, Any]) -> str:
    if any(
        flag in source_flags
        for flag in {
            "weak_identity_or_reservation_match",
            "low_reservation_match_confidence",
            "unmatched_reservation",
            "low_crm_match_confidence",
            "unmatched_crm",
        }
    ):
        return "low"
    sensitivity = policy.get("sensitivity", {})
    if stability >= as_float(sensitivity.get("stable_threshold"), 0.8):
        if any(flag in source_flags for flag in {"severity_inferred", "ltv_imputed"}):
            return "moderate"
        return "high"
    if stability >= as_float(sensitivity.get("moderate_threshold"), 0.6):
        return "moderate"
    return "low"


def _direct_reason_codes(
    stay: dict[str, Any],
    failure: dict[str, Any],
    selected: CandidateEvaluation,
    manager_review: bool,
) -> list[str]:
    reasons: list[str] = []
    if str(stay.get("guest_tier")) in {"loyalty_guest", "vip_guest", "event_or_suite_guest"}:
        reasons.append("high_guest_relationship_value")
    if as_float(failure.get("hotel_responsibility_score"), 0) >= 0.7:
        reasons.append("hotel_responsible_failure")
    if as_float(failure.get("severity"), 0) >= 4:
        reasons.append("high_severity_issue")
    if as_float(failure.get("review_risk_score"), 0) >= 0.7:
        reasons.append("high_review_risk")
    if as_bool(failure.get("reported_in_stay")):
        reasons.append("recoverable_before_checkout")
    if selected.comp_code not in {"partial_room_refund", "future_stay_credit"} and selected.guest_facing_value > selected.internal_cost_expected:
        reasons.append("high_perceived_value_lower_estimated_cost")
    if as_float(stay.get("repeat_comp_review_risk"), 0) >= 0.6:
        reasons.append("repeat_comp_pattern_review_needed")
    if manager_review:
        reasons.append("manager_review_required")
    return reasons


def _build_explanation(
    stay: dict[str, Any],
    failure: dict[str, Any],
    selected: CandidateEvaluation,
    reasons: list[str],
    alternative: CandidateEvaluation | None,
    stability: float,
) -> str:
    category = format_label(str(failure.get("failure_category", "service issue")))
    tier = format_label(str(stay.get("guest_tier", "guest")))
    article = "an" if tier[:1].lower() in {"a", "e", "i", "o", "u"} else "a"
    timing = "before checkout" if as_bool(failure.get("reported_in_stay")) else "after checkout"
    rationale = ", ".join(reason.replace("_", " ") for reason in reasons[:4]) or "moderate recovery need"
    alternative_clause = ""
    if alternative is not None:
        alternative_clause = (
            f" The closest alternative was ${alternative.guest_facing_value} {alternative.comp_label}; "
            "the recommended gesture scored better on recovery fit, estimated cost, and operational constraints."
        )
    return (
        f"Recommend ${selected.guest_facing_value} {selected.comp_label} for {article} {tier} with a severity "
        f"{failure.get('severity')} {category} reported {timing}. Estimated internal cost is "
        f"${selected.internal_cost_low}-${selected.internal_cost_high}, not an observed property margin. "
        f"Rationale: {rationale}. Recommendation stability is {stability:.0%}.{alternative_clause}"
    )


def recommend_comp(
    stay: dict[str, Any],
    failure: dict[str, Any],
    comp_catalog: list[dict[str, Any]] | None = None,
    policy: dict[str, Any] | None = None,
) -> Recommendation:
    selected_policy = policy or load_policy_config()
    scenario = ScenarioInput.from_mapping({**stay, **failure})
    normalized_stay, normalized_failure = scenario.to_engine_inputs()
    catalog = comp_catalog or configured_comp_catalog(selected_policy)
    need, tier, ranked = _rank_candidates(normalized_stay, normalized_failure, catalog, selected_policy)
    selected = ranked[0]
    review_config = selected_policy["manager_review"]
    manager_review = (
        tier >= int(review_config["minimum_tier"])
        or selected.guest_facing_value >= int(review_config["minimum_guest_facing_value"])
        or normalized_stay["repeat_comp_review_risk"] >= as_float(review_config["repeat_comp_review_threshold"])
    )
    counterfactuals, causal_context_reasons = _counterfactuals(
        normalized_stay,
        normalized_failure,
        selected.comp_code,
        catalog,
        selected_policy,
    )
    stability = _stability(normalized_stay, normalized_failure, selected.comp_code, catalog, selected_policy)
    source_flags = str(stay.get("data_quality_flags", ""))
    confidence = _confidence(stability, source_flags, selected_policy)
    if (
        confidence == "high"
        and "public_rate_pressure_changed_recovery" in causal_context_reasons
        and str(normalized_failure.get("pricing_provenance", "")).startswith("sample_seed")
    ):
        confidence = "moderate"
    manager_review = manager_review or confidence == "low"
    reasons = _direct_reason_codes(normalized_stay, normalized_failure, selected, manager_review)
    for reason in causal_context_reasons:
        if reason not in reasons:
            reasons.append(reason)
    review_risk = round(as_float(normalized_failure.get("review_risk_score"), 0), 3)
    brand_risk = round(clamp(review_risk * 0.55 + need / 100 * 0.45, 0, 1), 3)
    relationship_value = as_float(normalized_stay.get("estimated_lifetime_value"), 0)
    expected_recovery_value = int(
        round(
            (relationship_value * 0.035 + as_float(normalized_stay.get("stay_value"), 0) * 0.16)
            * (need / 100)
        )
    )
    leakage_risk = round(clamp(selected.internal_cost_expected / max(expected_recovery_value, 1), 0, 1), 3)
    alternative_rows = [item for item in ranked if item.comp_code != selected.comp_code][:2]
    explanation = _build_explanation(
        normalized_stay,
        normalized_failure,
        selected,
        reasons,
        alternative_rows[0] if alternative_rows else None,
        stability,
    )
    return Recommendation(
        comp_code=selected.comp_code,
        comp_label=selected.comp_label,
        recommended_value=selected.guest_facing_value,
        estimated_internal_cost=selected.internal_cost_expected,
        internal_cost_low=selected.internal_cost_low,
        internal_cost_high=selected.internal_cost_high,
        recommended_tier=tier,
        recovery_need_score=need,
        profit_leakage_risk=leakage_risk,
        review_risk_score=review_risk,
        brand_impact_risk=brand_risk,
        expected_recovery_value=expected_recovery_value,
        manager_review_flag=manager_review,
        recommendation_stability=stability,
        decision_confidence=confidence,
        policy_id=str(selected_policy["policy_id"]),
        policy_version=str(selected_policy["policy_version"]),
        reason_codes=reasons,
        counterfactuals=counterfactuals,
        alternatives=[item.as_public_dict() for item in alternative_rows],
        score_components={
            "policy_score": round(selected.score, 2),
            "fit_score": round(selected.fit_score, 3),
            "perceived_value": round(selected.perceived_value, 2),
            "leakage_penalty": round(selected.leakage_penalty, 2),
            "operational_penalty": round(selected.operational_penalty, 2),
        },
        assumptions=[
            "Internal cost is a policy range, not observed property margin.",
            "Guest relationship value and recovery value are synthetic scenario inputs.",
            "Public context cannot substitute for live occupancy, inventory, or approved hotel policy.",
        ],
        explanation=explanation,
    )


def format_label(value: str) -> str:
    label = value.replace("_", " ")
    replacements = {
        "f and b": "F&B",
        "spa wellness": "spa/wellness",
        "event or suite guest": "event/suite guest",
    }
    for source, target in replacements.items():
        label = label.replace(source, target)
    return label
