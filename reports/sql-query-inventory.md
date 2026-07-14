# SQL Query Inventory

This inventory documents the named SQL views built in the local DuckDB warehouse.

## `vw_comp_decision_summary`

```sql
CREATE OR REPLACE VIEW vw_comp_decision_summary AS
SELECT
    COUNT(*) AS recovery_cases,
    SUM(CAST(recommended_comp_value AS DOUBLE)) AS recommended_guest_value,
    SUM(CAST(estimated_internal_cost AS DOUBLE)) AS estimated_internal_cost,
    SUM(CAST(internal_cost_low AS DOUBLE)) AS internal_cost_low,
    SUM(CAST(internal_cost_high AS DOUBLE)) AS internal_cost_high,
    MEDIAN(CAST(recommendation_stability AS DOUBLE)) AS median_recommendation_stability,
    SUM(CASE WHEN decision_confidence = 'low' THEN 1 ELSE 0 END) AS low_confidence_cases,
    SUM(CASE WHEN manager_review_flag = 'true' THEN 1 ELSE 0 END) AS manager_review_cases,
    SUM(CASE WHEN CAST(review_risk_score AS DOUBLE) >= 0.70 THEN 1 ELSE 0 END) AS high_review_risk_cases
FROM mart_comp_recommendations
```

## `vw_comp_mix`

```sql
CREATE OR REPLACE VIEW vw_comp_mix AS
SELECT
    comp_label,
    COUNT(*) AS cases,
    SUM(CAST(recommended_comp_value AS DOUBLE)) AS recommended_guest_value,
    SUM(CAST(estimated_internal_cost AS DOUBLE)) AS estimated_internal_cost
FROM mart_comp_recommendations
GROUP BY comp_label
ORDER BY recommended_guest_value DESC
```

## `vw_manager_review_queue`

```sql
CREATE OR REPLACE VIEW vw_manager_review_queue AS
SELECT
    recovery_case_id,
    service_ticket_id,
    guest_tier,
    traveler_segment,
    failure_category,
    severity,
    recovery_need_score,
    review_risk_score,
    recommended_comp_value,
    internal_cost_low,
    internal_cost_high,
    comp_label,
    manager_review_flag,
    decision_confidence,
    recommendation_stability,
    policy_version,
    recommendation_counterfactuals,
    reservation_match_confidence,
    data_quality_flags
FROM mart_comp_recommendations
WHERE manager_review_flag = 'true'
   OR decision_confidence <> 'high'
   OR CAST(reservation_match_confidence AS DOUBLE) < 0.75
ORDER BY CAST(recovery_need_score AS DOUBLE) DESC, CAST(estimated_lifetime_value AS DOUBLE) DESC
```

## `vw_audit_decision_signal`

```sql
CREATE OR REPLACE VIEW vw_audit_decision_signal AS
SELECT
    audit_class,
    COUNT(*) AS cases,
    SUM(CAST(recommended_comp_value AS DOUBLE)) AS recommended_guest_value,
    SUM(CAST(recommended_internal_cost AS DOUBLE)) AS recommended_internal_cost,
    SUM(CAST(recommended_minus_actual_value AS DOUBLE)) AS recommended_minus_actual_value
FROM mart_comp_policy_audit
GROUP BY audit_class
ORDER BY cases DESC
```

## `vw_source_quality_snapshot`

```sql
CREATE OR REPLACE VIEW vw_source_quality_snapshot AS
SELECT 'tickets_missing_reservation_id' AS metric, COUNT(*) AS rows
FROM stg_service_tickets
WHERE pms_reservation_id IS NULL OR pms_reservation_id = ''
UNION ALL
SELECT 'tickets_missing_severity' AS metric, COUNT(*) AS rows
FROM stg_service_tickets
WHERE severity_raw IS NULL OR severity_raw = ''
UNION ALL
SELECT 'crm_duplicate_profiles' AS metric, COUNT(*) AS rows
FROM stg_guest_profiles_crm
WHERE duplicate_profile_flag = 'true'
UNION ALL
SELECT 'comp_ledger_orphan_records' AS metric, COUNT(*) AS rows
FROM stg_comp_ledger
WHERE service_ticket_id IS NULL OR service_ticket_id = ''
UNION ALL
SELECT 'low_confidence_recovery_cases' AS metric, COUNT(*) AS rows
FROM mart_recovery_cases
WHERE CAST(reservation_match_confidence AS DOUBLE) > 0
  AND CAST(reservation_match_confidence AS DOUBLE) < 0.75
```

## `vw_public_pricing_context`

```sql
CREATE OR REPLACE VIEW vw_public_pricing_context AS
SELECT
    context_date,
    target_public_rate,
    comp_set_median_rate,
    public_rate_pressure_index,
    high_demand_rate_flag,
    upgrade_opportunity_cost_proxy,
    refund_cost_pressure,
    rate_context_confidence,
    pricing_provenance
FROM mart_public_pricing_context
ORDER BY CAST(public_rate_pressure_index AS DOUBLE) DESC
```

## `vw_external_context_sources`

```sql
CREATE OR REPLACE VIEW vw_external_context_sources AS
SELECT 'rate_shop_snapshots' AS source_layer, COUNT(*) AS rows FROM stg_rate_shop_snapshots
UNION ALL
SELECT 'property_context' AS source_layer, COUNT(*) AS rows FROM stg_property_context
UNION ALL
SELECT 'proper_public_value_anchors' AS source_layer, COUNT(*) AS rows FROM stg_proper_public_value_anchors
UNION ALL
SELECT 'review_risk_context' AS source_layer, COUNT(*) AS rows FROM stg_review_risk_context
UNION ALL
SELECT 'local_demand_context' AS source_layer, COUNT(*) AS rows FROM stg_local_demand_context
```

## `vw_external_context_model_impact`

```sql
CREATE OR REPLACE VIEW vw_external_context_model_impact AS
SELECT
    comparison_id,
    decision_signal,
    control_comp_code,
    context_comp_code,
    recommendation_changed,
    recommended_value_delta,
    internal_cost_delta,
    context_reason_codes
FROM mart_external_context_model_impact
ORDER BY decision_signal
```

## `vw_policy_decision_recommendation`

```sql
CREATE OR REPLACE VIEW vw_policy_decision_recommendation AS
SELECT
    policy_id,
    policy_label,
    adequacy_rate AS safe_recovery_path_rate,
    gesture_adequacy_rate,
    high_risk_under_recovery_rate,
    internal_cost_mid,
    direct_room_refund_value,
    manager_review_rate,
    joint_guardrail_pass_probability,
    policy_selection_probability,
    executive_recommendation,
    evidence_boundary
FROM mart_policy_decision_summary
WHERE selected_for_shadow_evaluation = 'true'
```

## `vw_policy_tradeoff`

```sql
CREATE OR REPLACE VIEW vw_policy_tradeoff AS
SELECT
    policy_id,
    policy_label,
    selection_eligible,
    adequacy_rate AS safe_recovery_path_rate,
    gesture_adequacy_rate,
    high_risk_under_recovery_rate,
    internal_cost_low,
    internal_cost_mid,
    internal_cost_high,
    direct_room_refund_value,
    property_aligned_gesture_rate,
    manager_review_rate,
    joint_guardrail_pass_probability,
    selected_for_shadow_evaluation
FROM mart_policy_decision_summary
ORDER BY CAST(selected_for_shadow_evaluation AS BOOLEAN) DESC, CAST(internal_cost_mid AS DOUBLE)
```

## `vw_policy_segment_diagnostics`

```sql
CREATE OR REPLACE VIEW vw_policy_segment_diagnostics AS
SELECT *
FROM mart_policy_segment_diagnostics
WHERE suppressed_small_group = 'false'
```

## `vw_policy_uncertainty`

```sql
CREATE OR REPLACE VIEW vw_policy_uncertainty AS
SELECT
    policy_id,
    policy_label,
    sensitivity_draws,
    joint_guardrail_pass_probability,
    adequacy_guardrail_pass_probability,
    high_risk_guardrail_pass_probability,
    operational_guardrail_pass_probability,
    data_hold_guardrail_pass_probability,
    tier_five_review_guardrail_pass_probability,
    internal_cost_p05,
    internal_cost_p50,
    internal_cost_p95,
    policy_selection_probability,
    uncertainty_provenance
FROM mart_policy_uncertainty_summary
ORDER BY CAST(policy_selection_probability AS DOUBLE) DESC
```
