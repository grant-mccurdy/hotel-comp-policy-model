# S3 Data Lake Manifest

Generated at: `2026-07-10T17:57:12+00:00`

- Dry run: `False`
- Bucket: `<configured-bucket>`
- Prefix: `hotel-comp-policy-model`
- Run ID: `20260710T175712Z`
- Manifest URI: `s3://<configured-bucket>/hotel-comp-policy-model/_manifests/20260710T175712Z/s3_datalake_manifest.json`

## Data Lake Objects

| Warehouse table | Layer | Rows | Columns | S3 URI |
| --- | --- | ---: | ---: | --- |
| `RAW.STG_PMS_RESERVATIONS` | `source_or_context` | 1600 | 18 | `s3://<configured-bucket>/hotel-comp-policy-model/raw/20260710T175712Z/raw/stg_pms_reservations/raw_pms_reservations.csv` |
| `RAW.STG_GUEST_PROFILES_CRM` | `source_or_context` | 1725 | 10 | `s3://<configured-bucket>/hotel-comp-policy-model/raw/20260710T175712Z/raw/stg_guest_profiles_crm/raw_guest_profiles_crm.csv` |
| `RAW.STG_SERVICE_TICKETS` | `source_or_context` | 430 | 14 | `s3://<configured-bucket>/hotel-comp-policy-model/raw/20260710T175712Z/raw/stg_service_tickets/raw_service_tickets.csv` |
| `RAW.STG_COMP_LEDGER` | `source_or_context` | 281 | 11 | `s3://<configured-bucket>/hotel-comp-policy-model/raw/20260710T175712Z/raw/stg_comp_ledger/raw_comp_ledger.csv` |
| `RAW.STG_POS_OUTLET_CHARGES` | `source_or_context` | 3194 | 7 | `s3://<configured-bucket>/hotel-comp-policy-model/raw/20260710T175712Z/raw/stg_pos_outlet_charges/raw_pos_outlet_charges.csv` |
| `RAW.STG_REVIEWS_SURVEYS` | `source_or_context` | 204 | 9 | `s3://<configured-bucket>/hotel-comp-policy-model/raw/20260710T175712Z/raw/stg_reviews_surveys/raw_reviews_surveys.csv` |
| `RAW.STG_OPS_DAILY` | `source_or_context` | 365 | 7 | `s3://<configured-bucket>/hotel-comp-policy-model/raw/20260710T175712Z/raw/stg_ops_daily/raw_ops_daily.csv` |
| `RAW.STG_RATE_SHOP_SNAPSHOTS` | `source_or_context` | 2190 | 60 | `s3://<configured-bucket>/hotel-comp-policy-model/raw/20260710T175712Z/raw/stg_rate_shop_snapshots/rate_shop_snapshots_sample.csv` |
| `RAW.STG_PROPERTY_CONTEXT` | `source_or_context` | 5 | 31 | `s3://<configured-bucket>/hotel-comp-policy-model/raw/20260710T175712Z/raw/stg_property_context/property_context_public.csv` |
| `RAW.STG_PROPER_PUBLIC_VALUE_ANCHORS` | `source_or_context` | 11 | 14 | `s3://<configured-bucket>/hotel-comp-policy-model/raw/20260710T175712Z/raw/stg_proper_public_value_anchors/proper_public_value_anchors.csv` |
| `RAW.STG_REVIEW_RISK_CONTEXT` | `source_or_context` | 10 | 13 | `s3://<configured-bucket>/hotel-comp-policy-model/raw/20260710T175712Z/raw/stg_review_risk_context/review_risk_context.csv` |
| `RAW.STG_LOCAL_DEMAND_CONTEXT` | `source_or_context` | 365 | 13 | `s3://<configured-bucket>/hotel-comp-policy-model/raw/20260710T175712Z/raw/stg_local_demand_context/local_demand_context.csv` |
| `MARTS.MART_PUBLIC_PRICING_CONTEXT` | `derived_mart` | 365 | 24 | `s3://<configured-bucket>/hotel-comp-policy-model/raw/20260710T175712Z/marts/mart_public_pricing_context/public_pricing_context.csv` |
| `MARTS.MART_RECOVERY_CASES` | `derived_mart` | 430 | 84 | `s3://<configured-bucket>/hotel-comp-policy-model/raw/20260710T175712Z/marts/mart_recovery_cases/recovery_case_mart.csv` |
| `MARTS.MART_COMP_RECOMMENDATIONS` | `derived_mart` | 430 | 71 | `s3://<configured-bucket>/hotel-comp-policy-model/raw/20260710T175712Z/marts/mart_comp_recommendations/comp_recommendations.csv` |
| `MARTS.MART_COMP_POLICY_AUDIT` | `derived_mart` | 430 | 40 | `s3://<configured-bucket>/hotel-comp-policy-model/raw/20260710T175712Z/marts/mart_comp_policy_audit/comp_policy_audit.csv` |
| `MARTS.MART_EXTERNAL_CONTEXT_MODEL_IMPACT` | `derived_mart` | 5 | 15 | `s3://<configured-bucket>/hotel-comp-policy-model/raw/20260710T175712Z/marts/mart_external_context_model_impact/external_context_model_impact.csv` |
| `MARTS.DIM_COMP_CATALOG` | `derived_mart` | 10 | 15 | `s3://<configured-bucket>/hotel-comp-policy-model/raw/20260710T175712Z/marts/dim_comp_catalog/comp_catalog.csv` |

## Workflow Role

This S3 layer is the data lake landing zone. It stores public-safe CSV artifacts with row counts, hashes, and provenance before Snowflake loads them into structured warehouse tables.

Current scope: the landing zone mirrors the project CSV contract, so it includes both source/context artifacts and derived mart artifacts. A stricter production version would land only raw operational extracts first, then build all marts inside Snowflake.
