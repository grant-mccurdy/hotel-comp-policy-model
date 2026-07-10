from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict

from common import COMP_RECOMMENDATIONS_PATH, REPORT_DIR, ensure_dirs, read_csv_rows
from policy_engine import as_float


REPORT_PATH = REPORT_DIR / "policy-sensitivity.md"


def median(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def render_report(rows: list[dict[str, str]]) -> str:
    stabilities = [as_float(row.get("recommendation_stability"), 0) for row in rows]
    confidences = Counter(row.get("decision_confidence", "unknown") for row in rows)
    comp_counts = Counter(row.get("comp_code", "unknown") for row in rows)
    cost_low = sum(as_float(row.get("internal_cost_low"), 0) for row in rows)
    cost_expected = sum(as_float(row.get("estimated_internal_cost"), 0) for row in rows)
    cost_high = sum(as_float(row.get("internal_cost_high"), 0) for row in rows)
    context_changed = sum(bool(row.get("recommendation_counterfactuals", "").strip()) for row in rows)
    low_stability = [row for row in rows if as_float(row.get("recommendation_stability"), 0) < 0.6]
    cost_exceeds_value = sum(
        as_float(row.get("estimated_internal_cost"), 0) > as_float(row.get("expected_recovery_value"), 0)
        for row in rows
    )
    by_tier: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_tier[row.get("guest_tier", "unknown")].append(row)
    max_comp, max_count = comp_counts.most_common(1)[0] if comp_counts else ("", 0)
    lines = [
        "# Policy Sensitivity And Stability",
        "",
        "This report stress-tests a synthetic policy simulation. It does not validate business outcomes or estimate causal recovery effects.",
        "",
        "## Stability Summary",
        "",
        f"- Cases evaluated: `{len(rows)}`",
        f"- Median recommendation stability: `{median(stabilities):.1%}`",
        f"- High-confidence cases: `{confidences['high']}`",
        f"- Moderate-confidence cases: `{confidences['moderate']}`",
        f"- Low-confidence cases: `{confidences['low']}`",
        f"- Cases where a tested context removal changed the gesture: `{context_changed}`",
        f"- Cases below 60% stability: `{len(low_stability)}`",
        f"- Most common gesture: `{max_comp}` ({max_count / max(len(rows), 1):.1%})",
        "",
        "Each recommendation is rescored under ±20% perturbations to fit, cost, occupancy, context, the overall recovery-need scale, and every individual recovery-need weight. Stability is the share of perturbations that preserve the selected gesture.",
        "",
        "## Cost Uncertainty",
        "",
        "| Measure | Synthetic run |",
        "| --- | ---: |",
        f"| Low estimated internal-cost bound | ${cost_low:,.0f} |",
        f"| Midpoint policy estimate | ${cost_expected:,.0f} |",
        f"| High estimated internal-cost bound | ${cost_high:,.0f} |",
        f"| Cases where midpoint cost exceeds modeled recovery value | {cost_exceeds_value} |",
        "",
        "The range is intentional. Public prices can anchor guest-facing value, but property contribution margin remains unavailable.",
        "",
        "## Stability By Guest Context",
        "",
        "| Guest context | Cases | Average stability | Low-confidence cases |",
        "| --- | ---: | ---: | ---: |",
    ]
    for guest_tier, group in sorted(by_tier.items()):
        average = statistics.mean(as_float(row.get("recommendation_stability"), 0) for row in group)
        low = sum(row.get("decision_confidence") == "low" for row in group)
        lines.append(f"| {guest_tier.replace('_', ' ')} | {len(group)} | {average:.1%} | {low} |")
    lines.extend(
        [
            "",
            "## Lowest-Stability Cases",
            "",
            "| Case | Issue | Recommendation | Stability | Alternatives |",
            "| --- | --- | --- | ---: | --- |",
        ]
    )
    for row in sorted(rows, key=lambda item: as_float(item.get("recommendation_stability"), 0))[:10]:
        try:
            alternatives = json.loads(row.get("recommendation_alternatives_json", "[]"))
        except json.JSONDecodeError:
            alternatives = []
        alternative_labels = ", ".join(str(item.get("comp_label")) for item in alternatives)
        lines.append(
            f"| `{row.get('recovery_case_id', '')}` | {row.get('failure_category', '').replace('_', ' ')} | "
            f"{row.get('comp_label', '')} | {as_float(row.get('recommendation_stability'), 0):.1%} | {alternative_labels} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- High stability means the selected gesture survives the tested policy perturbations; it does not mean the gesture is empirically optimal.",
            "- Low stability should trigger manager review and parameter discussion rather than a stronger automated claim.",
            "- Real comp decisions, overrides, satisfaction recovery, reviews, and repeat-stay outcomes are required for outcome validation.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    ensure_dirs()
    if not COMP_RECOMMENDATIONS_PATH.exists():
        print("Missing recommendations. Run `make recommend` first.")
        return 1
    _, rows = read_csv_rows(COMP_RECOMMENDATIONS_PATH)
    REPORT_PATH.write_text(render_report(rows), encoding="utf-8")
    print(f"Wrote policy sensitivity report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
