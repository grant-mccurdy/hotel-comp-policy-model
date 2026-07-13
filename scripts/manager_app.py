from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

from common import POLICY_DECISION_SUMMARY_PATH, read_csv_rows
from evaluate_policy_strategies import recommend_policy_strategy
from recommend_scenario import money
from scenario_contract import ScenarioInput, ScenarioValidationError


DEFAULT_SCENARIO = {
    "guest_tier": "loyalty_guest",
    "traveler_segment": "coastal_weekend",
    "stay_value": "2800",
    "estimated_lifetime_value": "14000",
    "nightly_rate": "700",
    "repeat_comp_review_risk": "0.04",
    "failure_category": "room_readiness_delay",
    "failure_type": "outcome",
    "severity": "4",
    "hotel_responsibility": "0.90",
    "reported_in_stay": "true",
    "resolution_delay_minutes": "95",
    "sentiment_intensity": "0.76",
    "review_risk": "0.80",
    "occupancy_pressure": "0.72",
    "public_rate_pressure": "0.50",
    "high_demand_rate": "false",
    "upgrade_opportunity_cost": "0",
    "refund_cost_pressure": "1.00",
    "rate_context_confidence": "0.00",
    "property_context_confidence": "0.88",
    "rooftop_f_and_b_fit_modifier": "1.22",
    "spa_wellness_fit_modifier": "1.18",
    "lobby_lounge_fit_modifier": "1.12",
    "parking_fee_fit_modifier": "1.04",
    "late_checkout_fit_modifier": "1.04",
    "room_upgrade_fit_modifier": "1.08",
    "review_context_confidence": "0.00",
    "local_demand_pressure": "0.35",
    "high_local_demand": "false",
    "demand_context_confidence": "0.00",
}

PRESETS = {
    "arrival_delay": {
        **DEFAULT_SCENARIO,
        "failure_category": "room_readiness_delay",
        "severity": "4",
        "hotel_responsibility": "0.90",
        "occupancy_pressure": "0.72",
    },
    "dining_lapse": {
        **DEFAULT_SCENARIO,
        "guest_tier": "returning_guest",
        "stay_value": "1800",
        "estimated_lifetime_value": "7200",
        "nightly_rate": "600",
        "failure_category": "f_and_b_service_lapse",
        "failure_type": "process",
        "severity": "4",
        "hotel_responsibility": "0.78",
        "review_risk": "0.66",
        "occupancy_pressure": "0.64",
    },
    "suite_recovery": {
        **DEFAULT_SCENARIO,
        "guest_tier": "vip_guest",
        "traveler_segment": "event_or_suite_guest",
        "stay_value": "5200",
        "estimated_lifetime_value": "32000",
        "nightly_rate": "1300",
        "failure_category": "housekeeping_miss",
        "severity": "5",
        "hotel_responsibility": "0.95",
        "review_risk": "0.90",
        "occupancy_pressure": "0.86",
    },
    "parking_friction": {
        **DEFAULT_SCENARIO,
        "guest_tier": "loyalty_guest",
        "traveler_segment": "local_staycation",
        "stay_value": "1600",
        "estimated_lifetime_value": "9000",
        "nightly_rate": "530",
        "failure_category": "valet_or_parking_delay",
        "failure_type": "process",
        "severity": "3",
        "hotel_responsibility": "0.72",
        "review_risk": "0.58",
        "occupancy_pressure": "0.70",
    },
}

GUEST_TIERS = ["new_guest", "returning_guest", "loyalty_guest", "vip_guest", "event_or_suite_guest"]
TRAVELER_SEGMENTS = [
    "coastal_weekend",
    "wellness_getaway",
    "business_traveler",
    "design_leisure",
    "event_or_suite_guest",
    "local_staycation",
]
FAILURE_CATEGORIES = [
    "room_readiness_delay",
    "room_assignment_expectation_gap",
    "housekeeping_miss",
    "maintenance_issue",
    "noise_disruption",
    "billing_or_fee_dispute",
    "f_and_b_service_lapse",
    "rooftop_pool_access_issue",
    "spa_wellness_service_issue",
    "valet_or_parking_delay",
]


@dataclass(frozen=True)
class ManagerRecommendation:
    policy_id: str
    policy_label: str
    comparison_version: str
    comp_code: str
    comp_label: str
    recommended_value: int
    internal_cost_low: int
    internal_cost_high: int
    recommended_tier: int
    recovery_need_score: float
    manager_review_flag: bool
    joint_guardrail_pass_probability: float
    reason_codes: list[str]
    confirmation_items: list[str]
    alternatives: list[dict[str, object]]
    assumptions: list[str]
    explanation: str


def selected_policy_context() -> dict[str, str]:
    if not POLICY_DECISION_SUMMARY_PATH.exists():
        raise RuntimeError("Missing policy decision summary. Run `make compare-policies` first.")
    _, rows = read_csv_rows(POLICY_DECISION_SUMMARY_PATH)
    selected = next((row for row in rows if row.get("selected_for_pilot") == "true"), None)
    if selected is None:
        raise RuntimeError("No policy met the shadow-validation guardrails; the manager desk remains disabled.")
    return selected


def format_label(value: str) -> str:
    return value.replace("_", " ").replace("f and b", "F&B").replace("spa wellness", "spa/wellness")


def params_from_query(query: str) -> dict[str, str]:
    parsed = parse_qs(query)
    preset = str((parsed.get("preset") or [""])[0])
    params = dict(PRESETS.get(preset, DEFAULT_SCENARIO))
    for key, values in parsed.items():
        if key != "preset" and values:
            params[key] = values[0]
    return params


def select(name: str, options: list[tuple[str, str]], selected: str) -> str:
    output = []
    for value, label in options:
        selected_attr = " selected" if value == selected else ""
        output.append(f'<option value="{escape(value)}"{selected_attr}>{escape(label)}</option>')
    return f'<select id="{escape(name)}" name="{escape(name)}">{"".join(output)}</select>'


def number_input(
    name: str,
    params: dict[str, str],
    label: str,
    minimum: str,
    maximum: str,
    step: str = "1",
) -> str:
    value = escape(str(params.get(name, DEFAULT_SCENARIO[name])))
    return (
        f'<label for="{escape(name)}"><span>{escape(label)}</span>'
        f'<input id="{escape(name)}" name="{escape(name)}" value="{value}" type="number" '
        f'min="{escape(minimum)}" max="{escape(maximum)}" step="{escape(step)}" required></label>'
    )


def scenario_to_recommendation(params: dict[str, str]) -> tuple[ScenarioInput, ManagerRecommendation]:
    scenario = ScenarioInput.from_mapping(params)
    policy_context = selected_policy_context()
    result = recommend_policy_strategy(params, policy_context["policy_id"])
    reasons = ["tier_appropriate_recovery", "lowest_cost_robust_fit"]
    if result["manager_review_required"]:
        reasons.append("manager_review_required")
    if result["fit_uncertainty_review"]:
        reasons.append("fit_uncertainty_requires_review")
    if result["operational_pressure_review"]:
        reasons.append("operational_availability_requires_review")
    if float(params.get("hotel_responsibility", 0)) >= 0.7:
        reasons.append("hotel_responsible_failure")
    confirmation_items = [
        "Confirm actual gesture availability and marginal cost before approval.",
        "Record the manager decision, override reason, and guest response for controlled-test evaluation.",
    ]
    if result["operational_pressure_review"]:
        confirmation_items.insert(0, "Confirm room, outlet, or service capacity before offering the gesture.")
    recommendation = ManagerRecommendation(
        policy_id=str(result["policy_id"]),
        policy_label=str(result["policy_label"]),
        comparison_version=policy_context["comparison_version"],
        comp_code=str(result["comp_code"]),
        comp_label=str(result["comp_label"]),
        recommended_value=int(float(result["recommended_value"])),
        internal_cost_low=int(float(result["internal_cost_low"])),
        internal_cost_high=int(float(result["internal_cost_high"])),
        recommended_tier=int(result["reference_recovery_tier"]),
        recovery_need_score=float(result["reference_recovery_need_score"]),
        manager_review_flag=bool(result["manager_review_required"]),
        joint_guardrail_pass_probability=float(policy_context["joint_guardrail_pass_probability"]),
        reason_codes=reasons,
        confirmation_items=confirmation_items,
        alternatives=list(result["alternatives"]),
        assumptions=[
            "Synthetic policy comparison; not observed hotel performance or projected savings.",
            "Public property context informs guest-facing value and gesture fit, not internal margin.",
            "Actual policy, availability, marginal cost, and guest outcomes require shadow validation.",
        ],
        explanation=(
            f"{result['policy_label']} first requires a tier-appropriate, robust-fit recovery path, then selects "
            "the lowest modeled-cost eligible gesture. Manager review remains required when exposure, fit, or "
            "operating conditions warrant it."
        ),
    )
    return scenario, recommendation


def render_errors(errors: dict[str, str]) -> str:
    items = "".join(f"<li><strong>{escape(format_label(field))}:</strong> {escape(message)}</li>" for field, message in sorted(errors.items()))
    return f'<section class="validation" role="alert"><h2>Review scenario inputs</h2><ul>{items}</ul></section>'


def render_result(recommendation: ManagerRecommendation) -> str:
    suffix = " + manager note" if recommendation.recommended_tier >= 3 and recommendation.comp_code != "manager_note" else ""
    reasons = "".join(f'<span class="reason">{escape(format_label(reason))}</span>' for reason in recommendation.reason_codes)
    confirmation_items = "".join(f"<li>{escape(item)}</li>" for item in recommendation.confirmation_items)
    alternatives = "".join(
        "<tr>"
        f"<td>{escape(str(item['comp_label']))}</td>"
        f"<td>{escape(money(item['guest_facing_value']))}</td>"
        f"<td>{escape(money(item['internal_cost_low']))}-{escape(money(item['internal_cost_high']))}</td>"
        "</tr>"
        for item in recommendation.alternatives
    )
    review_status = "Manager approval" if recommendation.manager_review_flag else "Within simulated policy"
    return f"""
    <section class="result">
      <p class="eyebrow">Recommended recovery</p>
      <h2>{escape(money(recommendation.recommended_value))} {escape(recommendation.comp_label)}{suffix}</h2>
      <p class="decision-line">{escape(review_status)} · {escape(recommendation.policy_label)} shadow-validation candidate</p>
      <div class="metrics">
        <div><span>Estimated internal cost</span><strong>{escape(money(recommendation.internal_cost_low))}-{escape(money(recommendation.internal_cost_high))}</strong></div>
        <div><span>Recovery need</span><strong>{recommendation.recovery_need_score:.1f}/100</strong></div>
        <div><span>Policy assumption-stress pass rate</span><strong>{recommendation.joint_guardrail_pass_probability:.1%}</strong></div>
        <div><span>Policy comparison</span><strong>{escape(recommendation.comparison_version)}</strong></div>
      </div>
      <h3>Decision drivers</h3>
      <div class="reason-list">{reasons}</div>
      <h3>What must be confirmed</h3>
      <ul>{confirmation_items}</ul>
      <h3>Closest alternatives</h3>
      <table><thead><tr><th>Gesture</th><th>Guest value</th><th>Estimated cost</th></tr></thead><tbody>{alternatives}</tbody></table>
      <p>{escape(recommendation.explanation)}</p>
      <details><summary>Assumptions and boundary</summary><ul>{''.join(f'<li>{escape(item)}</li>' for item in recommendation.assumptions)}</ul></details>
    </section>
    """


def render_page(params: dict[str, str], errors: dict[str, str] | None = None) -> str:
    recommendation_html = render_errors(errors or {}) if errors else ""
    if not errors:
        _, recommendation = scenario_to_recommendation(params)
        recommendation_html = render_result(recommendation)
    preset_links = "".join(
        f'<a href="/?{urlencode({"preset": key})}">{escape(label)}</a>'
        for key, label in [
            ("arrival_delay", "Arrival delay"),
            ("dining_lapse", "Dining lapse"),
            ("suite_recovery", "Suite recovery"),
            ("parking_friction", "Parking friction"),
        ]
    )
    reported = params.get("reported_in_stay", "true")
    high_demand = params.get("high_demand_rate", "false")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Service Recovery Decision Desk</title>
  <style>
    :root {{ color-scheme: light; --ink:#191d1c; --muted:#626966; --line:#d8dcda; --paper:#f4f5f3; --accent:#176b5f; --accent-dark:#104b44; --warn:#8b3e20; }}
    * {{ box-sizing:border-box; }}
    html, body {{ width:100%; max-width:100%; overflow-x:hidden; }}
    body {{ margin:0; color:var(--ink); background:var(--paper); font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif; line-height:1.45; }}
    header {{ background:#fff; border-bottom:1px solid var(--line); padding:24px clamp(18px,4vw,52px); }}
    header h1 {{ margin:0; font-size:1.65rem; letter-spacing:0; }}
    header p {{ margin:5px 0 0; color:var(--muted); max-width:760px; }}
    .presets {{ display:flex; gap:8px; flex-wrap:wrap; margin-top:14px; }}
    .presets a {{ color:var(--accent-dark); text-decoration:none; border:1px solid var(--line); padding:6px 9px; border-radius:5px; font-size:.86rem; }}
    main {{ display:grid; grid-template-columns:minmax(320px,430px) minmax(0,1fr); gap:24px; padding:24px clamp(18px,4vw,52px) 44px; max-width:1440px; margin:auto; min-width:0; }}
    main > *, form, .result, .validation {{ min-width:0; max-width:100%; }}
    form, .result, .validation {{ background:#fff; border:1px solid var(--line); border-radius:7px; padding:18px; }}
    form {{ display:grid; gap:16px; align-self:start; }}
    fieldset {{ border:0; border-top:1px solid var(--line); margin:0; padding:15px 0 0; display:grid; gap:11px; }}
    fieldset:first-child {{ border-top:0; padding-top:0; }}
    legend {{ padding:0; margin-bottom:8px; font-weight:750; font-size:.9rem; color:var(--accent-dark); }}
    label {{ display:grid; gap:4px; color:var(--muted); font-size:.86rem; }}
    input, select {{ width:100%; min-width:0; max-width:100%; border:1px solid var(--line); border-radius:5px; padding:8px 9px; color:var(--ink); background:#fff; font:inherit; }}
    .radio {{ display:flex; gap:14px; }} .radio label {{ display:flex; align-items:center; gap:5px; color:var(--ink); }} .radio input {{ width:auto; }}
    button {{ border:0; border-radius:5px; padding:10px 14px; background:var(--accent); color:#fff; font:inherit; font-weight:750; cursor:pointer; }}
    h2 {{ color:var(--accent-dark); margin:4px 0 8px; font-size:1.55rem; letter-spacing:0; }}
    h3 {{ font-size:.95rem; margin:20px 0 8px; }}
    p {{ color:var(--muted); }} .eyebrow {{ text-transform:uppercase; color:var(--accent); font-size:.75rem; font-weight:800; margin:0; }}
    .decision-line {{ margin:0 0 16px; }}
    .metrics {{ display:grid; grid-template-columns:repeat(4,minmax(110px,1fr)); gap:8px; border-top:1px solid var(--line); border-bottom:1px solid var(--line); padding:14px 0; }}
    .metrics span {{ display:block; color:var(--muted); font-size:.76rem; }} .metrics strong {{ display:block; margin-top:3px; font-size:.98rem; overflow-wrap:anywhere; }}
    .reason-list {{ display:flex; gap:6px; flex-wrap:wrap; }} .reason {{ background:#edf5f2; color:var(--accent-dark); padding:4px 7px; border-radius:4px; font-size:.8rem; }}
    table {{ width:100%; border-collapse:collapse; }} th,td {{ padding:8px; border-bottom:1px solid var(--line); text-align:left; font-size:.86rem; }} th {{ color:var(--muted); font-weight:650; }}
    details {{ margin-top:18px; border-top:1px solid var(--line); padding-top:12px; color:var(--muted); }} summary {{ cursor:pointer; color:var(--ink); font-weight:650; }}
    .validation {{ border-color:#e4b7a5; }} .validation h2 {{ color:var(--warn); }}
    @media (max-width:900px) {{ main {{ grid-template-columns:minmax(0,1fr); }} .metrics {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} }}
    @media (max-width:600px) {{
      header {{ padding:18px; }}
      header h1 {{ font-size:1.4rem; overflow-wrap:anywhere; }}
      main {{ gap:18px; padding:18px 18px 32px; }}
      form, .result, .validation {{ padding:15px; }}
      h2 {{ font-size:1.3rem; overflow-wrap:anywhere; }}
      .presets a {{ flex:1 1 auto; text-align:center; }}
      .result {{ overflow-wrap:anywhere; }}
      .result table {{ display:table; table-layout:fixed; white-space:normal; }}
      .result th, .result td {{ padding:7px 4px; font-size:.78rem; overflow-wrap:anywhere; }}
      .result th:nth-child(1), .result td:nth-child(1) {{ width:44%; }}
      .result th:nth-child(2), .result td:nth-child(2) {{ width:22%; }}
      .result th:nth-child(3), .result td:nth-child(3) {{ width:34%; }}
      .result ul {{ padding-left:20px; }}
      button {{ width:100%; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Service Recovery Decision Desk</h1>
    <p>Luxury hospitality recovery policy simulation using synthetic operating data and public Santa Monica property context.</p>
    <nav class="presets" aria-label="Scenario presets">{preset_links}</nav>
  </header>
  <main>
    <form method="get" action="/">
      <fieldset>
        <legend>Guest relationship</legend>
        <label for="guest_tier"><span>Guest relationship</span>{select("guest_tier", [(x, format_label(x)) for x in GUEST_TIERS], params['guest_tier'])}</label>
        <label for="traveler_segment"><span>Stay context</span>{select("traveler_segment", [(x, format_label(x)) for x in TRAVELER_SEGMENTS], params['traveler_segment'])}</label>
        {number_input('stay_value', params, 'Current stay value', '0', '100000')}
        {number_input('estimated_lifetime_value', params, 'Estimated relationship value', '0', '1000000')}
        {number_input('nightly_rate', params, 'Nightly room rate', '0', '25000')}
        <label for="repeat_comp_review_risk"><span>Prior comp pattern review</span>{select('repeat_comp_review_risk', [('0.04','No concern'),('0.35','Review history'),('0.75','Manager review required')], params['repeat_comp_review_risk'])}</label>
      </fieldset>
      <fieldset>
        <legend>Service failure</legend>
        <label for="failure_category"><span>Issue</span>{select('failure_category', [(x, format_label(x)) for x in FAILURE_CATEGORIES], params['failure_category'])}</label>
        <label for="failure_type"><span>Failure type</span>{select('failure_type', [('process','Process'),('outcome','Outcome')], params['failure_type'])}</label>
        <label for="severity"><span>Severity</span>{select('severity', [(str(x), f'{x} / 5') for x in range(1,6)], params['severity'])}</label>
        <label for="hotel_responsibility"><span>Hotel responsibility</span>{select('hotel_responsibility', [('0.30','Low'),('0.65','Shared or moderate'),('0.90','High'),('0.98','Clear and severe')], params['hotel_responsibility'])}</label>
        <label><span>Reported during stay</span><span class="radio"><label><input type="radio" name="reported_in_stay" value="true"{' checked' if reported == 'true' else ''}>Yes</label><label><input type="radio" name="reported_in_stay" value="false"{' checked' if reported != 'true' else ''}>No</label></span></label>
        {number_input('resolution_delay_minutes', params, 'Resolution delay, minutes', '0', '10080')}
        <label for="review_risk"><span>Reputation risk</span>{select('review_risk', [('0.25','Low'),('0.50','Moderate'),('0.75','High'),('0.90','Critical')], params['review_risk'])}</label>
      </fieldset>
      <fieldset>
        <legend>Operational context</legend>
        <label for="occupancy_pressure"><span>Room availability pressure</span>{select('occupancy_pressure', [('0.35','Flexible'),('0.65','Moderate'),('0.85','Constrained'),('0.95','Very constrained')], params['occupancy_pressure'])}</label>
        <label for="public_rate_pressure"><span>Public rate pressure</span>{select('public_rate_pressure', [('0.35','Low'),('0.50','Typical'),('0.75','High'),('0.90','Peak')], params['public_rate_pressure'])}</label>
        <label><span>Peak demand period</span><span class="radio"><label><input type="radio" name="high_demand_rate" value="true"{' checked' if high_demand == 'true' else ''}>Yes</label><label><input type="radio" name="high_demand_rate" value="false"{' checked' if high_demand != 'true' else ''}>No</label></span></label>
        <details><summary>Advanced model inputs</summary>
          {number_input('sentiment_intensity', params, 'Sentiment intensity', '0', '1', '0.01')}
          {number_input('upgrade_opportunity_cost', params, 'Upgrade opportunity cost', '0', '10000')}
          {number_input('rate_context_confidence', params, 'Rate context confidence', '0', '1', '0.01')}
        </details>
      </fieldset>
      <button type="submit">Generate recommendation</button>
    </form>
    <div>{recommendation_html}</div>
  </main>
</body>
</html>"""


class ManagerHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        params = params_from_query(parsed.query)
        if parsed.path == "/healthz":
            self._send(200, "application/json; charset=utf-8", b'{"status":"ok"}')
            return
        if parsed.path == "/recommend.json":
            try:
                scenario, recommendation = scenario_to_recommendation(params)
            except ScenarioValidationError as exc:
                body = json.dumps({"error": "invalid_scenario", "fields": exc.errors}, indent=2).encode("utf-8")
                self._send(422, "application/json; charset=utf-8", body)
                return
            body = json.dumps(
                {
                    "inputs": scenario.__dict__,
                    "recommendation": asdict(recommendation),
                },
                indent=2,
                sort_keys=True,
            ).encode("utf-8")
            self._send(200, "application/json; charset=utf-8", body)
            return
        if parsed.path not in {"/", ""}:
            self._send(404, "text/plain; charset=utf-8", b"Not found")
            return
        try:
            body = render_page(params).encode("utf-8")
        except ScenarioValidationError as exc:
            body = render_page(params, exc.errors).encode("utf-8")
        self._send(200, "text/html; charset=utf-8", body)

    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local manager-facing recovery recommendation desk.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = HTTPServer((args.host, args.port), ManagerHandler)
    print(f"Manager demo running at http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped manager demo.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
