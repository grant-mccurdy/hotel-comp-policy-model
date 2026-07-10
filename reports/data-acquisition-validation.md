# Data Acquisition Validation

| Check | Status | Detail |
| --- | --- | --- |
| raw booking source exists | PASS | data/raw/hotel_booking_demand_tidy_tuesday.csv |
| booking manifest exists | PASS | data/manifests/hotel_booking_demand_manifest.json |
| booking sample exists | PASS | data/sample/booking_stays_sample.csv |
| review acquisition stub exists | PASS | data/manifests/hotel_review_signals_acquisition_stub.json |
| rate-shop snapshot exists | PASS | data/sample/external_context/rate_shop_snapshots_sample.csv |
| public pricing context exists | PASS | data/marts/public_pricing_context.csv |
| public pricing manifest exists | PASS | data/manifests/public_pricing_manifest.json |
| property context exists | PASS | data/sample/external_context/property_context_public.csv |
| property context manifest exists | PASS | data/manifests/property_context_manifest.json |
| review-risk context exists | PASS | data/sample/external_context/review_risk_context.csv |
| review-risk context manifest exists | PASS | data/manifests/review_risk_context_manifest.json |
| local demand context exists | PASS | data/sample/external_context/local_demand_context.csv |
| local demand context manifest exists | PASS | data/manifests/local_demand_context_manifest.json |
| external context model-impact mart exists | PASS | data/marts/external_context_model_impact.csv |
| manifest hash matches raw file | PASS | current sha256 matches manifest |
| manifest row count matches raw file | PASS | raw=119390, manifest=119390 |
| manifest column count matches raw file | PASS | raw=32, manifest=32 |
| required booking fields present | PASS | all required fields present |
| sample is reviewer-sized | PASS | 1000 rows, 36 columns |
| sample contains derived room mismatch | PASS | room_type_mismatch present |
| rate-shop extract has comprehensive fields | PASS | 60 columns |
| rate-shop extract has target and comp-set coverage | PASS | 365 target rows, 5 comp-set properties |
| rate-shop extract has usable quoted rates | PASS | 2190 rows |
| public pricing context has model fields | PASS | 24 columns |
| public pricing context has daily coverage | PASS | 365 context dates |
| public pricing context includes high-pressure dates | PASS | 99 high-pressure dates |
| property context has model fields | PASS | 31 columns |
| property context has target and comp-set rows | PASS | 1 target rows, 4 comp-set rows |
| Proper public value anchor manifest exists | PASS | data/manifests/proper_public_value_anchors_manifest.json |
| Proper public anchors have provenance fields | PASS | 11 anchors, 14 columns |
| Proper public anchors use official sources and preserve cost boundary | PASS | 11/11 official sources; 11/11 internal costs marked unknown |
| review-risk context has model fields | PASS | 13 columns |
| review-risk context covers failure taxonomy | PASS | 10 failure categories |
| local demand context has model fields | PASS | 13 columns |
| local demand context has annual coverage | PASS | 365 dates, 5 high-demand dates |
| external context model impact has comparisons | PASS | 5 comparisons, 15 columns |
| external context changes controlled recommendations | PASS | 4 changed recommendations |
| contract valid: source_booking_stays.schema.json | PASS | valid JSON |
| contract valid: source_review_signals.schema.json | PASS | valid JSON |
| contract valid: synthetic_service_failures.schema.json | PASS | valid JSON |
| contract valid: synthetic_source_systems.schema.json | PASS | valid JSON |
| contract valid: recovery_case_mart.schema.json | PASS | valid JSON |
| contract valid: comp_policy_audit.schema.json | PASS | valid JSON |
| contract valid: comp_recommendation.schema.json | PASS | valid JSON |
| contract valid: public_pricing_context.schema.json | PASS | valid JSON |
| contract valid: property_context.schema.json | PASS | valid JSON |
| contract valid: proper_public_value_anchors.schema.json | PASS | valid JSON |
| contract valid: review_risk_context.schema.json | PASS | valid JSON |
| contract valid: local_demand_context.schema.json | PASS | valid JSON |
| contract valid: external_context_model_impact.schema.json | PASS | valid JSON |
| contract valid: field_provenance.json | PASS | valid JSON |
| raw directory ignored | PASS | data/raw/ present in .gitignore |
| internal unavailable fields not marked observed | PASS | no overlap |
| DuckDB warehouse exists | PASS | data/warehouse/hotel_comp_policy.duckdb |
| DuckDB warehouse manifest exists | PASS | data/manifests/duckdb_warehouse_manifest.json |
| DuckDB warehouse views registered | PASS | all expected views present |
| DuckDB warehouse includes recommendation rows | PASS | 430 recommendation rows |
| DuckDB decision summary query works | PASS | 1 summary rows |
| DuckDB manager queue query works | PASS | 154 manager/data-quality queue rows |

## Public-Safety Boundary

- Full raw downloads are ignored in `data/raw/`.
- Compensation fields are policy-simulated, not observed public labels.
- Internal hotel fields remain marked as unavailable or synthetic.
