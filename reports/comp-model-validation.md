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
| exists: policy_case_comparison.csv | PASS | 2150 rows |
| exists: policy_decision_summary.csv | PASS | 5 rows |
| exists: policy_segment_diagnostics.csv | PASS | 125 rows |
| exists: policy_uncertainty_summary.csv | PASS | 5 rows |
| exists: comp_catalog.csv | PASS | 10 rows |
| exists: proper_public_value_anchors.csv | PASS | 11 rows |
| demo scenario catalog exists | PASS | 10 scenarios |
| demo scenario report generated | PASS | contains recommendations and public-safety note |
| methodology report exists | PASS | methodology explains policy simulation |
| manager demo assets exist | PASS | manager app and guide present |
| executive artifacts use the generated policy comparison | PASS | executive brief contains selected policy, tradeoff, and shadow-validation boundary |
| stakeholder report presents the generated decision as an executive data story | PASS | first-click report contains context, conflict, analytical climax, resolution, and bounded next step |
| technical decision analysis documents outcome exclusion | PASS | decision analysis preserves outcome and adoption boundaries |
| policy comparison contracts are valid | PASS | four contracts include primary keys and required fields |
| policy comparison has complete case-policy grain | PASS | 2150 rows, 2150 unique keys, 5 policies |
| exactly one policy is selected by the generated decision | PASS | selected cost_guardrail with executive recommendation |
| policy uncertainty probabilities are bounded | PASS | 5 policies; 0 invalid probabilities |
| policy segment diagnostics preserve unique grain and suppression | PASS | 125 unique rows; 0 groups below n=10 suppressed |
| missing baseline comps are unknown rather than under-recovery | PASS | 175 unmatched baseline cases excluded from adequacy |
| policy selection excludes synthetic post-stay outcomes | PASS | Synthetic post-stay scores are excluded from policy selection because no comp-treatment effect was generated. |
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
| late checkout appears for eligible recovery | PASS | 14 late-checkout recommendations |
| room upgrades constrained under high occupancy | PASS | 3/74 high-occupancy cases use room upgrades |
| recommendations include manager-review cases | PASS | 21 manager-review cases |
| comp audit includes required classes | PASS | all audit classes present |
| recommendation severity monotonicity | PASS | low tier=3, score=49.72; high tier=5, score=87.53 |
| public pricing changes controlled recommendation | PASS | low=room_upgrade/$360; high=rooftop_f_and_b_credit/$180; high reasons=high_guest_relationship_value,hotel_responsible_failure,high_severity_issue,high_review_risk,recoverable_before_checkout,high_perceived_value_lower_estimated_cost,public_rate_pressure_changed_recovery |
| mart carries public pricing fields | PASS | public pricing fields present |
| mart carries external context fields | PASS | property, review, and demand context fields present |
| recommendations carry external context fields | PASS | external context fields present |
| recommendations expose trust and uncertainty fields | PASS | all trust fields present |
| recommendation stability is bounded | PASS | 430/430 rows bounded |
| recommendations expose pricing context reasons | PASS | 47/120 high-pressure recommendations changed under the rate counterfactual |
| property reasons require a changed counterfactual | PASS | 37 recommendations changed without property-fit context |
| operational reasons require a changed counterfactual | PASS | 11 recommendations changed under the availability counterfactual |
| external context model impact report has changed decisions | PASS | 4 controlled comparisons changed recommendation |

## Interpretation

Validation intentionally checks both model behavior and realistic source-system messiness. A fully clean source layer would be less credible for the hotel comp-optimization problem.
