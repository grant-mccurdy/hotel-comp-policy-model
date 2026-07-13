# Context-Aware Comparator Recommendations

These synthetic cases demonstrate the context-aware Intelligent Generosity comparator. They are supporting model diagnostics, not the generated shadow-policy recommendations.
No Proper Hotels guest records, comp history, internal rates, margins, inventory, or proprietary policy are used.

## Scenario 1: Housekeeping Miss

**Recommended recovery:** $210 partial room refund

- Guest context: `loyalty guest` / `wellness getaway`
- Stay value: `$4,340`; estimated relationship value: `$24,010`
- Severity: `5/5`; hotel responsibility: `0.95`
- Estimated internal-cost range: `$210-$210`
- Decision confidence: `high`; stability: `96%`
- Manager review required: `true`
- Closest alternatives: `$220 Calabra or Palma dining credit, $400 Surya Spa or Recovery Suite credit`
- Decision-changing counterfactual: `No tested context removal changed the gesture.`

Recommend $210 partial room refund for a loyalty guest with a severity 5 housekeeping miss reported after checkout. Estimated internal cost is $210-$210, not an observed property margin. Rationale: high guest relationship value, hotel responsible failure, high severity issue, high review risk. Recommendation stability is 96%. The closest alternative was $220 Calabra or Palma dining credit; the recommended gesture scored better on recovery fit, estimated cost, and operational constraints.

## Scenario 2: Spa/Wellness Service Issue

**Recommended recovery:** $400 Surya Spa or Recovery Suite credit

- Guest context: `new guest` / `business traveler`
- Stay value: `$2,440`; estimated relationship value: `$5,360`
- Severity: `5/5`; hotel responsibility: `0.79`
- Estimated internal-cost range: `$120-$300`
- Decision confidence: `high`; stability: `100%`
- Manager review required: `true`
- Closest alternatives: `$220 Calabra or Palma dining credit, $215 future-stay credit`
- Decision-changing counterfactual: `No tested context removal changed the gesture.`

Recommend $400 Surya Spa or Recovery Suite credit for a new guest with a severity 5 spa/wellness service issue reported after checkout. Estimated internal cost is $120-$300, not an observed property margin. Rationale: hotel responsible failure, high severity issue, high perceived value lower estimated cost, manager review required. Recommendation stability is 100%. The closest alternative was $220 Calabra or Palma dining credit; the recommended gesture scored better on recovery fit, estimated cost, and operational constraints.

## Scenario 3: Housekeeping Miss

**Recommended recovery:** $255 future-stay credit

- Guest context: `new guest` / `wellness getaway`
- Stay value: `$4,380`; estimated relationship value: `$7,440`
- Severity: `5/5`; hotel responsibility: `0.95`
- Estimated internal-cost range: `$76-$217`
- Decision confidence: `high`; stability: `96%`
- Manager review required: `true`
- Closest alternatives: `$220 Calabra or Palma dining credit, $400 Surya Spa or Recovery Suite credit`
- Decision-changing counterfactual: `No tested context removal changed the gesture.`

Recommend $255 future-stay credit for a new guest with a severity 5 housekeeping miss reported before checkout. Estimated internal cost is $76-$217, not an observed property margin. Rationale: hotel responsible failure, high severity issue, high review risk, recoverable before checkout. Recommendation stability is 96%. The closest alternative was $220 Calabra or Palma dining credit; the recommended gesture scored better on recovery fit, estimated cost, and operational constraints.

## Scenario 4: Room Readiness Delay

**Recommended recovery:** $360 room upgrade

- Guest context: `new guest` / `local staycation`
- Stay value: `$4,260`; estimated relationship value: `$7,668`
- Severity: `5/5`; hotel responsibility: `0.93`
- Estimated internal-cost range: `$29-$234`
- Decision confidence: `moderate`; stability: `100%`
- Manager review required: `false`
- Closest alternatives: `$180 Calabra or Palma dining credit, $100 late checkout`
- Decision-changing counterfactual: `No tested context removal changed the gesture.`

Recommend $360 room upgrade for a new guest with a severity 5 room readiness delay reported before checkout. Estimated internal cost is $29-$234, not an observed property margin. Rationale: hotel responsible failure, high severity issue, recoverable before checkout, high perceived value lower estimated cost. Recommendation stability is 100%. The closest alternative was $180 Calabra or Palma dining credit; the recommended gesture scored better on recovery fit, estimated cost, and operational constraints.

## Scenario 5: Housekeeping Miss

**Recommended recovery:** $180 Calabra or Palma dining credit

- Guest context: `new guest` / `design leisure`
- Stay value: `$1,120`; estimated relationship value: `$2,016`
- Severity: `5/5`; hotel responsibility: `0.95`
- Estimated internal-cost range: `$45-$108`
- Decision confidence: `moderate`; stability: `100%`
- Manager review required: `false`
- Closest alternatives: `$330 Surya Spa or Recovery Suite credit, $120 Palma lounge credit`
- Decision-changing counterfactual: `No tested context removal changed the gesture.`

Recommend $180 Calabra or Palma dining credit for a new guest with a severity 5 housekeeping miss reported before checkout. Estimated internal cost is $45-$108, not an observed property margin. Rationale: hotel responsible failure, high severity issue, high review risk, recoverable before checkout. Recommendation stability is 100%. The closest alternative was $330 Surya Spa or Recovery Suite credit; the recommended gesture scored better on recovery fit, estimated cost, and operational constraints.

## Scenario 6: Billing Or Fee Dispute

**Recommended recovery:** $100 parking or destination-fee waiver

- Guest context: `new guest` / `local staycation`
- Stay value: `$4,200`; estimated relationship value: `$8,590`
- Severity: `4/5`; hotel responsibility: `0.6`
- Estimated internal-cost range: `$8-$35`
- Decision confidence: `high`; stability: `89%`
- Manager review required: `false`
- Closest alternatives: `$210 future-stay credit, $180 Calabra or Palma dining credit`
- Decision-changing counterfactual: `No tested context removal changed the gesture.`

Recommend $100 parking or destination-fee waiver for a new guest with a severity 4 billing or fee dispute reported after checkout. Estimated internal cost is $8-$35, not an observed property margin. Rationale: high severity issue, high perceived value lower estimated cost. Recommendation stability is 89%. The closest alternative was $210 future-stay credit; the recommended gesture scored better on recovery fit, estimated cost, and operational constraints.

## Scenario 7: Room Readiness Delay

**Recommended recovery:** $100 late checkout

- Guest context: `loyalty guest` / `design leisure`
- Stay value: `$790`; estimated relationship value: `$4,520`
- Severity: `3/5`; hotel responsibility: `0.88`
- Estimated internal-cost range: `$8-$45`
- Decision confidence: `high`; stability: `89%`
- Manager review required: `false`
- Closest alternatives: `$180 Calabra or Palma dining credit, $275 future-stay credit`
- Decision-changing counterfactual: `Operational availability changed the recommendation: without this signal, the model would prefer room upgrade at $360.`

Recommend $100 late checkout for a loyalty guest with a severity 3 room readiness delay reported before checkout. Estimated internal cost is $8-$45, not an observed property margin. Rationale: high guest relationship value, hotel responsible failure, recoverable before checkout, high perceived value lower estimated cost. Recommendation stability is 89%. The closest alternative was $180 Calabra or Palma dining credit; the recommended gesture scored better on recovery fit, estimated cost, and operational constraints.
