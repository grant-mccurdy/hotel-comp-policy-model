from __future__ import annotations

import json
import math
from decimal import Decimal, InvalidOperation
from html import escape

from common import (
    POLICY_DECISION_SUMMARY_PATH,
    POLICY_UNCERTAINTY_SUMMARY_PATH,
    PROJECT_ROOT,
    SNOWFLAKE_EXTRACT_MANIFEST_PATH,
    SNOWFLAKE_POLICY_TRADEOFF_EXTRACT_PATH,
    read_csv_rows,
    read_json,
)
from evaluate_policy_strategies import recommend_policy_strategy
from manager_app import PRESETS
from policy_config import comp_catalog, load_policy_scenarios
from policy_engine import recommend_comp
from scenario_contract import ScenarioInput


SCENARIO_PRESENTATION = [
    (
        "arrival_delay",
        "Arrival delay",
        "Room not ready at arrival",
        "Loyalty guest · severity 4 · hotel responsible · recovery possible during the stay",
    ),
    (
        "dining_lapse",
        "Dining lapse",
        "Dining service failure",
        "Returning guest · severity 4 · hotel responsible · recovery possible during the stay",
    ),
    (
        "suite_recovery",
        "Suite recovery",
        "Housekeeping failure during a VIP stay",
        "VIP guest · severity 5 · hotel responsible · high relationship exposure",
    ),
    (
        "parking_friction",
        "Valet delay",
        "Valet or parking delay",
        "Loyalty guest · severity 3 · hotel responsible · recovery possible during the stay",
    ),
]


REASON_LABELS = {
    "high_guest_relationship_value": "Protects an important guest relationship",
    "hotel_responsible_failure": "Hotel clearly owns the service failure",
    "high_severity_issue": "Material disruption to the stay",
    "high_review_risk": "Elevated reputation risk",
    "recoverable_before_checkout": "There is still time to recover the stay",
    "high_perceived_value_lower_estimated_cost": "High perceived value with less room-rate erosion",
    "repeat_comp_pattern_review_needed": "Prior recovery pattern warrants manager review",
    "lost_in_stay_recovery_window": "The in-stay recovery window has already closed",
}


def money(value: int | float) -> str:
    numeric = float(value)
    return f"-${abs(numeric):,.0f}" if numeric < 0 else f"${numeric:,.0f}"


def compact_money(value: int | float) -> str:
    return f"${float(value) / 1000:.1f}K"


def plain_counterfactual(counterfactuals: list[str]) -> str:
    if not counterfactuals:
        return "No single operating condition tested on its own changed the preferred gesture."
    text = counterfactuals[0]
    replacements = {
        "Operational availability changed the recommendation: without this signal, the model would prefer ": (
            "If room availability were less constrained, the preferred recovery would shift to "
        ),
        "Public rate pressure changed the recommendation: without this signal, the model would prefer ": (
            "If public rate pressure were lower, the preferred recovery would shift to "
        ),
        "Property fit changed the recommendation: without this signal, the model would prefer ": (
            "Without the property-specific experience fit, the preferred recovery would shift to "
        ),
        "Local demand context changed the recommendation: without this signal, the model would prefer ": (
            "If local demand pressure were removed, the preferred recovery would shift to "
        ),
    }
    for source, replacement in replacements.items():
        if text.startswith(source):
            return replacement + text[len(source) :]
    return text.replace("the model", "the policy")


def normalize_snowflake_row(row: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in row.items():
        text = "" if value is None else str(value)
        if text.lower() in {"true", "false"}:
            text = text.lower()
        normalized[key.lower()] = text
    return normalized


def equivalent_value(left: str, right: str) -> bool:
    if left == right:
        return True
    try:
        return Decimal(left) == Decimal(right)
    except (InvalidOperation, ValueError):
        return False


def policy_summary_rows() -> tuple[list[dict[str, str]], dict[str, object]]:
    local_fields, local_rows = read_csv_rows(POLICY_DECISION_SUMMARY_PATH)
    provenance: dict[str, object] = {
        "source": "local_mart",
        "label": "Versioned local decision mart",
        "parity_verified": False,
        "generated_at": "local build",
    }
    if not SNOWFLAKE_POLICY_TRADEOFF_EXTRACT_PATH.exists():
        return local_rows, provenance

    _, extracted_rows_raw = read_csv_rows(SNOWFLAKE_POLICY_TRADEOFF_EXTRACT_PATH)
    extracted_rows = [normalize_snowflake_row(row) for row in extracted_rows_raw]
    if not extracted_rows or not set(local_fields).issubset(extracted_rows[0]):
        provenance["status"] = "extract_contract_mismatch"
        return local_rows, provenance

    local_by_policy = {row["policy_id"]: row for row in local_rows}
    extracted_by_policy = {row["policy_id"]: row for row in extracted_rows}
    parity = local_by_policy.keys() == extracted_by_policy.keys() and all(
        equivalent_value(local_row[field], extracted_by_policy[policy_id][field])
        for policy_id, local_row in local_by_policy.items()
        for field in local_fields
    )
    if not parity:
        provenance["status"] = "extract_parity_failed"
        return local_rows, provenance

    manifest = (
        read_json(SNOWFLAKE_EXTRACT_MANIFEST_PATH)
        if SNOWFLAKE_EXTRACT_MANIFEST_PATH.exists()
        else {}
    )
    ordered_extracted_rows = [extracted_by_policy[row["policy_id"]] for row in local_rows]
    return ordered_extracted_rows, {
        "source": "snowflake_extract",
        "label": "Snowflake decision-view extract",
        "parity_verified": True,
        "generated_at": manifest.get("generated_at", "verified cloud extract"),
        "view": "MARTS.VW_POLICY_TRADEOFF",
    }


def policy_decision_context() -> dict[str, object]:
    if not POLICY_DECISION_SUMMARY_PATH.exists():
        raise RuntimeError("Missing policy decision summary. Run `make compare-policies` first.")
    rows, decision_provenance = policy_summary_rows()
    selected = next((row for row in rows if row.get("selected_for_pilot") == "true"), None)
    if selected is None:
        return {
            "selected_policy_id": "",
            "selected_policy_label": "No manager-facing policy",
            "recommendation": "Do not advance a policy; no candidate cleared the declared shadow-validation guardrails.",
            "summary_rows": rows,
            "tradeoff": "Revise policy assumptions and validate real marginal costs before exposing recommendations to managers.",
            "decision_provenance": decision_provenance,
        }
    intelligent = next(row for row in rows if row.get("policy_id") == "intelligent_generosity")
    cost_delta = float(selected["internal_cost_mid"]) - float(intelligent["internal_cost_mid"])
    refund_delta = float(selected["direct_room_refund_value"]) - float(intelligent["direct_room_refund_value"])
    review_delta = float(selected["manager_review_rate"]) - float(intelligent["manager_review_rate"])
    cost_direction = "reduces" if cost_delta < 0 else "increases"
    refund_direction = "reduces" if refund_delta < 0 else "increases"
    review_direction = "reduces" if review_delta < 0 else "increases"
    return {
        "selected_policy_id": selected["policy_id"],
        "selected_policy_label": selected["policy_label"],
        "recommendation": selected["executive_recommendation"],
        "summary_rows": rows,
        "selected": selected,
        "decision_provenance": decision_provenance,
        "tradeoff": (
            f"Compared with Intelligent Generosity, the selected policy {cost_direction} modeled midpoint cost by "
            f"{money(abs(cost_delta))}, {refund_direction} direct-refund face-value exposure by "
            f"{money(abs(refund_delta))}, and {review_direction} manager-review volume by "
            f"{abs(review_delta):.1%}. "
            "These are simulated tradeoffs for shadow validation, not projected results."
        ),
    }


def render_policy_decision_figure(decision_context: dict[str, object]) -> str:
    if not POLICY_UNCERTAINTY_SUMMARY_PATH.exists():
        raise RuntimeError("Missing policy uncertainty summary. Run `make compare-policies` first.")

    _, uncertainty_rows = read_csv_rows(POLICY_UNCERTAINTY_SUMMARY_PATH)
    uncertainty_by_policy = {row["policy_id"]: row for row in uncertainty_rows}
    threshold = float(
        load_policy_scenarios()["pilot_guardrails"]["minimum_guardrail_pass_probability"]
    )
    selected_policy_id = str(decision_context["selected_policy_id"])
    rows: list[dict[str, object]] = []

    for summary in decision_context["summary_rows"]:
        uncertainty = uncertainty_by_policy[str(summary["policy_id"])]
        eligible = str(summary["selection_eligible"]).lower() == "true"
        pass_rate = float(uncertainty["joint_guardrail_pass_probability"])
        selected = str(summary["policy_id"]) == selected_policy_id
        if not eligible:
            status_class = "comparator"
            status_label = "Comparator only"
            result_value = "Not eligible"
        elif pass_rate < threshold:
            status_class = "failed"
            status_label = "Does not qualify"
            result_value = f"{pass_rate:.1%} pass"
        elif selected:
            status_class = "selected"
            status_label = "Selected"
            result_value = f"{pass_rate:.1%} pass"
        else:
            status_class = "qualified"
            status_label = "Qualifies"
            result_value = f"{pass_rate:.1%} pass"
        rows.append(
            {
                "policy_label": str(summary["policy_label"]),
                "status_class": status_class,
                "status_label": status_label,
                "result_value": result_value,
                "modeled_adequacy_rate": float(summary["adequacy_rate"]),
                "high_risk_under_recovery_rate": float(
                    summary["high_risk_under_recovery_rate"]
                ),
                "low": float(uncertainty["internal_cost_p05"]),
                "median": float(uncertainty["internal_cost_p50"]),
                "high": float(uncertainty["internal_cost_p95"]),
            }
        )

    rows.sort(key=lambda row: float(row["median"]))
    axis_max = math.ceil(max(float(row["high"]) for row in rows) / 5000) * 5000
    ticks = range(0, int(axis_max) + 1, 20000)
    tick_html = "".join(
        f'<span style="left:{tick / axis_max:.2%}">{compact_money(tick)}</span>'
        for tick in ticks
    )
    row_html: list[str] = []
    for row in rows:
        low = float(row["low"])
        median = float(row["median"])
        high = float(row["high"])
        range_text = (
            f"Median {compact_money(median)}"
            if low == high
            else f"Median {compact_money(median)} · range {compact_money(low)}–{compact_money(high)}"
        )
        modeled_adequacy_rate = float(row["modeled_adequacy_rate"])
        under_recovery_rate = float(row["high_risk_under_recovery_rate"])
        row_summary = (
            f"{row['policy_label']}: adequate or reviewed {modeled_adequacy_rate:.1%}; "
            f"inadequate and unreviewed {under_recovery_rate:.1%}; {range_text}; "
            f"{row['result_value']}, {row['status_label']}"
        )
        row_html.append(
            f'<div class="policy-plot-row {row["status_class"]}" role="group" '
            f'aria-label="{escape(row_summary)}">'
            f'<div class="policy-plot-label"><strong>{escape(str(row["policy_label"]))}</strong></div>'
            '<div class="protection-cell">'
            '<div class="protection-metric safe-path">'
            f'<span><b>Adequate or reviewed</b><strong>{modeled_adequacy_rate:.1%}</strong></span>'
            f'<span class="metric-track" aria-hidden="true"><i style="width:{modeled_adequacy_rate:.2%}"></i></span>'
            '</div>'
            '<div class="protection-metric under-recovery">'
            f'<span><b>Inadequate and unreviewed</b><strong>{under_recovery_rate:.1%}</strong></span>'
            f'<span class="metric-track" aria-hidden="true"><i style="width:{under_recovery_rate:.2%}"></i></span>'
            '</div>'
            '</div>'
            f'<div class="cost-cell"><div class="cost-track" '
            f'style="--cost-low:{low / axis_max:.2%};--cost-mid:{median / axis_max:.2%};--cost-high:{high / axis_max:.2%}" '
            f'aria-label="{escape(str(row["policy_label"]))}: {escape(range_text)}">'
            '<span class="cost-interval"></span><span class="cost-median"></span></div>'
            f'<span class="cost-readout">{escape(range_text)}</span></div>'
            f'<div class="guardrail-result"><strong>{escape(str(row["result_value"]))}</strong>'
            f'<span>{escape(str(row["status_label"]))}</span></div></div>'
        )

    return (
        '<figure class="policy-decision-figure" aria-labelledby="policy-figure-heading" aria-describedby="policy-figure-caption">'
        '<div class="selection-rule">'
        '<div><span class="rule-number">1</span><p><strong>Qualify</strong> Clear every modeled guardrail in at least '
        f'{threshold:.0%} of draws.</p></div>'
        '<span class="rule-arrow" aria-hidden="true">→</span>'
        '<div><span class="rule-number">2</span><p><strong>Choose</strong> Compare modeled cost only among qualifiers.</p></div>'
        '</div>'
        '<div class="figure-axis" aria-hidden="true"><span>Policy</span><span>Modeled adequacy</span>'
        f'<div class="axis-track">{tick_html}</div><span>Decision</span></div>'
        f'<div class="policy-plot">{"".join(row_html)}</div>'
        '<figcaption id="policy-figure-caption"><strong>How to read:</strong> Adequate or reviewed cases pass the modeled test; inadequate, unreviewed cases do not. Lines show cost P05–P95 across 5,000 shared stress draws; dots show medians. Policies must clear every guardrail in 80% of draws before cost comparison. '
        '<span class="figure-source"><strong>Source:</strong> synthetic policy mart, 430 cases; <a href="reports/methodology-and-assumptions.md">methods</a> and <a href="reports/policy-sensitivity.md">sensitivity analysis</a>. Not projected savings.</span></figcaption>'
        '</figure>'
    )


def build_scenario_presentations() -> list[dict[str, object]]:
    decision = policy_decision_context()
    selected_policy_id = str(decision["selected_policy_id"])
    if not selected_policy_id:
        selected_policy_id = "intelligent_generosity"
    selected_summary = next(
        row for row in decision["summary_rows"] if row["policy_id"] == selected_policy_id
    )
    scenarios: list[dict[str, object]] = []
    for key, tab_label, title, context in SCENARIO_PRESENTATION:
        strategy_result = recommend_policy_strategy(dict(PRESETS[key]), selected_policy_id)
        scenario = ScenarioInput.from_mapping(dict(PRESETS[key]))
        stay, failure = scenario.to_engine_inputs()
        context_recommendation = recommend_comp(stay, failure, comp_catalog())
        reason_labels = [
            "Meets recovery-tier and issue-fit guardrails",
            "Lowest modeled cost among robust-fit gestures",
        ]
        if strategy_result["manager_review_required"]:
            reason_labels.append("Manager approval retained for exposure or uncertainty")
        if float(PRESETS[key].get("hotel_responsibility", 0)) >= 0.7:
            reason_labels.append("Hotel owns the service failure")
        if bool(strategy_result["operational_pressure_review"]):
            reason_labels.append("Operating pressure requires availability confirmation")
        alternative = strategy_result["alternatives"][0]
        manager_note = int(strategy_result["reference_recovery_tier"]) >= 3 and strategy_result["comp_code"] != "manager_note"
        scenarios.append(
            {
                "key": key,
                "tab_label": tab_label,
                "title": title,
                "context": context,
                "amount": money(strategy_result["recommended_value"]),
                "gesture": str(strategy_result["comp_label"]) + (" + manager note" if manager_note else ""),
                "cost_range": f"{money(strategy_result['internal_cost_low'])}-{money(strategy_result['internal_cost_high'])}",
                "approval": "Manager approval" if strategy_result["manager_review_required"] else "Within policy",
                "robustness": (
                    f"Policy clears all modeled guardrails in {float(selected_summary['joint_guardrail_pass_probability']):.1%} of shared stress draws"
                ),
                "reasons": reason_labels,
                "counterfactual": (
                    "Shadow mode must confirm availability and marginal cost. "
                    + plain_counterfactual(context_recommendation.counterfactuals)
                ),
                "alternative": (
                    f"{money(float(alternative['guest_facing_value']))} {alternative['comp_label']}"
                ),
            }
        )
    return scenarios


def render_stakeholder_page() -> str:
    decision_context = policy_decision_context()
    scenarios = build_scenario_presentations()
    default = scenarios[0]
    scenario_json = json.dumps({row["key"]: row for row in scenarios}).replace("</", "<\\/")
    tabs = "".join(
        f'<button class="scenario-tab" type="button" data-scenario="{escape(str(row["key"]))}" '
        f'aria-pressed="{"true" if index == 0 else "false"}">{escape(str(row["tab_label"]))}</button>'
        for index, row in enumerate(scenarios)
    )
    reasons = "".join(f"<li>{escape(str(reason))}</li>" for reason in default["reasons"])
    selected_label = escape(str(decision_context["selected_policy_label"]))
    tradeoff = escape(str(decision_context["tradeoff"]))
    decision_figure = render_policy_decision_figure(decision_context)
    summary_by_policy = {
        str(row["policy_id"]): row for row in decision_context["summary_rows"]
    }
    baseline = summary_by_policy["synthetic_discretionary_baseline"]
    baseline_adequacy = f"{float(baseline['adequacy_rate']):.1%}"
    baseline_high_risk = f"{float(baseline['high_risk_under_recovery_rate']):.1%}"
    baseline_unknown = int(baseline["unknown_or_hold_cases"])
    comparison_cases = int(baseline["cases"])
    decision_provenance = dict(decision_context["decision_provenance"])
    decision_source_note = (
        "Decision metrics were extracted from Snowflake and parity-checked against the versioned policy mart."
        if decision_provenance.get("parity_verified")
        else "Decision metrics use the versioned local mart; cloud execution evidence is reported separately."
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="A luxury-hospitality service recovery decision prototype for intelligent, explainable guest recovery.">
  <title>Which Comp Policy Should Enter Shadow Validation?</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #17201d;
      --muted: #5c6662;
      --line: #d7ddda;
      --paper: #f3f5f3;
      --white: #ffffff;
      --teal: #12685b;
      --teal-dark: #0d4c43;
      --teal-soft: #e7f1ee;
      --coral: #ad4f37;
      --coral-soft: #f8ece7;
      --gold: #9a742f;
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    html, body {{ width: 100%; max-width: 100%; overflow-x: hidden; }}
    body {{
      margin: 0;
      background: var(--white);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
      font-size: 16px;
      line-height: 1.55;
    }}
    a {{ color: var(--teal-dark); text-underline-offset: 3px; }}
    .shell {{ width: min(1120px, calc(100% - 40px)); margin: 0 auto; }}
    .eyebrow {{
      margin: 0 0 10px;
      color: var(--teal);
      font-size: .76rem;
      font-weight: 800;
      text-transform: uppercase;
    }}
    header {{ border-bottom: 1px solid var(--line); background: var(--white); }}
    .topline {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      min-height: 54px;
      border-bottom: 1px solid var(--line);
      color: var(--muted);
      font-size: .82rem;
    }}
    .topline strong {{ color: var(--ink); }}
    .intro {{ padding: 46px 0 40px; }}
    h1, h2, h3 {{ margin-top: 0; letter-spacing: 0; line-height: 1.17; }}
    h1 {{ max-width: 780px; margin-bottom: 14px; font-size: 3.25rem; }}
    h2 {{ margin-bottom: 12px; font-size: 1.75rem; }}
    h3 {{ margin-bottom: 8px; font-size: 1rem; }}
    .lead {{ max-width: 800px; margin: 0; color: var(--muted); font-size: 1.13rem; }}
    .proposal {{
      display: grid;
      grid-template-columns: 180px minmax(0, 1fr);
      gap: 22px;
      margin-top: 32px;
      padding-top: 25px;
      border-top: 3px solid var(--teal);
    }}
    .proposal strong {{ color: var(--teal-dark); font-size: .84rem; text-transform: uppercase; }}
    .proposal p {{ max-width: 780px; margin: 0; font-size: 1.14rem; font-weight: 650; }}
    .evidence-boundary {{ max-width: 850px; margin: 18px 0 0 202px; color: var(--muted); font-size: .84rem; }}
    section {{ padding: 54px 0; }}
    .band {{ background: var(--paper); border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); }}
    .section-head {{ max-width: 720px; margin-bottom: 28px; }}
    .section-head p {{ margin: 0; color: var(--muted); }}
    .story-layout {{ display: grid; grid-template-columns: minmax(0, 1.08fr) minmax(330px, .92fr); gap: 58px; align-items: start; }}
    .story-copy .section-head {{ margin-bottom: 18px; }}
    .story-copy > p {{ margin: 0; color: var(--muted); }}
    .story-copy > p + p {{ margin-top: 14px; }}
    .story-turn {{ padding-left: 18px; border-left: 3px solid var(--teal); color: var(--ink) !important; font-size: 1.03rem; font-weight: 650; }}
    .baseline-signal {{ padding: 24px 0; border-top: 3px solid var(--coral); border-bottom: 1px solid var(--line); }}
    .baseline-signal h3 {{ margin-bottom: 16px; font-size: 1.08rem; }}
    .baseline-metrics {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }}
    .baseline-metrics span {{ display: block; color: var(--muted); font-size: .72rem; }}
    .baseline-metrics strong {{ display: block; margin-top: 3px; color: var(--ink); font-size: 1.35rem; }}
    .baseline-boundary {{ margin: 18px 0 0; color: var(--muted); font-size: .82rem; }}
    .policy-decision-figure {{ margin: 0; border: 1px solid var(--line); background: var(--white); }}
    .selection-rule {{ display: grid; grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr); gap: 18px; align-items: center; padding: 18px 20px; border-bottom: 1px solid var(--line); background: #edf5f2; }}
    .selection-rule > div {{ display: grid; grid-template-columns: 30px minmax(0, 1fr); gap: 10px; align-items: start; }}
    .selection-rule p {{ margin: 0; color: var(--muted); font-size: .86rem; }}
    .selection-rule strong {{ display: block; color: var(--ink); }}
    .rule-number {{ display: grid; width: 28px; height: 28px; place-items: center; border-radius: 50%; background: var(--teal); color: var(--white); font-size: .78rem; font-weight: 800; }}
    .rule-arrow {{ color: var(--teal); font-size: 1.5rem; font-weight: 800; }}
    .figure-axis, .policy-plot-row {{ display: grid; grid-template-columns: minmax(150px, .65fr) minmax(210px, .9fr) minmax(270px, 1.25fr) 110px; gap: 18px; align-items: center; }}
    .figure-axis {{ padding: 16px 20px 10px; color: var(--muted); font-size: .7rem; font-weight: 750; text-transform: uppercase; }}
    .axis-track {{ position: relative; height: 20px; border-bottom: 1px solid var(--line); }}
    .axis-track span {{ position: absolute; bottom: 2px; transform: translateX(-50%); color: var(--muted); font-size: .68rem; font-weight: 600; text-transform: none; }}
    .axis-track span:first-child {{ transform: none; }}
    .policy-plot-row {{ --row-color: #68736e; min-height: 78px; padding: 13px 20px; border-top: 1px solid var(--line); }}
    .policy-plot-row.selected {{ --row-color: var(--teal); background: var(--teal-soft); }}
    .policy-plot-row.qualified {{ --row-color: #42665d; }}
    .policy-plot-row.failed {{ --row-color: var(--coral); }}
    .policy-plot-row.comparator {{ --row-color: #8a938f; }}
    .policy-plot-label strong, .guardrail-result strong {{ display: block; color: var(--ink); font-size: .9rem; }}
    .policy-plot-label span, .guardrail-result span {{ display: block; margin-top: 3px; color: var(--muted); font-size: .74rem; }}
    .policy-plot-row.selected .policy-plot-label span, .policy-plot-row.selected .guardrail-result span {{ color: var(--teal-dark); font-weight: 750; }}
    .protection-cell {{ display: grid; gap: 8px; min-width: 0; }}
    .protection-metric > span:first-child {{ display: flex; justify-content: space-between; gap: 10px; color: var(--muted); font-size: .7rem; }}
    .protection-metric b {{ font-weight: 600; }}
    .protection-metric strong {{ color: var(--ink); font-size: .76rem; }}
    .metric-track {{ display: block; height: 5px; margin-top: 3px; overflow: hidden; background: #e2e7e4; }}
    .metric-track i {{ display: block; height: 100%; background: var(--teal); }}
    .under-recovery .metric-track i {{ background: var(--coral); }}
    .cost-cell {{ min-width: 0; }}
    .cost-track {{ position: relative; height: 22px; border-bottom: 1px solid var(--line); }}
    .cost-interval {{ position: absolute; top: 9px; left: var(--cost-low); width: calc(var(--cost-high) - var(--cost-low)); min-width: 3px; height: 4px; border-radius: 2px; background: var(--row-color); }}
    .cost-median {{ position: absolute; top: 4px; left: var(--cost-mid); width: 14px; height: 14px; transform: translateX(-50%); border: 3px solid var(--white); border-radius: 50%; background: var(--row-color); box-shadow: 0 0 0 1px var(--row-color); }}
    .cost-readout {{ display: block; margin-top: 5px; color: var(--muted); font-size: .72rem; }}
    .guardrail-result {{ text-align: right; }}
    .policy-decision-figure figcaption {{ padding: 16px 20px; border-top: 1px solid var(--line); background: #fafbfa; color: var(--muted); font-size: .84rem; }}
    .policy-decision-figure figcaption strong {{ color: var(--ink); }}
    .figure-source {{ display: block; margin-top: 7px; }}
    .comparison-note {{ display: grid; grid-template-columns: 180px minmax(0, 1fr); gap: 22px; margin-top: 22px; padding-top: 20px; border-top: 1px solid var(--line); }}
    .comparison-note strong {{ color: var(--coral); font-size: .82rem; text-transform: uppercase; }}
    .comparison-note p {{ margin: 0; color: var(--muted); }}
    .scenario-tabs {{
      display: flex;
      width: fit-content;
      max-width: 100%;
      margin-bottom: 18px;
      border: 1px solid var(--line);
      border-radius: 6px;
      overflow-x: auto;
      background: var(--white);
    }}
    .scenario-tab {{
      flex: 0 0 auto;
      min-height: 40px;
      border: 0;
      border-right: 1px solid var(--line);
      padding: 9px 14px;
      background: var(--white);
      color: var(--muted);
      font: inherit;
      font-size: .86rem;
      cursor: pointer;
    }}
    .scenario-tab:last-child {{ border-right: 0; }}
    .scenario-tab[aria-pressed="true"] {{ background: var(--teal); color: var(--white); font-weight: 750; }}
    .scenario-tab:focus-visible {{ outline: 3px solid #86bcb4; outline-offset: -3px; }}
    .decision {{
      display: grid;
      grid-template-columns: minmax(0, 1.18fr) minmax(290px, .82fr);
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: 7px;
      overflow: hidden;
      background: var(--white);
    }}
    .decision-main, .decision-support {{ min-width: 0; padding: 28px; }}
    .decision-support {{ border-left: 1px solid var(--line); background: #fafbfa; }}
    .scenario-context {{ margin: 0 0 18px; color: var(--muted); font-size: .9rem; }}
    .recommendation {{ margin: 0; color: var(--teal-dark); font-size: 1.65rem; font-weight: 800; line-height: 1.25; overflow-wrap: anywhere; }}
    .recommendation span:first-child {{ color: var(--coral); }}
    .decision-metrics {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin: 24px 0;
      padding: 16px 0;
      border-top: 1px solid var(--line);
      border-bottom: 1px solid var(--line);
    }}
    .decision-metrics span {{ display: block; color: var(--muted); font-size: .76rem; }}
    .decision-metrics strong {{ display: block; margin-top: 4px; font-size: .94rem; overflow-wrap: anywhere; }}
    .reasons {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 9px 20px; margin: 12px 0 0; padding: 0; list-style: none; }}
    .reasons li {{ position: relative; padding-left: 17px; font-size: .9rem; }}
    .reasons li::before {{ content: ""; position: absolute; left: 0; top: .62em; width: 7px; height: 7px; border-radius: 50%; background: var(--teal); }}
    .decision-support h3:not(:first-child) {{ margin-top: 24px; }}
    .decision-support p {{ margin: 0; color: var(--muted); font-size: .91rem; }}
    .alternative {{ color: var(--ink) !important; font-weight: 700; }}
    .property-menu {{
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      margin-top: 25px;
      border-top: 1px solid var(--line);
      border-bottom: 1px solid var(--line);
    }}
    .property-menu div {{ min-width: 0; padding: 16px 14px; border-right: 1px solid var(--line); }}
    .property-menu div:first-child {{ padding-left: 0; }}
    .property-menu div:last-child {{ border-right: 0; padding-right: 0; }}
    .property-menu strong {{ display: block; color: var(--teal-dark); font-size: .79rem; text-transform: uppercase; }}
    .property-menu span {{ display: block; margin-top: 4px; color: var(--muted); font-size: .86rem; }}
    .pilot {{ display: grid; grid-template-columns: minmax(0, .9fr) minmax(0, 1.1fr); gap: 56px; align-items: start; }}
    .pilot-callout {{ border-left: 4px solid var(--coral); padding-left: 20px; }}
    .pilot-callout p {{ margin: 0; color: var(--muted); }}
    .pilot-callout strong {{ display: block; margin-bottom: 7px; color: var(--coral); font-size: .84rem; text-transform: uppercase; }}
    .success-measures {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px 26px; }}
    .success-measures p {{ margin: 0; color: var(--muted); font-size: .9rem; }}
    .data-needed {{ margin: 28px 0 0; padding-top: 20px; border-top: 1px solid var(--line); color: var(--muted); font-size: .9rem; }}
    .data-needed strong {{ color: var(--ink); }}
    .evidence {{ padding: 38px 0; background: #202825; color: #e9efec; }}
    .evidence-grid {{ display: grid; grid-template-columns: minmax(0, 1.25fr) minmax(280px, .75fr); gap: 52px; }}
    .evidence h2 {{ color: var(--white); font-size: 1.25rem; }}
    .evidence p {{ margin: 0; color: #bdc8c3; font-size: .9rem; }}
    .pipeline-proof {{ margin-top: 14px !important; color: #d8e3de !important; }}
    .evidence-links {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 9px 20px; align-content: start; }}
    .evidence a {{ color: #d8eee8; font-size: .88rem; }}
    footer {{ padding: 18px 0; background: #151a18; color: #9caaa4; font-size: .77rem; }}
    @media (max-width: 820px) {{
      .proposal {{ grid-template-columns: 1fr; gap: 8px; }}
      .evidence-boundary {{ margin-left: 0; }}
      .comparison-note {{ grid-template-columns: 1fr; gap: 6px; }}
      .story-layout {{ grid-template-columns: 1fr; gap: 32px; }}
      .selection-rule {{ grid-template-columns: 1fr; gap: 12px; }}
      .rule-arrow {{ justify-self: start; margin-left: 6px; transform: rotate(90deg); }}
      .figure-axis {{ display: none; }}
      .policy-plot-row {{ grid-template-columns: minmax(0, 1fr) auto; gap: 10px 18px; }}
      .policy-plot-label {{ grid-column: 1; grid-row: 1; }}
      .guardrail-result {{ grid-column: 2; grid-row: 1; }}
      .protection-cell {{ grid-column: 1 / -1; grid-row: 2; }}
      .cost-cell {{ grid-column: 1 / -1; grid-row: 3; }}
      .decision {{ grid-template-columns: 1fr; }}
      .decision-support {{ border-top: 1px solid var(--line); border-left: 0; }}
      .property-menu {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .property-menu div, .property-menu div:first-child, .property-menu div:last-child {{ padding: 14px; border-right: 0; border-bottom: 1px solid var(--line); }}
      .property-menu div:nth-child(odd) {{ border-right: 1px solid var(--line); }}
      .property-menu div:last-child {{ border-bottom: 0; }}
      .pilot, .evidence-grid {{ grid-template-columns: 1fr; gap: 32px; }}
    }}
    @media (max-width: 560px) {{
      .shell {{ width: min(100% - 32px, 1120px); }}
      .topline {{ align-items: flex-start; flex-direction: column; justify-content: center; gap: 2px; padding: 10px 0; }}
      .intro {{ padding: 34px 0 30px; }}
      h1 {{ font-size: 2rem; }}
      h2 {{ font-size: 1.45rem; }}
      .lead {{ font-size: 1rem; }}
      section {{ padding: 42px 0; }}
      .scenario-tabs {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); width: 100%; overflow: hidden; }}
      .scenario-tab {{ width: 100%; border-right: 1px solid var(--line); border-bottom: 1px solid var(--line); }}
      .scenario-tab:nth-child(2n) {{ border-right: 0; }}
      .scenario-tab:nth-last-child(-n+2) {{ border-bottom: 0; }}
      .decision-main, .decision-support {{ padding: 20px; }}
      .recommendation {{ font-size: 1.35rem; }}
      .decision-metrics {{ grid-template-columns: 1fr; gap: 10px; }}
      .decision-metrics div {{ padding-bottom: 10px; border-bottom: 1px solid var(--line); }}
      .decision-metrics div:last-child {{ padding-bottom: 0; border-bottom: 0; }}
      .reasons, .success-measures, .evidence-links {{ grid-template-columns: 1fr; }}
      .property-menu {{ grid-template-columns: 1fr; }}
      .property-menu div:nth-child(odd) {{ border-right: 0; }}
      .policy-plot-row {{ padding: 15px; }}
      .policy-decision-figure figcaption {{ padding: 15px; }}
    }}
    @media print {{
      body {{ font-size: 13px; }}
      .scenario-tabs {{ display: none; }}
      section {{ break-inside: avoid; padding: 28px 0; }}
      .evidence, footer {{ background: var(--white); color: var(--ink); }}
      .evidence p, .evidence a {{ color: var(--ink); }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="shell topline">
      <strong>Executive discussion brief</strong>
      <span>Public Santa Monica Proper context · Synthetic hotel operations</span>
    </div>
    <div class="shell intro">
      <p class="eyebrow">Luxury hospitality service recovery</p>
      <h1>Which Comp Policy Should Enter Shadow Validation?</h1>
      <p class="lead">A synthetic guest incident frames the decision: how should a luxury hotel balance recovery, consistency, and comp cost?</p>
      <div class="proposal">
        <strong>Executive answer</strong>
        <p>Shadow-test {selected_label} for four weeks or 50 eligible cases. It had the lowest modeled cost among policies clearing every guardrail.</p>
      </div>
      <p class="evidence-boundary"><strong>Decision scope:</strong> candidate selection for shadow validation, not policy adoption. Synthetic results do not estimate Proper Hotels performance or savings; public context informs gesture fit only.</p>
    </div>
  </header>

  <main>
    <section id="context-and-conflict">
      <div class="shell story-layout">
        <div class="story-copy">
          <div class="section-head">
            <p class="eyebrow">Operating context</p>
            <h2>A room delay forces a choice before the full cost is known</h2>
          </div>
          <p><strong>{escape(str(default['title']))}.</strong> {escape(str(default['context']))}. The manager must choose cash-like relief, an experience gesture, or escalation before availability and marginal cost are known.</p>
          <p class="story-turn">One incident becomes a policy problem: how can managers recover this guest consistently without replacing judgment?</p>
        </div>
        <aside class="baseline-signal" aria-label="Synthetic discretionary comparator signal">
          <p class="eyebrow">Synthetic stress-test signal</p>
          <h3>The cheapest synthetic comparator fails the modeled adequacy test</h3>
          <div class="baseline-metrics">
            <div><span>Adequate or reviewed</span><strong>{baseline_adequacy}</strong></div>
            <div><span>Inadequate and unreviewed</span><strong>{baseline_high_risk}</strong></div>
            <div><span>Unknown or held cases</span><strong>{baseline_unknown}</strong></div>
          </div>
          <p class="baseline-boundary">These are synthetic failure conditions, not Proper Hotels observations or measured guest outcomes.</p>
        </aside>
      </div>
    </section>

    <section class="band" id="policy-comparison">
      <div class="shell">
        <div class="section-head">
          <p class="eyebrow">Policy comparison</p>
          <h2 id="policy-figure-heading">Three policies clear the modeled guardrails; Guardrailed Recovery has the lowest modeled cost</h2>
          <p>Five policies faced the same {comparison_cases} synthetic cases. Cost was compared only after adequacy, escalation, data-quality, and feasibility guardrails.</p>
        </div>
        {decision_figure}
        <div class="comparison-note"><strong>Material tradeoff</strong><p>{tradeoff}</p></div>
      </div>
    </section>

    <section id="worked-decision">
      <div class="shell">
        <div class="section-head">
          <p class="eyebrow">Manager application</p>
          <h2>The selected policy turns the opening case into a manager-ready choice</h2>
          <p>The arrival-delay case returns first; the tabs show how the rule adapts elsewhere.</p>
        </div>
        <div class="scenario-tabs" role="group" aria-label="Worked recovery scenarios">{tabs}</div>
        <article class="decision" id="decision-panel" aria-live="polite">
          <div class="decision-main">
            <p class="eyebrow">Recommended recovery</p>
            <h3 id="scenario-title">{escape(str(default['title']))}</h3>
            <p class="scenario-context" id="scenario-context">{escape(str(default['context']))}</p>
            <p class="recommendation"><span id="scenario-amount">{escape(str(default['amount']))}</span> <span id="scenario-gesture">{escape(str(default['gesture']))}</span></p>
            <div class="decision-metrics">
              <div><span>Working cost range</span><strong id="scenario-cost">{escape(str(default['cost_range']))}</strong></div>
              <div><span>Approval path</span><strong id="scenario-approval">{escape(str(default['approval']))}</strong></div>
              <div><span>Policy stress test</span><strong id="scenario-robustness">{escape(str(default['robustness']))}</strong></div>
            </div>
            <h3>Why this fits</h3>
            <ul class="reasons" id="scenario-reasons">{reasons}</ul>
          </div>
          <aside class="decision-support">
            <h3>What would change it?</h3>
            <p id="scenario-counterfactual">{escape(str(default['counterfactual']))}</p>
            <h3>Closest alternative</h3>
            <p class="alternative" id="scenario-alternative">{escape(str(default['alternative']))}</p>
            <h3>Why a range, not one cost?</h3>
            <p>Public prices anchor value; property data must replace assumed marginal cost.</p>
          </aside>
        </article>
        <div class="property-menu" aria-label="Property-aligned recovery menu">
          <div><strong>Dining</strong><span>Calabra or Palma credit</span></div>
          <div><strong>Wellness</strong><span>Surya Spa or Recovery Suite</span></div>
          <div><strong>Stay</strong><span>Room upgrade or late checkout</span></div>
          <div><strong>Fee relief</strong><span>Valet or destination-fee waiver</span></div>
          <div><strong>Relationship</strong><span>Future-stay credit</span></div>
        </div>
      </div>
    </section>

    <section class="band" id="pilot">
      <div class="shell pilot">
        <div>
          <p class="eyebrow">Controlled validation</p>
          <h2>The next decision is whether the rule survives real operations</h2>
          <div class="pilot-callout">
            <strong>Four weeks or 50 eligible cases, whichever is later</strong>
            <p>Compare invisible recommendations with manager decisions and replace assumed costs before exposing guidance.</p>
          </div>
        </div>
        <div>
          <h3>Measure before adoption</h3>
          <div class="success-measures">
            <div><h3>Guest recovery</h3><p>Satisfaction, reviews, and unresolved complaints.</p></div>
            <div><h3>Relationship</h3><p>Repeat stays, cancellations, and retained revenue.</p></div>
            <div><h3>Economics</h3><p>Marginal cost and room-rate erosion.</p></div>
            <div><h3>Adoption</h3><p>Overrides, approval time, and exceptions.</p></div>
          </div>
          <p class="data-needed"><strong>Decision gate:</strong> advance only if protections hold with actual costs and outcomes; otherwise revise or stop. Minimum data: comps, service tickets, outcomes, costs, and operating constraints.</p>
        </div>
      </div>
    </section>

    <section class="evidence" id="evidence">
      <div class="shell evidence-grid">
        <div>
          <h2>Methods and engineering evidence</h2>
          <p>Supporting reports document reconciliation, decision contracts, stress tests, and S3-to-Snowflake lineage.</p>
          <p class="pipeline-proof">{escape(decision_source_note)}</p>
        </div>
        <nav class="evidence-links" aria-label="Supporting technical evidence">
          <a href="reports/engineering-evidence.md">Engineering evidence</a>
          <a href="reports/methodology-and-assumptions.md">Methodology and assumptions</a>
          <a href="reports/policy-decision-analysis.md">Policy decision analysis</a>
          <a href="reports/policy-sensitivity.md">Policy sensitivity</a>
          <a href="reports/data-lineage.md">Data lineage</a>
          <a href="reports/snowflake-validation.md">Warehouse validation</a>
          <a href="reports/proper-public-context.md">Public property context</a>
          <a href="reports/comp-optimization-dashboard.html">Simulation audit dashboard</a>
        </nav>
      </div>
    </section>
  </main>

  <footer>
    <div class="shell">This prototype uses synthetic hotel operations and bounded public Santa Monica Proper context. It does not use or claim access to internal guest, comp, rate, margin, inventory, or policy data.</div>
  </footer>

  <script type="application/json" id="scenario-data">{scenario_json}</script>
  <script>
    (() => {{
      const scenarios = JSON.parse(document.getElementById("scenario-data").textContent);
      const tabs = [...document.querySelectorAll(".scenario-tab")];
      const fields = {{
        title: document.getElementById("scenario-title"),
        context: document.getElementById("scenario-context"),
        amount: document.getElementById("scenario-amount"),
        gesture: document.getElementById("scenario-gesture"),
        cost_range: document.getElementById("scenario-cost"),
        approval: document.getElementById("scenario-approval"),
        robustness: document.getElementById("scenario-robustness"),
        counterfactual: document.getElementById("scenario-counterfactual"),
        alternative: document.getElementById("scenario-alternative")
      }};
      const reasonList = document.getElementById("scenario-reasons");

      function selectScenario(key, updateUrl = true) {{
        const scenario = scenarios[key];
        if (!scenario) return;
        Object.entries(fields).forEach(([name, node]) => {{ node.textContent = scenario[name]; }});
        reasonList.replaceChildren(...scenario.reasons.map(reason => {{
          const item = document.createElement("li");
          item.textContent = reason;
          return item;
        }}));
        tabs.forEach(tab => tab.setAttribute("aria-pressed", String(tab.dataset.scenario === key)));
        if (updateUrl && history.replaceState && window.location.protocol !== "file:") {{
          const url = new URL(window.location.href);
          url.searchParams.set("scenario", key);
          history.replaceState(null, "", url);
        }}
      }}

      tabs.forEach(tab => tab.addEventListener("click", () => selectScenario(tab.dataset.scenario)));
      const requested = new URLSearchParams(window.location.search).get("scenario");
      if (requested && scenarios[requested]) selectScenario(requested, false);
    }})();
  </script>
</body>
</html>"""


def main() -> int:
    output_path = PROJECT_ROOT / "index.html"
    output_path.write_text(render_stakeholder_page(), encoding="utf-8")
    print(f"Wrote stakeholder report to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
