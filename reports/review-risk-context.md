# Review Risk Context

This layer maps public review themes or review-taxonomy priors to service-failure risk.

It is not actual post-recovery satisfaction, guest lifetime value, or Proper Hotels internal reputation monitoring.

## Source Summary

- Observed public context count across categories: `0`
- Sample-seed context count across categories: `2190`

## Highest Review-Risk Priors

| Failure category | Prior | Themes |
| --- | ---: | --- |
| `room_readiness_delay` | 0.74 | rooms;service;arrival |
| `housekeeping_miss` | 0.72 | rooms;cleanliness;service |
| `maintenance_issue` | 0.69 | rooms;maintenance;amenities |
| `room_assignment_expectation_gap` | 0.68 | rooms;expectations;service |
| `spa_wellness_service_issue` | 0.64 | spa;wellness;amenities |

## Decision Use

- Calibrate issue-level review risk rather than treating every issue type the same.
- Increase recovery need when a failure category has high reputation sensitivity.
- Reduce confidence when only sample-seed context is available.
