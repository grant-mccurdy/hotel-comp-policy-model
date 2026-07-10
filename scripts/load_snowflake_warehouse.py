from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import snowflake.connector
from cryptography.hazmat.primitives import serialization

from common import (
    COMP_CATALOG_PATH,
    COMP_POLICY_AUDIT_PATH,
    COMP_RECOMMENDATIONS_PATH,
    EXTERNAL_CONTEXT_MODEL_IMPACT_PATH,
    LOCAL_DEMAND_CONTEXT_PATH,
    MANIFEST_DIR,
    PROJECT_ROOT,
    PROPER_PUBLIC_CONTEXT_PATH,
    PROPERTY_CONTEXT_PATH,
    PUBLIC_PRICING_CONTEXT_PATH,
    RATE_SHOP_SNAPSHOT_PATH,
    RECOVERY_CASE_MART_PATH,
    REPORT_DIR,
    REVIEW_RISK_CONTEXT_PATH,
    ensure_dirs,
    read_json,
    utc_now_iso,
    write_json,
)
from generate_synthetic_source_systems import (
    COMP_LEDGER_PATH,
    CRM_PROFILES_PATH,
    OPS_DAILY_PATH,
    PMS_RESERVATIONS_PATH,
    POS_CHARGES_PATH,
    REVIEWS_SURVEYS_PATH,
    SERVICE_TICKETS_PATH,
)


SNOWFLAKE_DATABASE = "HOTEL_COMP_POLICY_MODEL"
SNOWFLAKE_WAREHOUSE = "HOTEL_COMP_WH"
SNOWFLAKE_STAGE = "PROJECT_CSV_STAGE"
DEFAULT_CONNECTION = "hotel_comp_dev_keypair"
DEFAULT_PRIVATE_KEY_PATH = Path.home() / ".config" / "snowflake" / "keys" / "hotel_comp_policy_model_key.p8"

SQL_DIR = PROJECT_ROOT / "sql" / "snowflake"
SNOWFLAKE_MANIFEST_PATH = MANIFEST_DIR / "snowflake_warehouse_manifest.json"
SNOWFLAKE_LINEAGE_REPORT = REPORT_DIR / "snowflake-warehouse-lineage.md"
SNOWFLAKE_VALIDATION_REPORT = REPORT_DIR / "snowflake-validation.md"
SNOWFLAKE_S3_COPY_MANIFEST_PATH = MANIFEST_DIR / "snowflake_s3_copy_manifest.json"


CSV_TABLES = [
    ("RAW", "STG_PMS_RESERVATIONS", PMS_RESERVATIONS_PATH, "Synthetic PMS reservation extract"),
    ("RAW", "STG_GUEST_PROFILES_CRM", CRM_PROFILES_PATH, "Synthetic CRM guest profiles"),
    ("RAW", "STG_SERVICE_TICKETS", SERVICE_TICKETS_PATH, "Synthetic service-ticket system"),
    ("RAW", "STG_COMP_LEDGER", COMP_LEDGER_PATH, "Synthetic comp ledger"),
    ("RAW", "STG_POS_OUTLET_CHARGES", POS_CHARGES_PATH, "Synthetic outlet charges"),
    ("RAW", "STG_REVIEWS_SURVEYS", REVIEWS_SURVEYS_PATH, "Synthetic review and survey signals"),
    ("RAW", "STG_OPS_DAILY", OPS_DAILY_PATH, "Synthetic daily operational pressure"),
    ("RAW", "STG_RATE_SHOP_SNAPSHOTS", RATE_SHOP_SNAPSHOT_PATH, "Public quoted-rate sample/API extract"),
    ("RAW", "STG_PROPERTY_CONTEXT", PROPERTY_CONTEXT_PATH, "Public property and competitive-set context"),
    ("RAW", "STG_PROPER_PUBLIC_VALUE_ANCHORS", PROPER_PUBLIC_CONTEXT_PATH, "Observed public Santa Monica Proper value anchors"),
    ("RAW", "STG_REVIEW_RISK_CONTEXT", REVIEW_RISK_CONTEXT_PATH, "Review-risk theme priors by issue category"),
    ("RAW", "STG_LOCAL_DEMAND_CONTEXT", LOCAL_DEMAND_CONTEXT_PATH, "Local event/weather demand-pressure context"),
    ("MARTS", "MART_PUBLIC_PRICING_CONTEXT", PUBLIC_PRICING_CONTEXT_PATH, "Daily public pricing context"),
    ("MARTS", "MART_RECOVERY_CASES", RECOVERY_CASE_MART_PATH, "Case-level recovery decision mart"),
    ("MARTS", "MART_COMP_RECOMMENDATIONS", COMP_RECOMMENDATIONS_PATH, "Policy-engine recommendation output"),
    ("MARTS", "MART_COMP_POLICY_AUDIT", COMP_POLICY_AUDIT_PATH, "Comp policy audit output"),
    ("MARTS", "MART_EXTERNAL_CONTEXT_MODEL_IMPACT", EXTERNAL_CONTEXT_MODEL_IMPACT_PATH, "External-context impact output"),
    ("MARTS", "DIM_COMP_CATALOG", COMP_CATALOG_PATH, "Comp type catalog"),
]

VIEW_OBJECTS = [
    ("MARTS", "VW_COMP_DECISION_SUMMARY", "Executive rollup of comp value, cost, recovery value, and manager review volume"),
    ("MARTS", "VW_COMP_MIX", "Comp-type mix by cases, guest-facing value, and internal cost"),
    ("MARTS", "VW_MANAGER_REVIEW_QUEUE", "Manager review queue combining escalation and low-match-confidence cases"),
    ("AUDIT", "VW_AUDIT_DECISION_SIGNAL", "Audit classes for under-recovery, over-comping, review, and data-quality holds"),
    ("AUDIT", "VW_SOURCE_QUALITY_SNAPSHOT", "Compact source-quality metrics for messy-data review"),
    ("MARTS", "VW_PUBLIC_PRICING_CONTEXT", "Public quoted-rate context for comp opportunity-cost reasoning"),
    ("AUDIT", "VW_EXTERNAL_CONTEXT_SOURCES", "External-context source row counts"),
    ("MARTS", "VW_EXTERNAL_CONTEXT_MODEL_IMPACT", "Controlled public-context model-impact comparisons"),
]


def connection_name() -> str:
    return os.environ.get("SNOWFLAKE_CONNECTION", DEFAULT_CONNECTION)


def role_name() -> str:
    if "admin" in connection_name().lower():
        return "ACCOUNTADMIN"
    return os.environ.get("SNOWFLAKE_ROLE", "HOTEL_COMP_DEV_ROLE")


def account_name() -> str:
    account = os.environ.get("SNOWFLAKE_ACCOUNT", "").strip()
    if not account:
        raise RuntimeError("SNOWFLAKE_ACCOUNT is required for connector-based loading.")
    return account


def user_name() -> str:
    user = os.environ.get("SNOWFLAKE_USER", "").strip()
    if not user:
        raise RuntimeError("SNOWFLAKE_USER is required for connector-based loading.")
    return user


def private_key_path() -> Path:
    return Path(os.environ.get("SNOWFLAKE_PRIVATE_KEY_PATH", str(DEFAULT_PRIVATE_KEY_PATH))).expanduser()


def private_key_der() -> bytes:
    key = serialization.load_pem_private_key(private_key_path().read_bytes(), password=None)
    return key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def connector_connection() -> snowflake.connector.SnowflakeConnection:
    account = os.environ.get("SNOWFLAKE_ACCOUNT", "").strip()
    user = os.environ.get("SNOWFLAKE_USER", "").strip()
    if not account and not user:
        return snowflake.connector.connect(connection_name=connection_name())
    if not account or not user:
        raise RuntimeError("Set both SNOWFLAKE_ACCOUNT and SNOWFLAKE_USER, or use a configured connection name.")
    return snowflake.connector.connect(
        account=account,
        user=user,
        private_key=private_key_der(),
        role=role_name(),
        warehouse=SNOWFLAKE_WAREHOUSE,
        database=SNOWFLAKE_DATABASE,
        schema="RAW",
    )


def snow_binary() -> str:
    explicit = os.environ.get("SNOWFLAKE_CLI")
    if explicit:
        return explicit
    venv_snow = PROJECT_ROOT / ".venv" / "bin" / "snow"
    if venv_snow.exists():
        return str(venv_snow)
    found = shutil.which("snow")
    if found:
        return found
    raise RuntimeError(
        "Snowflake CLI not found. Install it with `python3 -m venv .venv` and "
        "`.venv/bin/python -m pip install -r requirements-snowflake.txt`."
    )


def run_snow(args: list[str], *, capture_json: bool = False, check: bool = True) -> subprocess.CompletedProcess[str]:
    command = [snow_binary(), *args]
    result = subprocess.run(command, cwd=PROJECT_ROOT, text=True, capture_output=True, check=False)
    if check and result.returncode != 0:
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        raise RuntimeError(f"Snowflake CLI command failed with exit code {result.returncode}: {' '.join(args)}")
    if capture_json:
        return result
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result


def execute_sql_file(path: Path) -> None:
    run_snow(
        [
            "sql",
            "--connection",
            connection_name(),
            "--filename",
            str(path),
            "--enhanced-exit-codes",
        ]
    )


def execute_sql(query: str, *, capture_json: bool = False, check: bool = True) -> Any:
    args = [
        "sql",
        "--connection",
        connection_name(),
        "--query",
        query,
        "--enhanced-exit-codes",
    ]
    if capture_json:
        args.extend(["--format", "JSON"])
    result = run_snow(args, capture_json=capture_json, check=check)
    if capture_json:
        return parse_json_output(result.stdout)
    return None


def parse_json_output(stdout: str) -> Any:
    text = stdout.strip()
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end < start:
        raise RuntimeError(f"Expected JSON output from Snowflake CLI, received: {stdout[:500]}")
    return json.loads(text[start : end + 1])


def csv_header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        return next(reader)


def csv_row_count(path: Path) -> int:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        next(reader)
        return sum(1 for _ in reader)


def csv_records(path: Path) -> list[list[str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        next(reader)
        return [row for row in reader]


def snowflake_identifier(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_").upper()
    cleaned = re.sub(r"_+", "_", cleaned)
    if not cleaned:
        cleaned = "COLUMN"
    if cleaned[0].isdigit():
        cleaned = f"C_{cleaned}"
    return cleaned


def normalized_columns(path: Path) -> list[str]:
    seen: dict[str, int] = {}
    columns = []
    for header in csv_header(path):
        base = snowflake_identifier(header)
        count = seen.get(base, 0)
        seen[base] = count + 1
        columns.append(base if count == 0 else f"{base}_{count + 1}")
    return columns


def fq(schema: str, table: str) -> str:
    return f"{SNOWFLAKE_DATABASE}.{schema}.{table}"


def table_ddl(schema: str, table: str, path: Path) -> str:
    columns = ",\n  ".join(f"{column} VARCHAR" for column in normalized_columns(path))
    return f"CREATE OR REPLACE TABLE {fq(schema, table)} (\n  {columns}\n);"


def copy_into_sql(schema: str, table: str, stage_folder: str) -> str:
    return f"""
COPY INTO {fq(schema, table)}
FROM @{SNOWFLAKE_DATABASE}.RAW.{SNOWFLAKE_STAGE}/{stage_folder}
FILE_FORMAT = (FORMAT_NAME = {SNOWFLAKE_DATABASE}.RAW.CSV_WITH_HEADER)
ON_ERROR = 'ABORT_STATEMENT';
""".strip()


def put_sql(path: Path, stage_folder: str) -> str:
    return (
        f"PUT file://{path} @{SNOWFLAKE_DATABASE}.RAW.{SNOWFLAKE_STAGE}/{stage_folder} "
        "AUTO_COMPRESS=FALSE OVERWRITE=TRUE PARALLEL=4;"
    )


def insert_rows(
    cursor: snowflake.connector.cursor.SnowflakeCursor,
    schema: str,
    table: str,
    path: Path,
    chunk_size: int = 500,
) -> int:
    columns = normalized_columns(path)
    placeholders = ", ".join(["%s"] * len(columns))
    column_sql = ", ".join(columns)
    insert_sql = f"INSERT INTO {fq(schema, table)} ({column_sql}) VALUES ({placeholders})"
    records = csv_records(path)
    for start in range(0, len(records), chunk_size):
        cursor.executemany(insert_sql, records[start : start + chunk_size])
    return len(records)


def stage_folder(schema: str, table: str) -> str:
    return f"{schema.lower()}/{table.lower()}"


def local_table_counts() -> dict[str, int]:
    counts = {}
    for schema, table, path, _description in CSV_TABLES:
        counts[f"{schema}.{table}"] = csv_row_count(path) if path.exists() else -1
    return counts


def required_files_exist() -> None:
    missing = [str(path.relative_to(PROJECT_ROOT)) for _schema, _table, path, _description in CSV_TABLES if not path.exists()]
    if missing:
        raise RuntimeError("Missing generated CSV files. Run `make artifacts` first. Missing: " + ", ".join(missing))


def test_connection() -> None:
    run_snow(["connection", "test", "--connection", connection_name()])


def bootstrap() -> None:
    execute_sql_file(SQL_DIR / "00_bootstrap.sql")
    execute_sql_file(SQL_DIR / "01_create_stage_and_formats.sql")
    bootstrap_user = os.environ.get("SNOWFLAKE_BOOTSTRAP_USER", "").strip()
    if bootstrap_user:
        execute_sql(f"GRANT ROLE HOTEL_COMP_DEV_ROLE TO USER {snowflake_identifier(bootstrap_user)}")


def load_tables() -> dict[str, int]:
    required_files_exist()
    execute_sql_file(SQL_DIR / "01_create_stage_and_formats.sql")
    loaded_counts = {}

    connection = connector_connection()
    cursor = connection.cursor()
    try:
        for schema, table, path, description in CSV_TABLES:
            print(f"Loading {schema}.{table}: {description}")
            cursor.execute(table_ddl(schema, table, path))
            cursor.execute(f"TRUNCATE TABLE {fq(schema, table)}")
            loaded_counts[f"{schema}.{table}"] = insert_rows(cursor, schema, table, path)
            print(f"Loaded {loaded_counts[f'{schema}.{table}']} rows into {schema}.{table}")
    finally:
        cursor.close()
        connection.close()

    execute_sql_file(SQL_DIR / "02_create_views.sql")
    manifest = {
        "generated_at": utc_now_iso(),
        "connection": connection_name(),
        "database": SNOWFLAKE_DATABASE,
        "warehouse": SNOWFLAKE_WAREHOUSE,
        "stage": f"{SNOWFLAKE_DATABASE}.RAW.{SNOWFLAKE_STAGE}",
        "tables_loaded": loaded_counts,
        "views_defined": [f"{schema}.{view}" for schema, view, _description in VIEW_OBJECTS],
        "load_method": "snowflake_connector_batch_insert",
        "source_contract": "CSV source systems -> Snowflake RAW/MARTS tables -> analytic views",
    }
    write_json(SNOWFLAKE_MANIFEST_PATH, manifest)
    SNOWFLAKE_LINEAGE_REPORT.write_text(render_lineage(manifest), encoding="utf-8")
    return loaded_counts


def row_count_query(objects: list[tuple[str, str]]) -> str:
    selects = [
        f"SELECT '{schema}.{name}' AS OBJECT_NAME, COUNT(*) AS SNOWFLAKE_ROWS FROM {fq(schema, name)}"
        for schema, name in objects
    ]
    return "\nUNION ALL\n".join(selects) + "\nORDER BY OBJECT_NAME"


def validate() -> list[dict[str, Any]]:
    table_objects = [(schema, table) for schema, table, _path, _description in CSV_TABLES]
    view_objects = [(schema, view) for schema, view, _description in VIEW_OBJECTS]
    table_rows = execute_sql(row_count_query(table_objects), capture_json=True)
    view_rows = execute_sql(row_count_query(view_objects), capture_json=True)
    expected = local_table_counts()
    validation_rows = []

    for row in table_rows:
        object_name = row["OBJECT_NAME"]
        snowflake_rows = int(row["SNOWFLAKE_ROWS"])
        expected_rows = expected.get(object_name, -1)
        validation_rows.append(
            {
                "object_name": object_name,
                "object_type": "table",
                "expected_local_rows": expected_rows,
                "snowflake_rows": snowflake_rows,
                "status": "PASS" if expected_rows == snowflake_rows else "FAIL",
            }
        )

    for row in view_rows:
        validation_rows.append(
            {
                "object_name": row["OBJECT_NAME"],
                "object_type": "view",
                "expected_local_rows": "",
                "snowflake_rows": int(row["SNOWFLAKE_ROWS"]),
                "status": "PASS" if int(row["SNOWFLAKE_ROWS"]) >= 0 else "FAIL",
            }
        )

    SNOWFLAKE_VALIDATION_REPORT.write_text(render_validation(validation_rows), encoding="utf-8")
    print(f"Wrote Snowflake validation report: {SNOWFLAKE_VALIDATION_REPORT.relative_to(PROJECT_ROOT)}")
    if any(row["status"] == "FAIL" for row in validation_rows):
        raise RuntimeError("Snowflake validation found row-count mismatches.")
    return validation_rows


def render_lineage(manifest: dict[str, Any] | None = None) -> str:
    counts = local_table_counts()
    s3_copy_manifest = (
        read_json(SNOWFLAKE_S3_COPY_MANIFEST_PATH)
        if SNOWFLAKE_S3_COPY_MANIFEST_PATH.exists()
        else None
    )
    load_description = (
        "S3 data lake external stage with Snowflake `COPY INTO`"
        if s3_copy_manifest
        else "Snowflake connector batch insert from public-safe CSV artifacts"
    )
    lines = [
        "# Snowflake Warehouse Lineage",
        "",
        "This is the primary cloud warehouse path for the project workflow.",
        "",
        "Snowflake is used for the warehouse load, SQL view layer, validation, and query extracts. DuckDB remains a local fallback for reviewers or environments without Snowflake credentials.",
        "",
        "The project supports connector batch inserts and an enterprise ingestion path through an S3 external stage. The status section identifies the most recently evidenced load method.",
        "",
        "## Warehouse Objects",
        "",
        f"- Database: `{SNOWFLAKE_DATABASE}`",
        f"- Warehouse: `{SNOWFLAKE_WAREHOUSE}`",
        "- Schemas: `RAW`, `STAGING`, `MARTS`, `AUDIT`",
        f"- Internal stage: `{SNOWFLAKE_DATABASE}.RAW.{SNOWFLAKE_STAGE}`",
        f"- Load method: {load_description}",
        "",
        "## Source-To-Table Map",
        "",
        "| Snowflake table | Local rows | Source purpose |",
        "| --- | ---: | --- |",
    ]
    for schema, table, _path, description in CSV_TABLES:
        lines.append(f"| `{schema}.{table}` | {counts[f'{schema}.{table}']} | {description} |")

    lines.extend(
        [
            "",
            "## Analytics Views",
            "",
            "| Snowflake view | Use |",
            "| --- | --- |",
        ]
    )
    for schema, view, description in VIEW_OBJECTS:
        lines.append(f"| `{schema}.{view}` | {description} |")

    lines.extend(
        [
            "",
            "## Commands",
            "",
            "```bash",
            "make snowflake-test",
            "make snowflake-bootstrap",
            "make snowflake-load",
            "make snowflake-validate",
            "make snowflake-extracts",
            "```",
            "",
            "## Status",
            "",
        ]
    )
    if s3_copy_manifest:
        lines.extend(
            [
                f"- Verified external-stage load generated at: `{s3_copy_manifest['generated_at']}`",
                f"- S3 run ID: `{s3_copy_manifest['s3_run_id']}`",
                f"- Tables loaded through `COPY INTO`: `{len(s3_copy_manifest['tables_loaded'])}`",
                "- Bucket, account, role, and credential identifiers are intentionally omitted from this public report.",
            ]
        )
    elif manifest:
        lines.extend(
            [
                f"- Last Snowflake load manifest generated at: `{manifest['generated_at']}`",
                f"- Connection name used: `{manifest['connection']}`",
                "- Credentials and Snowflake connection files are intentionally not stored in this repository.",
            ]
        )
    else:
        lines.extend(
            [
                "- Offline lineage generated from local CSV files.",
                "- Run `make all` after configuring Snowflake CLI to execute the cloud warehouse workflow.",
            ]
        )
    lines.append("")
    return "\n".join(lines)


def render_validation(rows: list[dict[str, Any]]) -> str:
    passed = sum(1 for row in rows if row["status"] == "PASS")
    failed = sum(1 for row in rows if row["status"] == "FAIL")
    lines = [
        "# Snowflake Validation",
        "",
        f"Generated at: `{utc_now_iso()}`",
        "",
        "## Summary",
        "",
        f"- Checks passed: `{passed}`",
        f"- Checks failed: `{failed}`",
        "",
        "| Object | Type | Local rows | Snowflake rows | Status |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            f"| `{row['object_name']}` | {row['object_type']} | {row['expected_local_rows']} | {row['snowflake_rows']} | {row['status']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Table checks compare Snowflake-loaded row counts against the public-safe CSV artifacts generated locally. View checks confirm that the analytic Snowflake layer is queryable.",
            "",
        ]
    )
    return "\n".join(lines)


def write_offline_lineage() -> None:
    ensure_dirs()
    SNOWFLAKE_LINEAGE_REPORT.write_text(render_lineage(), encoding="utf-8")
    print(f"Wrote Snowflake lineage report: {SNOWFLAKE_LINEAGE_REPORT.relative_to(PROJECT_ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Load the hotel comp policy artifacts into Snowflake.")
    parser.add_argument(
        "command",
        choices=["test", "bootstrap", "load", "validate", "lineage", "all"],
        help="Snowflake operation to run.",
    )
    args = parser.parse_args()
    ensure_dirs()

    try:
        if args.command == "test":
            test_connection()
        elif args.command == "bootstrap":
            bootstrap()
        elif args.command == "load":
            load_tables()
        elif args.command == "validate":
            validate()
        elif args.command == "lineage":
            write_offline_lineage()
        elif args.command == "all":
            test_connection()
            bootstrap()
            load_tables()
            validate()
    except RuntimeError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
