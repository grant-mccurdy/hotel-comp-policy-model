# Snowflake Warehouse Lineage

This is the primary cloud warehouse path for the project workflow.

Snowflake is used for the warehouse load, SQL view layer, validation, and query extracts. DuckDB remains a local fallback for reviewers or environments without Snowflake credentials.

The project supports connector batch inserts and an enterprise ingestion path through an S3 external stage. The status section identifies the most recently evidenced load method.
RAW tables preserve source-shaped text. Curated MARTS use a versioned type contract for numeric, Boolean, and date fields.

## Warehouse Objects

- Database: `HOTEL_COMP_POLICY_MODEL`
- Warehouse: `HOTEL_COMP_WH`
- Schemas: `RAW`, `STAGING`, `MARTS`, `AUDIT`
- Internal stage: `HOTEL_COMP_POLICY_MODEL.RAW.PROJECT_CSV_STAGE`
- Load method: S3 data lake external stage with Snowflake `COPY INTO`

## Source-To-Table Map

| Snowflake table | Local rows | Source purpose |
| --- | ---: | --- |
| `RAW.STG_PMS_RESERVATIONS` | 1600 | Synthetic PMS reservation extract |
| `RAW.STG_GUEST_PROFILES_CRM` | 1725 | Synthetic CRM guest profiles |
| `RAW.STG_SERVICE_TICKETS` | 430 | Synthetic service-ticket system |
| `RAW.STG_COMP_LEDGER` | 281 | Synthetic comp ledger |
| `RAW.STG_POS_OUTLET_CHARGES` | 3194 | Synthetic outlet charges |
| `RAW.STG_REVIEWS_SURVEYS` | 204 | Synthetic review and survey signals |
| `RAW.STG_OPS_DAILY` | 365 | Synthetic daily operational pressure |
| `RAW.STG_RATE_SHOP_SNAPSHOTS` | 2190 | Public quoted-rate sample/API extract |
| `RAW.STG_PROPERTY_CONTEXT` | 5 | Public property and competitive-set context |
| `RAW.STG_PROPER_PUBLIC_VALUE_ANCHORS` | 11 | Observed public Santa Monica Proper value anchors |
| `RAW.STG_REVIEW_RISK_CONTEXT` | 10 | Review-risk theme priors by issue category |
| `RAW.STG_LOCAL_DEMAND_CONTEXT` | 365 | Local event/weather demand-pressure context |
| `MARTS.MART_PUBLIC_PRICING_CONTEXT` | 365 | Daily public pricing context |
| `MARTS.MART_RECOVERY_CASES` | 430 | Case-level recovery decision mart |
| `MARTS.MART_COMP_RECOMMENDATIONS` | 430 | Policy-engine recommendation output |
| `MARTS.MART_COMP_POLICY_AUDIT` | 430 | Comp policy audit output |
| `MARTS.MART_EXTERNAL_CONTEXT_MODEL_IMPACT` | 5 | External-context impact output |
| `MARTS.MART_POLICY_CASE_COMPARISON` | 2150 | Case-by-policy evaluation matrix |
| `MARTS.MART_POLICY_DECISION_SUMMARY` | 5 | Executive policy comparison and shadow-candidate selection |
| `MARTS.MART_POLICY_SEGMENT_DIAGNOSTICS` | 125 | Policy diagnostics by synthetic case segment |
| `MARTS.MART_POLICY_UNCERTAINTY_SUMMARY` | 5 | Probabilistic policy uncertainty output |
| `MARTS.DIM_COMP_CATALOG` | 10 | Comp type catalog |

## Analytics Views

| Snowflake view | Use |
| --- | --- |
| `MARTS.VW_COMP_DECISION_SUMMARY` | Supporting rollup of modeled comp value, cost, stability, and manager review volume |
| `MARTS.VW_COMP_MIX` | Comp-type mix by cases, guest-facing value, and internal cost |
| `MARTS.VW_MANAGER_REVIEW_QUEUE` | Manager review queue combining escalation and low-match-confidence cases |
| `AUDIT.VW_AUDIT_DECISION_SIGNAL` | Audit classes for under-recovery, over-comping, review, and data-quality holds |
| `AUDIT.VW_SOURCE_QUALITY_SNAPSHOT` | Compact source-quality metrics for messy-data review |
| `MARTS.VW_PUBLIC_PRICING_CONTEXT` | Public quoted-rate context for comp opportunity-cost reasoning |
| `AUDIT.VW_EXTERNAL_CONTEXT_SOURCES` | External-context source row counts |
| `MARTS.VW_EXTERNAL_CONTEXT_MODEL_IMPACT` | Controlled public-context model-impact comparisons |
| `MARTS.VW_POLICY_DECISION_RECOMMENDATION` | Selected shadow-validation policy and executive decision metrics |
| `MARTS.VW_POLICY_TRADEOFF` | Candidate-policy adequacy, cost, refund, and review tradeoffs |
| `MARTS.VW_POLICY_SEGMENT_DIAGNOSTICS` | Unsuppressed segment-level policy diagnostics |
| `MARTS.VW_POLICY_UNCERTAINTY` | Probabilistic guardrail and cost uncertainty |

## Commands

```bash
make snowflake-test
make snowflake-bootstrap
make snowflake-load
make snowflake-validate
make snowflake-extracts
```

## Status

- Verified external-stage load generated at: `2026-07-14T17:07:41+00:00`
- S3 run ID: `20260714T170606Z`
- Tables loaded through `COPY INTO`: `22`
- Bucket, account, role, and credential identifiers are intentionally omitted from this public report.
