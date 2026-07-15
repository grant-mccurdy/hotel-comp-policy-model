# Hotel Comp Decision Engine

A focused work sample for one luxury-hotel operating question:

> How can managers choose the right gesture for the guest and situation while making cost, constraints, and reasoning visible?

The operating principle is **intelligent generosity**: protect the guest relationship and brand experience while making recovery consistency, operational constraints, and cost visible.

## Business Task

Comp decisions must balance the seriousness of the failure, hotel responsibility, guest relationship, recovery timing, operational availability, and the cost of the gesture. The goal is not to minimize comps. It is to make a well-matched recovery decision consistently and explainably.

## Proposed Product

Build a manager-facing **Comp Decision Engine**. The engine establishes a minimum recovery obligation from the failure, filters out inadequate or unavailable gestures, and ranks the remaining options with cost and reasoning visible. Guest relationship value may add generosity but cannot reduce what the service failure warrants.

The current implementation demonstrates the recommendation contract and the method for deciding whether a real model improves on current manager judgment. It does not use synthetic policy rankings as evidence for a property decision.

## Start Here

1. Read the [stakeholder brief](https://grant-mccurdy.github.io/projects/hotel-comp-policy-model/) or [PDF](reports/hotel-comp-decision-framework.pdf).
2. Review the worked recommendation and the real-data model-selection standard.
3. Use the [manager decision desk guide](reports/manager-demo-guide.md) to run the synthetic prototype.

The report is the primary deliverable. The decision desk proves the product concept. Statistical simulation, data engineering, cloud infrastructure, and API implementation are supporting evidence.

## Example Manager Decision

```text
Recommended recovery: late checkout ($100 modeled guest-facing value)
Assumed internal cost range: $8-$45
Input-sensitivity stability: high
Manager review required: no

Why:
- serious hotel-responsible room-readiness delay
- recovery can still occur during the stay
- clears the configured recovery-fit floor
- lower modeled cost than a direct refund
```

## Scope Control

| Priority | Included work |
| --- | --- |
| Primary | Stakeholder brief, business question, proposed decision product, worked recommendation, real-data comparison method, focused next step |
| Supporting | Synthetic source systems, statistical policy simulation, runtime API, tests, data lineage, S3/Snowflake workflow, and deployment architecture |
| Deferred | Live hotel integrations, production deployment, persistent operational logging, and retrieval over approved internal policies |

New work should strengthen the primary deliverable or provide evidence directly supporting it. Infrastructure expansion is out of scope until the stakeholder brief and product demonstration are accepted.

## Recommendation Contract

The versioned manager output includes:

- recovery gesture and guest-facing amount;
- estimated internal-cost range;
- service-recovery floor, relationship adjustment, recovery tier, and manager-review flag;
- two nearest alternatives;
- reason codes and conditions requiring confirmation;
- delivery timing, hospitality-note template, manager-review path, and policy ID;
- runtime and model version identifiers;
- explicit assumptions and unavailable internal inputs.

Invalid probabilities, negative values, impossible severity, unknown categories, and unknown gesture codes are rejected before scoring. Explicit availability controls prevent the engine from selecting an unavailable gesture.

## How The Real Model Would Be Chosen

With actual property data, compare four approaches on the same future-dated cases:

1. Current manager judgment.
2. Explicit and transparent recovery rules.
3. An interpretable statistical model.
4. A nonlinear benchmark such as boosted trees.

Estimate satisfaction recovery, review risk, repeat-stay behavior, marginal cost, and operational feasibility separately. Compare temporal holdout performance, calibration, paired uncertainty, recovery safeguards, segment behavior, manager override patterns, decision speed, and usability. Historical actions are not automatically causal; shadow observation or a controlled test is required where comparable treatment overlap is weak.

## Evidence Boundary

All operating records, comp history, guest values, margins, and outcomes are synthetic. Official Santa Monica Proper pages provide bounded public context for available experiences and guest-facing value anchors. The project does not use or claim access to Proper Hotels internal data, policy, inventory, rates, margins, or guest records.

Public prices do not reveal contribution margin. Internal-cost ranges remain declared assumptions until property accounting data are available.

## Run Locally

On Debian or Ubuntu, install virtual-environment support once if `python3 -m venv` reports that `ensurepip` is unavailable:

```bash
sudo apt-get install python3-venv
```

Install [Quarto](https://quarto.org/docs/get-started/) and R, then create the isolated Python environment and restore the versioned R packages:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
Rscript -e 'if (!requireNamespace("renv", quietly = TRUE)) install.packages("renv"); renv::restore(prompt = FALSE)'
make PYTHON=.venv/bin/python local-all
```

Preview the primary stakeholder report:

```bash
python3 -m http.server 8000
```

Open `http://127.0.0.1:8000`. The root `index.html` is the stakeholder brief, and the PDF is written to `reports/hotel-comp-decision-framework.pdf`.

Run the supporting decision desk locally after installing [`uv`](https://docs.astral.sh/uv/):

```bash
make PYTHON=.venv/bin/python runtime-bundle
cd cloudflare
uv run pywrangler dev
```

The local interface serves the guided synthetic decision desk and recommendation API. It is supporting product evidence, not the primary stakeholder deliverable. See the [decision-engine architecture](docs/decision-engine-architecture.md).

## Validation

```bash
make PYTHON=.venv/bin/python test
make PYTHON=.venv/bin/python validate
make PYTHON=.venv/bin/python public-audit
```

Validation covers input boundaries, deterministic output, recovery-floor independence from guest value, explicit gesture availability, severity monotonicity, operational constraints, complete case-policy grain, policy-order-invariant shared sensitivity draws, generated rather than hardcoded shadow selection, runtime-bundle parity, narrative-source fencing, PII rejection, missing-baseline treatment, uncertainty bounds, small-group suppression, data contracts, source-system messiness, and public-release safety.

## Supporting Technical Evidence

- [Decision-engine architecture](docs/decision-engine-architecture.md)
- [Policy selection technical appendix](reports/policy-selection-technical-appendix.qmd)
- [Generated policy decision analysis](reports/policy-decision-analysis.md)
- [Assumption-stress analysis](reports/policy-sensitivity.md)
- [Data lineage](reports/data-lineage.md)
- [Engineering and warehouse evidence](reports/engineering-evidence.md)
- [Official-property public context](reports/proper-public-context.md)

The synthetic data pipeline intentionally includes missing identifiers, duplicate CRM profiles, dirty labels, delayed records, and orphaned transactions. The S3/Snowflake and edge-runtime implementations demonstrate reproducibility and production-shaped engineering; they do not change the stakeholder conclusion.

## Project Boundary

This is a decision-product and model-comparison prototype, not an empirically optimized property policy. Property calibration requires actual comp actions, manager overrides, post-recovery satisfaction, review outcomes, repeat stays, marginal costs, live operational constraints, and approved recovery policy.
