# Project Status

## Current State

The project is a working synthetic comp-policy comparison and manager decision prototype for a Santa Monica luxury lifestyle hotel context. The canonical `index.html` now leads with a concrete executive recommendation: approve a four-week, minimum-50-case shadow validation of **Guardrailed recovery**, the lowest modeled-cost candidate that clears the declared simulation guardrails.

The recommendation is for invisible shadow validation followed, conditionally, by a controlled manager-assisted phase. It is not manager-facing deployment or permanent policy adoption. The sanitized static bundle is published at `https://grant-mccurdy.github.io/projects/hotel-comp-policy-model/` and was inspected at desktop and mobile widths on 2026-07-13.

## Implemented

- Messy synthetic PMS, CRM, service, comp, POS, survey, and daily-operations sources.
- Recovery-case mart with identity-match confidence and data-quality holds.
- One shared recovery-need and tier reference across five candidate policies.
- 2,150 case-policy evaluations from 430 cases and five policies.
- Synthetic baseline replay that treats missing comp records as unknown.
- Declared guest-protection, high-risk, feasibility, data-hold, and escalation guardrails.
- 10,000-draw paired case bootstrap with case-level policy alignment.
- 5,000 shared-world assumption-stress draws with coherent recovery-weight, fit, occupancy, and gesture-cost realizations across policies.
- Deterministic shadow-candidate selection based on guardrails first, modeled cost second.
- Segment diagnostics with minimum-cell suppression.
- Executive decision summary, uncertainty report, case-policy mart, and machine-readable contracts.
- First-click stakeholder page with five-policy comparison, explicit tradeoff, worked decisions, and shadow-validation design.
- Manager desk and JSON endpoint using the generated shadow-validation candidate.
- DuckDB fallback plus a verified S3-to-Snowflake path with separate source landing/model-output zones, typed MARTS, decision views, and report-source parity.
- Sanitized engineering evidence showing 22 loaded tables, 12 queryable views, and 12 decision-semantic checks.
- Unit, randomized, pipeline, source-quality, model-behavior, and public-release checks.

## Current Generated Result

- Shadow-validation candidate: `cost_guardrail` / Guardrailed recovery.
- Assumption-stress guardrail pass rate: `99.6%` across 5,000 coherent shared draws.
- Selection frequency: `99.6%` under the declared shared-world stress design.
- Material downside: greater direct-refund face-value exposure than Intelligent Generosity.
- Evidence boundary: constrained optimization under declared assumptions, not hotel findings, causal effects, projected savings, or independent evidence of improved guest outcomes.

## Required Before Controlled Use

- Actual comp actions, approvals, overrides, and policy versions.
- Marginal-cost ranges by gesture and current operating availability.
- Post-recovery satisfaction, review, cancellation, and repeat-stay outcomes.
- Jointly reviewed severity, responsibility, adequacy, and escalation definitions.
- Shadow-mode reconciliation and pre-registered controlled-phase endpoints.

## Remaining Deployment Scope

- Regenerate and visually inspect the stakeholder report, engineering appendix, and manager desk at desktop and mobile sizes.
- Republish the sanitized GitHub Pages bundle after source review and explicit commit/push approval.
