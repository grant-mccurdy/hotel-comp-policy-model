# Project Status

## Current State

The project is a working synthetic service-recovery decision system for a Santa Monica luxury lifestyle hotel context. The canonical `index.html` presents the operating recommendation, worked decisions, and pilot proposal in stakeholder language. Supporting layers reconcile messy source-shaped data, score a versioned policy, expose alternatives and counterfactuals, and test recommendation stability.

## Implemented

- Shared input validation across batch scoring, CLI, HTML manager desk, and JSON endpoint.
- Generated first-click stakeholder webpage with four policy-engine scenarios and a bounded pilot proposal.
- Versioned policy configuration with parameter provenance and public anchor IDs.
- Guest-facing value plus low/mid/high internal-cost assumptions.
- Two ranked alternatives for every recommendation.
- Counterfactual explanations limited to signals that change the selected gesture.
- ±20% parameter perturbation and recommendation-stability reporting.
- Manager review for high tier, high value, repeat-comp pattern, or low-confidence data.
- Eleven dated official Santa Monica Proper public anchors.
- Synthetic PMS, CRM, service, comp, POS, review/survey, and daily-ops source systems.
- Recovery-case mart with identity-match confidence and data-quality flags.
- DuckDB local warehouse and Snowflake warehouse definitions.
- Optional S3 landing layer and Snowflake external-stage loader.
- Verified S3 external-stage `COPY INTO` run covering 18 tables, followed by Snowflake row-count and view validation.
- Unit, randomized, pipeline, source-quality, model-behavior, and public-release checks.
- Verified clean-checkout GitHub Actions local-validation workflow.
- Container-ready manager decision desk with health endpoint.
- Verified local container build and `200` health response.
- Reviewed the stakeholder report and manager desk at desktop and true `390x844` mobile viewports with no page-level horizontal overflow.

## Evidence Boundary

- Operating records and historical comp actions are synthetic.
- Public property facts and published guest-facing values are observed context.
- Public rate, review-risk, and local-demand layers are sample-seed stress tests unless a manifest explicitly records observed acquisition.
- Internal cost, margin, inventory, occupancy, approval policy, satisfaction recovery, and repeat-stay effects are unavailable.
- Simulated under-recovery and over-comping counts demonstrate the audit workflow; they are not business findings.

## Remaining Before External Release

- Make the repository publicly visible only after explicit publication approval.
- Add a hosted stakeholder-report URL only after explicit publication approval.
