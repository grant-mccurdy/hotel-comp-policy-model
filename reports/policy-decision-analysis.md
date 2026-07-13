# Comp Policy Decision Analysis

## Executive Decision

Approve a four-week, minimum-50-case shadow validation of Guardrailed recovery as the leading candidate. Under the declared synthetic case mix and policy assumptions, it cleared the guest-protection, data-quality, escalation, and operational guardrails with the lowest modeled cost among eligible policies.

> **Evidence boundary:** this is constrained optimization over synthetic hotel operations and declared policy assumptions. It supports selecting a candidate for shadow validation, not manager-facing use, permanent adoption, actual savings, or claims about Proper Hotels performance.

## Policy Comparison

| Policy | Safe recovery path | Gesture fit | High-risk under-recovery | Midpoint cost | Direct refund face value | Manager review | Assumption-stress pass rate | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Synthetic discretionary baseline | 44.7% | 44.7% | 67.6% | $19,109 | $7,345 | unknown | 0.0% | Comparator |
| Tiered standardization | 91.7% | 88.1% | 21.5% | $24,527 | $7,875 | 27.2% | 0.0% | Comparator |
| Guardrailed recovery | 100.0% | 100.0% | 0.0% | $29,104 | $10,835 | 27.4% | 99.6% | Shadow-validation candidate |
| Recovery first | 100.0% | 54.8% | 0.0% | $49,632 | $1,595 | 63.3% | 100.0% | Comparator |
| Intelligent generosity | 100.0% | 64.8% | 0.0% | $39,010 | $1,300 | 57.7% | 100.0% | Comparator |

## Decision Rule

A policy can advance to shadow validation only when at least 80% of assumption-stress draws satisfy all declared guardrails: at least 90% of evaluable cases receive either an adequate gesture or explicit manager review, no more than 5% of high-risk cases are both inadequate and unreviewed, no more than 2% operational infeasibility, complete data-hold compliance, and complete tier-5 manager review.

Safe recovery path counts an adequate gesture or an explicit manager-review path. Gesture fit evaluates the proposed gesture alone.

Guardrailed recovery is deliberately an adequacy-constrained cost optimizer. Its advantage is therefore a decision-analysis result under the declared fit and cost assumptions, not independent evidence of superior guest outcomes.

Among qualifying policies, the decision rule selects the lowest median modeled internal cost. Policies within 1% are resolved by lower direct-refund exposure and then lower manager-review burden.

## Statistical Evidence

- Paired case bootstrap draws: `10000`
- Shared-world assumption-stress draws: `5000`
- Bootstrap intervals describe synthetic case-mix variability, not sampling uncertainty for Proper Hotels.
- Each stress draw applies the same recovery-weight, gesture-fit, occupancy-pressure, and comp-cost realization to every policy before comparison.
- Synthetic post-stay scores are excluded because their generator does not include a comp-treatment effect.

## Selected Policy Tradeoff

- Selected policy: **Guardrailed recovery**
- Safe recovery-path coverage: `100.0%`
- Strict gesture adequacy before manager review: `100.0%`
- High-risk under-recovery: `0.0%`
- Modeled midpoint internal cost: `$29,104`
- Cost uncertainty range (5th-95th percentile): `$27,342-$33,944`
- Direct room-refund face-value exposure: `$10,835`
- Manager-review rate: `27.4%`
- Assumption-stress guardrail pass rate: `99.6%`

## Proposed Shadow Validation

1. Run shadow mode for four weeks or 50 eligible cases, whichever is later.
2. Validate reservation and CRM matching, property-reviewed marginal-cost ranges, manager override capture, and complete outcome instrumentation.
3. Calculate the controlled-phase sample requirement from shadow event volume, outcome variance, baseline recovery, and a pre-specified minimum detectable effect.
4. Randomize policy-eligible cases between usual manager judgment and decision support. Tier-5 and low-confidence cases always remain manager-controlled.
5. Measure post-recovery satisfaction, resolution time, actual marginal cost, room refunds, overrides, reviews, and repeat stays before any permanent policy decision.

## Model Improvement After Controlled-Test Data

Fit a Bayesian hierarchical recovery-outcome model with partial pooling by issue type, manager, guest segment, and operating conditions. Use posterior probabilities to evaluate whether decision support preserves guest recovery while reducing cost or room-rate erosion. Until those outcomes exist, the project remains a robust policy simulation rather than an empirically optimized comp model.
