# Local Demand Context

This layer provides daily event/weather pressure proxies for external demand context.

The current version is sample-seed context, not observed occupancy, internal revenue, or live event/weather truth.

## Source Summary

- Context dates: `365`
- High local-demand dates: `5`
- Strongest context date: `2026-07-03`
- Strongest local demand pressure: `0.769`
- Strongest context label: `holiday_coastal_demand`

## Decision Use

- Add external pressure to room-upgrade and late-checkout opportunity-cost reasoning.
- Support explanation when the model preserves room inventory value.
- Keep the distinction clear between public demand context and true hotel occupancy.
