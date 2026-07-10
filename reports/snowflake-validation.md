# Snowflake Validation

Generated at: `2026-07-10T18:05:51+00:00`

## Summary

- Checks passed: `26`
- Checks failed: `0`

| Object | Type | Local rows | Snowflake rows | Status |
| --- | --- | ---: | ---: | --- |
| `MARTS.DIM_COMP_CATALOG` | table | 10 | 10 | PASS |
| `MARTS.MART_COMP_POLICY_AUDIT` | table | 430 | 430 | PASS |
| `MARTS.MART_COMP_RECOMMENDATIONS` | table | 430 | 430 | PASS |
| `MARTS.MART_EXTERNAL_CONTEXT_MODEL_IMPACT` | table | 5 | 5 | PASS |
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
| `MARTS.VW_MANAGER_REVIEW_QUEUE` | view |  | 154 | PASS |
| `MARTS.VW_PUBLIC_PRICING_CONTEXT` | view |  | 365 | PASS |

## Interpretation

Table checks compare Snowflake-loaded row counts against the public-safe CSV artifacts generated locally. View checks confirm that the analytic Snowflake layer is queryable.
