from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from html import escape

from common import (
    COMP_POLICY_AUDIT_PATH,
    COMP_RECOMMENDATIONS_PATH,
    EXTERNAL_CONTEXT_MODEL_IMPACT_PATH,
    LOCAL_DEMAND_CONTEXT_PATH,
    PROPERTY_CONTEXT_PATH,
    PROPER_PUBLIC_CONTEXT_PATH,
    PUBLIC_PRICING_CONTEXT_PATH,
    RECOVERY_CASE_MART_PATH,
    REVIEW_RISK_CONTEXT_PATH,
    REPORT_DIR,
    PROJECT_ROOT,
    ensure_dirs,
    read_csv_rows,
)
from policy_engine import as_float
from stakeholder_report import build_scenario_presentations, render_stakeholder_page


SAMPLE_RECOMMENDATIONS_REPORT = REPORT_DIR / "sample-recommendations.md"
EXECUTIVE_BRIEF_REPORT = REPORT_DIR / "executive-comp-optimization-brief.md"
DASHBOARD_REPORT = REPORT_DIR / "comp-optimization-dashboard.html"
DISCUSSION_BRIEF_REPORT = REPORT_DIR / "luxury-hotel-comp-optimization-discussion-brief.md"
STAKEHOLDER_REPORT = PROJECT_ROOT / "index.html"


def money(value: str | int | float) -> str:
    try:
        return f"${float(value):,.0f}"
    except (TypeError, ValueError):
        return "$0"


def aggregate_sum(rows: list[dict[str, str]], field: str) -> float:
    return sum(as_float(row.get(field), 0) for row in rows)


def format_label(value: str) -> str:
    label = value.replace("_", " ")
    return label.replace("f and b", "F&B").replace("spa wellness", "spa/wellness").replace("event or suite", "event/suite")


def top_sum(
    rows: list[dict[str, str]], group_field: str, value_field: str, limit: int = 8
) -> list[tuple[str, float]]:
    totals: dict[str, float] = defaultdict(float)
    for row in rows:
        totals[row[group_field]] += as_float(row.get(value_field), 0)
    return sorted(totals.items(), key=lambda item: item[1], reverse=True)[:limit]


def parse_json_list(value: str) -> list[dict[str, object]]:
    try:
        parsed = json.loads(value or "[]")
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def choose_sample_rows(recommendations: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = sorted(
        recommendations,
        key=lambda row: (
            as_float(row.get("recommended_tier"), 0),
            as_float(row.get("recovery_need_score"), 0),
            as_float(row.get("recommended_comp_value"), 0),
        ),
        reverse=True,
    )
    selected: list[dict[str, str]] = []
    seen_comp: set[str] = set()
    for row in rows:
        if row["comp_code"] in seen_comp:
            continue
        selected.append(row)
        seen_comp.add(row["comp_code"])
        if len(selected) >= 8:
            break
    return selected


def render_sample_recommendations(recommendations: list[dict[str, str]]) -> str:
    lines = [
        "# Sample Recovery Recommendations",
        "",
        "These synthetic cases demonstrate an explainable service-recovery policy in a Santa Monica luxury lifestyle context.",
        "No Proper Hotels guest records, comp history, internal rates, margins, inventory, or proprietary policy are used.",
        "",
    ]
    for index, row in enumerate(choose_sample_rows(recommendations), start=1):
        alternatives = parse_json_list(row.get("recommendation_alternatives_json", "[]"))
        alternative_text = ", ".join(
            f"{money(item.get('guest_facing_value', 0))} {item.get('comp_label', '')}" for item in alternatives
        )
        lines.extend(
            [
                f"## Scenario {index}: {format_label(row['failure_category']).title()}",
                "",
                f"**Recommended recovery:** {money(row['recommended_comp_value'])} {row['comp_label']}",
                "",
                f"- Guest context: `{format_label(row['guest_tier'])}` / `{format_label(row['traveler_segment'])}`",
                f"- Stay value: `{money(row['stay_value'])}`; estimated relationship value: `{money(row['estimated_lifetime_value'])}`",
                f"- Severity: `{row['severity']}/5`; hotel responsibility: `{row['hotel_responsibility_score']}`",
                f"- Estimated internal-cost range: `{money(row['internal_cost_low'])}-{money(row['internal_cost_high'])}`",
                f"- Decision confidence: `{row['decision_confidence']}`; stability: `{as_float(row['recommendation_stability']):.0%}`",
                f"- Manager review required: `{row['manager_review_flag']}`",
                f"- Closest alternatives: `{alternative_text}`",
                f"- Decision-changing counterfactual: `{row.get('recommendation_counterfactuals') or 'No tested context removal changed the gesture.'}`",
                "",
                row["recommendation_explanation"],
                "",
            ]
        )
    return "\n".join(lines)


def render_executive_brief(
    recommendations: list[dict[str, str]],
    audit_rows: list[dict[str, str]],
    pricing_rows: list[dict[str, str]],
    property_rows: list[dict[str, str]],
    proper_anchor_rows: list[dict[str, str]],
    review_context_rows: list[dict[str, str]],
    demand_rows: list[dict[str, str]],
    impact_rows: list[dict[str, str]],
) -> str:
    audit_counts = Counter(row["audit_class"] for row in audit_rows)
    comp_counts = Counter(row["comp_label"] for row in recommendations)
    manager_reviews = sum(row["manager_review_flag"] == "true" for row in recommendations)
    low_confidence = sum(row.get("decision_confidence") == "low" for row in recommendations)
    data_holds = audit_counts["data_quality_hold"]
    stabilities = [as_float(row.get("recommendation_stability"), 0) for row in recommendations]
    context_changed = sum(row.get("recommendation_changed") == "true" for row in impact_rows)
    total_low_cost = aggregate_sum(recommendations, "internal_cost_low")
    total_mid_cost = aggregate_sum(recommendations, "estimated_internal_cost")
    total_high_cost = aggregate_sum(recommendations, "internal_cost_high")
    refunds = sum(row["comp_code"] == "partial_room_refund" for row in recommendations)
    example = build_scenario_presentations()[0]
    observed_pricing = any(row.get("pricing_provenance") == "observed_public_market_context" for row in pricing_rows)
    lines = [
        "# Service Recovery Decision Brief",
        "",
        "## Executive Decision",
        "",
        "Adopt a tiered service-recovery policy that preserves managerial judgment while standardizing three decisions: how much recovery is justified, which gesture best fits the failure, and when weak data or high exposure requires review.",
        "",
        "The target is intelligent generosity, not minimum comp spend. High-perceived-value property experiences should be considered before direct room-rate erosion when they fit the failure and operational conditions.",
        "",
        "> **Evidence boundary:** all operating cases and historical comp actions in this run are synthetic. Counts below demonstrate workflow behavior; they are not Proper Hotels findings or projected savings.",
        "",
        "## Illustrative Policy Run",
        "",
        "| Signal | Synthetic result | Management use |",
        "| --- | ---: | --- |",
        f"| Service-failure cases scored | {len(recommendations)} | Demonstrates batch decisioning |",
        f"| Median recommendation stability | {statistics.median(stabilities):.0%} | Identifies decisions robust to ±20% parameter changes |",
        f"| Manager-review cases | {manager_reviews} | Preserves human approval for high-exposure decisions |",
        f"| Low-confidence cases | {low_confidence} | Avoids false certainty |",
        f"| Data-quality holds | {data_holds} | Prevents weak joins from becoming manager or guest judgments |",
        f"| Direct room refunds | {refunds} | Reserves rate erosion for severe cases |",
        f"| Estimated internal-cost range | {money(total_low_cost)}-{money(total_high_cost)} | Shows assumption uncertainty; midpoint {money(total_mid_cost)} |",
        "",
        "## Simulated Policy Audit",
        "",
        "| Audit class | Cases | Intended decision |",
        "| --- | ---: | --- |",
        f"| Under-recovered | {audit_counts['under_recovered']} | Consider a stronger or better-timed gesture |",
        f"| Potentially over-comped | {audit_counts['over_comped']} | Review consistency and estimated cost |",
        f"| Aligned recovery | {audit_counts['aligned_recovery']} | Preserve the simulated policy decision |",
        f"| Manager review | {audit_counts['manager_review_required']} | Require human approval |",
        f"| Data-quality hold | {audit_counts['data_quality_hold']} | Resolve source matching first |",
        "",
        "These classes compare one synthetic historical policy with the proposed simulated policy. They demonstrate the audit mechanism, not observed leakage or recovered profit.",
        "",
        "## Property-Relevant Evidence",
        "",
        f"- Official Santa Monica Proper public anchors: `{len(proper_anchor_rows)}`",
        f"- Public property/competitive-set profiles: `{len(property_rows)}`",
        f"- Pricing context mode: `{'observed public quotes' if observed_pricing else 'reproducible sample-seed stress test'}`",
        f"- Controlled context comparisons changing a recommendation: `{context_changed}/{len(impact_rows)}`",
        f"- Review-risk context rows: `{len(review_context_rows)}`; local-demand context rows: `{len(demand_rows)}`",
        "",
        "Official public sources establish that property-aligned recovery can include Palma or Calabra dining, Surya Spa or Recovery Suite experiences, late checkout, destination-fee relief, valet relief, and room-category gestures. Public prices anchor guest-facing denominations only; they do not reveal contribution margin.",
        "",
        "## Example Decision",
        "",
        f"**Recommended recovery:** {example['amount']} {example['gesture']}",
        "",
        f"- Working internal-cost range: `{example['cost_range']}`",
        f"- Approval path: `{example['approval']}`",
        f"- Decision robustness: `{example['robustness']}`",
        f"- What would change it: `{example['counterfactual']}`",
        "",
        "For a loyalty guest facing a severity-4, hotel-responsible room-readiness delay, the policy favors a property-aligned dining credit over immediate room-rate erosion. The decision protects an important guest relationship while the stay can still be recovered, and manager approval remains part of the path.",
        "",
        "## Recommended Operating Design",
        "",
        "- Auto-recommend only when source matching, policy stability, and operational availability are adequate.",
        "- Require manager approval for severe failures, high guest-facing value, unstable recommendations, or repeat-comp pattern review.",
        "- Record accepted, rejected, and overridden recommendations with reason codes.",
        "- Measure post-recovery satisfaction, review outcome, repeat stay, and actual marginal cost before training an outcome model.",
        "- Treat public rate, property, review, and demand context as bounded supplements to internal systems.",
        "",
        "## Data Required For A Pilot",
        "",
        "- Historical comp actions, approval notes, policy versions, and manager overrides.",
        "- Post-recovery satisfaction, review outcomes, repeat stays, and cancellations.",
        "- Contribution-margin ranges by comp type.",
        "- Live occupancy, inventory, outlet capacity, staffing, and room-type constraints.",
        "- A jointly reviewed severity, responsibility, and approval taxonomy.",
        "",
    ]
    if comp_counts:
        lines.extend(["## Illustrative Recovery Mix", "", "| Gesture | Cases |", "| --- | ---: |"])
        for label, count in comp_counts.most_common():
            lines.append(f"| {label} | {count} |")
        lines.append("")
    return "\n".join(lines)


def render_dashboard(recommendations: list[dict[str, str]], audit_rows: list[dict[str, str]]) -> str:
    audit_counts = Counter(row["audit_class"] for row in audit_rows)
    comp_counts = Counter(row["comp_label"] for row in recommendations)
    confidences = Counter(row.get("decision_confidence", "unknown") for row in recommendations)
    max_comp = max(comp_counts.values()) if comp_counts else 1
    stabilities = [as_float(row.get("recommendation_stability"), 0) for row in recommendations]
    manager_reviews = sum(row["manager_review_flag"] == "true" for row in recommendations)
    low_match = sum(as_float(row.get("reservation_match_confidence"), 0) < 0.75 for row in recommendations)
    cost_low = aggregate_sum(recommendations, "internal_cost_low")
    cost_high = aggregate_sum(recommendations, "internal_cost_high")
    comp_bars = "".join(
        f'<div class="bar-row"><span>{escape(label)}</span><div class="track"><i style="width:{count / max_comp * 100:.1f}%"></i></div><strong>{count}</strong></div>'
        for label, count in comp_counts.most_common()
    )
    audit_rows_html = "".join(
        f"<tr><td>{escape(format_label(label))}</td><td>{count}</td></tr>" for label, count in audit_counts.most_common()
    )
    queue = sorted(
        [row for row in recommendations if row["manager_review_flag"] == "true" or row.get("decision_confidence") != "high"],
        key=lambda row: (as_float(row.get("recovery_need_score"), 0), as_float(row.get("estimated_lifetime_value"), 0)),
        reverse=True,
    )[:12]
    queue_rows = "".join(
        "<tr>"
        f"<td>{escape(format_label(row['failure_category']))}</td>"
        f"<td>{escape(format_label(row['guest_tier']))}</td>"
        f"<td>{money(row['recommended_comp_value'])} {escape(row['comp_label'])}</td>"
        f"<td>{money(row['internal_cost_low'])}-{money(row['internal_cost_high'])}</td>"
        f"<td>{escape(row['decision_confidence'])} / {as_float(row['recommendation_stability']):.0%}</td>"
        "</tr>"
        for row in queue
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Service Recovery Policy Review</title>
  <style>
    :root {{ --ink:#191d1c;--muted:#626966;--line:#d8dcda;--paper:#f3f5f3;--accent:#176b5f;--soft:#e9f2ef;--warn:#955329; }}
    * {{ box-sizing:border-box; }} body {{ margin:0;background:var(--paper);color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;line-height:1.45; }}
    header {{ padding:28px clamp(20px,5vw,64px);background:#fff;border-bottom:1px solid var(--line); }} h1 {{ margin:0;font-size:1.75rem;letter-spacing:0; }} header p {{ color:var(--muted);max-width:850px;margin:7px 0 0; }}
    main {{ max-width:1320px;margin:auto;padding:24px clamp(20px,5vw,64px) 48px; }} .boundary {{ border-left:4px solid var(--warn);background:#fff7f2;padding:12px 14px;margin-bottom:20px;color:#6c3d24; }}
    .metrics {{ display:grid;grid-template-columns:repeat(4,minmax(150px,1fr));gap:10px;margin:20px 0 28px; }} .metric {{ background:#fff;border:1px solid var(--line);border-radius:6px;padding:15px; }} .metric span {{ display:block;color:var(--muted);font-size:.8rem; }} .metric strong {{ display:block;margin-top:4px;font-size:1.35rem; }}
    .grid {{ display:grid;grid-template-columns:1.25fr .75fr;gap:18px;margin-bottom:22px; }} section {{ background:#fff;border:1px solid var(--line);border-radius:6px;padding:18px; }} h2 {{ margin:0 0 14px;font-size:1.08rem;color:#154f47;letter-spacing:0; }}
    .bar-row {{ display:grid;grid-template-columns:minmax(190px,1.5fr) minmax(100px,2fr) 42px;align-items:center;gap:10px;margin:9px 0;font-size:.85rem; }} .track {{ height:9px;background:#edf0ee;border-radius:2px;overflow:hidden; }} .track i {{ display:block;height:100%;background:var(--accent); }}
    table {{ width:100%;border-collapse:collapse; }} th,td {{ padding:9px 8px;border-bottom:1px solid var(--line);text-align:left;font-size:.82rem; }} th {{ color:var(--muted);font-weight:650; }} .confidence {{ display:flex;gap:8px;flex-wrap:wrap; }} .confidence div {{ background:var(--soft);padding:9px;border-radius:4px;min-width:110px; }}
    @media(max-width:850px) {{ .metrics {{ grid-template-columns:repeat(2,minmax(130px,1fr)); }} .grid {{ grid-template-columns:1fr; }} .bar-row {{ grid-template-columns:minmax(130px,1fr) 1fr 34px; }} }}
  </style>
</head>
<body>
  <header><h1>Service Recovery Policy Review</h1><p>Decision support for intelligent generosity in a Santa Monica luxury lifestyle context.</p></header>
  <main>
    <div class="boundary"><strong>Synthetic policy simulation.</strong> These are workflow demonstrations, not Proper Hotels findings, actual leakage, or projected savings.</div>
    <div class="metrics">
      <div class="metric"><span>Cases evaluated</span><strong>{len(recommendations)}</strong></div>
      <div class="metric"><span>Median stability</span><strong>{statistics.median(stabilities):.0%}</strong></div>
      <div class="metric"><span>Manager review</span><strong>{manager_reviews}</strong></div>
      <div class="metric"><span>Estimated cost range</span><strong>{money(cost_low)}-{money(cost_high)}</strong></div>
    </div>
    <div class="grid">
      <section><h2>Illustrative Recovery Mix</h2>{comp_bars}</section>
      <section><h2>Decision Confidence</h2><div class="confidence"><div>High<br><strong>{confidences['high']}</strong></div><div>Moderate<br><strong>{confidences['moderate']}</strong></div><div>Low<br><strong>{confidences['low']}</strong></div></div><p>Low reservation-match confidence: <strong>{low_match}</strong></p></section>
    </div>
    <div class="grid">
      <section><h2>Simulated Policy Audit</h2><table><thead><tr><th>Class</th><th>Cases</th></tr></thead><tbody>{audit_rows_html}</tbody></table></section>
      <section><h2>Operating Decision</h2><p>Standardize recovery tiers and option selection, but retain manager approval for severe, costly, unstable, repeat-pattern, or low-confidence cases.</p><p>Public context calibrates option fit and guest-facing value. Internal margin and availability remain required for a pilot.</p></section>
    </div>
    <section><h2>Manager Review Queue Preview</h2><table><thead><tr><th>Issue</th><th>Guest</th><th>Recommendation</th><th>Estimated cost</th><th>Confidence</th></tr></thead><tbody>{queue_rows}</tbody></table></section>
  </main>
</body>
</html>"""


def render_discussion_brief(
    recommendations: list[dict[str, str]], audit_rows: list[dict[str, str]], proper_anchor_rows: list[dict[str, str]]
) -> str:
    audit_counts = Counter(row["audit_class"] for row in audit_rows)
    example = build_scenario_presentations()[0]
    return "\n".join(
        [
            "# Luxury Hotel Service Recovery Discussion Brief",
            "",
            "## Purpose",
            "",
            "This prototype demonstrates how fragmented hotel operating data could support more consistent, explainable comp decisions while preserving luxury hospitality and manager judgment.",
            "",
            "It uses synthetic PMS, CRM, service, comp, POS, survey, and operational data plus bounded public Santa Monica property context. It does not use Proper Hotels internal data or policy.",
            "",
            "## Decision Product",
            "",
            "For each service failure, the system recommends a recovery gesture and amount, estimated cost range, manager-review path, two alternatives, decision stability, and a counterfactual explanation.",
            "",
            f"**Example:** {example['amount']} {example['gesture']} with a working cost range of {example['cost_range']}.",
            "",
            "For a loyalty guest facing a severity-4, hotel-responsible room-readiness delay, the policy favors a property-aligned dining credit over immediate room-rate erosion. The recommendation requires manager approval and would shift to a room upgrade if room availability were less constrained.",
            "",
            "## What Is Demonstrated",
            "",
            "- Multi-source reconciliation and source-match confidence.",
            "- Versioned policy assumptions and observed-public provenance.",
            "- Cost ranges and parameter sensitivity instead of false precision.",
            "- Human review for high-exposure or low-confidence decisions.",
            f"- `{len(proper_anchor_rows)}` official-property public anchors for option fit and guest-facing value.",
            f"- A simulated audit with `{audit_counts['manager_review_required']}` manager-review and `{audit_counts['data_quality_hold']}` data-hold cases.",
            "",
            "## Production Conversation",
            "",
            "The next step would be a data and policy workshop: map actual comp actions and costs, define severity and responsibility rubrics, identify post-recovery outcomes, and determine which decisions should be recommended, escalated, or held.",
            "",
        ]
    )


def main() -> int:
    ensure_dirs()
    required = [COMP_RECOMMENDATIONS_PATH, RECOVERY_CASE_MART_PATH, COMP_POLICY_AUDIT_PATH]
    if any(not path.exists() for path in required):
        print("Missing recommendation/audit data. Run `make artifacts` first.")
        return 1
    _, recommendations = read_csv_rows(COMP_RECOMMENDATIONS_PATH)
    _, audit_rows = read_csv_rows(COMP_POLICY_AUDIT_PATH)
    _, pricing_rows = read_csv_rows(PUBLIC_PRICING_CONTEXT_PATH) if PUBLIC_PRICING_CONTEXT_PATH.exists() else ([], [])
    _, property_rows = read_csv_rows(PROPERTY_CONTEXT_PATH) if PROPERTY_CONTEXT_PATH.exists() else ([], [])
    _, proper_anchor_rows = read_csv_rows(PROPER_PUBLIC_CONTEXT_PATH) if PROPER_PUBLIC_CONTEXT_PATH.exists() else ([], [])
    _, review_rows = read_csv_rows(REVIEW_RISK_CONTEXT_PATH) if REVIEW_RISK_CONTEXT_PATH.exists() else ([], [])
    _, demand_rows = read_csv_rows(LOCAL_DEMAND_CONTEXT_PATH) if LOCAL_DEMAND_CONTEXT_PATH.exists() else ([], [])
    _, impact_rows = read_csv_rows(EXTERNAL_CONTEXT_MODEL_IMPACT_PATH) if EXTERNAL_CONTEXT_MODEL_IMPACT_PATH.exists() else ([], [])
    SAMPLE_RECOMMENDATIONS_REPORT.write_text(render_sample_recommendations(recommendations), encoding="utf-8")
    EXECUTIVE_BRIEF_REPORT.write_text(
        render_executive_brief(
            recommendations,
            audit_rows,
            pricing_rows,
            property_rows,
            proper_anchor_rows,
            review_rows,
            demand_rows,
            impact_rows,
        ),
        encoding="utf-8",
    )
    DASHBOARD_REPORT.write_text(render_dashboard(recommendations, audit_rows), encoding="utf-8")
    DISCUSSION_BRIEF_REPORT.write_text(
        render_discussion_brief(recommendations, audit_rows, proper_anchor_rows), encoding="utf-8"
    )
    STAKEHOLDER_REPORT.write_text(render_stakeholder_page(), encoding="utf-8")
    print(f"Wrote stakeholder report to {STAKEHOLDER_REPORT}")
    print(f"Wrote supporting decision reports to {REPORT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
