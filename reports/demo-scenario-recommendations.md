# Demo Scenario Recommendations

These named synthetic scenarios are designed for a short manager/executive walkthrough of the comp policy model.

No Proper Hotels data, internal rates, guest records, comp history, or proprietary policy is used.

## scenario_01: High-value repeat guest waits for room

**Recommended comp:** $220 Calabra or Palma dining credit + manager note

- Guest: `loyalty guest` / `coastal weekend`
- Stay value: `$2,800`; estimated lifetime value: `$14,000`
- Issue: `room readiness delay`; severity `4/5`; hotel responsibility `0.9`
- Review risk: `0.8`; brand-impact risk: `0.788`
- Estimated internal cost range: `$55-$132`
- Decision confidence: `high`; stability: `93%`
- Manager review required: `true`
- Policy version: `smp-public-context-v1.0.0`
- Scenario note: Classic high-review-risk arrival recovery case
- Reason codes: `high guest relationship value, hotel responsible failure, high severity issue, high review risk, recoverable before checkout, high perceived value lower estimated cost, manager review required, operational pressure changed recovery`
- Counterfactuals: `Operational availability changed the recommendation: without this signal, the model would prefer room upgrade at $435.`

Recommend $220 Calabra or Palma dining credit for a loyalty guest with a severity 4 room readiness delay reported before checkout. Estimated internal cost is $55-$132, not an observed property margin. Rationale: high guest relationship value, hotel responsible failure, high severity issue, high review risk. Recommendation stability is 93%. The closest alternative was $435 room upgrade; the recommended gesture scored better on recovery fit, estimated cost, and operational constraints.

## scenario_02: Rooftop dining service lapse for returning guest

**Recommended comp:** $180 Calabra or Palma dining credit + manager note

- Guest: `returning guest` / `design leisure`
- Stay value: `$1,800`; estimated lifetime value: `$7,200`
- Issue: `F&B service lapse`; severity `4/5`; hotel responsibility `0.78`
- Review risk: `0.66`; brand-impact risk: `0.67`
- Estimated internal cost range: `$45-$108`
- Decision confidence: `high`; stability: `100%`
- Manager review required: `false`
- Policy version: `smp-public-context-v1.0.0`
- Scenario note: Hospitality-preserving F&B credit should beat a refund
- Reason codes: `hotel responsible failure, high severity issue, recoverable before checkout, high perceived value lower estimated cost`
- Counterfactuals: `No tested context signal changed the selected gesture.`

Recommend $180 Calabra or Palma dining credit for a returning guest with a severity 4 F&B service lapse reported before checkout. Estimated internal cost is $45-$108, not an observed property margin. Rationale: hotel responsible failure, high severity issue, recoverable before checkout, high perceived value lower estimated cost. Recommendation stability is 100%. The closest alternative was $210 future-stay credit; the recommended gesture scored better on recovery fit, estimated cost, and operational constraints.

## scenario_03: Spa wellness miss after checkout

**Recommended comp:** $400 Surya Spa or Recovery Suite credit + manager note

- Guest: `new guest` / `wellness getaway`
- Stay value: `$2,400`; estimated lifetime value: `$5,200`
- Issue: `spa/wellness service issue`; severity `5/5`; hotel responsibility `0.82`
- Review risk: `0.78`; brand-impact risk: `0.792`
- Estimated internal cost range: `$120-$300`
- Decision confidence: `high`; stability: `100%`
- Manager review required: `true`
- Policy version: `smp-public-context-v1.0.0`
- Scenario note: Delayed recovery with wellness-specific comp
- Reason codes: `hotel responsible failure, high severity issue, high review risk, high perceived value lower estimated cost, manager review required`
- Counterfactuals: `No tested context signal changed the selected gesture.`

Recommend $400 Surya Spa or Recovery Suite credit for a new guest with a severity 5 spa/wellness service issue reported after checkout. Estimated internal cost is $120-$300, not an observed property margin. Rationale: hotel responsible failure, high severity issue, high review risk, high perceived value lower estimated cost. Recommendation stability is 100%. The closest alternative was $280 future-stay credit; the recommended gesture scored better on recovery fit, estimated cost, and operational constraints.

## scenario_04: Valet delay for loyalty guest

**Recommended comp:** $100 parking or destination-fee waiver + manager note

- Guest: `loyalty guest` / `local staycation`
- Stay value: `$1,600`; estimated lifetime value: `$9,000`
- Issue: `valet or parking delay`; severity `3/5`; hotel responsibility `0.72`
- Review risk: `0.58`; brand-impact risk: `0.587`
- Estimated internal cost range: `$8-$35`
- Decision confidence: `high`; stability: `100%`
- Manager review required: `false`
- Policy version: `smp-public-context-v1.0.0`
- Scenario note: Parking/fee waiver fit case
- Reason codes: `high guest relationship value, hotel responsible failure, recoverable before checkout, high perceived value lower estimated cost`
- Counterfactuals: `No tested context signal changed the selected gesture.`

Recommend $100 parking or destination-fee waiver for a loyalty guest with a severity 3 valet or parking delay reported before checkout. Estimated internal cost is $8-$35, not an observed property margin. Rationale: high guest relationship value, hotel responsible failure, recoverable before checkout, high perceived value lower estimated cost. Recommendation stability is 100%. The closest alternative was $180 Calabra or Palma dining credit; the recommended gesture scored better on recovery fit, estimated cost, and operational constraints.

## scenario_05: Housekeeping miss for VIP suite guest

**Recommended comp:** $440 partial room refund + manager note

- Guest: `vip guest` / `event/suite guest`
- Stay value: `$5,200`; estimated lifetime value: `$32,000`
- Issue: `housekeeping miss`; severity `5/5`; hotel responsibility `0.95`
- Review risk: `0.9`; brand-impact risk: `0.902`
- Estimated internal cost range: `$440-$440`
- Decision confidence: `high`; stability: `96%`
- Manager review required: `true`
- Policy version: `smp-public-context-v1.0.0`
- Scenario note: Severe hotel-responsible case needing manager review
- Reason codes: `high guest relationship value, hotel responsible failure, high severity issue, high review risk, recoverable before checkout, manager review required`
- Counterfactuals: `No tested context signal changed the selected gesture.`

Recommend $440 partial room refund for a vip guest with a severity 5 housekeeping miss reported before checkout. Estimated internal cost is $440-$440, not an observed property margin. Rationale: high guest relationship value, hotel responsible failure, high severity issue, high review risk. Recommendation stability is 96%. The closest alternative was $455 future-stay credit; the recommended gesture scored better on recovery fit, estimated cost, and operational constraints.

## scenario_06: Billing dispute with repeat comp pattern

**Recommended comp:** $85 parking or destination-fee waiver + manager note

- Guest: `returning guest` / `business traveler`
- Stay value: `$1,450`; estimated lifetime value: `$6,200`
- Issue: `billing or fee dispute`; severity `3/5`; hotel responsibility `0.55`
- Review risk: `0.52`; brand-impact risk: `0.528`
- Estimated internal cost range: `$7-$30`
- Decision confidence: `high`; stability: `100%`
- Manager review required: `true`
- Policy version: `smp-public-context-v1.0.0`
- Scenario note: Prior comp pattern requires manager review rather than an automatic decision
- Reason codes: `recoverable before checkout, high perceived value lower estimated cost, repeat comp pattern review needed, manager review required`
- Counterfactuals: `No tested context signal changed the selected gesture.`

Recommend $85 parking or destination-fee waiver for a returning guest with a severity 3 billing or fee dispute reported before checkout. Estimated internal cost is $7-$30, not an observed property margin. Rationale: recoverable before checkout, high perceived value lower estimated cost, repeat comp pattern review needed, manager review required. Recommendation stability is 100%. The closest alternative was $100 Palma lounge credit; the recommended gesture scored better on recovery fit, estimated cost, and operational constraints.

## scenario_07: Light noise disruption when occupancy allows late checkout

**Recommended comp:** $75 late checkout

- Guest: `new guest` / `coastal weekend`
- Stay value: `$1,200`; estimated lifetime value: `$2,500`
- Issue: `noise disruption`; severity `2/5`; hotel responsibility `0.15`
- Review risk: `0.25`; brand-impact risk: `0.285`
- Estimated internal cost range: `$6-$34`
- Decision confidence: `high`; stability: `100%`
- Manager review required: `false`
- Policy version: `smp-public-context-v1.0.0`
- Scenario note: Low-severity recovery where late checkout can preserve goodwill without high comp cost
- Reason codes: `recoverable before checkout, high perceived value lower estimated cost`
- Counterfactuals: `No tested context signal changed the selected gesture.`

Recommend $75 late checkout for a new guest with a severity 2 noise disruption reported before checkout. Estimated internal cost is $6-$34, not an observed property margin. Rationale: recoverable before checkout, high perceived value lower estimated cost. Recommendation stability is 100%. The closest alternative was $135 Calabra or Palma dining credit; the recommended gesture scored better on recovery fit, estimated cost, and operational constraints.

## scenario_08: Room assignment gap on special occasion

**Recommended comp:** $435 room upgrade + manager note

- Guest: `event/suite guest` / `coastal weekend`
- Stay value: `$4,400`; estimated lifetime value: `$26,000`
- Issue: `room assignment expectation gap`; severity `4/5`; hotel responsibility `0.8`
- Review risk: `0.72`; brand-impact risk: `0.743`
- Estimated internal cost range: `$35-$283`
- Decision confidence: `high`; stability: `100%`
- Manager review required: `true`
- Policy version: `smp-public-context-v1.0.0`
- Scenario note: Upgrade-forward recovery case
- Reason codes: `high guest relationship value, hotel responsible failure, high severity issue, high review risk, recoverable before checkout, high perceived value lower estimated cost, manager review required`
- Counterfactuals: `No tested context signal changed the selected gesture.`

Recommend $435 room upgrade for an event/suite guest with a severity 4 room assignment expectation gap reported before checkout. Estimated internal cost is $35-$283, not an observed property margin. Rationale: high guest relationship value, hotel responsible failure, high severity issue, high review risk. Recommendation stability is 100%. The closest alternative was $385 future-stay credit; the recommended gesture scored better on recovery fit, estimated cost, and operational constraints.

## scenario_09: Minor billing friction for first-time guest

**Recommended comp:** $75 parking or destination-fee waiver

- Guest: `new guest` / `design leisure`
- Stay value: `$900`; estimated lifetime value: `$1,600`
- Issue: `billing or fee dispute`; severity `1/5`; hotel responsibility `0.2`
- Review risk: `0.25`; brand-impact risk: `0.26`
- Estimated internal cost range: `$6-$26`
- Decision confidence: `high`; stability: `96%`
- Manager review required: `false`
- Policy version: `smp-public-context-v1.0.0`
- Scenario note: Low-cost fee-waiver case that avoids over-refunding a modest issue
- Reason codes: `recoverable before checkout, high perceived value lower estimated cost`
- Counterfactuals: `No tested context signal changed the selected gesture.`

Recommend $75 parking or destination-fee waiver for a new guest with a severity 1 billing or fee dispute reported before checkout. Estimated internal cost is $6-$26, not an observed property margin. Rationale: recoverable before checkout, high perceived value lower estimated cost. Recommendation stability is 96%. The closest alternative was $135 Calabra or Palma dining credit; the recommended gesture scored better on recovery fit, estimated cost, and operational constraints.

## scenario_10: Severe room readiness issue after checkout

**Recommended comp:** $330 partial room refund + manager note

- Guest: `vip guest` / `business traveler`
- Stay value: `$3,900`; estimated lifetime value: `$24,000`
- Issue: `room readiness delay`; severity `5/5`; hotel responsibility `0.95`
- Review risk: `0.9`; brand-impact risk: `0.917`
- Estimated internal cost range: `$330-$330`
- Decision confidence: `high`; stability: `100%`
- Manager review required: `true`
- Policy version: `smp-public-context-v1.0.0`
- Scenario note: Rare partial-refund or future-stay-credit edge case
- Reason codes: `high guest relationship value, hotel responsible failure, high severity issue, high review risk, manager review required`
- Counterfactuals: `No tested context signal changed the selected gesture.`

Recommend $330 partial room refund for a vip guest with a severity 5 room readiness delay reported after checkout. Estimated internal cost is $330-$330, not an observed property margin. Rationale: high guest relationship value, hotel responsible failure, high severity issue, high review risk. Recommendation stability is 100%. The closest alternative was $340 future-stay credit; the recommended gesture scored better on recovery fit, estimated cost, and operational constraints.
