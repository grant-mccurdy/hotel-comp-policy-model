# Project Status

## North Star

This project is a focused response to one luxury-hotel operating problem:

> How can managers choose the right recovery gesture for the guest and situation while making cost, constraints, and reasoning visible?

The intended work sample has two primary artifacts:

1. A concise stakeholder brief explaining the proposed decision product and how it would be evaluated with actual property data.
2. A runnable synthetic decision desk showing what a manager-facing recommendation could look like.

Everything else is supporting evidence.

## Primary Deliverable State

- The HTML and PDF brief define the business problem, proposed product, illustrative recommendation, real-data model comparison, and focused first step.
- The primary report does not present a synthetic policy ranking as a Proper Hotels recommendation.
- The decision desk returns one gesture, guest-facing value, assumed cost range, reasons, alternatives, timing, and approval path.
- The manager confirms availability and remains responsible for accepting or overriding the recommendation.

## Supporting Evidence

- Messy synthetic PMS, CRM, service, comp, POS, survey, and operations sources.
- Recovery-case mart with source-match confidence and data-quality holds.
- Statistical policy comparison, paired resampling, assumption stress, and segment diagnostics.
- Service-recovery floor independent of guest relationship value.
- Explicit filtering of unavailable gestures and review routing for repeat-comp patterns.
- Versioned runtime bundle, API contracts, automated tests, and public-safety checks.
- DuckDB plus S3-to-Snowflake lineage and validation evidence.
- Local Cloudflare Worker implementation for the synthetic decision desk.

These components demonstrate execution quality. They are not separate stakeholder conclusions.

## Scope Freeze

Until the stakeholder brief and decision product are accepted, do not add:

- new infrastructure platforms;
- live hotel integrations;
- persistent operational logging;
- retrieval or chat features;
- additional policy families or synthetic outcome claims;
- generic dashboards unrelated to the manager recommendation workflow.

## Required For Property Calibration

- Actual comp actions, approvals, overrides, policy versions, and delivery timing.
- Marginal cost and operational availability by gesture.
- Post-recovery satisfaction, review, cancellation, repeat-stay, and resolution outcomes.
- Joint definitions for severity, responsibility, adequate recovery, and escalation.
- Temporal validation and assessment of historical action-selection bias.
- Shadow observation followed by a powered controlled test only when the workflow is credible.

## Next Decision

Review the stakeholder brief and decision desk as a single work sample. The next development task should address a concrete comprehension or trust issue found in that review, not expand the platform.

The revised worktree has not been committed, pushed, deployed, or republished. Those remain separate approval checkpoints.
