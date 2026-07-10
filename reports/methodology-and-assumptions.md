# Methodology And Assumptions

## Decision Frame

This is an explainable policy simulation. The model asks:

> Given a service failure, guest relationship, operational constraints, and source-data confidence, what recovery gesture best protects the guest relationship without creating unnecessary cost or room-rate erosion?

The target is intelligent generosity, not comp minimization.

## Evidence Classes

| Evidence | Use |
| --- | --- |
| Observed public booking data | Shapes synthetic booking and stay context |
| Official Santa Monica Proper public facts | Establishes property-fit and guest-facing value anchors |
| Sample-seed public context | Stress-tests pricing, review-risk, and demand logic |
| Synthetic operating systems | Demonstrates reconciliation, decisioning, and audit workflow |
| Policy assumptions | Defines weights, thresholds, cost ranges, and option scoring |
| Internal unavailable data | Prevents unsupported claims about margins, outcomes, inventory, or policy |

The current policy is `smp-public-context-v1.0.0` in `config/policy.v1.json`.

## Input Validation

One scenario contract validates the batch pipeline, CLI, HTML interface, and JSON endpoint. Probabilities must be between zero and one, severity must be a whole number from one through five, monetary values must be nonnegative, and unknown categories are rejected.

Derived fields such as guest-value score are calculated consistently. Missing or inferred source values remain visible through data-quality flags.

## Policy Logic

1. Calculate recovery need from severity, hotel responsibility, reputation risk, guest value, sentiment, delay, recovery timing, and issue baseline. Losing the in-stay recovery window raises timing risk; it does not reduce the measured need.
2. Convert recovery need into a five-tier policy band.
3. Score eligible gestures by issue fit, perceived guest value, estimated cost range, property fit, room availability, public-rate pressure, and repeat-comp pattern review. Room upgrades and late checkout are unavailable after checkout.
4. Return the top gesture, two alternatives, manager-review decision, and policy version.
5. Remove important context signals one at a time. Report a context reason only when the selected gesture changes.
6. Rescore under ±20% perturbations to fit, cost, occupancy, external context, the overall recovery-need scale, and each individual recovery-need weight. Report the share preserving the selected gesture as stability.

## Cost And Value

Guest-facing values can be anchored to published fees, credits, and wellness values. Internal marginal cost cannot be inferred from public price.

Each gesture therefore carries low, midpoint, and high internal-cost assumptions. These ranges support sensitivity analysis; they are not Proper Hotels accounting estimates.

The modeled recovery-value field is also policy-simulated. It should not be interpreted as causal revenue protected or projected return on comp spend.

## Explainability

Direct reasons identify policy factors such as high severity or clear hotel responsibility. Context reasons require a changed counterfactual. For example:

```text
Operational availability changed the recommendation:
without this signal, the model would prefer a room upgrade.
```

High stability means the decision survives tested parameter changes. It does not mean the decision is empirically optimal.

## Simulated Policy Audit

The historical comp ledger is synthetic. Audit classes such as under-recovered, over-comped, aligned, manager review, and data-quality hold demonstrate how a real historical policy could be reviewed. Their counts and dollar values are not observed findings.

## Research Anchors

- Hart, Heskett, and Sasser, [The Profitable Art of Service Recovery](https://hbr.org/1990/07/the-profitable-art-of-service-recovery).
- de Matos, Henrique, and Rossi, [Service Recovery Paradox: A Meta-Analysis](https://doi.org/10.1177/1094670507303012).
- Tax, Brown, and Chandrashekaran, [Customer Evaluations of Service Complaint Experiences](https://doi.org/10.1177/002224299806200205).
- Vargas-Calderon et al., [Review-Based Quality-of-Service Framework](https://arxiv.org/abs/2107.10328).

These sources motivate disciplined recovery, fairness, timing, and review signals. They do not provide property-specific policy weights.

## Production Requirements

- Historical actions, approvals, policy versions, and manager overrides.
- Post-recovery satisfaction, review, repeat-stay, and cancellation outcomes.
- Marginal-cost ranges by gesture.
- Live occupancy, inventory, room type, outlet, staffing, and timing constraints.
- Jointly reviewed severity, responsibility, and escalation definitions.
- Prospective monitoring before any automated decisioning.
