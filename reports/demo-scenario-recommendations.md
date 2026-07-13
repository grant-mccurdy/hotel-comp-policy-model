# Demo Scenario Recommendations

These named synthetic scenarios demonstrate recommendations from the generated shadow-validation candidate.

No Proper Hotels data, internal rates, guest records, comp history, or proprietary policy is used.

## scenario_01: High-value repeat guest waits for room

**Recommended comp:** $240 partial room refund + manager note

- Guest: `loyalty guest` / `coastal weekend`
- Stay value: `$2,800`; estimated lifetime value: `$14,000`
- Issue: `room readiness delay`; severity `4/5`; hotel responsibility `0.9`
- Estimated internal cost range: `$240-$240`
- Policy assumption-stress pass rate: `99.6%`
- Manager review required: `true`
- Policy: `Guardrailed recovery` (`cost_guardrail`)
- Comparison version: `comp-policy-comparison-v1.0.0`
- Scenario note: Classic high-review-risk arrival recovery case
- Reason codes: `tier appropriate recovery, lowest cost robust fit, manager review required, hotel responsible failure`
- Confirm before use: `Confirm actual gesture availability and marginal cost before approval. | Record the manager decision, override reason, and guest response for controlled-test evaluation.`

Guardrailed recovery first requires a tier-appropriate, robust-fit recovery path, then selects the lowest modeled-cost eligible gesture. Manager review remains required when exposure, fit, or operating conditions warrant it.

## scenario_02: Rooftop dining service lapse for returning guest

**Recommended comp:** $180 Calabra or Palma dining credit + manager note

- Guest: `returning guest` / `design leisure`
- Stay value: `$1,800`; estimated lifetime value: `$7,200`
- Issue: `F&B service lapse`; severity `4/5`; hotel responsibility `0.78`
- Estimated internal cost range: `$45-$108`
- Policy assumption-stress pass rate: `99.6%`
- Manager review required: `false`
- Policy: `Guardrailed recovery` (`cost_guardrail`)
- Comparison version: `comp-policy-comparison-v1.0.0`
- Scenario note: Hospitality-preserving F&B credit should beat a refund
- Reason codes: `tier appropriate recovery, lowest cost robust fit, hotel responsible failure`
- Confirm before use: `Confirm actual gesture availability and marginal cost before approval. | Record the manager decision, override reason, and guest response for controlled-test evaluation.`

Guardrailed recovery first requires a tier-appropriate, robust-fit recovery path, then selects the lowest modeled-cost eligible gesture. Manager review remains required when exposure, fit, or operating conditions warrant it.

## scenario_03: Spa wellness miss after checkout

**Recommended comp:** $400 Surya Spa or Recovery Suite credit + manager note

- Guest: `new guest` / `wellness getaway`
- Stay value: `$2,400`; estimated lifetime value: `$5,200`
- Issue: `spa/wellness service issue`; severity `5/5`; hotel responsibility `0.82`
- Estimated internal cost range: `$120-$300`
- Policy assumption-stress pass rate: `99.6%`
- Manager review required: `true`
- Policy: `Guardrailed recovery` (`cost_guardrail`)
- Comparison version: `comp-policy-comparison-v1.0.0`
- Scenario note: Delayed recovery with wellness-specific comp
- Reason codes: `tier appropriate recovery, lowest cost robust fit, manager review required, hotel responsible failure`
- Confirm before use: `Confirm actual gesture availability and marginal cost before approval. | Record the manager decision, override reason, and guest response for controlled-test evaluation.`

Guardrailed recovery first requires a tier-appropriate, robust-fit recovery path, then selects the lowest modeled-cost eligible gesture. Manager review remains required when exposure, fit, or operating conditions warrant it.

## scenario_04: Valet delay for loyalty guest

**Recommended comp:** $100 parking or destination-fee waiver + manager note

- Guest: `loyalty guest` / `local staycation`
- Stay value: `$1,600`; estimated lifetime value: `$9,000`
- Issue: `valet or parking delay`; severity `3/5`; hotel responsibility `0.72`
- Estimated internal cost range: `$8-$35`
- Policy assumption-stress pass rate: `99.6%`
- Manager review required: `false`
- Policy: `Guardrailed recovery` (`cost_guardrail`)
- Comparison version: `comp-policy-comparison-v1.0.0`
- Scenario note: Parking/fee waiver fit case
- Reason codes: `tier appropriate recovery, lowest cost robust fit, hotel responsible failure`
- Confirm before use: `Confirm actual gesture availability and marginal cost before approval. | Record the manager decision, override reason, and guest response for controlled-test evaluation.`

Guardrailed recovery first requires a tier-appropriate, robust-fit recovery path, then selects the lowest modeled-cost eligible gesture. Manager review remains required when exposure, fit, or operating conditions warrant it.

## scenario_05: Housekeeping miss for VIP suite guest

**Recommended comp:** $455 future-stay credit + manager note

- Guest: `vip guest` / `event/suite guest`
- Stay value: `$5,200`; estimated lifetime value: `$32,000`
- Issue: `housekeeping miss`; severity `5/5`; hotel responsibility `0.95`
- Estimated internal cost range: `$136-$387`
- Policy assumption-stress pass rate: `99.6%`
- Manager review required: `true`
- Policy: `Guardrailed recovery` (`cost_guardrail`)
- Comparison version: `comp-policy-comparison-v1.0.0`
- Scenario note: Severe hotel-responsible case needing manager review
- Reason codes: `tier appropriate recovery, lowest cost robust fit, manager review required, hotel responsible failure`
- Confirm before use: `Confirm actual gesture availability and marginal cost before approval. | Record the manager decision, override reason, and guest response for controlled-test evaluation.`

Guardrailed recovery first requires a tier-appropriate, robust-fit recovery path, then selects the lowest modeled-cost eligible gesture. Manager review remains required when exposure, fit, or operating conditions warrant it.

## scenario_06: Billing dispute with repeat comp pattern

**Recommended comp:** $0 manager note and personal follow-up

- Guest: `returning guest` / `business traveler`
- Stay value: `$1,450`; estimated lifetime value: `$6,200`
- Issue: `billing or fee dispute`; severity `3/5`; hotel responsibility `0.55`
- Estimated internal cost range: `$0-$0`
- Policy assumption-stress pass rate: `99.6%`
- Manager review required: `true`
- Policy: `Guardrailed recovery` (`cost_guardrail`)
- Comparison version: `comp-policy-comparison-v1.0.0`
- Scenario note: Prior comp pattern requires manager review rather than an automatic decision
- Reason codes: `tier appropriate recovery, lowest cost robust fit, manager review required, fit uncertainty requires review`
- Confirm before use: `Confirm actual gesture availability and marginal cost before approval. | Record the manager decision, override reason, and guest response for controlled-test evaluation.`

Guardrailed recovery first requires a tier-appropriate, robust-fit recovery path, then selects the lowest modeled-cost eligible gesture. Manager review remains required when exposure, fit, or operating conditions warrant it.

## scenario_07: Light noise disruption when occupancy allows late checkout

**Recommended comp:** $75 late checkout

- Guest: `new guest` / `coastal weekend`
- Stay value: `$1,200`; estimated lifetime value: `$2,500`
- Issue: `noise disruption`; severity `2/5`; hotel responsibility `0.15`
- Estimated internal cost range: `$6-$34`
- Policy assumption-stress pass rate: `99.6%`
- Manager review required: `false`
- Policy: `Guardrailed recovery` (`cost_guardrail`)
- Comparison version: `comp-policy-comparison-v1.0.0`
- Scenario note: Low-severity recovery where late checkout can preserve goodwill without high comp cost
- Reason codes: `tier appropriate recovery, lowest cost robust fit`
- Confirm before use: `Confirm actual gesture availability and marginal cost before approval. | Record the manager decision, override reason, and guest response for controlled-test evaluation.`

Guardrailed recovery first requires a tier-appropriate, robust-fit recovery path, then selects the lowest modeled-cost eligible gesture. Manager review remains required when exposure, fit, or operating conditions warrant it.

## scenario_08: Room assignment gap on special occasion

**Recommended comp:** $435 room upgrade + manager note

- Guest: `event/suite guest` / `coastal weekend`
- Stay value: `$4,400`; estimated lifetime value: `$26,000`
- Issue: `room assignment expectation gap`; severity `4/5`; hotel responsibility `0.8`
- Estimated internal cost range: `$35-$283`
- Policy assumption-stress pass rate: `99.6%`
- Manager review required: `true`
- Policy: `Guardrailed recovery` (`cost_guardrail`)
- Comparison version: `comp-policy-comparison-v1.0.0`
- Scenario note: Upgrade-forward recovery case
- Reason codes: `tier appropriate recovery, lowest cost robust fit, manager review required, hotel responsible failure`
- Confirm before use: `Confirm actual gesture availability and marginal cost before approval. | Record the manager decision, override reason, and guest response for controlled-test evaluation.`

Guardrailed recovery first requires a tier-appropriate, robust-fit recovery path, then selects the lowest modeled-cost eligible gesture. Manager review remains required when exposure, fit, or operating conditions warrant it.

## scenario_09: Minor billing friction for first-time guest

**Recommended comp:** $0 manager note and personal follow-up

- Guest: `new guest` / `design leisure`
- Stay value: `$900`; estimated lifetime value: `$1,600`
- Issue: `billing or fee dispute`; severity `1/5`; hotel responsibility `0.2`
- Estimated internal cost range: `$0-$0`
- Policy assumption-stress pass rate: `99.6%`
- Manager review required: `true`
- Policy: `Guardrailed recovery` (`cost_guardrail`)
- Comparison version: `comp-policy-comparison-v1.0.0`
- Scenario note: Low-cost fee-waiver case that avoids over-refunding a modest issue
- Reason codes: `tier appropriate recovery, lowest cost robust fit, manager review required, fit uncertainty requires review`
- Confirm before use: `Confirm actual gesture availability and marginal cost before approval. | Record the manager decision, override reason, and guest response for controlled-test evaluation.`

Guardrailed recovery first requires a tier-appropriate, robust-fit recovery path, then selects the lowest modeled-cost eligible gesture. Manager review remains required when exposure, fit, or operating conditions warrant it.

## scenario_10: Severe room readiness issue after checkout

**Recommended comp:** $330 partial room refund + manager note

- Guest: `vip guest` / `business traveler`
- Stay value: `$3,900`; estimated lifetime value: `$24,000`
- Issue: `room readiness delay`; severity `5/5`; hotel responsibility `0.95`
- Estimated internal cost range: `$330-$330`
- Policy assumption-stress pass rate: `99.6%`
- Manager review required: `true`
- Policy: `Guardrailed recovery` (`cost_guardrail`)
- Comparison version: `comp-policy-comparison-v1.0.0`
- Scenario note: Rare partial-refund or future-stay-credit edge case
- Reason codes: `tier appropriate recovery, lowest cost robust fit, manager review required, hotel responsible failure`
- Confirm before use: `Confirm actual gesture availability and marginal cost before approval. | Record the manager decision, override reason, and guest response for controlled-test evaluation.`

Guardrailed recovery first requires a tier-appropriate, robust-fit recovery path, then selects the lowest modeled-cost eligible gesture. Manager review remains required when exposure, fit, or operating conditions warrant it.
