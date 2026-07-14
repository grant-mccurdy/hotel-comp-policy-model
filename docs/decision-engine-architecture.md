# Comp Decision Engine Architecture

This is a supporting technical appendix. The stakeholder brief and manager recommendation workflow are the primary deliverables; infrastructure choices documented here are implementation evidence, not the business conclusion.

## Business Contract

The engine answers one operational question:

> Which available recovery gesture best meets the hotel's obligation to the guest while making cost, constraints, and reasoning visible?

The current runtime is a synthetic demonstration of a proposed recommendation contract. It is not an empirically optimized property policy.

## Decision Sequence

1. Validate a bounded scenario contract.
2. Calculate a service-recovery floor from severity, hotel responsibility, disruption, timing, and reputation risk.
3. Add relationship-based generosity without lowering that floor for any guest.
4. Remove unavailable, operationally infeasible, or tier-inadequate gestures.
5. Rank the remaining gestures under the versioned prototype rule.
6. Return one recommendation, two alternatives, cost range, reasons, stability, timing, and approval path.
7. During future shadow evaluation, record the manager's decision, override, delivered gesture, actual cost, and outcome.

Repeat-comp patterns trigger review. They do not reduce the service-recovery floor.

## Runtime Boundary

`make runtime-bundle` converts the offline comparison result into a versioned runtime artifact:

```text
synthetic source systems + public context
    -> recovery-case mart
    -> candidate policy comparison
    -> paired bootstrap + shared assumption stress
    -> selected shadow-evaluation candidate
    -> checksummed runtime policy bundle
    -> Cloudflare Python Worker
```

The Worker reads the generated bundle, not analysis CSVs. The canonical JSON bundle and generated Python module must have the same checksum and content. The checksum covers decision semantics but excludes the volatile source-build timestamp, so identical policy behavior retains the same runtime identity across reproducible rebuilds.

## Public API

### `POST /v1/intake/parse`

Accepts a synthetic incident narrative of at most 1,000 characters. Workers AI suggests a bounded subset of incident fields. The source text is explicitly fenced as untrusted, model output is schema-validated, uncertain fields remain unresolved, and all suggestions require manager confirmation. Raw narrative text is not retained.

### `POST /v1/recommend`

Accepts a confirmed synthetic scenario in this envelope:

```json
{
  "scenario_mode": "public_synthetic_demo",
  "scenario": {
    "guest_tier": "returning_guest",
    "failure_category": "room_readiness_delay",
    "severity": 4
  }
}
```

For browser compatibility, `scenario_mode` may instead be included inside `scenario`; both forms are enforced as synthetic-only. The response returns:

- versioned model and policy identifiers;
- recovery-floor and relationship-adjustment components;
- recommended gesture, value, cost range, timing, and note template;
- two feasible alternatives;
- plain-language reasoning;
- input-sensitivity stability and its limited interpretation;
- approval path and required confirmations;
- evidence boundary and unavailable inputs.

### `GET /healthz`

Returns runtime bundle identity, evidence class, and the public demo's disabled-persistence status.

## Public And Shadow Environments

The public environment is synthetic-only and stateless. It has no D1 binding, rejects obvious contact and reservation identifiers in narrative input, and does not expose any endpoint for recording decisions.

The future shadow environment is separate and protected by Cloudflare Access. Its append-only D1 contract is defined in `cloudflare/migrations/0001_shadow_log.sql`, but no live database or authenticated route is created by the public build. Operational events would later be exported into the S3-to-Snowflake analytical path for calibration and monitoring.

## Analytical Model Selection

Snowflake remains the offline analytical environment. With actual property data, compare manager judgment, explicit rules, an interpretable statistical model, and a nonlinear benchmark on the same out-of-time cases.

Required evidence includes:

- calibration and temporal holdout performance for recovery, review, repeat-stay, cost, and feasibility outcomes;
- paired uncertainty for policy-level differences;
- adequacy, escalation, availability, and data-quality guardrails;
- segment diagnostics with small-cell suppression;
- override rate and reason quality;
- actual marginal cost and resolution time;
- checks for treatment overlap and historical selection bias.

Historical decisions alone do not identify the causal effect of gestures that managers chose selectively. Shadow observation and, when justified, a powered controlled pilot remain necessary.

## Retrieval Boundary

RAG is intentionally deferred until approved policies, SOPs, and property guidance are available. Retrieval may later cite the rules or operating guidance relevant to a recommendation. It must not calculate the score, infer live availability, or replace structured hotel-system inputs.

## Local Worker Validation

```bash
make runtime-bundle
cd cloudflare
uv run pywrangler dev
```

No deployment, D1 creation, or live Cloudflare mutation is part of the local validation command.
