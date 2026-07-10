# External Context Model Impact

This report tests whether public context changes recommendations in controlled scenarios.

The goal is bounded decision usefulness: public context should influence recommendations when it maps to comp fit, opportunity cost, reputation risk, or local demand pressure.

- Comparisons tested: `5`
- Recommendations changed by context: `4`

| Signal | Control recommendation | Context recommendation | Value delta | Interpretation |
| --- | --- | --- | ---: | --- |
| public_rate_pressure | room_upgrade ($360) | rooftop_f_and_b_credit ($180) | $-180 | High public rate pressure should protect room inventory value and can shift recovery away from upgrades. |
| property_fit | late_checkout ($85) | room_upgrade ($300) | $215 | Public property context should strengthen room/experience gestures when demand pressure is low enough to make them operationally plausible. |
| review_risk_prior | rooftop_f_and_b_credit ($150) | future_stay_credit ($245) | $95 | Issue categories with higher reputation sensitivity should increase recovery strength. |
| local_demand_pressure | room_upgrade ($360) | rooftop_f_and_b_credit ($180) | $-180 | External demand pressure should make room-based gestures more expensive and strengthen lower-margin alternatives. |
| spa_wellness_fit | spa_wellness_credit ($330) | spa_wellness_credit ($330) | $0 | A property with strong wellness context should make spa/wellness recovery more defensible. |

## Decision Standard

- Public context should never replace internal hotel data.
- Public context should be visible in reason codes when it affects a recommendation.
- If context is weak or sample-seed only, confidence should be lower and the model should remain conservative.
