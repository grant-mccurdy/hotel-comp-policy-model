# S3 Data Lake Manifest

Generated at: `2026-07-14T17:06:06+00:00`

- Dry run: `False`
- Bucket: `<configured-bucket>`
- Prefix: `hotel-comp-policy-model`
- Run ID: `20260714T170606Z`
- Manifest URI: `s3://<configured-bucket>/hotel-comp-policy-model/_manifests/20260714T170606Z/s3_datalake_manifest.json`

## Data Lake Objects

| Warehouse table | S3 zone | Layer | Rows | Columns | S3 URI |
| --- | --- | --- | ---: | ---: | --- |
| `RAW.STG_PMS_RESERVATIONS` | `landing` | `source_or_context` | 1600 | 18 | `s3://<configured-bucket>/hotel-comp-policy-model/landing/20260714T170606Z/raw/stg_pms_reservations/raw_pms_reservations.csv` |
| `RAW.STG_GUEST_PROFILES_CRM` | `landing` | `source_or_context` | 1725 | 10 | `s3://<configured-bucket>/hotel-comp-policy-model/landing/20260714T170606Z/raw/stg_guest_profiles_crm/raw_guest_profiles_crm.csv` |
| `RAW.STG_SERVICE_TICKETS` | `landing` | `source_or_context` | 430 | 14 | `s3://<configured-bucket>/hotel-comp-policy-model/landing/20260714T170606Z/raw/stg_service_tickets/raw_service_tickets.csv` |
| `RAW.STG_COMP_LEDGER` | `landing` | `source_or_context` | 281 | 11 | `s3://<configured-bucket>/hotel-comp-policy-model/landing/20260714T170606Z/raw/stg_comp_ledger/raw_comp_ledger.csv` |
| `RAW.STG_POS_OUTLET_CHARGES` | `landing` | `source_or_context` | 3194 | 7 | `s3://<configured-bucket>/hotel-comp-policy-model/landing/20260714T170606Z/raw/stg_pos_outlet_charges/raw_pos_outlet_charges.csv` |
| `RAW.STG_REVIEWS_SURVEYS` | `landing` | `source_or_context` | 204 | 9 | `s3://<configured-bucket>/hotel-comp-policy-model/landing/20260714T170606Z/raw/stg_reviews_surveys/raw_reviews_surveys.csv` |
| `RAW.STG_OPS_DAILY` | `landing` | `source_or_context` | 365 | 7 | `s3://<configured-bucket>/hotel-comp-policy-model/landing/20260714T170606Z/raw/stg_ops_daily/raw_ops_daily.csv` |
| `RAW.STG_RATE_SHOP_SNAPSHOTS` | `landing` | `source_or_context` | 2190 | 60 | `s3://<configured-bucket>/hotel-comp-policy-model/landing/20260714T170606Z/raw/stg_rate_shop_snapshots/rate_shop_snapshots_sample.csv` |
| `RAW.STG_PROPERTY_CONTEXT` | `landing` | `source_or_context` | 5 | 31 | `s3://<configured-bucket>/hotel-comp-policy-model/landing/20260714T170606Z/raw/stg_property_context/property_context_public.csv` |
| `RAW.STG_PROPER_PUBLIC_VALUE_ANCHORS` | `landing` | `source_or_context` | 11 | 14 | `s3://<configured-bucket>/hotel-comp-policy-model/landing/20260714T170606Z/raw/stg_proper_public_value_anchors/proper_public_value_anchors.csv` |
| `RAW.STG_REVIEW_RISK_CONTEXT` | `landing` | `source_or_context` | 10 | 13 | `s3://<configured-bucket>/hotel-comp-policy-model/landing/20260714T170606Z/raw/stg_review_risk_context/review_risk_context.csv` |
| `RAW.STG_LOCAL_DEMAND_CONTEXT` | `landing` | `source_or_context` | 365 | 13 | `s3://<configured-bucket>/hotel-comp-policy-model/landing/20260714T170606Z/raw/stg_local_demand_context/local_demand_context.csv` |
| `MARTS.MART_PUBLIC_PRICING_CONTEXT` | `model-output` | `derived_mart` | 365 | 24 | `s3://<configured-bucket>/hotel-comp-policy-model/model-output/20260714T170606Z/marts/mart_public_pricing_context/public_pricing_context.csv` |
| `MARTS.MART_RECOVERY_CASES` | `model-output` | `derived_mart` | 430 | 84 | `s3://<configured-bucket>/hotel-comp-policy-model/model-output/20260714T170606Z/marts/mart_recovery_cases/recovery_case_mart.csv` |
| `MARTS.MART_COMP_RECOMMENDATIONS` | `model-output` | `derived_mart` | 430 | 72 | `s3://<configured-bucket>/hotel-comp-policy-model/model-output/20260714T170606Z/marts/mart_comp_recommendations/comp_recommendations.csv` |
| `MARTS.MART_COMP_POLICY_AUDIT` | `model-output` | `derived_mart` | 430 | 41 | `s3://<configured-bucket>/hotel-comp-policy-model/model-output/20260714T170606Z/marts/mart_comp_policy_audit/comp_policy_audit.csv` |
| `MARTS.MART_EXTERNAL_CONTEXT_MODEL_IMPACT` | `model-output` | `derived_mart` | 5 | 15 | `s3://<configured-bucket>/hotel-comp-policy-model/model-output/20260714T170606Z/marts/mart_external_context_model_impact/external_context_model_impact.csv` |
| `MARTS.MART_POLICY_CASE_COMPARISON` | `model-output` | `derived_mart` | 2150 | 44 | `s3://<configured-bucket>/hotel-comp-policy-model/model-output/20260714T170606Z/marts/mart_policy_case_comparison/policy_case_comparison.csv` |
| `MARTS.MART_POLICY_DECISION_SUMMARY` | `model-output` | `derived_mart` | 5 | 38 | `s3://<configured-bucket>/hotel-comp-policy-model/model-output/20260714T170606Z/marts/mart_policy_decision_summary/policy_decision_summary.csv` |
| `MARTS.MART_POLICY_SEGMENT_DIAGNOSTICS` | `model-output` | `derived_mart` | 125 | 12 | `s3://<configured-bucket>/hotel-comp-policy-model/model-output/20260714T170606Z/marts/mart_policy_segment_diagnostics/policy_segment_diagnostics.csv` |
| `MARTS.MART_POLICY_UNCERTAINTY_SUMMARY` | `model-output` | `derived_mart` | 5 | 15 | `s3://<configured-bucket>/hotel-comp-policy-model/model-output/20260714T170606Z/marts/mart_policy_uncertainty_summary/policy_uncertainty_summary.csv` |
| `MARTS.DIM_COMP_CATALOG` | `model-output` | `derived_mart` | 10 | 15 | `s3://<configured-bucket>/hotel-comp-policy-model/model-output/20260714T170606Z/marts/dim_comp_catalog/comp_catalog.csv` |

## Workflow Role

S3 preserves versioned, public-safe artifacts with row counts, hashes, and provenance before Snowflake loads them into structured warehouse tables.

Source and context snapshots use the `landing` zone. Python policy-engine outputs use the separate `model-output` zone because bootstrap and sensitivity computation remain appropriately outside SQL. Snowflake types, validates, and serves both layers through governed tables and views.
