from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

try:  # Package imports for the Worker runtime.
    from .evaluate_policy_strategies import recommend_policy_strategy
    from .policy_engine import as_float, service_recovery_floor_score
    from .scenario_contract import ScenarioInput
except ImportError:  # Direct script and existing local-test compatibility.
    from evaluate_policy_strategies import recommend_policy_strategy
    from policy_engine import as_float, service_recovery_floor_score
    from scenario_contract import ScenarioInput


REASON_TEXT = {
    "hotel_responsible_failure": "The hotel bears substantial responsibility for the service failure.",
    "high_severity_issue": "The disruption is severe enough to require a meaningful recovery gesture.",
    "high_review_risk": "The unresolved experience carries elevated reputation risk.",
    "recoverable_before_checkout": "There is still time to recover the experience during the stay.",
    "high_guest_relationship_value": "The guest relationship supports additional generosity above the recovery floor.",
    "high_perceived_value_lower_estimated_cost": "The gesture offers visible guest value without immediate room-rate erosion.",
    "repeat_comp_pattern_review_needed": "The repeat-comp pattern requires review but does not remove the recovery obligation.",
    "manager_review_required": "The exposure or operating context requires manager review.",
    "availability_requires_confirmation": "Live availability must be confirmed before the gesture is offered.",
}

LOW_DATA_CONFIDENCE_FLAGS = {
    "weak_identity_or_reservation_match",
    "low_reservation_match_confidence",
    "unmatched_reservation",
    "low_crm_match_confidence",
    "unmatched_crm",
}


@dataclass(frozen=True)
class DecisionResponse:
    schema_version: str
    runtime_bundle_version: str
    runtime_bundle_checksum: str
    evidence_class: str
    scenario: dict[str, Any]
    recommendation: dict[str, Any]
    alternatives: list[dict[str, Any]]
    reasoning: dict[str, Any]
    confidence: dict[str, Any]
    approval: dict[str, Any]
    policy_evidence: dict[str, Any]
    required_confirmations: list[str]
    assumptions: list[str]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _reason_codes(scenario: ScenarioInput, result: dict[str, Any], manager_review: bool) -> list[str]:
    reasons: list[str] = []
    if scenario.hotel_responsibility >= 0.7:
        reasons.append("hotel_responsible_failure")
    if scenario.severity >= 4:
        reasons.append("high_severity_issue")
    if scenario.review_risk >= 0.7:
        reasons.append("high_review_risk")
    if scenario.reported_in_stay:
        reasons.append("recoverable_before_checkout")
    if scenario.guest_value_score >= 0.65:
        reasons.append("high_guest_relationship_value")
    if (
        str(result["comp_code"]) not in {"partial_room_refund", "future_stay_credit"}
        and as_float(result["recommended_value"]) > as_float(result["internal_cost_mid"])
    ):
        reasons.append("high_perceived_value_lower_estimated_cost")
    if scenario.repeat_comp_review_risk >= 0.6:
        reasons.append("repeat_comp_pattern_review_needed")
    if not scenario.availability_confirmed:
        reasons.append("availability_requires_confirmation")
    if manager_review:
        reasons.append("manager_review_required")
    return reasons


def _scenario_stability(
    mapping: dict[str, Any],
    policy_id: str,
    policy: dict[str, Any],
    scenario_config: dict[str, Any],
    selected_code: str,
) -> float:
    variants: list[dict[str, Any]] = [dict(mapping)]
    for field in ("hotel_responsibility", "sentiment_intensity", "review_risk", "occupancy_pressure"):
        value = as_float(mapping.get(field), 0.5)
        for delta in (-0.05, 0.05):
            variants.append({**mapping, field: max(0.0, min(1.0, value + delta))})
    winners = [
        str(recommend_policy_strategy(row, policy_id, policy, scenario_config)["comp_code"])
        for row in variants
    ]
    return round(sum(code == selected_code for code in winners) / len(winners), 3)


def _confidence_level(stability: float, source_flags: str, availability_confirmed: bool) -> str:
    flags = {value for value in source_flags.split(";") if value}
    if flags & LOW_DATA_CONFIDENCE_FLAGS or stability < 0.6:
        return "low"
    if stability >= 0.8 and availability_confirmed:
        return "high"
    return "moderate"


def _delivery_timing(comp_code: str, reported_in_stay: bool) -> str:
    if not reported_in_stay:
        return "Manager follow-up within 24 hours after checkout"
    if comp_code in {"room_upgrade", "late_checkout"}:
        return "Before checkout, after live inventory confirmation"
    return "During the stay, as soon as the gesture can be delivered"


def _hospitality_note(failure_category: str, comp_label: str, value: int) -> str:
    issue = failure_category.replace("_", " ").replace("f and b", "food and beverage")
    experiential = {"late checkout", "room upgrade", "manager note and personal follow-up"}
    gesture = comp_label if value == 0 or comp_label in experiential else f"a ${value} {comp_label}"
    return (
        f"We missed the mark with the {issue}, and I am sorry. "
        f"I would like to offer {gesture} and make sure our team follows through promptly."
    )


def build_decision(mapping: dict[str, Any], bundle: dict[str, Any]) -> DecisionResponse:
    scenario = ScenarioInput.from_mapping(mapping)
    normalized_mapping = {**mapping, **asdict(scenario)}
    normalized_mapping["available_comp_codes"] = list(scenario.available_comp_codes)
    selection = bundle["selection"]
    policy = bundle["policy"]
    scenario_config = bundle["scenario_config"]
    policy_id = str(selection["policy_id"])
    result = recommend_policy_strategy(normalized_mapping, policy_id, policy, scenario_config)

    stay, failure = scenario.to_engine_inputs()
    floor_score = service_recovery_floor_score(stay, failure, policy)
    recovery_need = as_float(result["reference_recovery_need_score"])
    relationship_adjustment = round(max(0.0, recovery_need - floor_score), 2)
    manager_review = bool(result["manager_review_required"]) or not scenario.availability_confirmed
    selected_code = str(result["comp_code"])
    stability = _scenario_stability(
        normalized_mapping,
        policy_id,
        policy,
        scenario_config,
        selected_code,
    )
    confidence_level = _confidence_level(
        stability,
        str(mapping.get("data_quality_flags", "")),
        scenario.availability_confirmed,
    )
    reason_codes = _reason_codes(scenario, result, manager_review)
    recommended_value = int(as_float(result["recommended_value"]))
    comp_label = str(result["comp_label"])

    confirmations = [
        "Confirm the failure severity, hotel responsibility, and guest context.",
        "Confirm the selected gesture is operationally available and its actual marginal cost.",
    ]
    if manager_review:
        confirmations.append("Record the manager decision and any override reason before delivery.")

    approval_level = "senior manager review" if int(result["reference_recovery_tier"]) >= 5 or recommended_value >= 400 else "manager confirmation"
    if not manager_review:
        approval_level = "within configured recovery band"

    return DecisionResponse(
        schema_version="comp-decision-response-v1",
        runtime_bundle_version=str(bundle["bundle_version"]),
        runtime_bundle_checksum=str(bundle["bundle_checksum"]),
        evidence_class=str(bundle["evidence_class"]),
        scenario={
            "guest_tier": scenario.guest_tier,
            "failure_category": scenario.failure_category,
            "severity": scenario.severity,
            "hotel_responsibility": scenario.hotel_responsibility,
            "reported_in_stay": scenario.reported_in_stay,
            "recovery_floor_score": floor_score,
            "relationship_adjustment": relationship_adjustment,
            "recovery_need_score": recovery_need,
            "recovery_tier": int(result["reference_recovery_tier"]),
        },
        recommendation={
            "comp_code": selected_code,
            "comp_label": comp_label,
            "guest_facing_value": recommended_value,
            "internal_cost_low": int(as_float(result["internal_cost_low"])),
            "internal_cost_expected": int(as_float(result["internal_cost_mid"])),
            "internal_cost_high": int(as_float(result["internal_cost_high"])),
            "delivery_timing": _delivery_timing(selected_code, scenario.reported_in_stay),
            "hospitality_note_template": _hospitality_note(
                scenario.failure_category,
                comp_label,
                recommended_value,
            ),
        },
        alternatives=list(result["alternatives"]),
        reasoning={
            "reason_codes": reason_codes,
            "plain_language": [REASON_TEXT[code] for code in reason_codes],
            "selection_rule": (
                "Meet the configured recovery and feasibility safeguards first, then choose the lowest modeled-cost "
                "eligible gesture. Guest relationship value can add generosity but cannot lower the recovery floor."
            ),
        },
        confidence={
            "level": confidence_level,
            "input_sensitivity_stability": stability,
            "meaning": (
                "Stability under small input changes and completeness of the supplied context; "
                "not a probability that the recommendation will recover the guest."
            ),
        },
        approval={
            "manager_review_required": manager_review,
            "approval_path": approval_level,
            "repeat_comp_pattern_changes_recovery_floor": False,
        },
        policy_evidence={
            "policy_id": policy_id,
            "policy_label": str(selection["policy_label"]),
            "policy_version": str(policy["policy_version"]),
            "comparison_version": str(scenario_config["comparison_version"]),
            "synthetic_cases": int(as_float(selection["cases"])),
            "joint_guardrail_pass_probability": as_float(selection["joint_guardrail_pass_probability"]),
            "status": "shadow_evaluation_candidate",
        },
        required_confirmations=confirmations,
        assumptions=[
            "The current policy comparison and operating outcomes are synthetic workflow evidence.",
            "Public property context anchors guest-facing options, not internal cost or margin.",
            "Actual inventory, marginal cost, approved policy, and recovery outcomes are unavailable.",
        ],
    )
