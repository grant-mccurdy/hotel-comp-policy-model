from __future__ import annotations

from typing import Any

from common import (
    CLOUD_EXECUTION_EVIDENCE_PATH,
    POLICY_CASE_COMPARISON_PATH,
    POLICY_DECISION_SUMMARY_PATH,
    PROJECT_ROOT,
    REPORT_DIR,
    read_csv_rows,
    read_json,
    sha256_file,
)
from load_snowflake_warehouse import (
    CSV_TABLES,
    SNOWFLAKE_MART_TYPE_CONTRACT_PATH,
    VIEW_OBJECTS,
    column_definitions,
    csv_row_count,
)
from stakeholder_report import policy_summary_rows


ENGINEERING_EVIDENCE_REPORT = REPORT_DIR / "engineering-evidence.md"
S3_DATALAKE_MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "s3_datalake_manifest.json"


def s3_manifest_matches_local(evidence: dict[str, Any]) -> bool:
    if not S3_DATALAKE_MANIFEST_PATH.exists():
        return False
    manifest = read_json(S3_DATALAKE_MANIFEST_PATH)
    if manifest.get("run_id") != evidence.get("source_run_id"):
        return False
    entries = manifest.get("entries", [])
    if len(entries) != len(CSV_TABLES):
        return False
    for entry in entries:
        path = PROJECT_ROOT / entry["local_path"]
        if not path.exists() or sha256_file(path) != entry.get("sha256"):
            return False
    return True


def current_cloud_status(evidence: dict[str, Any] | None) -> tuple[bool, str]:
    if evidence is None:
        return False, "No verified cloud execution manifest is available."
    _, local_summary = read_csv_rows(POLICY_DECISION_SUMMARY_PATH)
    selected = next(row for row in local_summary if row["selected_for_pilot"] == "true")
    current = (
        int(evidence.get("source_and_model_tables", -1)) == len(CSV_TABLES)
        and int(evidence.get("analytics_views", -1)) == len(VIEW_OBJECTS)
        and int(evidence.get("case_policy_rows", -1)) == csv_row_count(POLICY_CASE_COMPARISON_PATH)
        and evidence.get("comparison_version") == selected["comparison_version"]
        and evidence.get("selected_policy_id") == selected["policy_id"]
        and int(evidence.get("checks_failed", -1)) == 0
        and s3_manifest_matches_local(evidence)
    )
    if current:
        return True, "Current policy build is validated in Snowflake."
    return False, "The recorded cloud run does not match the current policy build."


def typed_mart_counts() -> tuple[int, int]:
    typed = 0
    total = 0
    for schema, _table, path, _description in CSV_TABLES:
        if schema != "MARTS":
            continue
        definitions = column_definitions(schema, path)
        total += len(definitions)
        typed += sum(snowflake_type != "VARCHAR" for _column, snowflake_type in definitions)
    return typed, total


def render_engineering_evidence() -> str:
    evidence = (
        read_json(CLOUD_EXECUTION_EVIDENCE_PATH)
        if CLOUD_EXECUTION_EVIDENCE_PATH.exists()
        else None
    )
    cloud_current, cloud_status = current_cloud_status(evidence)
    type_contract = read_json(SNOWFLAKE_MART_TYPE_CONTRACT_PATH)
    typed_columns, mart_columns = typed_mart_counts()
    summary_rows, decision_provenance = policy_summary_rows()
    selected = next(row for row in summary_rows if row["selected_for_pilot"] == "true")
    raw_tables = sum(schema == "RAW" for schema, _table, _path, _description in CSV_TABLES)
    model_tables = sum(schema == "MARTS" for schema, _table, _path, _description in CSV_TABLES)
    cloud_label = "PASS - current" if cloud_current else "NOT CURRENT"
    decision_source = (
        "Snowflake decision-view extract with exact local-mart parity"
        if decision_provenance.get("parity_verified")
        else "Versioned local mart; Snowflake extract not current or unavailable"
    )
    load_method = evidence.get("load_method", "not verified") if evidence else "not verified"
    validated_at = evidence.get("validated_at", "not verified") if evidence else "not verified"
    checks_passed = evidence.get("checks_passed", 0) if evidence else 0
    checks_failed = evidence.get("checks_failed", 0) if evidence else 0
    semantic_checks = evidence.get("semantic_checks", 0) if evidence else 0

    return "\n".join(
        [
            "# Engineering Evidence",
            "",
            "This appendix shows how the static executive decision is produced, validated, and kept traceable. It is supporting evidence for the decision product, not a claim that cloud infrastructure improves the synthetic model's statistical validity.",
            "",
            "> **Evidence boundary:** operating records and policy outcomes are synthetic. Account, bucket, role, credential, and guest identifiers are intentionally omitted.",
            "",
            "## Decision Lineage",
            "",
            "```text",
            "synthetic PMS / CRM / service / comp / POS / survey / operations",
            "+ bounded public property, pricing, review, and demand context",
            "        |",
            "        v",
            "S3 landing/{run_id}              source-faithful, versioned snapshots",
            "        |",
            "        v",
            "Snowflake RAW                    source-shaped VARCHAR ingestion",
            "        |",
            "        v",
            "Python policy engine             bootstrap, policy comparison, sensitivity",
            "        |",
            "        v",
            "S3 model-output/{run_id}         versioned statistical outputs",
            "        |",
            "        v",
            "Snowflake typed MARTS / AUDIT    decision views and quality controls",
            "        |",
            "        v",
            "parity-checked extract           static executive decision brief",
            "```",
            "",
            "Python remains responsible for the paired bootstrap and coherent shared-world assumption stress test. Snowflake is responsible for typed persistence, SQL serving views, reconciliation, and decision-semantic validation.",
            "",
            "## Verified Execution",
            "",
            f"- Cloud status: **{cloud_label}** - {cloud_status}",
            f"- Last validated at: `{validated_at}`",
            f"- Load method: `{load_method}`",
            f"- Source/context tables: `{raw_tables}`",
            f"- Model and decision tables: `{model_tables}`",
            f"- Analytic and audit views: `{len(VIEW_OBJECTS)}`",
            f"- Structural and semantic checks passed: `{checks_passed}`; failed: `{checks_failed}`",
            f"- Decision-semantic checks: `{semantic_checks}`",
            f"- Case-policy rows: `{csv_row_count(POLICY_CASE_COMPARISON_PATH)}`",
            f"- Candidate policies: `{len(summary_rows)}`",
            f"- Selected shadow-validation candidate: `{selected['policy_label']}`",
            f"- Published decision source: `{decision_source}`",
            "",
            "## Data Contracts And Quality Gates",
            "",
            f"The curated Snowflake layer uses `{type_contract['contract_name']}:{type_contract['version']}`. `{typed_columns}` of `{mart_columns}` MARTS columns are explicitly numeric, Boolean, or date types; identifiers, labels, explanations, and provenance remain text.",
            "",
            "Validation covers:",
            "",
            "- Local-to-Snowflake row parity for every table.",
            "- Queryability of every MARTS and AUDIT view.",
            "- One selected policy and five complete candidate-policy outputs.",
            "- Complete case-policy grain with no duplicate case-policy keys.",
            "- Simulation-rate bounds and low/mid/high cost ordering.",
            "- Selected-policy and executive-metric parity.",
            "- Data-hold, tier-five review, high-risk recovery, and feasibility guardrails.",
            "- Typed MARTS fields and small-group suppression behavior.",
            "",
            "## Security And Cost Controls",
            "",
            "| Control | Implementation |",
            "| --- | --- |",
            "| Public access | S3 public access is blocked; no cloud resources are exposed by the report. |",
            "| Encryption | S3 objects use server-side encryption and bucket versioning. |",
            "| AWS access | Snowflake assumes a prefix-scoped IAM role with an external ID. |",
            "| Snowflake access | Project-scoped role; credentials and connection files stay outside Git. |",
            "| Compute cost | X-Small warehouse with auto-resume and 60-second auto-suspend. |",
            "| Reproducibility | Run IDs, row counts, hashes, contracts, and sanitized validation evidence. |",
            "| Automation | Local tests run independently; cloud validation is deliberately manually triggered to control credentials and cost. |",
            "",
            "## Reproducible Paths",
            "",
            "```bash",
            "make local-all       # credential-free DuckDB path",
            "make enterprise-all  # S3 -> Snowflake -> validated extracts -> reports",
            "```",
            "",
            "The default report remains static so a stakeholder does not need cloud credentials or a running warehouse. A validated extract is materialized before publication.",
            "",
            "## Deliberate Limitations",
            "",
            "- The dataset is small; S3 and Snowflake support lineage and production-shaped workflow rather than computational scale.",
            "- Loads currently publish complete versioned snapshots instead of incremental change-data capture.",
            "- Statistical policy outputs are produced in Python and then governed in Snowflake; they are not reimplemented in SQL.",
            "- No real hotel operating data, internal cost, policy, or guest outcome enters this workflow.",
            "",
            "## Reviewable Implementation",
            "",
            "- S3 publisher: `scripts/publish_s3_datalake.py`",
            "- S3-to-Snowflake loader: `scripts/load_snowflake_from_s3.py`",
            "- Snowflake loader and validation: `scripts/load_snowflake_warehouse.py`",
            "- Analytic views: `sql/snowflake/02_create_views.sql`",
            "- Cloud workflow: `.github/workflows/snowflake-validation.yml`",
            "- Warehouse type contract: `data/contracts/snowflake_mart_types.json`",
            "",
        ]
    )


def write_engineering_evidence() -> None:
    ENGINEERING_EVIDENCE_REPORT.write_text(render_engineering_evidence(), encoding="utf-8")
    print(f"Wrote engineering evidence: {ENGINEERING_EVIDENCE_REPORT.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    write_engineering_evidence()
