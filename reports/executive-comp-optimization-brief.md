# Service Recovery Decision Brief

## Executive Decision

Adopt a tiered service-recovery policy that preserves managerial judgment while standardizing three decisions: how much recovery is justified, which gesture best fits the failure, and when weak data or high exposure requires review.

The target is intelligent generosity, not minimum comp spend. High-perceived-value property experiences should be considered before direct room-rate erosion when they fit the failure and operational conditions.

> **Evidence boundary:** all operating cases and historical comp actions in this run are synthetic. Counts below demonstrate workflow behavior; they are not Proper Hotels findings or projected savings.

## Illustrative Policy Run

| Signal | Synthetic result | Management use |
| --- | ---: | --- |
| Service-failure cases scored | 430 | Demonstrates batch decisioning |
| Median recommendation stability | 100% | Identifies decisions robust to ±20% parameter changes |
| Manager-review cases | 22 | Preserves human approval for high-exposure decisions |
| Low-confidence cases | 12 | Avoids false certainty |
| Data-quality holds | 12 | Prevents weak joins from becoming manager or guest judgments |
| Direct room refunds | 5 | Reserves rate erosion for severe cases |
| Estimated internal-cost range | $21,864-$61,817 | Shows assumption uncertainty; midpoint $39,807 |

## Simulated Policy Audit

| Audit class | Cases | Intended decision |
| --- | ---: | --- |
| Under-recovered | 117 | Consider a stronger or better-timed gesture |
| Potentially over-comped | 21 | Review consistency and estimated cost |
| Aligned recovery | 270 | Preserve the simulated policy decision |
| Manager review | 10 | Require human approval |
| Data-quality hold | 12 | Resolve source matching first |

These classes compare one synthetic historical policy with the proposed simulated policy. They demonstrate the audit mechanism, not observed leakage or recovered profit.

## Property-Relevant Evidence

- Official Santa Monica Proper public anchors: `11`
- Public property/competitive-set profiles: `5`
- Pricing context mode: `reproducible sample-seed stress test`
- Controlled context comparisons changing a recommendation: `4/5`
- Review-risk context rows: `10`; local-demand context rows: `365`

Official public sources establish that property-aligned recovery can include Palma or Calabra dining, Surya Spa or Recovery Suite experiences, late checkout, destination-fee relief, valet relief, and room-category gestures. Public prices anchor guest-facing denominations only; they do not reveal contribution margin.

## Example Decision

**Recommended recovery:** $220 Calabra or Palma dining credit + manager note

- Working internal-cost range: `$55-$132`
- Approval path: `Manager approval`
- Decision robustness: `93% of assumption checks keep this gesture`
- What would change it: `If room availability were less constrained, the preferred recovery would shift to room upgrade at $435.`

For a loyalty guest facing a severity-4, hotel-responsible room-readiness delay, the policy favors a property-aligned dining credit over immediate room-rate erosion. The decision protects an important guest relationship while the stay can still be recovered, and manager approval remains part of the path.

## Recommended Operating Design

- Auto-recommend only when source matching, policy stability, and operational availability are adequate.
- Require manager approval for severe failures, high guest-facing value, unstable recommendations, or repeat-comp pattern review.
- Record accepted, rejected, and overridden recommendations with reason codes.
- Measure post-recovery satisfaction, review outcome, repeat stay, and actual marginal cost before training an outcome model.
- Treat public rate, property, review, and demand context as bounded supplements to internal systems.

## Data Required For A Pilot

- Historical comp actions, approval notes, policy versions, and manager overrides.
- Post-recovery satisfaction, review outcomes, repeat stays, and cancellations.
- Contribution-margin ranges by comp type.
- Live occupancy, inventory, outlet capacity, staffing, and room-type constraints.
- A jointly reviewed severity, responsibility, and approval taxonomy.

## Illustrative Recovery Mix

| Gesture | Cases |
| --- | ---: |
| Calabra or Palma dining credit | 183 |
| Surya Spa or Recovery Suite credit | 94 |
| room upgrade | 53 |
| parking or destination-fee waiver | 42 |
| future-stay credit | 37 |
| late checkout | 16 |
| partial room refund | 5 |
