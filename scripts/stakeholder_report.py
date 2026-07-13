from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from html import escape

from common import (
    POLICY_DECISION_SUMMARY_PATH,
    SNOWFLAKE_EXTRACT_MANIFEST_PATH,
    SNOWFLAKE_POLICY_TRADEOFF_EXTRACT_PATH,
    read_csv_rows,
    read_json,
)
from evaluate_policy_strategies import recommend_policy_strategy
from manager_app import PRESETS
from policy_config import comp_catalog
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
            "These are simulated tradeoffs to validate in shadow mode, not projected business results."
        ),
    }


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
            "Meets the reference recovery tier and issue-fit guardrail",
            "Uses the lowest modeled cost among robust-fit gestures",
        ]
        if strategy_result["manager_review_required"]:
            reason_labels.append("Retains manager approval for exposure or uncertainty")
        if float(PRESETS[key].get("hotel_responsibility", 0)) >= 0.7:
            reason_labels.append("Hotel clearly owns the service failure")
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
                    f"Clears guardrails in {float(selected_summary['joint_guardrail_pass_probability']):.1%} of shared assumption-stress draws"
                ),
                "reasons": reason_labels,
                "counterfactual": (
                    "Shadow mode must confirm actual availability and marginal cost; changed property inputs could shift the recommendation. "
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
    selected = decision_context.get("selected")
    summary_rows = list(decision_context["summary_rows"])
    scenarios = build_scenario_presentations()
    default = scenarios[0]
    scenario_json = json.dumps({row["key"]: row for row in scenarios}).replace("</", "<\\/")
    tabs = "".join(
        f'<button class="scenario-tab" type="button" data-scenario="{escape(str(row["key"]))}" '
        f'aria-pressed="{"true" if index == 0 else "false"}">{escape(str(row["tab_label"]))}</button>'
        for index, row in enumerate(scenarios)
    )
    reasons = "".join(f"<li>{escape(str(reason))}</li>" for reason in default["reasons"])
    comparison_rows = "".join(
        ("<tr class=\"selected-policy\">" if row.get("selected_for_pilot") == "true" else "<tr>")
        + f"<th scope=\"row\">{escape(row['policy_label'])}</th>"
        + f"<td data-label=\"Safe path\">{float(row['adequacy_rate']):.0%}</td>"
        + f"<td data-label=\"Gesture fit\">{float(row['gesture_adequacy_rate']):.0%}</td>"
        + f"<td data-label=\"Midpoint cost\">{money(float(row['internal_cost_mid']))}</td>"
        + f"<td data-label=\"Direct refund\">{money(float(row['direct_room_refund_value']))}</td>"
        + (
            "<td data-label=\"Manager review\">Unknown</td>"
            if int(row.get("manager_review_evaluable_cases", 0)) == 0
            else f"<td data-label=\"Manager review\">{float(row['manager_review_rate']):.0%}</td>"
        )
        + f"<td data-label=\"Stress-test pass rate\">{float(row['joint_guardrail_pass_probability']):.1%}</td></tr>"
        for row in summary_rows
    )
    selected_label = escape(str(decision_context["selected_policy_label"]))
    executive_recommendation = escape(str(decision_context["recommendation"]))
    tradeoff = escape(str(decision_context["tradeoff"]))
    decision_provenance = dict(decision_context["decision_provenance"])
    decision_source_note = (
        "Decision metrics were extracted from Snowflake and parity-checked against the versioned policy mart."
        if decision_provenance.get("parity_verified")
        else "Decision metrics use the versioned local mart; cloud execution evidence is reported separately."
    )
    selected_metrics = selected or {
        "adequacy_rate": "0",
        "gesture_adequacy_rate": "0",
        "joint_guardrail_pass_probability": "0",
        "internal_cost_mid": "0",
    }
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="A luxury-hospitality service recovery decision prototype for intelligent, explainable guest recovery.">
  <title>Service Recovery Decision Prototype</title>
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
    .principle {{ margin: 18px 0 0 202px; color: var(--muted); font-size: .91rem; }}
    .principle b {{ color: var(--ink); }}
    .evidence-boundary {{ max-width: 850px; margin: 18px 0 0 202px; color: var(--muted); font-size: .84rem; }}
    section {{ padding: 54px 0; }}
    .band {{ background: var(--paper); border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); }}
    .section-head {{ max-width: 720px; margin-bottom: 28px; }}
    .section-head p {{ margin: 0; color: var(--muted); }}
    .policy-table-wrap {{ width: 100%; overflow-x: auto; border: 1px solid var(--line); background: var(--white); }}
    .policy-comparison-table {{ width: 100%; min-width: 820px; border-collapse: collapse; }}
    .policy-comparison-table th, .policy-comparison-table td {{ padding: 12px 13px; border-bottom: 1px solid var(--line); text-align: left; font-size: .82rem; }}
    .policy-comparison-table thead th {{ color: var(--muted); font-weight: 700; }}
    .policy-comparison-table tbody th {{ max-width: 210px; color: var(--ink); }}
    .policy-comparison-table .selected-policy {{ background: var(--teal-soft); }}
    .policy-comparison-table .selected-policy th {{ color: var(--teal-dark); }}
    .comparison-note {{ display: grid; grid-template-columns: 180px minmax(0, 1fr); gap: 22px; margin-top: 22px; padding-top: 20px; border-top: 1px solid var(--line); }}
    .comparison-note strong {{ color: var(--coral); font-size: .82rem; text-transform: uppercase; }}
    .comparison-note p {{ margin: 0; color: var(--muted); }}
    .comparison-definition {{ margin: 14px 0 0; color: var(--muted); font-size: .82rem; }}
    .selection-metrics {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); margin-top: 26px; border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); }}
    .selection-metrics div {{ padding: 15px; border-right: 1px solid var(--line); }}
    .selection-metrics div:last-child {{ border-right: 0; }}
    .selection-metrics span {{ display: block; color: var(--muted); font-size: .74rem; }}
    .selection-metrics strong {{ display: block; margin-top: 4px; font-size: 1rem; }}
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
    .policy-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); margin-top: 28px; }}
    .policy-step {{ min-width: 0; padding: 0 28px; border-right: 1px solid var(--line); }}
    .policy-step:first-child {{ padding-left: 0; }}
    .policy-step:last-child {{ padding-right: 0; border-right: 0; }}
    .step-number {{ display: block; margin-bottom: 13px; color: var(--coral); font-size: 1.5rem; font-weight: 800; }}
    .policy-step p {{ margin: 0; color: var(--muted); font-size: .92rem; }}
    .drivers {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 24px; margin-top: 38px; padding-top: 28px; border-top: 1px solid var(--line); }}
    .drivers p {{ margin: 0; color: var(--muted); font-size: .88rem; }}
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
      .principle, .evidence-boundary {{ margin-left: 0; }}
      .comparison-note {{ grid-template-columns: 1fr; gap: 6px; }}
      .selection-metrics {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .selection-metrics div:nth-child(2) {{ border-right: 0; }}
      .selection-metrics div:nth-child(-n+2) {{ border-bottom: 1px solid var(--line); }}
      .decision {{ grid-template-columns: 1fr; }}
      .decision-support {{ border-top: 1px solid var(--line); border-left: 0; }}
      .property-menu {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .property-menu div, .property-menu div:first-child, .property-menu div:last-child {{ padding: 14px; border-right: 0; border-bottom: 1px solid var(--line); }}
      .property-menu div:nth-child(odd) {{ border-right: 1px solid var(--line); }}
      .property-menu div:last-child {{ border-bottom: 0; }}
      .policy-grid {{ grid-template-columns: 1fr; gap: 24px; }}
      .policy-step, .policy-step:first-child, .policy-step:last-child {{ padding: 0 0 24px; border-right: 0; border-bottom: 1px solid var(--line); }}
      .policy-step:last-child {{ padding-bottom: 0; border-bottom: 0; }}
      .drivers {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
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
      .reasons, .drivers, .success-measures, .evidence-links {{ grid-template-columns: 1fr; }}
      .property-menu {{ grid-template-columns: 1fr; }}
      .property-menu div:nth-child(odd) {{ border-right: 0; }}
      .principle span {{ display: block; }}
      .selection-metrics {{ grid-template-columns: 1fr; }}
      .selection-metrics div, .selection-metrics div:nth-child(2) {{ border-right: 0; border-bottom: 1px solid var(--line); }}
      .selection-metrics div:last-child {{ border-bottom: 0; }}
      .policy-comparison-table {{ min-width: 0; }}
      .policy-comparison-table thead {{ display: none; }}
      .policy-comparison-table, .policy-comparison-table tbody, .policy-comparison-table tr {{ display: block; }}
      .policy-comparison-table tr {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); padding: 14px; border-bottom: 1px solid var(--line); }}
      .policy-comparison-table tr:last-child {{ border-bottom: 0; }}
      .policy-comparison-table tbody th {{ grid-column: 1 / -1; max-width: none; padding: 0 0 10px; border: 0; font-size: .95rem; }}
      .policy-comparison-table td {{ padding: 7px 8px 7px 0; border: 0; font-weight: 700; }}
      .policy-comparison-table td::before {{ content: attr(data-label); display: block; margin-bottom: 2px; color: var(--muted); font-size: .7rem; font-weight: 500; }}
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
      <h1>Comp Policy Shadow-Validation Decision</h1>
      <p class="lead">A simulation-backed recommendation on which service-recovery policy should enter invisible shadow validation before any manager-facing or permanent operating change.</p>
      <div class="proposal">
        <strong>Executive decision</strong>
        <p>{executive_recommendation}</p>
      </div>
      <p class="principle"><b>Selected policy:</b> <span>{selected_label} · guest protection first · cost choice second · manager judgment retained</span></p>
      <p class="evidence-boundary">Synthetic policy comparison, not observed Proper Hotels performance or projected savings. Public property context informs gesture fit and guest-facing value only.</p>
    </div>
  </header>

  <main>
    <section class="band" id="policy-comparison">
      <div class="shell">
        <div class="section-head">
          <p class="eyebrow">Decision evidence</p>
          <h2>Five policies tested against the same 430 synthetic recovery cases</h2>
          <p>Given the declared assumptions, the selection rule requires a safe recovery path, reliable escalation, data-quality holds, and operational feasibility before modeled cost can determine the shadow-validation candidate.</p>
        </div>
        <div class="policy-table-wrap">
          <table class="policy-comparison-table">
            <thead><tr><th>Policy</th><th>Safe path</th><th>Gesture fit</th><th>Midpoint cost</th><th>Direct refund face value</th><th>Manager review</th><th>Stress-test pass rate</th></tr></thead>
            <tbody>{comparison_rows}</tbody>
          </table>
        </div>
        <div class="selection-metrics" aria-label="Selected policy evidence">
          <div><span>Safe recovery path</span><strong>{float(selected_metrics['adequacy_rate']):.0%}</strong></div>
          <div><span>Strict gesture fit</span><strong>{float(selected_metrics['gesture_adequacy_rate']):.0%}</strong></div>
          <div><span>Modeled midpoint cost</span><strong>{money(float(selected_metrics['internal_cost_mid']))}</strong></div>
          <div><span>Assumption-stress pass rate</span><strong>{float(selected_metrics['joint_guardrail_pass_probability']):.1%}</strong></div>
        </div>
        <div class="comparison-note"><strong>Material tradeoff</strong><p>{tradeoff}</p></div>
        <p class="comparison-definition">Safe path means an adequate gesture or an explicit manager-review path; gesture fit reports adequacy of the proposed gesture alone. This is constrained optimization under declared assumptions, not independent evidence of guest or profit outcomes.</p>
      </div>
    </section>

    <section id="worked-decision">
      <div class="shell">
        <div class="section-head">
          <p class="eyebrow">Worked decision</p>
          <h2>From service failure to a manager-ready recommendation</h2>
          <p>Choose a scenario to see how the same operating policy adapts to the guest, failure, timing, and available recovery options.</p>
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
              <div><span>Decision robustness</span><strong id="scenario-robustness">{escape(str(default['robustness']))}</strong></div>
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
            <p>Public prices can anchor guest-facing value. Actual marginal cost requires property accounting, inventory, and outlet-capacity data.</p>
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

    <section id="operating-policy">
      <div class="shell">
        <div class="section-head">
          <p class="eyebrow">Proposed shadow-validation policy</p>
          <h2>Guardrails determine safety before cost determines the gesture</h2>
          <p>{selected_label} is an adequacy-constrained, manager-assisted policy. It is not a mandate to minimize comps.</p>
        </div>
        <div class="policy-grid">
          <div class="policy-step"><span class="step-number">01</span><h3>Protect</h3><p>Require a tier-appropriate gesture with a recovery-fit margin that survives the tested assumption range.</p></div>
          <div class="policy-step"><span class="step-number">02</span><h3>Review</h3><p>Escalate weak-fit, severe, high-value, capacity-constrained, or repeat-pattern cases rather than forcing an automated answer.</p></div>
          <div class="policy-step"><span class="step-number">03</span><h3>Choose</h3><p>Only after protection and review rules pass, select the lowest modeled-cost adequate gesture and preserve alternatives.</p></div>
        </div>
        <div class="drivers">
          <div><h3>Guest relationship</h3><p>Current stay value, repeat relationship, and the value at risk.</p></div>
          <div><h3>Service failure</h3><p>Severity, hotel responsibility, delay, sentiment, and reputation exposure.</p></div>
          <div><h3>Operating conditions</h3><p>Room availability, timing, demand pressure, and whether recovery is still possible in stay.</p></div>
          <div><h3>Gesture economics</h3><p>Guest-perceived value, working cost range, property fit, and room-rate erosion.</p></div>
        </div>
      </div>
    </section>

    <section class="band" id="pilot">
      <div class="shell pilot">
        <div>
          <p class="eyebrow">Proposed next step</p>
          <h2>Shadow first, manager-assisted test second</h2>
          <div class="pilot-callout">
            <strong>Four weeks or 50 eligible cases, whichever is later</strong>
            <p>Run recommendations invisibly, reconcile them with manager decisions, replace assumed costs, and calculate the controlled-phase sample requirement before exposing guidance.</p>
          </div>
        </div>
        <div>
          <h3>What the controlled test should measure</h3>
          <div class="success-measures">
            <div><h3>Guest recovery</h3><p>Post-resolution satisfaction, review sentiment, and unresolved complaints.</p></div>
            <div><h3>Relationship</h3><p>Repeat stays, cancellations, and retained future revenue.</p></div>
            <div><h3>Economics</h3><p>Marginal cost, guest-facing value, and avoidable room-rate erosion.</p></div>
            <div><h3>Operating adoption</h3><p>Manager overrides, approval time, consistency, and reasons for exceptions.</p></div>
          </div>
          <p class="data-needed"><strong>Minimum data:</strong> comp actions and approvals, service tickets, guest and stay context, post-recovery outcomes, marginal-cost ranges, and live operating constraints.</p>
        </div>
      </div>
    </section>

    <section class="evidence" id="evidence">
      <div class="shell evidence-grid">
        <div>
          <h2>Substantial technical work sits behind a deliberately simple decision product</h2>
          <p>The prototype reconciles synthetic PMS, CRM, service, comp, POS, survey, and operating extracts; preserves data-quality holds; versions policy assumptions; returns alternatives; and checks whether recommendations remain stable when assumptions change.</p>
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
    <div class="shell">This discussion prototype uses synthetic hotel operations and bounded public Santa Monica Proper context. It does not use or claim access to Proper Hotels internal guest records, comp history, rates, margins, inventory, or policy.</div>
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
