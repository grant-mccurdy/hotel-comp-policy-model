# Snowflake Query Extracts

Generated at: `2026-07-10T18:05:56+00:00`

These extracts prove that the project warehouse is being queried from Snowflake, not only loaded there.

The CSV extracts are local execution artifacts under `data/warehouse/snowflake_extracts/` and are ignored by Git. Reviewable lineage remains in this Markdown report.

| Extract | Snowflake view | Rows | Purpose |
| --- | --- | ---: | --- |
| `data/warehouse/snowflake_extracts/comp_decision_summary.csv` | `MARTS.VW_COMP_DECISION_SUMMARY` | 1 | Executive decision summary used to verify value, cost, recovery, and review volume in Snowflake. |
| `data/warehouse/snowflake_extracts/comp_mix.csv` | `MARTS.VW_COMP_MIX` | 7 | Comp-type mix by cases, guest-facing value, and estimated internal cost. |
| `data/warehouse/snowflake_extracts/manager_review_queue.csv` | `MARTS.VW_MANAGER_REVIEW_QUEUE` | 154 | Manager review queue for escalation and low-confidence data matches. |
| `data/warehouse/snowflake_extracts/audit_decision_signal.csv` | `AUDIT.VW_AUDIT_DECISION_SIGNAL` | 5 | Audit-class rollup for under-recovery, over-comping, manager review, and data-quality holds. |
| `data/warehouse/snowflake_extracts/source_quality_snapshot.csv` | `AUDIT.VW_SOURCE_QUALITY_SNAPSHOT` | 5 | Source-quality snapshot showing messy-data conditions surfaced in Snowflake. |
| `data/warehouse/snowflake_extracts/external_context_sources.csv` | `AUDIT.VW_EXTERNAL_CONTEXT_SOURCES` | 5 | External-context source row counts loaded to Snowflake. |
| `data/warehouse/snowflake_extracts/external_context_model_impact.csv` | `MARTS.VW_EXTERNAL_CONTEXT_MODEL_IMPACT` | 5 | Controlled checks showing whether public context changed recommendations. |

## Workflow Role

The Snowflake-centered path is:

```text
public-safe CSV artifacts
-> RAW and MARTS tables
-> MARTS and AUDIT views
-> query extracts and validation reports
-> executive and manager-facing artifacts
```

DuckDB remains a local fallback for users without Snowflake credentials.
