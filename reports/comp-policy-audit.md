# Comp Policy Audit

This audit compares synthetic historical comp actions against the modeled intelligent-generosity recommendation.

The point is not to minimize comp spend. The point is to identify where generosity protects guest value and where compensation leaks profit without proportional recovery benefit.

## Audit Summary

| Audit class | Cases | Historical comp value | Recommended comp value |
| --- | ---: | ---: | ---: |
| under recovered | 117 | $4,660 | $32,775 |
| over comped | 21 | $7,375 | $4,000 |
| aligned recovery | 270 | $24,900 | $47,840 |
| manager review required | 10 | $1,135 | $3,160 |
| data quality hold | 12 | $470 | $3,290 |

## Decision Matrix

| Case type | Meaning | Management action |
| --- | --- | --- |
| Under-recovered high-value cases | Guest relationship or review risk is not sufficiently protected | Increase generosity or act faster |
| Over-comped low-risk cases | Comp spend may exceed modeled recovery value | Tighten approval policy or route for review |
| Correctly generous cases | Spend appears aligned to recovery need | Preserve policy |
| Manager-review cases | High severity, high value, high spend, or unusual variance | Human review before final action |
| Data-quality holds | Weak match confidence or incomplete source context | Fix source reconciliation before auditing behavior |

## Largest Under-Recovery Opportunities

| Case | Guest tier | Issue | Recommended delta | Action |
| --- | --- | --- | ---: | --- |
| case_00025 | event_or_suite_guest | housekeeping miss | $380 | Increase or improve recovery; historical/synthetic comp appears below modeled relationship and brand risk. |
| case_00015 | returning_guest | room assignment expectation gap | $360 | Increase or improve recovery; historical/synthetic comp appears below modeled relationship and brand risk. |
| case_00020 | vip_guest | room assignment expectation gap | $360 | Increase or improve recovery; historical/synthetic comp appears below modeled relationship and brand risk. |
| case_00029 | new_guest | room assignment expectation gap | $360 | Increase or improve recovery; historical/synthetic comp appears below modeled relationship and brand risk. |
| case_00081 | new_guest | room readiness delay | $360 | Increase or improve recovery; historical/synthetic comp appears below modeled relationship and brand risk. |
| case_00118 | new_guest | room assignment expectation gap | $360 | Increase or improve recovery; historical/synthetic comp appears below modeled relationship and brand risk. |
| case_00161 | new_guest | room assignment expectation gap | $360 | Increase or improve recovery; historical/synthetic comp appears below modeled relationship and brand risk. |
| case_00166 | new_guest | room assignment expectation gap | $360 | Increase or improve recovery; historical/synthetic comp appears below modeled relationship and brand risk. |

## Largest Potential Profit-Leakage Cases

| Case | Guest tier | Issue | Over-comp value | Action |
| --- | --- | --- | ---: | --- |
| case_00077 | loyalty_guest | valet or parking delay | $300 | Review for profit leakage; historical/synthetic comp appears high relative to modeled recovery need. |
| case_00004 | new_guest | valet or parking delay | $290 | Review for profit leakage; historical/synthetic comp appears high relative to modeled recovery need. |
| case_00002 | returning_guest | housekeeping miss | $285 | Review for profit leakage; historical/synthetic comp appears high relative to modeled recovery need. |
| case_00258 | vip_guest | f and b service lapse | $245 | Review for profit leakage; historical/synthetic comp appears high relative to modeled recovery need. |
| case_00185 | vip_guest | rooftop pool access issue | $205 | Review for profit leakage; historical/synthetic comp appears high relative to modeled recovery need. |
| case_00288 | new_guest | rooftop pool access issue | $185 | Review for profit leakage; historical/synthetic comp appears high relative to modeled recovery need. |
| case_00092 | loyalty_guest | rooftop pool access issue | $165 | Review for profit leakage; historical/synthetic comp appears high relative to modeled recovery need. |
| case_00065 | new_guest | billing or fee dispute | $160 | Review for profit leakage; historical/synthetic comp appears high relative to modeled recovery need. |

## Public-Safety Note

All rows are synthetic. This is not an analysis of actual Proper Hotels data, guest records, comp history, or internal policy.
