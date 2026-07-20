DECISION_DESK_HTML = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Run a synthetic hotel service-recovery scenario and inspect an explainable recommendation, alternatives, cost assumptions, and review path.">
  <title>Hotel Comp Decision Desk</title>
  <style>
:root {
  --ink: #18221f;
  --muted: #5c6763;
  --line: #d8dedb;
  --paper: #ffffff;
  --wash: #f3f6f4;
  --green: #12685b;
  --green-dark: #0d5147;
  --coral: #b84f3f;
  --amber: #8b5d14;
  --focus: #2c78b8;
}

* { box-sizing: border-box; }

html { scroll-behavior: smooth; }

body {
  margin: 0;
  color: var(--ink);
  background: var(--wash);
  font: 15px/1.5 Inter, ui-sans-serif, system-ui, sans-serif;
  letter-spacing: 0;
}

a { color: var(--green-dark); }

.skip-link {
  position: fixed;
  z-index: 100;
  top: 8px;
  left: 8px;
  padding: 8px 12px;
  background: var(--ink);
  color: #fff;
  transform: translateY(-160%);
}

.skip-link:focus { transform: translateY(0); }

header { background: var(--paper); border-bottom: 1px solid var(--line); }

.shell { width: min(1180px, calc(100% - 32px)); margin: 0 auto; }

.masthead {
  min-height: 78px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

h1 { margin: 0; font-size: 1.55rem; line-height: 1.15; letter-spacing: 0; }
h2 { margin: 0; font-size: 1.15rem; line-height: 1.25; letter-spacing: 0; }

.eyebrow {
  margin: 0 0 4px;
  color: var(--green);
  font-size: .76rem;
  font-weight: 750;
  text-transform: uppercase;
}

.context-links { display: flex; flex-wrap: wrap; gap: 16px; font-size: .82rem; font-weight: 700; }
.context-links a { text-decoration-thickness: 1px; text-underline-offset: 3px; }

main { padding: 24px 0 52px; }

.demo-intro {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 18px 20px;
  border: 1px solid #b9d3cb;
  background: #e9f2ef;
}

.demo-intro p:last-child { max-width: 760px; margin: 6px 0 0; color: #36413d; }

.boundary { margin: 12px 0 20px; color: var(--muted); font-size: .82rem; }

.workspace {
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(340px, .92fr);
  gap: 24px;
  align-items: start;
}

.panel { background: var(--paper); border: 1px solid var(--line); border-radius: 6px; }
.panel-head { padding: 16px 20px; border-bottom: 1px solid var(--line); }
.panel-head h2, .result h2 { font-size: 1.05rem; }
.panel-body { padding: 20px; }

fieldset { min-width: 0; margin: 0 0 22px; padding: 0; border: 0; }

legend {
  width: 100%;
  margin-bottom: 12px;
  padding-bottom: 7px;
  border-bottom: 1px solid var(--line);
  font-size: .8rem;
  font-weight: 750;
  text-transform: uppercase;
}

.grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }

label { display: grid; gap: 6px; min-width: 0; color: var(--muted); font-size: .82rem; font-weight: 650; }

.field-term {
  position: relative;
  width: max-content;
  max-width: 100%;
  border-bottom: 1px dotted #6e7b76;
  color: var(--ink);
  cursor: help;
}

.field-term::after {
  position: absolute;
  z-index: 10;
  bottom: calc(100% + 8px);
  left: 0;
  width: min(310px, calc(100vw - 44px));
  padding: 9px 11px;
  border: 1px solid #9eaaa5;
  border-radius: 4px;
  background: #202825;
  color: #fff;
  box-shadow: 0 7px 18px rgb(24 34 31 / 18%);
  content: attr(data-help);
  font-size: .76rem;
  font-weight: 500;
  line-height: 1.45;
  opacity: 0;
  pointer-events: none;
  transform: translateY(4px);
  transition: opacity 120ms ease, transform 120ms ease;
  visibility: hidden;
}

.field-term:hover::after, .field-term:focus::after { opacity: 1; transform: translateY(0); visibility: visible; }
.field-term:focus-visible { border-radius: 2px; outline: 3px solid color-mix(in srgb, var(--focus) 35%, transparent); outline-offset: 2px; }

input, select, textarea {
  width: 100%;
  min-width: 0;
  border: 1px solid #b9c2be;
  border-radius: 4px;
  background: #fff;
  color: var(--ink);
  font: inherit;
  letter-spacing: 0;
}

input, select { min-height: 42px; padding: 8px 10px; }
textarea { min-height: 88px; padding: 10px; resize: vertical; }
input:focus, select:focus, textarea:focus, button:focus-visible, a:focus-visible { outline: 3px solid color-mix(in srgb, var(--focus) 35%, transparent); outline-offset: 1px; }

.narrative { display: grid; grid-template-columns: 1fr auto; gap: 10px; align-items: end; }

button {
  min-height: 42px;
  padding: 9px 15px;
  border: 1px solid transparent;
  border-radius: 4px;
  font: inherit;
  font-weight: 750;
  cursor: pointer;
}

button.primary { width: 100%; color: #fff; background: var(--green); }
button.primary:hover { background: var(--green-dark); }
button.secondary { color: var(--green-dark); background: #fff; border-color: #82ad9f; white-space: nowrap; }
button.secondary:hover { border-color: var(--green); }
button:disabled { opacity: .55; cursor: not-allowed; }

.sample-button { min-width: 180px; }
.checks { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px 12px; }
.check { display: flex; align-items: flex-start; gap: 8px; color: var(--ink); font-size: .84rem; font-weight: 500; }
.check input { width: 17px; min-height: 17px; margin: 2px 0 0; }

.advanced-inputs { margin: 0 0 20px; border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); }
.advanced-inputs summary { display: grid; gap: 2px; padding: 12px 0; color: var(--green-dark); font-weight: 750; cursor: pointer; }
.advanced-inputs summary small { color: var(--muted); font-size: .76rem; font-weight: 500; }
.advanced-body { padding-top: 8px; }

.confirm { margin: 0 0 14px; padding: 12px; background: #f7f8f7; border-left: 3px solid var(--amber); }
.status { min-height: 22px; margin: 8px 0 0; color: var(--muted); font-size: .8rem; }
.status.error { color: var(--coral); }

.result { position: sticky; top: 18px; min-height: 430px; }
.empty { display: grid; gap: 8px; padding: 48px 24px; color: var(--muted); text-align: center; }
.empty strong { color: var(--ink); }
.recommendation { padding: 20px; }
.decision-label { margin: 0 0 4px; color: var(--muted); font-size: .75rem; font-weight: 750; text-transform: uppercase; }
.gesture { margin: 0; font-size: 1.8rem; line-height: 1.15; letter-spacing: 0; }
.value { color: var(--green); }

.meta { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); margin: 18px 0; border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); }
.metric { min-width: 0; padding: 12px 10px; border-right: 1px solid var(--line); }
.metric:last-child { border-right: 0; }
.metric span { display: block; color: var(--muted); font-size: .72rem; text-transform: uppercase; }
.metric strong { overflow-wrap: anywhere; font-size: .92rem; }
.reason-list, .confirm-list { margin: 8px 0 18px; padding-left: 20px; }
.reason-list li, .confirm-list li { margin-bottom: 6px; }
.note { margin: 14px 0; padding: 12px 14px; border-left: 3px solid var(--green); background: #f2f7f5; }
.note p { margin: 4px 0 0; color: #36413d; }

table { width: 100%; border-collapse: collapse; font-size: .82rem; }
th, td { padding: 8px 6px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }
th { color: var(--muted); font-size: .7rem; text-transform: uppercase; }
.badge { display: inline-block; padding: 2px 7px; border-radius: 4px; background: #e9f2ef; color: var(--green-dark); font-size: .74rem; font-weight: 750; }
.evidence { margin: 18px 0 0; padding-top: 12px; border-top: 1px solid var(--line); color: var(--muted); font-size: .76rem; }

@media (max-width: 880px) {
  .masthead { align-items: flex-start; flex-direction: column; padding: 16px 0; gap: 10px; }
  .demo-intro { align-items: flex-start; }
  .workspace { grid-template-columns: 1fr; }
  .result { position: static; min-height: 260px; }
}

@media (max-width: 560px) {
  .shell { width: min(100% - 20px, 1180px); }
  .context-links { gap: 12px; }
  main { padding-top: 14px; }
  .demo-intro { align-items: stretch; flex-direction: column; gap: 14px; padding: 15px; }
  .sample-button { width: 100%; }
  .grid, .checks, .narrative { grid-template-columns: 1fr; }
  .panel-body { padding: 16px; }
  .meta { grid-template-columns: 1fr 1fr; }
  .metric:nth-child(2) { border-right: 0; }
  .metric:nth-child(-n + 2) { border-bottom: 1px solid var(--line); }
  .gesture { font-size: 1.5rem; }
}

@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
  *, *::before, *::after { transition-duration: .01ms !important; }
}
  </style>
</head>
<body>
  <a class="skip-link" href="#main">Skip to decision workspace</a>
  <header>
    <div class="shell masthead">
      <div>
        <p class="eyebrow">Synthetic service-recovery prototype</p>
        <h1>Hotel Comp Decision Desk</h1>
      </div>
      <nav class="context-links" aria-label="Project context">
        <a href="https://grant-mccurdy.github.io/projects/hotel-comp-policy-model.html">Project brief</a>
        <a href="https://grant-mccurdy.github.io/projects/hotel-comp-policy-model/">Decision report</a>
        <a href="https://github.com/grant-mccurdy/hotel-comp-policy-model">Source</a>
      </nav>
    </div>
  </header>

  <main id="main" class="shell">
    <div class="demo-intro">
      <div>
        <p class="eyebrow">Start with a complete example</p>
        <h2>See the decision contract first</h2>
        <p>Run the built-in synthetic room-readiness scenario, then change the incident fields to inspect how the recommendation responds.</p>
      </div>
      <button id="sample-button" class="secondary sample-button" type="button">Run sample scenario</button>
    </div>
    <p class="boundary">Public demonstration only. Use synthetic scenarios; do not enter names, contact details, reservation identifiers, or actual guest records.</p>

    <div class="workspace">
      <section class="panel" aria-labelledby="scenario-title">
        <div class="panel-head"><h2 id="scenario-title">Recovery scenario</h2></div>
        <form id="scenario-form" class="panel-body">
          <fieldset>
            <legend>Incident</legend>
            <div class="narrative">
              <label>Synthetic incident summary
                <textarea id="incident_summary" maxlength="1000" placeholder="A returning guest waited 95 minutes for the room after check-in and is visibly frustrated..."></textarea>
              </label>
              <button id="parse-button" class="secondary" type="button">Suggest fields</button>
            </div>
            <p id="parse-status" class="status" role="status"></p>
            <div class="grid">
              <label>Issue
                <select name="failure_category" required>
                  <option value="room_readiness_delay">Room readiness delay</option>
                  <option value="room_assignment_expectation_gap">Room expectation gap</option>
                  <option value="housekeeping_miss">Housekeeping miss</option>
                  <option value="maintenance_issue">Maintenance issue</option>
                  <option value="noise_disruption">Noise disruption</option>
                  <option value="billing_or_fee_dispute">Billing or fee dispute</option>
                  <option value="f_and_b_service_lapse">Food and beverage lapse</option>
                  <option value="rooftop_pool_access_issue">Rooftop or pool access</option>
                  <option value="spa_wellness_service_issue">Spa or wellness issue</option>
                  <option value="valet_or_parking_delay">Valet or parking delay</option>
                </select>
              </label>
              <label><span class="field-term" tabindex="0" aria-label="Severity: How much the incident disrupted the promised stay experience. Rate the failure itself, not guest emotion, guest value, or hotel responsibility." data-help="How much the incident disrupted the promised stay experience. Rate the failure itself, not guest emotion, guest value, or hotel responsibility.">Severity</span>
                <select name="severity" required>
                  <option value="2">2 - Noticeable</option><option value="3">3 - Material</option>
                  <option value="4" selected>4 - Serious</option><option value="5">5 - Critical</option>
                </select>
              </label>
              <label>Hotel responsibility
                <select name="hotel_responsibility" required>
                  <option value="0.35">Limited</option><option value="0.65">Shared</option>
                  <option value="0.90" selected>High</option><option value="1">Full</option>
                </select>
              </label>
              <label>Resolution delay
                <select name="resolution_delay_minutes" required>
                  <option value="25">Under 30 minutes</option><option value="60">30-60 minutes</option>
                  <option value="95" selected>60-120 minutes</option><option value="240">Over two hours</option>
                </select>
              </label>
              <label>Guest sentiment
                <select name="sentiment_intensity" required>
                  <option value="0.30">Calm</option><option value="0.55">Concerned</option>
                  <option value="0.76" selected>Frustrated</option><option value="0.92">Highly escalated</option>
                </select>
              </label>
            </div>
            <input type="hidden" name="failure_type" value="outcome">
            <input type="hidden" name="reported_in_stay" value="true">
          </fieldset>

          <details class="advanced-inputs">
            <summary><span>Scenario assumptions</span><small>Guest context, recovery options, review risk, and simulated operations</small></summary>
            <div class="advanced-body">
              <fieldset>
                <legend>Guest and stay context</legend>
                <div class="grid">
                  <label>Guest relationship
                    <select name="guest_tier" required>
                      <option value="new_guest">New guest</option><option value="returning_guest" selected>Returning guest</option>
                      <option value="loyalty_guest">Loyalty guest</option><option value="vip_guest">VIP guest</option>
                      <option value="event_or_suite_guest">Event or suite guest</option>
                    </select>
                  </label>
                  <label>Traveler context
                    <select name="traveler_segment" required>
                      <option value="coastal_weekend" selected>Coastal weekend</option><option value="wellness_getaway">Wellness getaway</option>
                      <option value="business_traveler">Business traveler</option><option value="design_leisure">Design leisure</option>
                      <option value="event_or_suite_guest">Event or suite</option><option value="local_staycation">Local staycation</option>
                    </select>
                  </label>
                  <label>Stay value ($)<input name="stay_value" type="number" min="0" max="100000" value="1800" required></label>
                  <label>Nightly rate ($)<input name="nightly_rate" type="number" min="0" max="25000" value="600" required></label>
                  <label>Estimated relationship value ($)<input name="estimated_lifetime_value" type="number" min="0" max="1000000" value="7200" required></label>
                  <label><span class="field-term" tabindex="0" aria-label="Repeat-comp review signal: Verified prior recovery history that may require manager review. It never reduces what the current failure warrants and is not an abuse label." data-help="Verified prior recovery history that may require manager review. It never reduces what the current failure warrants and is not an abuse label.">Repeat-comp review signal</span>
                    <select name="repeat_comp_review_risk" required><option value="0.04" selected>None</option><option value="0.35">Watch</option><option value="0.75">Review</option></select>
                  </label>
                  <label><span class="field-term" tabindex="0" aria-label="Review risk: Observed likelihood that an unresolved incident becomes a negative public review or reputation issue. Do not infer this from guest status or demographics." data-help="Observed likelihood that an unresolved incident becomes a negative public review or reputation issue. Do not infer this from guest status or demographics.">Review risk</span>
                    <select name="review_risk" required>
                      <option value="0.30">Low</option><option value="0.55">Moderate</option>
                      <option value="0.80" selected>High</option><option value="0.94">Very high</option>
                    </select>
                  </label>
                </div>
              </fieldset>

              <fieldset>
                <legend>Available recovery options</legend>
                <div class="checks">
                  <label class="check"><input type="checkbox" name="available_comp_codes" value="amenity_gesture" checked>In-room amenity</label>
                  <label class="check"><input type="checkbox" name="available_comp_codes" value="late_checkout" checked>Late checkout</label>
                  <label class="check"><input type="checkbox" name="available_comp_codes" value="parking_fee_waiver" checked>Fee waiver</label>
                  <label class="check"><input type="checkbox" name="available_comp_codes" value="lobby_lounge_credit" checked>Palma credit</label>
                  <label class="check"><input type="checkbox" name="available_comp_codes" value="rooftop_f_and_b_credit" checked>Calabra or Palma credit</label>
                  <label class="check"><input type="checkbox" name="available_comp_codes" value="spa_wellness_credit" checked>Spa or wellness credit</label>
                  <label class="check"><input type="checkbox" name="available_comp_codes" value="room_upgrade" checked>Room upgrade</label>
                  <label class="check"><input type="checkbox" name="available_comp_codes" value="partial_room_refund" checked>Partial room refund</label>
                  <label class="check"><input type="checkbox" name="available_comp_codes" value="future_stay_credit" checked>Future-stay credit</label>
                </div>
              </fieldset>

              <fieldset>
                <legend>Simulated operating context</legend>
                <div class="grid">
                  <label>Occupancy pressure<select name="occupancy_pressure"><option value="0.35">Flexible</option><option value="0.65">Moderate</option><option value="0.72" selected>Constrained</option><option value="0.92">Peak</option></select></label>
                  <label>Public rate pressure<select name="public_rate_pressure"><option value="0.35">Low</option><option value="0.50" selected>Typical</option><option value="0.75">High</option><option value="0.90">Peak</option></select></label>
                </div>
              </fieldset>
            </div>
          </details>

          <input type="hidden" name="scenario_mode" value="public_synthetic_demo">
          <input type="hidden" name="availability_confirmed" value="true">
          <input type="hidden" name="property_context_confidence" value="0.88">
          <input type="hidden" name="rooftop_f_and_b_fit_modifier" value="1.22">
          <input type="hidden" name="spa_wellness_fit_modifier" value="1.18">
          <input type="hidden" name="lobby_lounge_fit_modifier" value="1.12">
          <input type="hidden" name="parking_fee_fit_modifier" value="1.04">
          <input type="hidden" name="late_checkout_fit_modifier" value="1.04">
          <input type="hidden" name="room_upgrade_fit_modifier" value="1.08">
          <div class="confirm"><label class="check"><input id="confirm-inputs" type="checkbox" required>I confirm this is a synthetic scenario and the structured fields are correct.</label></div>
          <button id="recommend-button" class="primary" type="submit">Generate recommendation</button>
          <p id="recommend-status" class="status" role="status"></p>
        </form>
      </section>

      <aside id="result" class="panel result" aria-live="polite">
        <div class="panel-head"><h2>Decision support</h2></div>
        <div class="empty"><strong>Run the sample to see the output contract.</strong><span>Recommendations include the selected gesture, alternatives, assumptions, and approval path.</span></div>
      </aside>
    </div>
  </main>
  <script>
const form = document.getElementById('scenario-form');
const parseButton = document.getElementById('parse-button');
const sampleButton = document.getElementById('sample-button');
const parseStatus = document.getElementById('parse-status');
const recommendStatus = document.getElementById('recommend-status');
const resultPanel = document.getElementById('result');
const recommendButton = document.getElementById('recommend-button');

const escapeHtml = (value) => String(value ?? '').replace(/[&<>'"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[char]);
const money = (value) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(Number(value || 0));
const label = (value) => String(value || '').replaceAll('_', ' ').replaceAll('f and b', 'F&B');

function scenarioPayload() {
  const data = new FormData(form);
  const payload = {};
  for (const [key, value] of data.entries()) {
    if (key === 'available_comp_codes') continue;
    payload[key] = value;
  }
  payload.available_comp_codes = ['manager_note', ...data.getAll('available_comp_codes')];
  return payload;
}

function applySuggestedValue(control, value) {
  if (control.tagName !== 'SELECT') {
    control.value = String(value);
    return;
  }
  const options = Array.from(control.options);
  const exact = options.find((option) => option.value === String(value));
  if (exact) {
    control.value = exact.value;
    return;
  }
  const numericValue = Number(value);
  const numericOptions = options.filter((option) => Number.isFinite(Number(option.value)));
  if (!Number.isFinite(numericValue) || !numericOptions.length) return;
  const nearest = numericOptions.reduce((best, option) =>
    Math.abs(Number(option.value) - numericValue) < Math.abs(Number(best.value) - numericValue) ? option : best
  );
  control.value = nearest.value;
}

function renderDecision(body) {
  const rec = body.recommendation;
  const confidence = body.confidence;
  const experiential = ['late_checkout', 'room_upgrade', 'manager_note'].includes(rec.comp_code);
  const decisionHeading = experiential
    ? escapeHtml(rec.comp_label)
    : `<span class="value">${money(rec.guest_facing_value)}</span> ${escapeHtml(rec.comp_label)}`;
  const alternatives = body.alternatives
    .map((item) => `<tr><td>${escapeHtml(item.comp_label)}</td><td>${money(item.guest_facing_value)}</td><td>${money(item.internal_cost_low)}-${money(item.internal_cost_high)}</td></tr>`)
    .join('');
  const reasons = body.reasoning.plain_language.map((item) => `<li>${escapeHtml(item)}</li>`).join('');
  const confirmations = body.required_confirmations.map((item) => `<li>${escapeHtml(item)}</li>`).join('');
  resultPanel.innerHTML = `
    <div class="panel-head"><h2>Decision support</h2></div>
    <div class="recommendation">
      <p class="decision-label">Recommended recovery</p>
      <h3 class="gesture">${decisionHeading}</h3>
      <p>${escapeHtml(rec.delivery_timing)}</p>
      <div class="meta">
        <div class="metric"><span>Guest value</span><strong>${money(rec.guest_facing_value)}</strong></div>
        <div class="metric"><span>Estimated cost</span><strong>${money(rec.internal_cost_low)}-${money(rec.internal_cost_high)}</strong></div>
        <div class="metric"><span>Stability</span><strong>${Math.round(confidence.input_sensitivity_stability * 100)}%</strong></div>
        <div class="metric"><span>Approval</span><strong>${escapeHtml(body.approval.approval_path)}</strong></div>
      </div>
      <h4>Why this gesture</h4><ul class="reason-list">${reasons}</ul>
      <div class="note"><strong>Manager note</strong><p>${escapeHtml(rec.hospitality_note_template)}</p></div>
      <h4>Closest feasible alternatives</h4>
      <table><thead><tr><th>Gesture</th><th>Guest value</th><th>Assumed cost</th></tr></thead><tbody>${alternatives}</tbody></table>
      <h4>Confirm before delivery</h4><ul class="confirm-list">${confirmations}</ul>
      <p><span class="badge">${escapeHtml(confidence.level)} stability confidence</span></p>
      <p class="evidence">${escapeHtml(confidence.meaning)} All costs and operating outcomes are synthetic assumptions; public property context informs guest-facing options only.</p>
    </div>`;
}

async function requestRecommendation({ scrollToResult = true } = {}) {
  if (!form.reportValidity()) return;
  recommendStatus.className = 'status';
  recommendStatus.textContent = 'Comparing eligible recovery gestures...';
  recommendButton.disabled = true;
  sampleButton.disabled = true;
  try {
    const response = await fetch('/v1/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario: scenarioPayload() }),
    });
    const body = await response.json();
    if (!response.ok) throw new Error(body.message || body.error || 'Recommendation failed.');
    renderDecision(body);
    recommendStatus.textContent = 'Recommendation generated.';
    if (scrollToResult) resultPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (error) {
    recommendStatus.className = 'status error';
    recommendStatus.textContent = error.message;
  } finally {
    recommendButton.disabled = false;
    sampleButton.disabled = false;
  }
}

sampleButton.addEventListener('click', async () => {
  form.reset();
  document.getElementById('incident_summary').value = 'A returning guest waited 95 minutes for the room after check-in and is visibly frustrated.';
  document.getElementById('confirm-inputs').checked = true;
  parseStatus.textContent = '';
  await requestRecommendation();
});

parseButton.addEventListener('click', async () => {
  parseStatus.className = 'status';
  parseStatus.textContent = 'Parsing synthetic incident...';
  parseButton.disabled = true;
  try {
    const response = await fetch('/v1/intake/parse', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ incident_summary: document.getElementById('incident_summary').value, scenario_mode: 'public_synthetic_demo' }),
    });
    const body = await response.json();
    if (!response.ok) throw new Error(body.message || body.error || 'Narrative parsing failed.');
    for (const [field, value] of Object.entries(body.suggested_fields)) {
      if (value === null || value === undefined) continue;
      const control = form.querySelector(`[name="${CSS.escape(field)}"]`);
      if (control) applySuggestedValue(control, value);
    }
    document.getElementById('confirm-inputs').checked = false;
    const fallbackUsed = body.parser_mode === 'deterministic_fallback';
    const prefix = fallbackUsed
      ? 'AI extraction was temporarily unavailable; conservative text matches were applied.'
      : 'Suggested fields applied.';
    parseStatus.textContent = body.unresolved_fields.length
      ? `${prefix} Review all fields; unresolved: ${body.unresolved_fields.map(label).join(', ')}.`
      : `${prefix} Review and confirm them before scoring.`;
  } catch (error) {
    parseStatus.className = 'status error';
    parseStatus.textContent = error.message;
  } finally {
    parseButton.disabled = false;
  }
});

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  await requestRecommendation();
});
  </script>
</body>
</html>
'''
