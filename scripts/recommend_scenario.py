from __future__ import annotations

import argparse
import json
import sys
from typing import Any

try:
    from .policy_config import comp_catalog
    from .policy_engine import Recommendation, recommend_comp
    from .scenario_contract import (
        FAILURE_CATEGORIES,
        GUEST_TIER_SCORE,
        ScenarioInput,
        ScenarioValidationError,
        derive_guest_value_score,
    )
except ImportError:
    from policy_config import comp_catalog
    from policy_engine import Recommendation, recommend_comp
    from scenario_contract import (
        FAILURE_CATEGORIES,
        GUEST_TIER_SCORE,
        ScenarioInput,
        ScenarioValidationError,
        derive_guest_value_score,
    )


def money(value: int | float) -> str:
    return f"${float(value):,.0f}"


def parse_bool_arg(value: str) -> bool:
    normalized = str(value).lower().strip()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError("Expected true/false")


def namespace_mapping(args: argparse.Namespace) -> dict[str, Any]:
    return {key: value for key, value in vars(args).items() if key != "format"}


def build_inputs(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    return ScenarioInput.from_mapping(namespace_mapping(args)).to_engine_inputs()


def recommendation_to_dict(recommendation: Recommendation) -> dict[str, Any]:
    return {
        "comp_code": recommendation.comp_code,
        "comp_label": recommendation.comp_label,
        "recommended_value": recommendation.recommended_value,
        "estimated_internal_cost": recommendation.estimated_internal_cost,
        "internal_cost_low": recommendation.internal_cost_low,
        "internal_cost_high": recommendation.internal_cost_high,
        "recommended_tier": recommendation.recommended_tier,
        "recovery_need_score": recommendation.recovery_need_score,
        "profit_leakage_risk": recommendation.profit_leakage_risk,
        "review_risk_score": recommendation.review_risk_score,
        "brand_impact_risk": recommendation.brand_impact_risk,
        "expected_recovery_value": recommendation.expected_recovery_value,
        "manager_review_required": recommendation.manager_review_flag,
        "recommendation_stability": recommendation.recommendation_stability,
        "decision_confidence": recommendation.decision_confidence,
        "policy_id": recommendation.policy_id,
        "policy_version": recommendation.policy_version,
        "reason_codes": recommendation.reason_codes,
        "counterfactuals": recommendation.counterfactuals,
        "alternatives": recommendation.alternatives,
        "score_components": recommendation.score_components,
        "assumptions": recommendation.assumptions,
        "explanation": recommendation.explanation,
    }


def render_text(result: dict[str, Any]) -> str:
    suffix = " + manager note" if result["recommended_tier"] >= 3 and result["comp_code"] != "manager_note" else ""
    reasons = "\n".join(f"- {reason.replace('_', ' ')}" for reason in result["reason_codes"])
    counterfactuals = "\n".join(f"- {item}" for item in result["counterfactuals"]) or "- No tested context signal changed the selected gesture."
    alternatives = "\n".join(
        f"- {money(item['guest_facing_value'])} {item['comp_label']} (estimated cost {money(item['internal_cost_low'])}-{money(item['internal_cost_high'])})"
        for item in result["alternatives"]
    )
    review_line = "Yes" if result["manager_review_required"] else "No"
    return f"""Recommended recovery: {money(result['recommended_value'])} {result['comp_label']}{suffix}

Estimated internal cost range: {money(result['internal_cost_low'])}-{money(result['internal_cost_high'])}
Recovery need score: {result['recovery_need_score']}
Decision confidence: {result['decision_confidence']} ({result['recommendation_stability']:.0%} stability)
Manager review required: {review_line}
Policy version: {result['policy_version']}

Why:
{reasons}

What changed the decision:
{counterfactuals}

Closest alternatives:
{alternatives}

Explanation:
{result['explanation']}
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Recommend a luxury hotel recovery gesture for a validated synthetic service-failure scenario."
    )
    parser.add_argument("--guest-tier", required=True, choices=sorted(GUEST_TIER_SCORE))
    parser.add_argument("--traveler-segment", default="coastal_weekend")
    parser.add_argument("--stay-value", required=True, type=float)
    parser.add_argument("--estimated-lifetime-value", required=True, type=float)
    parser.add_argument("--guest-value-score", type=float)
    parser.add_argument("--repeat-comp-review-risk", "--repeat-comp-abuse-risk", dest="repeat_comp_review_risk", type=float, default=0.05)
    parser.add_argument("--nightly-rate", type=float, default=650)
    parser.add_argument("--failure-category", required=True, choices=sorted(FAILURE_CATEGORIES))
    parser.add_argument("--failure-type", default="outcome", choices=["outcome", "process"])
    parser.add_argument("--severity", required=True, type=int)
    parser.add_argument("--hotel-responsibility", required=True, type=float)
    parser.add_argument("--reported-in-stay", required=True, type=parse_bool_arg)
    parser.add_argument("--resolution-delay-minutes", type=int, default=90)
    parser.add_argument("--sentiment-intensity", type=float, default=0.65)
    parser.add_argument("--review-risk", required=True, type=float)
    parser.add_argument("--occupancy-pressure", required=True, type=float)
    parser.add_argument("--public-rate-pressure", type=float, default=0.5)
    parser.add_argument("--high-demand-rate", type=parse_bool_arg, default=False)
    parser.add_argument("--upgrade-opportunity-cost", type=float, default=0)
    parser.add_argument("--refund-cost-pressure", type=float, default=1.0)
    parser.add_argument("--rate-context-confidence", type=float, default=0.0)
    parser.add_argument("--pricing-provenance", default="manual_scenario_context")
    parser.add_argument("--has-rooftop-f-and-b", type=parse_bool_arg, default=True)
    parser.add_argument("--has-lobby-lounge", type=parse_bool_arg, default=True)
    parser.add_argument("--has-spa-wellness", type=parse_bool_arg, default=True)
    parser.add_argument("--has-pool-or-rooftop", type=parse_bool_arg, default=True)
    parser.add_argument("--has-parking-or-fee-recovery-context", type=parse_bool_arg, default=True)
    parser.add_argument("--property-context-confidence", type=float, default=0.88)
    parser.add_argument("--rooftop-f-and-b-fit-modifier", type=float, default=1.22)
    parser.add_argument("--spa-wellness-fit-modifier", type=float, default=1.18)
    parser.add_argument("--lobby-lounge-fit-modifier", type=float, default=1.12)
    parser.add_argument("--parking-fee-fit-modifier", type=float, default=1.04)
    parser.add_argument("--late-checkout-fit-modifier", type=float, default=1.04)
    parser.add_argument("--room-upgrade-fit-modifier", type=float, default=1.08)
    parser.add_argument("--review-context-confidence", type=float, default=0.0)
    parser.add_argument("--local-demand-pressure", type=float, default=0.35)
    parser.add_argument("--high-local-demand", type=parse_bool_arg, default=False)
    parser.add_argument("--demand-context-confidence", type=float, default=0.0)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        scenario = ScenarioInput.from_mapping(namespace_mapping(args))
    except ScenarioValidationError as exc:
        if args.format == "json":
            print(json.dumps({"error": "invalid_scenario", "fields": exc.errors}, indent=2, sort_keys=True))
        else:
            print("Invalid scenario:", file=sys.stderr)
            for field, message in sorted(exc.errors.items()):
                print(f"- {field}: {message}", file=sys.stderr)
        return 2
    stay, failure = scenario.to_engine_inputs()
    recommendation = recommend_comp(stay, failure, comp_catalog())
    result = recommendation_to_dict(recommendation)
    result["inputs"] = {"stay": stay, "failure": failure}
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(render_text(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
