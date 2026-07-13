# DuckDB Warehouse Lineage

The local DuckDB warehouse provides a SQL inspection layer over the synthetic hotel operating data.

The database file is generated locally and ignored by Git. Reviewable outputs remain in CSV and Markdown.

## Source-To-Table Map

| DuckDB object | Rows | Source purpose |
| --- | ---: | --- |
| `stg_pms_reservations` | 1600 | Synthetic PMS reservation extract |
| `stg_guest_profiles_crm` | 1725 | Synthetic CRM guest profiles with duplicate-profile behavior |
| `stg_service_tickets` | 430 | Synthetic service-ticket system with missing IDs and dirty issue labels |
| `stg_comp_ledger` | 281 | Synthetic comp ledger with dirty comp labels and orphan records |
| `stg_pos_outlet_charges` | 3194 | Synthetic outlet charges for F&B, spa/wellness, and parking behavior |
| `stg_reviews_surveys` | 204 | Synthetic post-stay review and survey signals |
| `stg_ops_daily` | 365 | Synthetic daily operational pressure |
| `stg_rate_shop_snapshots` | 2190 | Public quoted-rate snapshot sample or API extract |
| `stg_property_context` | 5 | Public property and competitive-set context |
| `stg_proper_public_value_anchors` | 11 | Observed public Santa Monica Proper value and option anchors |
| `stg_review_risk_context` | 10 | Public review-risk theme priors by issue category |
| `stg_local_demand_context` | 365 | Local event/weather demand-pressure context |
| `mart_public_pricing_context` | 365 | Daily public pricing context used as comp opportunity-cost input |
| `mart_recovery_cases` | 430 | Case-level recovery decision mart |
| `mart_comp_recommendations` | 430 | Policy-engine comp recommendation output |
| `mart_comp_policy_audit` | 430 | Audit classifications comparing historical/synthetic comp to recommendation |
| `mart_external_context_model_impact` | 5 | Controlled scenarios showing public-context recommendation impact |
| `mart_policy_case_comparison` | 2150 | Case-by-policy evaluation matrix |
| `mart_policy_decision_summary` | 5 | Executive policy comparison and shadow-candidate selection |
| `mart_policy_segment_diagnostics` | 125 | Policy diagnostics by synthetic case segment |
| `mart_policy_uncertainty_summary` | 5 | Probabilistic policy guardrail and cost uncertainty |
| `dim_comp_catalog` | 10 | Comp type catalog and cost/perceived-value assumptions |

## Analytics Views

| View | Rows | Use |
| --- | ---: | --- |
| `vw_comp_decision_summary` | 1 | Supporting rollup of modeled comp value, cost, stability, and manager review volume. |
| `vw_comp_mix` | 7 | Comp-type mix by cases, guest-facing value, and internal cost. |
| `vw_manager_review_queue` | 151 | Manager review queue combining escalation and low-match-confidence cases. |
| `vw_audit_decision_signal` | 5 | Audit-class decision signal for under-recovery, over-comping, review, and data-quality holds. |
| `vw_source_quality_snapshot` | 5 | Compact source-quality metrics for messy-data review. |
| `vw_public_pricing_context` | 365 | Public quoted-rate context used for room-comp opportunity-cost reasoning. |
| `vw_external_context_sources` | 5 | Row counts for public/sample external-context layers. |
| `vw_external_context_model_impact` | 5 | Controlled model-impact comparisons for public-context signals. |
| `vw_policy_decision_recommendation` | 1 | Selected shadow-validation recommendation and supporting decision metrics. |
| `vw_policy_tradeoff` | 5 | Five-policy cost, adequacy, refund, review, and robustness comparison. |
| `vw_policy_segment_diagnostics` | 125 | Unsuppressed segment-level policy diagnostics. |
| `vw_policy_uncertainty` | 5 | Probabilistic guardrail and cost uncertainty by policy. |

## Rebuild Command

```bash
make warehouse
```

## Example SQL

```sql
SELECT * FROM vw_comp_decision_summary;
SELECT * FROM vw_comp_mix ORDER BY recommended_guest_value DESC;
SELECT * FROM vw_manager_review_queue LIMIT 20;
SELECT * FROM vw_public_pricing_context LIMIT 20;
SELECT * FROM vw_external_context_model_impact;
SELECT * FROM vw_policy_decision_recommendation;
SELECT * FROM vw_policy_tradeoff;
SELECT * FROM vw_policy_uncertainty;
```
