# Engineering Evidence

This appendix shows how the static executive decision is produced, validated, and kept traceable. It is supporting evidence for the decision product, not a claim that cloud infrastructure improves the synthetic model's statistical validity.

> **Evidence boundary:** operating records and policy outcomes are synthetic. Account, bucket, role, credential, and guest identifiers are intentionally omitted.

## Decision Lineage

```text
synthetic PMS / CRM / service / comp / POS / survey / operations
+ bounded public property, pricing, review, and demand context
        |
        v
S3 landing/{run_id}              source-faithful, versioned snapshots
        |
        v
Snowflake RAW                    source-shaped VARCHAR ingestion
        |
        v
Python policy engine             bootstrap, policy comparison, sensitivity
        |
        v
S3 model-output/{run_id}         versioned statistical outputs
        |
        v
Snowflake typed MARTS / AUDIT    decision views and quality controls
        |
        v
parity-checked extract           static executive decision brief
```

Python remains responsible for the paired bootstrap and coherent shared-world assumption stress test. Snowflake is responsible for typed persistence, SQL serving views, reconciliation, and decision-semantic validation.

## Verified Execution

- Cloud status: **NOT CURRENT** - The recorded cloud run does not match the current policy build.
- Last validated at: `2026-07-14T17:08:17+00:00`
- Load method: `s3_external_stage_copy_into`
- Source/context tables: `12`
- Model and decision tables: `10`
- Analytic and audit views: `12`
- Structural and semantic checks passed: `46`; failed: `0`
- Decision-semantic checks: `12`
- Case-policy rows: `2150`
- Candidate policies: `5`
- Selected shadow-validation candidate: `Guardrailed recovery`
- Published decision source: `Versioned local mart; Snowflake extract not current or unavailable`

## Operational Decision Runtime

The manager-facing prototype uses the same deterministic Python decision modules as the offline comparison workflow. A generated, checksummed bundle freezes the selected rule, catalog, guardrails, and provenance for the Worker; generated module hashes prevent the edge runtime from quietly drifting away from the canonical source.

- Runtime bundle: `comp-decision-runtime-v1.0.0`
- Evidence class: `synthetic_workflow_demonstration`
- Bundle checksum: `d8087159e84597e8a4ba46703db4fba67081dd3faaad8363389fa2561d84aac0` (PASS)
- Canonical-to-Worker source parity: **PASS** across `8` modules
- Frozen shadow candidate: `Guardrailed recovery`
- Public persistence control: **PASS - disabled and unbound**
- Public API: `POST /v1/recommend` accepts bounded synthetic incident fields and returns the recommendation contract.
- Optional intake API: `POST /v1/intake/parse` maps synthetic narrative into suggested fields only; the manager must confirm those fields before scoring.
- Recommendation authority: deterministic policy code. The language model does not select or price the gesture.
- Future shadow logging: an append-only D1 migration is versioned for review but is not bound to the public Worker.

## Data Contracts And Quality Gates

The curated Snowflake layer uses `snowflake_mart_types:v1`. `253` of `360` MARTS columns are explicitly numeric, Boolean, or date types; identifiers, labels, explanations, and provenance remain text.

Validation covers:

- Local-to-Snowflake row parity for every table.
- Queryability of every MARTS and AUDIT view.
- One selected policy and five complete candidate-policy outputs.
- Complete case-policy grain with no duplicate case-policy keys.
- Simulation-rate bounds and low/mid/high cost ordering.
- Selected-policy and executive-metric parity.
- Data-hold, tier-five review, high-risk recovery, and feasibility guardrails.
- Typed MARTS fields and small-group suppression behavior.

## Security And Cost Controls

| Control | Implementation |
| --- | --- |
| Public access | S3 public access is blocked; no cloud resources are exposed by the report. |
| Encryption | S3 objects use server-side encryption and bucket versioning. |
| AWS access | Snowflake assumes a prefix-scoped IAM role with an external ID. |
| Snowflake access | Project-scoped role; credentials and connection files stay outside Git. |
| Compute cost | X-Small warehouse with auto-resume and 60-second auto-suspend. |
| Reproducibility | Run IDs, row counts, hashes, contracts, and sanitized validation evidence. |
| Automation | Local tests run independently; cloud validation is deliberately manually triggered to control credentials and cost. |

## Reproducible Paths

```bash
make local-all       # credential-free DuckDB path
make enterprise-all  # S3 -> Snowflake -> validated extracts -> reports
```

The default report remains static so a stakeholder does not need cloud credentials or a running warehouse. A validated extract is materialized before publication.

## Deliberate Limitations

- The dataset is small; S3 and Snowflake support lineage and production-shaped workflow rather than computational scale.
- Loads publish complete versioned snapshots instead of incremental change-data capture.
- Statistical policy outputs are produced in Python and then governed in Snowflake; they are not reimplemented in SQL.
- No real hotel operating data, internal cost, policy, or guest outcome enters this workflow.

## Reviewable Implementation

- S3 publisher: `scripts/publish_s3_datalake.py`
- S3-to-Snowflake loader: `scripts/load_snowflake_from_s3.py`
- Snowflake loader and validation: `scripts/load_snowflake_warehouse.py`
- Analytic views: `sql/snowflake/02_create_views.sql`
- Cloud workflow: `.github/workflows/snowflake-validation.yml`
- Warehouse type contract: `data/contracts/snowflake_mart_types.json`
- Runtime bundle builder: `scripts/build_runtime_policy_bundle.py`
- Canonical recommendation service: `scripts/decision_service.py`
- Worker entry point: `cloudflare/src/entry.py`
- Runtime/API contract tests: `tests/test_decision_service.py`, `tests/test_intake_contract.py`, and `tests/test_worker_assets.py`
