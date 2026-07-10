# Luxury Hotel Service Recovery Discussion Brief

## Purpose

This prototype demonstrates how fragmented hotel operating data could support more consistent, explainable comp decisions while preserving luxury hospitality and manager judgment.

It uses synthetic PMS, CRM, service, comp, POS, survey, and operational data plus bounded public Santa Monica property context. It does not use Proper Hotels internal data or policy.

## Decision Product

For each service failure, the system recommends a recovery gesture and amount, estimated cost range, manager-review path, two alternatives, decision stability, and a counterfactual explanation.

**Example:** $220 Calabra or Palma dining credit + manager note with a working cost range of $55-$132.

For a loyalty guest facing a severity-4, hotel-responsible room-readiness delay, the policy favors a property-aligned dining credit over immediate room-rate erosion. The recommendation requires manager approval and would shift to a room upgrade if room availability were less constrained.

## What Is Demonstrated

- Multi-source reconciliation and source-match confidence.
- Versioned policy assumptions and observed-public provenance.
- Cost ranges and parameter sensitivity instead of false precision.
- Human review for high-exposure or low-confidence decisions.
- `11` official-property public anchors for option fit and guest-facing value.
- A simulated audit with `10` manager-review and `12` data-hold cases.

## Production Conversation

The next step would be a data and policy workshop: map actual comp actions and costs, define severity and responsibility rubrics, identify post-recovery outcomes, and determine which decisions should be recommended, escalated, or held.
