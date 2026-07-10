# AGENTS.md

## Project Purpose

Build an explainable luxury-hotel service-recovery policy prototype using
synthetic operating data and bounded public property context.

## Evidence Boundary

- Never claim access to Proper Hotels internal data, policy, rates, inventory,
  costs, margins, guest records, comp history, or outcomes.
- Label synthetic operating results as workflow demonstrations, not business
  findings, savings, or causal effects.
- Public property prices may anchor guest-facing value only. They do not reveal
  internal marginal cost.
- Preserve provenance and confidence fields through all downstream artifacts.

## Required Checks

Before proposing a commit or release, run:

```bash
make test
make local-all
make public-audit
```

Review the canonical stakeholder report, manager interface, generated executive
brief, policy sensitivity report, and public-release audit. Do not commit or
push without explicit user approval.
