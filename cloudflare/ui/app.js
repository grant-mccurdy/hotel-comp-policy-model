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
