from __future__ import annotations

import json
from html import escape

from common import (
    COMP_POLICY_AUDIT_PATH,
    COMP_RECOMMENDATIONS_PATH,
    EXTERNAL_CONTEXT_MODEL_IMPACT_PATH,
    LOCAL_DEMAND_CONTEXT_PATH,
    POLICY_CASE_COMPARISON_PATH,
    POLICY_DECISION_SUMMARY_PATH,
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
from generate_engineering_evidence import write_engineering_evidence
from stakeholder_report import (
    build_scenario_presentations,
    policy_decision_context,
    render_stakeholder_page,
)


SAMPLE_RECOMMENDATIONS_REPORT = REPORT_DIR / "sample-recommendations.md"
EXECUTIVE_BRIEF_REPORT = REPORT_DIR / "executive-comp-optimization-brief.md"
DASHBOARD_REPORT = REPORT_DIR / "comp-optimization-dashboard.html"
DISCUSSION_BRIEF_REPORT = REPORT_DIR / "luxury-hotel-comp-optimization-discussion-brief.md"
INTERACTIVE_POLICY_PROTOTYPE = REPORT_DIR / "interactive-policy-prototype.html"


def money(value: str | int | float) -> str:
    try:
        numeric = float(value)
        return f"-${abs(numeric):,.0f}" if numeric < 0 else f"${numeric:,.0f}"
    except (TypeError, ValueError):
        return "$0"


def format_label(value: str) -> str:
    label = value.replace("_", " ")
    return label.replace("f and b", "F&B").replace("spa wellness", "spa/wellness").replace("event or suite", "event/suite")


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
        "# Context-Aware Comparator Recommendations",
        "",
        "These synthetic cases demonstrate the context-aware Intelligent Generosity comparator. They are supporting model diagnostics, not the generated shadow-policy recommendations.",
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
    decision: dict[str, object],
    pricing_rows: list[dict[str, str]],
    property_rows: list[dict[str, str]],
    proper_anchor_rows: list[dict[str, str]],
    review_context_rows: list[dict[str, str]],
    demand_rows: list[dict[str, str]],
    impact_rows: list[dict[str, str]],
) -> str:
    summary_rows = list(decision["summary_rows"])
    selected = decision.get("selected")
    context_changed = sum(row.get("recommendation_changed") == "true" for row in impact_rows)
    example = build_scenario_presentations()[0]
    observed_pricing = any(row.get("pricing_provenance") == "observed_public_market_context" for row in pricing_rows)
    comparison_lines = [
        "| Policy | Safe recovery path | Strict gesture fit | Modeled midpoint cost | Direct refund face value | Manager review | Assumption-stress pass rate |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary_rows:
        manager_review = (
            "Unknown"
            if int(row.get("manager_review_evaluable_cases", 0)) == 0
            else f"{as_float(row['manager_review_rate']):.1%}"
        )
        marker = " **(shadow-validation candidate)**" if row.get("selected_for_pilot") == "true" else ""
        comparison_lines.append(
            f"| {row['policy_label']}{marker} | {as_float(row['adequacy_rate']):.1%} | "
            f"{as_float(row['gesture_adequacy_rate']):.1%} | {money(row['internal_cost_mid'])} | "
            f"{money(row['direct_room_refund_value'])} | {manager_review} | "
            f"{as_float(row['joint_guardrail_pass_probability']):.1%} |"
        )
    selected_label = str(decision["selected_policy_label"])
    baseline = next(
        (row for row in summary_rows if row.get("policy_id") == "synthetic_discretionary_baseline"),
        {"unknown_or_hold_cases": "0"},
    )
    selected_metrics = selected or {
        "cases": "0",
        "unknown_or_hold_cases": "0",
        "adequacy_rate": "0",
        "gesture_adequacy_rate": "0",
        "internal_cost_low": "0",
        "internal_cost_mid": "0",
        "internal_cost_high": "0",
        "direct_room_refund_value": "0",
        "manager_review_rate": "0",
        "joint_guardrail_pass_probability": "0",
    }
    decision_provenance = dict(decision["decision_provenance"])
    decision_source = (
        "Snowflake `MARTS.VW_POLICY_TRADEOFF`, parity-checked against the versioned local mart"
        if decision_provenance.get("parity_verified")
        else "versioned local policy-decision mart; see engineering evidence for cloud validation status"
    )
    lines = [
        "# Comp Policy Shadow-Validation Decision Brief",
        "",
        "## Executive Decision",
        "",
        str(decision["recommendation"]),
        "",
        "This authorizes invisible shadow validation only, not manager-facing guidance or a permanent comp-policy change. Replace assumed costs with property accounting data and proceed to a controlled manager-assisted test only if the guest-protection and operating guardrails continue to hold.",
        "",
        "> **Evidence boundary:** all service cases, historical comp actions, costs, and policy outcomes are synthetic. This is constrained optimization under declared assumptions; it is not Proper Hotels performance, causal evidence, projected savings, or independent proof that the selected rule improves guest outcomes.",
        "",
        f"**Decision data source:** {decision_source}.",
        "",
        "## Five-Policy Decision Evidence",
        "",
        *comparison_lines,
        "",
        "Safe recovery path means an adequate proposed gesture or an explicit manager-review path; strict gesture fit evaluates the proposed gesture alone.",
        "",
        f"The same `{selected_metrics['cases']}` synthetic recovery cases were evaluated under every policy. `{selected_label}` advanced only after clearing the declared safe-recovery, high-risk escalation, operational-feasibility, data-hold, and tier-5 review rules in at least 80% of shared assumption-stress draws. Modeled cost broke ties only among policies that passed those protections.",
        "",
        "Because the candidate is designed to minimize modeled cost subject to the same fit guardrail used in evaluation, this result identifies the preferred rule under the declared assumptions; it does not independently estimate guest recovery or profitability.",
        "",
        "## Material Tradeoff",
        "",
        str(decision["tradeoff"]),
        "",
        f"The candidate's simulated direct-refund exposure is `{money(selected_metrics['direct_room_refund_value'])}` and its modeled total cost range is `{money(selected_metrics['internal_cost_low'])}-{money(selected_metrics['internal_cost_high'])}`. The policy is not a comp-minimization rule: it first requires an adequate recovery path, then chooses the lowest modeled-cost robust gesture. Actual margin and guest outcomes must decide whether that tradeoff is acceptable.",
        "",
        "## Worked Manager Decision",
        "",
        f"**Recommended recovery:** {example['amount']} {example['gesture']}",
        "",
        f"- Working internal-cost range: `{example['cost_range']}`",
        f"- Approval path: `{example['approval']}`",
        f"- Policy robustness: `{example['robustness']}`",
        f"- Closest alternative: `{example['alternative']}`",
        f"- What would change it: `{example['counterfactual']}`",
        "",
        "This example is generated by the selected policy from a severity-4, hotel-responsible room-readiness delay. It preserves manager review and exposes an alternative instead of presenting a black-box directive.",
        "",
        "## Property-Relevant Context",
        "",
        f"- Official Santa Monica Proper public anchors: `{len(proper_anchor_rows)}`",
        f"- Public property/competitive-set profiles: `{len(property_rows)}`",
        f"- Pricing context mode: `{'observed public quotes' if observed_pricing else 'reproducible sample-seed stress test'}`",
        f"- Controlled context comparisons changing a recommendation: `{context_changed}/{len(impact_rows)}`",
        f"- Review-risk context rows: `{len(review_context_rows)}`; local-demand context rows: `{len(demand_rows)}`",
        "",
        "Official public sources establish that property-aligned recovery can include Palma or Calabra dining, Surya Spa or Recovery Suite experiences, late checkout, destination-fee relief, valet relief, and room-category gestures. Public prices anchor guest-facing denominations only; they do not reveal contribution margin.",
        "",
        "## Shadow-Validation Design",
        "",
        "1. Run four weeks or 50 eligible cases in shadow mode, whichever is later; do not expose recommendations to managers or guests.",
        "2. Reconcile proposed gestures against actual manager decisions, availability, marginal cost, and policy exceptions.",
        "3. Pre-register the controlled-phase endpoints and sample requirement before manager-assisted use.",
        "4. Stop or revise the validation if guest-protection, data-quality, escalation, or feasibility guardrails fail.",
        "",
        "## Data Required Before A Controlled Test",
        "",
        "- Historical comp actions, approval notes, policy versions, and manager overrides.",
        "- Post-recovery satisfaction, review outcomes, repeat stays, and cancellations.",
        "- Contribution-margin ranges by comp type.",
        "- Live occupancy, inventory, outlet capacity, staffing, and room-type constraints.",
        "- A jointly reviewed severity, responsibility, and approval taxonomy.",
        "",
        f"The synthetic discretionary baseline contains `{baseline['unknown_or_hold_cases']}` unknown or held cases. Missing historical comp records are treated as unknown, not automatically labeled under-recovery.",
        "",
    ]
    return "\n".join(lines)


def render_dashboard(decision: dict[str, object], case_rows: list[dict[str, str]]) -> str:
    summary_rows = list(decision["summary_rows"])
    selected = decision.get("selected")
    selected_id = str(decision["selected_policy_id"])
    selected_metrics = selected or {
        "cases": "0",
        "adequacy_rate": "0",
        "internal_cost_mid": "0",
        "joint_guardrail_pass_probability": "0",
    }
    comparison_rows = "".join(
        ("<tr class=\"selected\">" if row.get("selected_for_pilot") == "true" else "<tr>")
        + f"<th>{escape(row['policy_label'])}</th>"
        + f"<td>{as_float(row['adequacy_rate']):.1%}</td>"
        + f"<td>{as_float(row['gesture_adequacy_rate']):.1%}</td>"
        + f"<td>{money(row['internal_cost_mid'])}</td>"
        + f"<td>{money(row['direct_room_refund_value'])}</td>"
        + (
            "<td>Unknown</td>"
            if int(row.get("manager_review_evaluable_cases", 0)) == 0
            else f"<td>{as_float(row['manager_review_rate']):.1%}</td>"
        )
        + f"<td>{as_float(row['joint_guardrail_pass_probability']):.1%}</td></tr>"
        for row in summary_rows
    )
    selected_cases = [row for row in case_rows if row.get("policy_id") == selected_id]
    queue = sorted(
        [
            row
            for row in selected_cases
            if row.get("manager_review_required") == "true" or row.get("data_hold_case") == "true"
        ],
        key=lambda row: (
            row.get("data_hold_case") == "true",
            as_float(row.get("reference_recovery_tier"), 0),
            as_float(row.get("selected_guest_facing_value"), 0),
        ),
        reverse=True,
    )[:12]
    queue_rows = "".join(
        "<tr>"
        f"<td>{escape(row['recovery_case_id'])}</td>"
        f"<td>{escape(format_label(row['failure_category']))}</td>"
        f"<td>{escape(format_label(row['guest_tier']))}</td>"
        f"<td>{money(row['selected_guest_facing_value'])} {escape(row['selected_comp_label'])}</td>"
        f"<td>{money(row['internal_cost_low'])}-{money(row['internal_cost_high'])}</td>"
        f"<td>{'Data hold' if row.get('data_hold_case') == 'true' else 'Manager review'}</td>"
        "</tr>"
        for row in queue
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Comp Policy Simulation Audit</title>
  <style>
    :root {{ --ink:#191d1c;--muted:#626966;--line:#d8dcda;--paper:#f3f5f3;--accent:#176b5f;--soft:#e9f2ef;--warn:#955329; }}
    * {{ box-sizing:border-box; }} body {{ margin:0;background:var(--paper);color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;line-height:1.45; }}
    header {{ padding:28px clamp(20px,5vw,64px);background:#fff;border-bottom:1px solid var(--line); }} h1 {{ margin:0;font-size:1.75rem;letter-spacing:0; }} header p {{ color:var(--muted);max-width:850px;margin:7px 0 0; }}
    main {{ max-width:1320px;margin:auto;padding:24px clamp(20px,5vw,64px) 48px; }} .boundary {{ border-left:4px solid var(--warn);background:#fff7f2;padding:12px 14px;margin-bottom:20px;color:#6c3d24; }}
    .metrics {{ display:grid;grid-template-columns:repeat(4,minmax(150px,1fr));gap:10px;margin:20px 0 28px; }} .metric {{ background:#fff;border:1px solid var(--line);border-radius:6px;padding:15px; }} .metric span {{ display:block;color:var(--muted);font-size:.8rem; }} .metric strong {{ display:block;margin-top:4px;font-size:1.35rem; }}
    section {{ margin-bottom:22px;background:#fff;border:1px solid var(--line);border-radius:6px;padding:18px; }} h2 {{ margin:0 0 14px;font-size:1.08rem;color:#154f47;letter-spacing:0; }}
    .table-wrap {{ width:100%;overflow-x:auto; }} table {{ width:100%;min-width:850px;border-collapse:collapse; }} th,td {{ padding:10px 9px;border-bottom:1px solid var(--line);text-align:left;font-size:.82rem; }} th {{ color:var(--muted);font-weight:650; }} tr.selected {{ background:var(--soft); }} .decision {{ border-left:4px solid var(--accent);padding-left:14px; }}
    @media(max-width:850px) {{ .metrics {{ grid-template-columns:repeat(2,minmax(130px,1fr)); }} }}
  </style>
</head>
<body>
  <header><h1>Comp Policy Simulation Audit</h1><p>Technical comparison supporting a shadow-validation candidate decision.</p></header>
  <main>
    <div class="boundary"><strong>Synthetic policy simulation.</strong> These are workflow demonstrations, not Proper Hotels findings, actual leakage, or projected savings.</div>
    <section class="decision"><h2>Generated Shadow-Validation Decision</h2><p><strong>{escape(str(decision['recommendation']))}</strong></p><p>{escape(str(decision['tradeoff']))}</p></section>
    <div class="metrics">
      <div class="metric"><span>Cases per policy</span><strong>{selected_metrics['cases']}</strong></div>
      <div class="metric"><span>Selected policy</span><strong>{escape(str(decision['selected_policy_label']))}</strong></div>
      <div class="metric"><span>Safe recovery path</span><strong>{as_float(selected_metrics['adequacy_rate']):.1%}</strong></div>
      <div class="metric"><span>Assumption-stress pass rate</span><strong>{as_float(selected_metrics['joint_guardrail_pass_probability']):.1%}</strong></div>
    </div>
    <section><h2>Five-Policy Comparison</h2><div class="table-wrap"><table><thead><tr><th>Policy</th><th>Safe path</th><th>Strict fit</th><th>Midpoint cost</th><th>Direct refund face value</th><th>Manager review</th><th>Assumption-stress pass rate</th></tr></thead><tbody>{comparison_rows}</tbody></table></div><p>Safe path includes an adequate gesture or an explicit manager-review path; strict fit evaluates the proposed gesture alone.</p></section>
    <section><h2>Selected-Policy Review Queue Preview</h2><div class="table-wrap"><table><thead><tr><th>Case</th><th>Issue</th><th>Guest</th><th>Recommendation</th><th>Estimated cost</th><th>Path</th></tr></thead><tbody>{queue_rows}</tbody></table></div></section>
  </main>
</body>
</html>"""


def render_discussion_brief(
    decision: dict[str, object], proper_anchor_rows: list[dict[str, str]]
) -> str:
    example = build_scenario_presentations()[0]
    return "\n".join(
        [
            "# Luxury Hotel Comp Policy Discussion Brief",
            "",
            "## Purpose",
            "",
            "This prototype compares five service-recovery policies and recommends which decision rule should enter invisible shadow validation while preserving luxury hospitality and manager judgment.",
            "",
            "It uses synthetic PMS, CRM, service, comp, POS, survey, and operational data plus bounded public Santa Monica property context. It does not use Proper Hotels internal data or policy.",
            "",
            "## Proposed Decision",
            "",
            str(decision["recommendation"]),
            "",
            str(decision["tradeoff"]),
            "",
            "This is a shadow-validation decision, not manager-facing deployment, permanent policy adoption, or an estimate of savings.",
            "",
            "## Manager Decision Product",
            "",
            "For each service failure, the selected policy returns a recovery gesture and amount, estimated cost range, manager-review path, and alternatives.",
            "",
            f"**Example:** {example['amount']} {example['gesture']} with a working cost range of {example['cost_range']}.",
            "",
            f"The example follows the `{decision['selected_policy_label']}` candidate and requires `{example['approval'].lower()}`.",
            "",
            "## What Is Demonstrated",
            "",
            "- Multi-source reconciliation and source-match confidence.",
            "- Versioned policy assumptions and observed-public provenance.",
            "- Cost ranges and parameter sensitivity instead of false precision.",
            "- Human review for high-exposure or low-confidence decisions.",
            f"- `{len(proper_anchor_rows)}` official-property public anchors for option fit and guest-facing value.",
            "- A paired case bootstrap, shared-world assumption stress test, and declared shadow-validation guardrails.",
            "",
            "## Production Conversation",
            "",
            "The next step is a data and policy workshop followed by shadow validation: map actual comp actions and costs, define severity and responsibility rubrics, identify post-recovery outcomes, and determine which decisions should be recommended, escalated, or held.",
            "",
        ]
    )


def main() -> int:
    ensure_dirs()
    required = [
        COMP_RECOMMENDATIONS_PATH,
        RECOVERY_CASE_MART_PATH,
        COMP_POLICY_AUDIT_PATH,
        POLICY_CASE_COMPARISON_PATH,
        POLICY_DECISION_SUMMARY_PATH,
    ]
    if any(not path.exists() for path in required):
        print("Missing recommendation/audit data. Run `make artifacts` first.")
        return 1
    _, recommendations = read_csv_rows(COMP_RECOMMENDATIONS_PATH)
    _, policy_case_rows = read_csv_rows(POLICY_CASE_COMPARISON_PATH)
    _, pricing_rows = read_csv_rows(PUBLIC_PRICING_CONTEXT_PATH) if PUBLIC_PRICING_CONTEXT_PATH.exists() else ([], [])
    _, property_rows = read_csv_rows(PROPERTY_CONTEXT_PATH) if PROPERTY_CONTEXT_PATH.exists() else ([], [])
    _, proper_anchor_rows = read_csv_rows(PROPER_PUBLIC_CONTEXT_PATH) if PROPER_PUBLIC_CONTEXT_PATH.exists() else ([], [])
    _, review_rows = read_csv_rows(REVIEW_RISK_CONTEXT_PATH) if REVIEW_RISK_CONTEXT_PATH.exists() else ([], [])
    _, demand_rows = read_csv_rows(LOCAL_DEMAND_CONTEXT_PATH) if LOCAL_DEMAND_CONTEXT_PATH.exists() else ([], [])
    _, impact_rows = read_csv_rows(EXTERNAL_CONTEXT_MODEL_IMPACT_PATH) if EXTERNAL_CONTEXT_MODEL_IMPACT_PATH.exists() else ([], [])
    decision = policy_decision_context()
    SAMPLE_RECOMMENDATIONS_REPORT.write_text(render_sample_recommendations(recommendations), encoding="utf-8")
    EXECUTIVE_BRIEF_REPORT.write_text(
        render_executive_brief(
            decision,
            pricing_rows,
            property_rows,
            proper_anchor_rows,
            review_rows,
            demand_rows,
            impact_rows,
        ),
        encoding="utf-8",
    )
    DASHBOARD_REPORT.write_text(render_dashboard(decision, policy_case_rows), encoding="utf-8")
    DISCUSSION_BRIEF_REPORT.write_text(
        render_discussion_brief(decision, proper_anchor_rows), encoding="utf-8"
    )
    write_engineering_evidence()
    INTERACTIVE_POLICY_PROTOTYPE.write_text(render_stakeholder_page(), encoding="utf-8")
    print(f"Wrote interactive policy prototype to {INTERACTIVE_POLICY_PROTOTYPE}")
    print(f"Wrote supporting decision reports to {REPORT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
