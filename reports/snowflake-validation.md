# Snowflake Validation

Generated at: `2026-07-14T17:08:17+00:00`

## Summary

- Checks passed: `46`
- Checks failed: `0`

| Object | Type | Local rows | Snowflake rows | Status |
| --- | --- | ---: | ---: | --- |
| `MARTS.DIM_COMP_CATALOG` | table | 10 | 10 | PASS |
| `MARTS.MART_COMP_POLICY_AUDIT` | table | 430 | 430 | PASS |
| `MARTS.MART_COMP_RECOMMENDATIONS` | table | 430 | 430 | PASS |
| `MARTS.MART_EXTERNAL_CONTEXT_MODEL_IMPACT` | table | 5 | 5 | PASS |
| `MARTS.MART_POLICY_CASE_COMPARISON` | table | 2150 | 2150 | PASS |
| `MARTS.MART_POLICY_DECISION_SUMMARY` | table | 5 | 5 | PASS |
| `MARTS.MART_POLICY_SEGMENT_DIAGNOSTICS` | table | 125 | 125 | PASS |
| `MARTS.MART_POLICY_UNCERTAINTY_SUMMARY` | table | 5 | 5 | PASS |
| `MARTS.MART_PUBLIC_PRICING_CONTEXT` | table | 365 | 365 | PASS |
| `MARTS.MART_RECOVERY_CASES` | table | 430 | 430 | PASS |
| `RAW.STG_COMP_LEDGER` | table | 281 | 281 | PASS |
| `RAW.STG_GUEST_PROFILES_CRM` | table | 1725 | 1725 | PASS |
| `RAW.STG_LOCAL_DEMAND_CONTEXT` | table | 365 | 365 | PASS |
| `RAW.STG_OPS_DAILY` | table | 365 | 365 | PASS |
| `RAW.STG_PMS_RESERVATIONS` | table | 1600 | 1600 | PASS |
| `RAW.STG_POS_OUTLET_CHARGES` | table | 3194 | 3194 | PASS |
| `RAW.STG_PROPERTY_CONTEXT` | table | 5 | 5 | PASS |
| `RAW.STG_PROPER_PUBLIC_VALUE_ANCHORS` | table | 11 | 11 | PASS |
| `RAW.STG_RATE_SHOP_SNAPSHOTS` | table | 2190 | 2190 | PASS |
| `RAW.STG_REVIEWS_SURVEYS` | table | 204 | 204 | PASS |
| `RAW.STG_REVIEW_RISK_CONTEXT` | table | 10 | 10 | PASS |
| `RAW.STG_SERVICE_TICKETS` | table | 430 | 430 | PASS |
| `AUDIT.VW_AUDIT_DECISION_SIGNAL` | view |  | 5 | PASS |
| `AUDIT.VW_EXTERNAL_CONTEXT_SOURCES` | view |  | 5 | PASS |
| `AUDIT.VW_SOURCE_QUALITY_SNAPSHOT` | view |  | 5 | PASS |
| `MARTS.VW_COMP_DECISION_SUMMARY` | view |  | 1 | PASS |
| `MARTS.VW_COMP_MIX` | view |  | 7 | PASS |
| `MARTS.VW_EXTERNAL_CONTEXT_MODEL_IMPACT` | view |  | 5 | PASS |
| `MARTS.VW_MANAGER_REVIEW_QUEUE` | view |  | 151 | PASS |
| `MARTS.VW_POLICY_DECISION_RECOMMENDATION` | view |  | 1 | PASS |
| `MARTS.VW_POLICY_SEGMENT_DIAGNOSTICS` | view |  | 125 | PASS |
| `MARTS.VW_POLICY_TRADEOFF` | view |  | 5 | PASS |
| `MARTS.VW_POLICY_UNCERTAINTY` | view |  | 5 | PASS |
| `MARTS.VW_PUBLIC_PRICING_CONTEXT` | view |  | 365 | PASS |

## Decision-Semantic Checks

| Check | Expected | Snowflake result | Status |
| --- | ---: | ---: | --- |
| `candidate_policy_count` | 5 | 5 | PASS |
| `selected_policy_count` | 1 | 1 | PASS |
| `case_policy_row_count` | 2150 | 2150 | PASS |
| `distinct_recovery_cases` | 430 | 430 | PASS |
| `complete_case_policy_matrix` | 0 | 0 | PASS |
| `probability_bounds` | 0 | 0 | PASS |
| `cost_ordering` | 0 | 0 | PASS |
| `selected_policy_parity` | cost_guardrail | cost_guardrail | PASS |
| `selected_metric_parity` | 1 | 1 | PASS |
| `selected_safety_guardrails` | 1 | 1 | PASS |
| `typed_mart_columns` | 4 | 4 | PASS |
| `suppressed_segment_filter` | 0 | 0 | PASS |

## Interpretation

Table checks reconcile Snowflake row counts to the generated public-safe artifacts. View checks confirm the analytic layer is queryable. Semantic checks verify policy grain, selection uniqueness, simulation-rate and cost bounds, selected-policy parity, safety guardrails, typed MARTS columns, and suppression behavior.
