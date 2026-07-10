# Five-Minute Demonstration

## 1. Stakeholder Decision Report

Open `index.html`.

Start with the operating recommendation, then use the arrival-delay and valet-delay scenarios. The proposed decision is a tiered service-recovery policy: standardize gesture selection and escalation while preserving manager approval for severe, costly, unstable, repeat-pattern, or low-confidence cases.

## 2. Operating Data

Show `reports/source-system-quality-report.md` and `reports/data-lineage.md`.

The workflow reconciles synthetic PMS, CRM, service-ticket, comp-ledger, POS, review/survey, and daily-operations extracts. Missing identifiers, duplicate profiles, dirty labels, delayed records, and low-confidence matches remain visible.

## 3. Public Property Context

Open `reports/proper-public-context.md`.

Official Santa Monica Proper pages establish plausible recovery options and guest-facing value anchors. They do not provide internal cost, margin, inventory, or policy.

## 4. Manager Decision Desk

```bash
python3 scripts/manager_app.py
```

Open `http://127.0.0.1:8765` and choose the arrival-delay preset. Review the recommendation, estimated cost range, manager approval, alternatives, stability, and operational counterfactual.

## 5. Model Trust

Open `reports/policy-sensitivity.md` and `reports/comp-model-validation.md`.

Explain that high stability means the gesture survived tested ±20% policy perturbations. It does not mean the gesture is empirically optimal. Real outcomes are required for outcome validation.

## Close

Return to the pilot section in `index.html`. The proposed next step is a data and policy workshop covering historical comps, manager overrides, severity definitions, marginal costs, inventory constraints, and measurable post-recovery outcomes.
