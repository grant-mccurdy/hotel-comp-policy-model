from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from common import PROJECT_ROOT, REPORT_DIR, WAREHOUSE_DIR, ensure_dirs, utc_now_iso
from load_snowflake_warehouse import connector_connection


SNOWFLAKE_EXTRACT_DIR = WAREHOUSE_DIR / "snowflake_extracts"
SNOWFLAKE_EXTRACT_REPORT = REPORT_DIR / "snowflake-query-extracts.md"

QUERY_EXPORTS = [
    (
        "comp_decision_summary",
        "MARTS.VW_COMP_DECISION_SUMMARY",
        "Executive decision summary used to verify value, cost, recovery, and review volume in Snowflake.",
    ),
    (
        "comp_mix",
        "MARTS.VW_COMP_MIX",
        "Comp-type mix by cases, guest-facing value, and estimated internal cost.",
    ),
    (
        "manager_review_queue",
        "MARTS.VW_MANAGER_REVIEW_QUEUE",
        "Manager review queue for escalation and low-confidence data matches.",
    ),
    (
        "audit_decision_signal",
        "AUDIT.VW_AUDIT_DECISION_SIGNAL",
        "Audit-class rollup for under-recovery, over-comping, manager review, and data-quality holds.",
    ),
    (
        "source_quality_snapshot",
        "AUDIT.VW_SOURCE_QUALITY_SNAPSHOT",
        "Source-quality snapshot showing messy-data conditions surfaced in Snowflake.",
    ),
    (
        "external_context_sources",
        "AUDIT.VW_EXTERNAL_CONTEXT_SOURCES",
        "External-context source row counts loaded to Snowflake.",
    ),
    (
        "external_context_model_impact",
        "MARTS.VW_EXTERNAL_CONTEXT_MODEL_IMPACT",
        "Controlled checks showing whether public context changed recommendations.",
    ),
]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if rows:
        fieldnames = list(rows[0].keys())
    else:
        fieldnames = ["NO_ROWS"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def fetch_view_rows(connection: Any, view_name: str) -> list[dict[str, Any]]:
    cursor = connection.cursor()
    try:
        cursor.execute(f"SELECT * FROM {view_name};")
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
        cursor.close()


def extract_view(connection: Any, name: str, view_name: str) -> tuple[Path, int]:
    rows = fetch_view_rows(connection, view_name)
    path = SNOWFLAKE_EXTRACT_DIR / f"{name}.csv"
    write_csv(path, rows)
    return path, len(rows)


def render_report(results: list[dict[str, Any]]) -> str:
    lines = [
        "# Snowflake Query Extracts",
        "",
        f"Generated at: `{utc_now_iso()}`",
        "",
        "These extracts prove that the project warehouse is being queried from Snowflake, not only loaded there.",
        "",
        "The CSV extracts are local execution artifacts under `data/warehouse/snowflake_extracts/` and are ignored by Git. Reviewable lineage remains in this Markdown report.",
        "",
        "| Extract | Snowflake view | Rows | Purpose |",
        "| --- | --- | ---: | --- |",
    ]
    for result in results:
        lines.append(
            f"| `{result['path']}` | `{result['view_name']}` | {result['rows']} | {result['description']} |"
        )
    lines.extend(
        [
            "",
            "## Workflow Role",
            "",
            "The Snowflake-centered path is:",
            "",
            "```text",
            "public-safe CSV artifacts",
            "-> RAW and MARTS tables",
            "-> MARTS and AUDIT views",
            "-> query extracts and validation reports",
            "-> executive and manager-facing artifacts",
            "```",
            "",
            "DuckDB remains a local fallback for users without Snowflake credentials.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    ensure_dirs()
    SNOWFLAKE_EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    connection = connector_connection()
    try:
        for name, view_name, description in QUERY_EXPORTS:
            path, row_count = extract_view(connection, name, view_name)
            results.append(
                {
                    "path": path.relative_to(PROJECT_ROOT).as_posix(),
                    "view_name": view_name,
                    "rows": row_count,
                    "description": description,
                }
            )
            print(f"Extracted {view_name}: {row_count} rows -> {path.relative_to(PROJECT_ROOT)}")
    finally:
        connection.close()
    SNOWFLAKE_EXTRACT_REPORT.write_text(render_report(results), encoding="utf-8")
    print(f"Wrote Snowflake query extract report: {SNOWFLAKE_EXTRACT_REPORT.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
