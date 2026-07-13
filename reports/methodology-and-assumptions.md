# Methodology And Assumptions

## Decision Frame

This is an explainable policy simulation. It asks two related questions:

1. Which candidate service-recovery rule is safe and economical enough to enter shadow validation?
2. Under that candidate, what recovery gesture, value, and approval path should a manager consider for a specific case?

The target is intelligent generosity, not comp minimization. Guest protection and escalation rules are evaluated before modeled cost.

## Evidence Boundary

| Evidence | Use |
| --- | --- |
| Observed public booking data | Shapes synthetic booking and stay context |
| Official Santa Monica Proper public facts | Establishes property-fit and guest-facing value anchors |
| Sample-seed public context | Stress-tests pricing, review-risk, and demand logic |
| Synthetic operating systems | Demonstrates reconciliation, decisioning, and audit workflow |
| Policy assumptions | Defines weights, thresholds, cost ranges, and option scoring |
| Unavailable internal data | Prevents claims about actual margins, outcomes, inventory, or policy |

All service cases, historical comp actions, guest values, costs, post-stay scores, and policy results are synthetic. Public prices do not reveal contribution margin.

## Shared Case Reference

Every candidate policy receives the same 430 recovery cases. A common reference calculation converts severity, hotel responsibility, reputation risk, guest relationship, sentiment, delay, timing, and issue type into a recovery-need score and five-tier band. This holds the required recovery level constant while the decision rule changes.

Low-confidence reservation or CRM matches become data holds. Missing synthetic baseline comp records remain unknown; they are not automatically classified as under-recovery.

## Candidate Policies

| Policy | Decision rule |
| --- | --- |
| Synthetic discretionary baseline | Replays matched synthetic historical actions; reference only |
| Tiered standardization | Chooses the highest issue-fit tier-appropriate gesture |
| Guardrailed recovery | Requires a robust fit margin, then chooses the lowest midpoint-cost eligible gesture |
| Recovery first | Prioritizes issue fit and guest-perceived value; cost is a tie-breaker |
| Intelligent generosity | Balances fit, cost, guest value, property context, demand, and operational pressure |

Room upgrades and late checkout are unavailable after checkout. High occupancy or demand does not make a gesture literally impossible; it triggers availability review. Severe, high-value, weak-fit, capacity-sensitive, repeat-pattern, and low-confidence decisions retain a human path.

## Shadow-Validation Guardrails

A policy can advance only if it clears all declared rules in at least 80% of the assumption-stress draws:

- safe recovery path at or above 90%;
- unreviewed high-risk under-recovery at or below 5%;
- operational infeasibility at or below 2%;
- complete data-hold compliance;
- complete tier-5 review compliance.

Safe recovery path means an adequate proposed gesture or explicit manager review. Strict gesture fit reports adequacy of the gesture alone. Among eligible policies, the lowest median modeled cost wins; policies within 1% are resolved by lower direct-refund exposure, then lower manager-review volume.

Guardrailed recovery is deliberately an adequacy-constrained cost optimizer. Its simulated advantage is therefore a constrained decision-analysis result under the declared fit and cost assumptions, not independent evidence that it improves guest recovery or profitability.

## Uncertainty Analysis

The paired case bootstrap resamples recovery-case IDs and applies each sampled case mix to every policy. Ten thousand draws produce 95% intervals for safe recovery, high-risk under-recovery, manager review, direct refunds, and total modeled cost.

The assumption stress test runs 5,000 draws using triangular multipliers from 0.8 to 1.2 around recovery-weight, fit, occupancy, and cost assumptions. Each draw applies one coherent world state to every policy: shared recovery-weight perturbations, shared fit shocks by gesture and issue type, shared occupancy pressure, and shared gesture-level cost quantiles. It then recalculates policy metrics, reapplies all shadow-validation guardrails, and reruns the selection rule. The outputs are an assumption-stress pass rate, a selection frequency, and modeled cost percentiles. They are not empirically calibrated probabilities of business success.

Synthetic post-stay scores are excluded from selection because the generator did not assign a comp-treatment effect. Using them would create false outcome evidence. The legacy `expected_recovery_value` field remains only for backward-compatible technical artifacts and is excluded from executive analysis.

## Current Generated Decision

The current run selects **Guardrailed recovery** for a four-week, minimum-50-case shadow validation. This does not authorize manager-facing guidance or permanent policy adoption. Replace assumed costs with property accounting data and expose guidance only through a pre-registered controlled test if the declared protections continue to hold.

## Production Validation

Shadow mode should collect actual comp actions, approvals, overrides, marginal costs, availability, and policy exceptions. A later controlled phase should pre-register guest-recovery and economic endpoints, including post-resolution satisfaction, review sentiment, unresolved complaints, cancellations, repeat stays, approval time, and avoidable room-rate erosion.

## Research Anchors

- Hart, Heskett, and Sasser, [The Profitable Art of Service Recovery](https://hbr.org/1990/07/the-profitable-art-of-service-recovery).
- de Matos, Henrique, and Rossi, [Service Recovery Paradox: A Meta-Analysis](https://doi.org/10.1177/1094670507303012).
- Tax, Brown, and Chandrashekaran, [Customer Evaluations of Service Complaint Experiences](https://doi.org/10.1177/002224299806200205).
- Vargas-Calderon et al., [Review-Based Quality-of-Service Framework](https://arxiv.org/abs/2107.10328).

These sources motivate disciplined recovery, fairness, timing, and review signals. They do not provide property-specific policy weights or outcomes.
