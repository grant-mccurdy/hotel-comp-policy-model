# Policy Comparison Assumption Stress Test

This report tests whether the simulated policy decision remains credible when the case mix is resampled and uncertain cost/fit assumptions are varied. It does not validate guest outcomes, estimate causal effects, or project Proper Hotels savings.

## Generated Shadow-Validation Decision

Approve a four-week, minimum-50-case shadow validation of Guardrailed recovery as the leading candidate. Under the declared synthetic case mix and policy assumptions, it cleared the guest-protection, data-quality, escalation, and operational guardrails with the lowest modeled cost among eligible policies.

## Shared-World Assumption Stress

| Policy | Assumption-stress pass rate | Selection frequency | Modeled cost P05 | P50 | P95 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Synthetic discretionary baseline | 0.0% | 0.0% | $19,109 | $19,109 | $19,109 |
| Tiered standardization | 0.0% | 0.0% | $22,884 | $25,914 | $29,379 |
| Guardrailed recovery | 99.6% | 99.6% | $27,342 | $30,467 | $33,944 |
| Recovery first | 100.0% | 0.0% | $41,818 | $51,114 | $60,481 |
| Intelligent generosity | 100.0% | 0.4% | $33,796 | $40,114 | $46,517 |

The assumption stress test applies one coherent set of recovery-weight, fit, occupancy, and gesture-cost assumptions to every policy in each draw. It then recalculates policy metrics, reapplies all shadow-validation guardrails, and reruns the selection rule.

## Paired Case-Bootstrap Intervals

| Policy | Safe recovery path | 95% interval | High-risk under-recovery | 95% interval | Manager review | 95% interval |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Synthetic discretionary baseline | 44.7% | 38.6%-50.8% | 67.6% | 58.7%-76.1% | Unknown | Unknown |
| Tiered standardization | 91.7% | 88.9%-94.2% | 21.5% | 15.4%-28.1% | 27.2% | 23.0%-31.4% |
| Guardrailed recovery | 100.0% | 100.0%-100.0% | 0.0% | 0.0%-0.0% | 27.4% | 23.3%-31.6% |
| Recovery first | 100.0% | 100.0%-100.0% | 0.0% | 0.0%-0.0% | 63.3% | 58.6%-67.7% |
| Intelligent generosity | 100.0% | 100.0%-100.0% | 0.0% | 0.0%-0.0% | 57.7% | 53.0%-62.3% |

Case IDs are resampled once per bootstrap draw and applied to every policy. This paired design preserves case-level comparability and quantifies sampling uncertainty without inventing additional hotel outcomes.

## Interpretation

- A high pass rate means a policy repeatedly clears the declared simulation rules under the tested assumptions; it does not establish real-world effectiveness.
- Selection frequency measures how often the same policy wins after all guardrails and tie-breakers are reapplied; it is not an empirically calibrated probability of business success.
- Cost percentiles reflect synthetic case mix and assumed marginal-cost ranges, not property accounting estimates.
- Shadow-mode data should replace cost assumptions and test manager overrides, operational feasibility, and guest-recovery outcomes before controlled use.
