# Legacy Context-Engine Diagnostic

This supporting diagnostic compares matched synthetic historical actions with the context-aware Intelligent Generosity recommendation. It is not the source of the executive shadow-validation decision; the five-policy comparison is authoritative.

The diagnostic shows how action variances, source holds, and review routing can be inspected. It cannot identify actual under-recovery, over-comping, profit leakage, or recovery benefit because neither the actions nor outcomes are observed hotel data.

## Audit Summary

| Audit class | Cases | Historical comp value | Recommended comp value |
| --- | ---: | ---: | ---: |
| under recovered | 53 | $4,410 | $15,400 |
| over comped | 21 | $7,375 | $4,000 |
| aligned recovery | 171 | $25,150 | $32,080 |
| manager review required | 5 | $1,135 | $1,740 |
| data quality hold | 180 | $470 | $36,585 |

## Decision Matrix

| Case type | Meaning | Management action |
| --- | --- | --- |
| Upward recommendation variance | Context engine recommends more than the matched synthetic action | Review assumptions and case detail |
| Downward recommendation variance | Context engine recommends less than the matched synthetic action | Review assumptions and case detail |
| Within tolerance | Synthetic action and recommendation are close under the diagnostic rule | No variance action |
| Manager-review cases | High severity, high value, high spend, or unusual variance | Human review before final action |
| Data-quality holds | Weak match confidence or incomplete source context | Fix source reconciliation before auditing behavior |

## Largest Simulated Upward Variances

| Case | Guest tier | Issue | Recommended delta | Action |
| --- | --- | --- | ---: | --- |
| case_00081 | new_guest | room readiness delay | $360 | Review upward variance between the matched synthetic action and context-engine recommendation. |
| case_00161 | new_guest | room assignment expectation gap | $360 | Review upward variance between the matched synthetic action and context-engine recommendation. |
| case_00082 | returning_guest | maintenance issue | $330 | Review upward variance between the matched synthetic action and context-engine recommendation. |
| case_00369 | returning_guest | maintenance issue | $330 | Review upward variance between the matched synthetic action and context-engine recommendation. |
| case_00110 | vip_guest | room assignment expectation gap | $305 | Review upward variance between the matched synthetic action and context-engine recommendation. |
| case_00044 | vip_guest | f and b service lapse | $300 | Review upward variance between the matched synthetic action and context-engine recommendation. |
| case_00362 | returning_guest | room readiness delay | $285 | Review upward variance between the matched synthetic action and context-engine recommendation. |
| case_00007 | new_guest | room readiness delay | $280 | Review upward variance between the matched synthetic action and context-engine recommendation. |

## Largest Simulated Downward Variances

| Case | Guest tier | Issue | Over-comp value | Action |
| --- | --- | --- | ---: | --- |
| case_00077 | loyalty_guest | valet or parking delay | $300 | Review downward variance between the matched synthetic action and context-engine recommendation. |
| case_00004 | new_guest | valet or parking delay | $290 | Review downward variance between the matched synthetic action and context-engine recommendation. |
| case_00002 | returning_guest | housekeeping miss | $285 | Review downward variance between the matched synthetic action and context-engine recommendation. |
| case_00258 | vip_guest | f and b service lapse | $245 | Review downward variance between the matched synthetic action and context-engine recommendation. |
| case_00185 | vip_guest | rooftop pool access issue | $205 | Review downward variance between the matched synthetic action and context-engine recommendation. |
| case_00288 | new_guest | rooftop pool access issue | $185 | Review downward variance between the matched synthetic action and context-engine recommendation. |
| case_00092 | loyalty_guest | rooftop pool access issue | $165 | Review downward variance between the matched synthetic action and context-engine recommendation. |
| case_00065 | new_guest | billing or fee dispute | $160 | Review downward variance between the matched synthetic action and context-engine recommendation. |

## Public-Safety Note

All rows are synthetic. This is not an analysis of actual Proper Hotels data, guest records, comp history, or internal policy.
