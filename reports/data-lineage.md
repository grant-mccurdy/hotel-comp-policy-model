# Data Lineage

The comp recommendation model consumes a curated recovery-case mart, not clean source rows.

```text
raw_pms_reservations
+ raw_guest_profiles_crm
+ raw_service_tickets
+ raw_comp_ledger
+ raw_pos_outlet_charges
+ raw_reviews_surveys
+ raw_ops_daily
+ public_pricing_context
+ public_property_context
+ review_risk_context
+ local_demand_context
-> identity and reservation matching
-> dirty issue and comp taxonomy normalization
-> public quoted-rate, property, review, and local-demand context joins
-> source-quality flags and match confidence
-> data/marts/recovery_case_mart.csv
-> comp recommendation model
```

## Mart Quality Signals

- Recovery cases: `430`
- Low reservation-match confidence cases: `10`
- Cases with inferred severity: `60`
- Cases with no historical comp record: `175`

These issues are intentionally retained because the business problem is partly a data-wrangling problem.
