# Comp Model Validation

| Check | Status | Detail |
| --- | --- | --- |
| exists: raw_pms_reservations.csv | PASS | 1600 rows |
| exists: raw_guest_profiles_crm.csv | PASS | 1725 rows |
| exists: raw_service_tickets.csv | PASS | 430 rows |
| exists: raw_comp_ledger.csv | PASS | 281 rows |
| exists: raw_reviews_surveys.csv | PASS | 204 rows |
| exists: recovery_case_mart.csv | PASS | 430 rows |
| exists: comp_recommendations.csv | PASS | 430 rows |
| exists: comp_policy_audit.csv | PASS | 430 rows |
| exists: comp_catalog.csv | PASS | 10 rows |
| exists: proper_public_value_anchors.csv | PASS | 11 rows |
| demo scenario catalog exists | PASS | 10 scenarios |
| demo scenario report generated | PASS | contains recommendations and public-safety note |
| methodology report exists | PASS | methodology explains policy simulation |
| manager demo assets exist | PASS | manager app and guide present |
| tickets include missing reservation IDs | PASS | 53 missing |
| tickets include missing severity | PASS | 60 missing |
| CRM includes duplicate profiles | PASS | 125 duplicate profiles |
| comp ledger includes orphan records | PASS | 64 without ticket ID |
| comp ledger has dirty label variants | PASS | 39 raw comp labels |
| reviews are delayed after review date | PASS | 128 delayed |
| mart preserves match confidence | PASS | reservation_match_confidence present |
| mart includes low-confidence cases | PASS | 9 low-confidence matches |
| recommendations include several comp types | PASS | 7 comp types |
| partial refunds are rare but present | PASS | 5 partial-refund recommendations |
| late checkout appears for eligible recovery | PASS | 16 late-checkout recommendations |
| room upgrades constrained under high occupancy | PASS | 3/74 high-occupancy cases use room upgrades |
| recommendations include manager-review cases | PASS | 22 manager-review cases |
| comp audit includes required classes | PASS | all audit classes present |
| recommendation severity monotonicity | PASS | low tier=3, score=49.72; high tier=5, score=87.53 |
| public pricing changes controlled recommendation | PASS | low=room_upgrade/$360; high=rooftop_f_and_b_credit/$180; high reasons=high_guest_relationship_value,hotel_responsible_failure,high_severity_issue,high_review_risk,recoverable_before_checkout,high_perceived_value_lower_estimated_cost,public_rate_pressure_changed_recovery |
| mart carries public pricing fields | PASS | public pricing fields present |
| mart carries external context fields | PASS | property, review, and demand context fields present |
| recommendations carry external context fields | PASS | external context fields present |
| recommendations expose trust and uncertainty fields | PASS | all trust fields present |
| recommendation stability is bounded | PASS | 430/430 rows bounded |
| recommendations expose pricing context reasons | PASS | 49/120 high-pressure recommendations changed under the rate counterfactual |
| property reasons require a changed counterfactual | PASS | 34 recommendations changed without property-fit context |
| operational reasons require a changed counterfactual | PASS | 16 recommendations changed under the availability counterfactual |
| external context model impact report has changed decisions | PASS | 4 controlled comparisons changed recommendation |

## Interpretation

Validation intentionally checks both model behavior and realistic source-system messiness. A fully clean source layer would be less credible for the hotel comp-optimization problem.
