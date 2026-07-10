# Policy Sensitivity And Stability

This report stress-tests a synthetic policy simulation. It does not validate business outcomes or estimate causal recovery effects.

## Stability Summary

- Cases evaluated: `430`
- Median recommendation stability: `100.0%`
- High-confidence cases: `285`
- Moderate-confidence cases: `133`
- Low-confidence cases: `12`
- Cases where a tested context removal changed the gesture: `83`
- Cases below 60% stability: `2`
- Most common gesture: `rooftop_f_and_b_credit` (42.6%)

Each recommendation is rescored under ±20% perturbations to fit, cost, occupancy, context, the overall recovery-need scale, and every individual recovery-need weight. Stability is the share of perturbations that preserve the selected gesture.

## Cost Uncertainty

| Measure | Synthetic run |
| --- | ---: |
| Low estimated internal-cost bound | $21,864 |
| Midpoint policy estimate | $39,807 |
| High estimated internal-cost bound | $61,817 |
| Cases where midpoint cost exceeds modeled recovery value | 35 |

The range is intentional. Public prices can anchor guest-facing value, but property contribution margin remains unavailable.

## Stability By Guest Context

| Guest context | Cases | Average stability | Low-confidence cases |
| --- | ---: | ---: | ---: |
| event or suite guest | 10 | 93.7% | 1 |
| loyalty guest | 59 | 96.4% | 3 |
| new guest | 229 | 97.3% | 6 |
| returning guest | 100 | 97.1% | 1 |
| vip guest | 32 | 98.4% | 1 |

## Lowest-Stability Cases

| Case | Issue | Recommendation | Stability | Alternatives |
| --- | --- | --- | ---: | --- |
| `case_00209` | room readiness delay | room upgrade | 55.6% | late checkout, Calabra or Palma dining credit |
| `case_00220` | room readiness delay | future-stay credit | 59.3% | Calabra or Palma dining credit, late checkout |
| `case_00286` | room readiness delay | late checkout | 63.0% | room upgrade, Calabra or Palma dining credit |
| `case_00083` | noise disruption | late checkout | 66.7% | Calabra or Palma dining credit, Palma lounge credit |
| `case_00353` | noise disruption | Surya Spa or Recovery Suite credit | 66.7% | Calabra or Palma dining credit, Palma lounge credit |
| `case_00377` | room readiness delay | room upgrade | 66.7% | late checkout, future-stay credit |
| `case_00397` | noise disruption | Calabra or Palma dining credit | 66.7% | Palma lounge credit, in-room amenity gesture |
| `case_00170` | room readiness delay | room upgrade | 77.8% | late checkout, Calabra or Palma dining credit |
| `case_00193` | housekeeping miss | future-stay credit | 77.8% | Calabra or Palma dining credit, Surya Spa or Recovery Suite credit |
| `case_00314` | room readiness delay | room upgrade | 77.8% | late checkout, Calabra or Palma dining credit |

## Interpretation

- High stability means the selected gesture survives the tested policy perturbations; it does not mean the gesture is empirically optimal.
- Low stability should trigger manager review and parameter discussion rather than a stronger automated claim.
- Real comp decisions, overrides, satisfaction recovery, reviews, and repeat-stay outcomes are required for outcome validation.
