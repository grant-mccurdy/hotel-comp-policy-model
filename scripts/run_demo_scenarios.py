from __future__ import annotations

import csv
from pathlib import Path

from common import PROJECT_ROOT, REPORT_DIR, ensure_dirs
from manager_app import scenario_to_recommendation
from recommend_scenario import money


SCENARIO_PATH = PROJECT_ROOT / "data" / "sample" / "scenarios" / "manager_scenarios.csv"
DEMO_REPORT_PATH = REPORT_DIR / "demo-scenario-recommendations.md"


def read_scenarios() -> list[dict[str, str]]:
    with SCENARIO_PATH.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def scenario_mapping(row: dict[str, str]) -> dict[str, object]:
    return {
        "property_context_confidence": 0.88,
        "rooftop_f_and_b_fit_modifier": 1.22,
        "spa_wellness_fit_modifier": 1.18,
        "lobby_lounge_fit_modifier": 1.12,
        "parking_fee_fit_modifier": 1.04,
        "late_checkout_fit_modifier": 1.04,
        "room_upgrade_fit_modifier": 1.08,
        **row,
    }
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


def render_report(scenarios: list[dict[str, str]]) -> str:
    lines = [
        "# Demo Scenario Recommendations",
        "",
        "These named synthetic scenarios demonstrate recommendations from the generated shadow-validation candidate.",
        "",
        "No Proper Hotels data, internal rates, guest records, comp history, or proprietary policy is used.",
        "",
    ]
    for row in scenarios:
        _, recommendation = scenario_to_recommendation(scenario_mapping(row))
        suffix = " + manager note" if recommendation.recommended_tier >= 3 and recommendation.comp_code != "manager_note" else ""
        reasons = ", ".join(reason.replace("_", " ") for reason in recommendation.reason_codes)
        lines.extend(
            [
                f"## {row['scenario_id']}: {row['scenario_name']}",
                "",
                f"**Recommended comp:** {money(recommendation.recommended_value)} {recommendation.comp_label}{suffix}",
                "",
                f"- Guest: `{format_label(row['guest_tier'])}` / `{format_label(row['traveler_segment'])}`",
                f"- Stay value: `{money(float(row['stay_value']))}`; estimated lifetime value: `{money(float(row['estimated_lifetime_value']))}`",
                f"- Issue: `{format_label(row['failure_category'])}`; severity `{row['severity']}/5`; hotel responsibility `{row['hotel_responsibility']}`",
                f"- Estimated internal cost range: `{money(recommendation.internal_cost_low)}-{money(recommendation.internal_cost_high)}`",
                f"- Policy assumption-stress pass rate: `{recommendation.joint_guardrail_pass_probability:.1%}`",
                f"- Manager review required: `{str(recommendation.manager_review_flag).lower()}`",
                f"- Policy: `{recommendation.policy_label}` (`{recommendation.policy_id}`)",
                f"- Comparison version: `{recommendation.comparison_version}`",
                f"- Scenario note: {row['scenario_note']}",
                f"- Reason codes: `{reasons}`",
                f"- Confirm before use: `{' | '.join(recommendation.confirmation_items)}`",
                "",
                recommendation.explanation,
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    ensure_dirs()
    if not SCENARIO_PATH.exists():
        print(f"Missing scenario catalog: {SCENARIO_PATH}")
        return 1
    scenarios = read_scenarios()
    DEMO_REPORT_PATH.write_text(render_report(scenarios), encoding="utf-8")
    print(f"Wrote demo scenario recommendations: {DEMO_REPORT_PATH.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
