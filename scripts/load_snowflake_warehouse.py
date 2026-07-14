from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from common import (
    CLOUD_EXECUTION_EVIDENCE_PATH,
    COMP_CATALOG_PATH,
    COMP_POLICY_AUDIT_PATH,
    COMP_RECOMMENDATIONS_PATH,
    EXTERNAL_CONTEXT_MODEL_IMPACT_PATH,
    LOCAL_DEMAND_CONTEXT_PATH,
    MANIFEST_DIR,
    POLICY_CASE_COMPARISON_PATH,
    POLICY_DECISION_SUMMARY_PATH,
    POLICY_SEGMENT_DIAGNOSTICS_PATH,
    POLICY_UNCERTAINTY_SUMMARY_PATH,
    PROJECT_ROOT,
    PROPER_PUBLIC_CONTEXT_PATH,
    PROPERTY_CONTEXT_PATH,
    PUBLIC_PRICING_CONTEXT_PATH,
    RATE_SHOP_SNAPSHOT_PATH,
    RECOVERY_CASE_MART_PATH,
    REPORT_DIR,
    REVIEW_RISK_CONTEXT_PATH,
    SNOWFLAKE_LOAD_CONTEXT_PATH,
    ensure_dirs,
    read_csv_rows,
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
SNOWFLAKE_MART_TYPE_CONTRACT_PATH = PROJECT_ROOT / "data" / "contracts" / "snowflake_mart_types.json"


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
    ("MARTS", "MART_POLICY_CASE_COMPARISON", POLICY_CASE_COMPARISON_PATH, "Case-by-policy evaluation matrix"),
    ("MARTS", "MART_POLICY_DECISION_SUMMARY", POLICY_DECISION_SUMMARY_PATH, "Executive policy comparison and shadow-candidate selection"),
    ("MARTS", "MART_POLICY_SEGMENT_DIAGNOSTICS", POLICY_SEGMENT_DIAGNOSTICS_PATH, "Policy diagnostics by synthetic case segment"),
    ("MARTS", "MART_POLICY_UNCERTAINTY_SUMMARY", POLICY_UNCERTAINTY_SUMMARY_PATH, "Probabilistic policy uncertainty output"),
    ("MARTS", "DIM_COMP_CATALOG", COMP_CATALOG_PATH, "Comp type catalog"),
]

VIEW_OBJECTS = [
    ("MARTS", "VW_COMP_DECISION_SUMMARY", "Supporting rollup of modeled comp value, cost, stability, and manager review volume"),
    ("MARTS", "VW_COMP_MIX", "Comp-type mix by cases, guest-facing value, and internal cost"),
    ("MARTS", "VW_MANAGER_REVIEW_QUEUE", "Manager review queue combining escalation and low-match-confidence cases"),
    ("AUDIT", "VW_AUDIT_DECISION_SIGNAL", "Audit classes for under-recovery, over-comping, review, and data-quality holds"),
    ("AUDIT", "VW_SOURCE_QUALITY_SNAPSHOT", "Compact source-quality metrics for messy-data review"),
    ("MARTS", "VW_PUBLIC_PRICING_CONTEXT", "Public quoted-rate context for comp opportunity-cost reasoning"),
    ("AUDIT", "VW_EXTERNAL_CONTEXT_SOURCES", "External-context source row counts"),
    ("MARTS", "VW_EXTERNAL_CONTEXT_MODEL_IMPACT", "Controlled public-context model-impact comparisons"),
    ("MARTS", "VW_POLICY_DECISION_RECOMMENDATION", "Selected shadow-validation policy and executive decision metrics"),
    ("MARTS", "VW_POLICY_TRADEOFF", "Candidate-policy adequacy, cost, refund, and review tradeoffs"),
    ("MARTS", "VW_POLICY_SEGMENT_DIAGNOSTICS", "Unsuppressed segment-level policy diagnostics"),
    ("MARTS", "VW_POLICY_UNCERTAINTY", "Probabilistic guardrail and cost uncertainty"),
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
    try:
        from cryptography.hazmat.primitives import serialization
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Snowflake key-pair authentication requires `requirements-snowflake.txt`."
        ) from exc
    key = serialization.load_pem_private_key(private_key_path().read_bytes(), password=None)
    return key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def connector_connection() -> Any:
    try:
        import snowflake.connector
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Snowflake connector operations require `requirements-snowflake.txt`."
        ) from exc
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


def mart_type_contract() -> dict[str, Any]:
    contract = read_json(SNOWFLAKE_MART_TYPE_CONTRACT_PATH)
    seen: dict[str, str] = {}
    for snowflake_type, columns in contract["column_types"].items():
        for column in columns:
            normalized = snowflake_identifier(column)
            if normalized in seen:
                raise RuntimeError(
                    f"Duplicate Snowflake type contract for {normalized}: "
                    f"{seen[normalized]} and {snowflake_type}"
                )
            seen[normalized] = snowflake_type
    return contract


def mart_type_lookup() -> dict[str, str]:
    contract = mart_type_contract()
    return {
        snowflake_identifier(column): snowflake_type
        for snowflake_type, columns in contract["column_types"].items()
        for column in columns
    }


def column_definitions(schema: str, path: Path) -> list[tuple[str, str]]:
    columns = normalized_columns(path)
    if schema == "RAW":
        return [(column, "VARCHAR") for column in columns]
    contract = mart_type_contract()
    lookup = mart_type_lookup()
    default_type = contract.get("default_mart_type", "VARCHAR")
    return [(column, lookup.get(column, default_type)) for column in columns]


def fq(schema: str, table: str) -> str:
    return f"{SNOWFLAKE_DATABASE}.{schema}.{table}"


def table_ddl(schema: str, table: str, path: Path) -> str:
    columns = ",\n  ".join(
        f"{column} {snowflake_type}" for column, snowflake_type in column_definitions(schema, path)
    )
    return f"CREATE OR REPLACE TABLE {fq(schema, table)} (\n  {columns}\n);"


def copy_into_sql(schema: str, table: str, stage_folder: str) -> str:
    file_format = "CSV_WITH_HEADER" if schema == "RAW" else "MART_CSV_WITH_HEADER"
    return f"""
COPY INTO {fq(schema, table)}
FROM @{SNOWFLAKE_DATABASE}.RAW.{SNOWFLAKE_STAGE}/{stage_folder}
FILE_FORMAT = (FORMAT_NAME = {SNOWFLAKE_DATABASE}.RAW.{file_format})
ON_ERROR = 'ABORT_STATEMENT';
""".strip()


def put_sql(path: Path, stage_folder: str) -> str:
    return (
        f"PUT file://{path} @{SNOWFLAKE_DATABASE}.RAW.{SNOWFLAKE_STAGE}/{stage_folder} "
        "AUTO_COMPRESS=FALSE OVERWRITE=TRUE PARALLEL=4;"
    )


def insert_rows(
    cursor: Any,
    schema: str,
    table: str,
    path: Path,
    chunk_size: int = 500,
) -> int:
    definitions = column_definitions(schema, path)
    columns = [column for column, _snowflake_type in definitions]
    placeholders = ", ".join(["%s"] * len(columns))
    column_sql = ", ".join(columns)
    insert_sql = f"INSERT INTO {fq(schema, table)} ({column_sql}) VALUES ({placeholders})"
    records = [
        [coerce_value(value, snowflake_type) for value, (_column, snowflake_type) in zip(row, definitions)]
        for row in csv_records(path)
    ]
    for start in range(0, len(records), chunk_size):
        cursor.executemany(insert_sql, records[start : start + chunk_size])
    return len(records)


def coerce_value(value: str, snowflake_type: str) -> Any:
    if snowflake_type == "VARCHAR":
        return value
    if value == "":
        return None
    if snowflake_type == "BOOLEAN":
        normalized = value.strip().lower()
        if normalized not in {"true", "false"}:
            raise ValueError(f"Expected boolean text, received {value!r}")
        return normalized == "true"
    if snowflake_type == "DATE":
        return date.fromisoformat(value)
    if snowflake_type == "NUMBER(38,0)":
        return int(value)
    if snowflake_type.startswith("NUMBER("):
        return Decimal(value)
    return value


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
    write_json(
        SNOWFLAKE_LOAD_CONTEXT_PATH,
        {
            "generated_at": manifest["generated_at"],
            "load_method": manifest["load_method"],
            "source_run_id": "connector_batch_insert",
            "tables_loaded": len(loaded_counts),
        },
    )
    SNOWFLAKE_LINEAGE_REPORT.write_text(render_lineage(manifest), encoding="utf-8")
    return loaded_counts


def row_count_query(objects: list[tuple[str, str]]) -> str:
    selects = [
        f"SELECT '{schema}.{name}' AS OBJECT_NAME, COUNT(*) AS SNOWFLAKE_ROWS FROM {fq(schema, name)}"
        for schema, name in objects
    ]
    return "\nUNION ALL\n".join(selects) + "\nORDER BY OBJECT_NAME"


def local_policy_decision() -> tuple[list[dict[str, str]], dict[str, str]]:
    _, rows = read_csv_rows(POLICY_DECISION_SUMMARY_PATH)
    selected = [row for row in rows if row.get("selected_for_shadow_evaluation", "").lower() == "true"]
    if len(selected) != 1:
        raise RuntimeError(f"Expected one locally selected policy, found {len(selected)}.")
    return rows, selected[0]


def semantic_validation_query() -> str:
    summary_rows, selected = local_policy_decision()
    expected_policies = len(summary_rows)
    expected_case_rows = csv_row_count(POLICY_CASE_COMPARISON_PATH)
    with POLICY_CASE_COMPARISON_PATH.open("r", encoding="utf-8", newline="") as handle:
        case_rows = list(csv.DictReader(handle))
    expected_cases = len({row["recovery_case_id"] for row in case_rows})
    selected_policy = selected["policy_id"].replace("'", "''")
    selected_cost = Decimal(selected["internal_cost_mid"])
    selected_guardrail = Decimal(selected["joint_guardrail_pass_probability"])
    checks = [
        f"""SELECT 'candidate_policy_count' AS CHECK_NAME, '{expected_policies}' AS EXPECTED_VALUE,
            TO_VARCHAR(COUNT(*)) AS ACTUAL_VALUE, IFF(COUNT(*) = {expected_policies}, 'PASS', 'FAIL') AS STATUS
            FROM MARTS.MART_POLICY_DECISION_SUMMARY""",
        """SELECT 'selected_policy_count', '1', TO_VARCHAR(COUNT(*)), IFF(COUNT(*) = 1, 'PASS', 'FAIL')
            FROM MARTS.MART_POLICY_DECISION_SUMMARY WHERE SELECTED_FOR_PILOT""",
        f"""SELECT 'case_policy_row_count', '{expected_case_rows}', TO_VARCHAR(COUNT(*)),
            IFF(COUNT(*) = {expected_case_rows}, 'PASS', 'FAIL')
            FROM MARTS.MART_POLICY_CASE_COMPARISON""",
        f"""SELECT 'distinct_recovery_cases', '{expected_cases}', TO_VARCHAR(COUNT(DISTINCT RECOVERY_CASE_ID)),
            IFF(COUNT(DISTINCT RECOVERY_CASE_ID) = {expected_cases}, 'PASS', 'FAIL')
            FROM MARTS.MART_POLICY_CASE_COMPARISON""",
        f"""SELECT 'complete_case_policy_matrix', '0', TO_VARCHAR(COUNT(*)), IFF(COUNT(*) = 0, 'PASS', 'FAIL')
            FROM (
              SELECT POLICY_ID, COUNT(*) AS ROWS_PER_POLICY
              FROM MARTS.MART_POLICY_CASE_COMPARISON
              GROUP BY POLICY_ID
              HAVING COUNT(*) <> {expected_cases}
            )""",
        """SELECT 'probability_bounds', '0', TO_VARCHAR(COUNT(*)), IFF(COUNT(*) = 0, 'PASS', 'FAIL')
            FROM MARTS.MART_POLICY_DECISION_SUMMARY
            WHERE JOINT_GUARDRAIL_PASS_PROBABILITY NOT BETWEEN 0 AND 1
               OR POLICY_SELECTION_PROBABILITY NOT BETWEEN 0 AND 1
               OR ADEQUACY_RATE NOT BETWEEN 0 AND 1
               OR GESTURE_ADEQUACY_RATE NOT BETWEEN 0 AND 1""",
        """SELECT 'cost_ordering', '0', TO_VARCHAR(COUNT(*)), IFF(COUNT(*) = 0, 'PASS', 'FAIL')
            FROM MARTS.MART_POLICY_DECISION_SUMMARY
            WHERE INTERNAL_COST_LOW > INTERNAL_COST_MID OR INTERNAL_COST_MID > INTERNAL_COST_HIGH""",
        f"""SELECT 'selected_policy_parity', '{selected_policy}',
            COALESCE(MAX(IFF(SELECTED_FOR_PILOT, POLICY_ID, NULL)), '<none>'),
            IFF(COALESCE(MAX(IFF(SELECTED_FOR_PILOT, POLICY_ID, NULL)), '<none>') = '{selected_policy}', 'PASS', 'FAIL')
            FROM MARTS.MART_POLICY_DECISION_SUMMARY""",
        f"""SELECT 'selected_metric_parity', '1', TO_VARCHAR(COUNT(*)), IFF(COUNT(*) = 1, 'PASS', 'FAIL')
            FROM MARTS.MART_POLICY_DECISION_SUMMARY
            WHERE SELECTED_FOR_PILOT
              AND ABS(INTERNAL_COST_MID - {selected_cost}) < 0.000001
              AND ABS(JOINT_GUARDRAIL_PASS_PROBABILITY - {selected_guardrail}) < 0.000001""",
        """SELECT 'selected_safety_guardrails', '1', TO_VARCHAR(COUNT(*)), IFF(COUNT(*) = 1, 'PASS', 'FAIL')
            FROM MARTS.MART_POLICY_DECISION_SUMMARY
            WHERE SELECTED_FOR_PILOT
              AND DATA_HOLD_COMPLIANCE_RATE = 1
              AND TIER_FIVE_REVIEW_COMPLIANCE_RATE = 1
              AND HIGH_RISK_UNDER_RECOVERY_RATE <= 0.05
              AND OPERATIONAL_INFEASIBILITY_RATE <= 0.02""",
        """SELECT 'typed_mart_columns', '4', TO_VARCHAR(COUNT(*)), IFF(COUNT(*) = 4, 'PASS', 'FAIL')
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'MARTS'
              AND (
                (TABLE_NAME = 'MART_POLICY_DECISION_SUMMARY' AND COLUMN_NAME = 'SELECTED_FOR_PILOT' AND DATA_TYPE = 'BOOLEAN')
                OR (TABLE_NAME = 'MART_POLICY_DECISION_SUMMARY' AND COLUMN_NAME = 'INTERNAL_COST_MID' AND DATA_TYPE = 'NUMBER')
                OR (TABLE_NAME = 'MART_POLICY_CASE_COMPARISON' AND COLUMN_NAME = 'SAFE_RECOVERY_PATH' AND DATA_TYPE = 'BOOLEAN')
                OR (TABLE_NAME = 'MART_PUBLIC_PRICING_CONTEXT' AND COLUMN_NAME = 'CONTEXT_DATE' AND DATA_TYPE = 'DATE')
              )""",
        """SELECT 'suppressed_segment_filter', '0', TO_VARCHAR(COUNT(*)), IFF(COUNT(*) = 0, 'PASS', 'FAIL')
            FROM MARTS.VW_POLICY_SEGMENT_DIAGNOSTICS WHERE SUPPRESSED_SMALL_GROUP""",
    ]
    return "\nUNION ALL\n".join(checks)


def semantic_validation_rows() -> list[dict[str, Any]]:
    rows = execute_sql(semantic_validation_query(), capture_json=True)
    return [
        {
            "object_name": row["CHECK_NAME"],
            "object_type": "semantic",
            "expected_local_rows": row["EXPECTED_VALUE"],
            "snowflake_rows": row["ACTUAL_VALUE"],
            "status": row["STATUS"],
        }
        for row in rows
    ]


def write_cloud_execution_evidence(validation_rows: list[dict[str, Any]]) -> None:
    summary_rows, selected = local_policy_decision()
    load_context = (
        read_json(SNOWFLAKE_LOAD_CONTEXT_PATH)
        if SNOWFLAKE_LOAD_CONTEXT_PATH.exists()
        else {
            "generated_at": "unknown",
            "load_method": "unknown",
            "source_run_id": "unknown",
            "tables_loaded": 0,
        }
    )
    write_json(
        CLOUD_EXECUTION_EVIDENCE_PATH,
        {
            "evidence_version": "v1",
            "validated_at": utc_now_iso(),
            "load_method": load_context["load_method"],
            "source_run_id": load_context["source_run_id"],
            "source_and_model_tables": len(CSV_TABLES),
            "analytics_views": len(VIEW_OBJECTS),
            "semantic_checks": sum(row["object_type"] == "semantic" for row in validation_rows),
            "checks_passed": sum(row["status"] == "PASS" for row in validation_rows),
            "checks_failed": sum(row["status"] == "FAIL" for row in validation_rows),
            "comparison_version": selected["comparison_version"],
            "candidate_policies": len(summary_rows),
            "case_policy_rows": csv_row_count(POLICY_CASE_COMPARISON_PATH),
            "selected_policy_id": selected["policy_id"],
            "selected_policy_label": selected["policy_label"],
            "decision_source_view": "MARTS.VW_POLICY_TRADEOFF",
            "public_safety": "Account, bucket, role, credential, and guest identifiers omitted.",
        },
    )


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

    validation_rows.extend(semantic_validation_rows())

    SNOWFLAKE_VALIDATION_REPORT.write_text(render_validation(validation_rows), encoding="utf-8")
    print(f"Wrote Snowflake validation report: {SNOWFLAKE_VALIDATION_REPORT.relative_to(PROJECT_ROOT)}")
    if any(row["status"] == "FAIL" for row in validation_rows):
        raise RuntimeError("Snowflake validation found structural or semantic mismatches.")
    write_cloud_execution_evidence(validation_rows)
    return validation_rows


def render_lineage(manifest: dict[str, Any] | None = None) -> str:
    counts = local_table_counts()
    load_context = read_json(SNOWFLAKE_LOAD_CONTEXT_PATH) if SNOWFLAKE_LOAD_CONTEXT_PATH.exists() else None
    load_description = (
        "S3 data lake external stage with Snowflake `COPY INTO`"
        if load_context and load_context.get("load_method") == "s3_external_stage_copy_into"
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
        "RAW tables preserve source-shaped text. Curated MARTS use a versioned type contract for numeric, Boolean, and date fields.",
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
    if load_context and load_context.get("load_method") == "s3_external_stage_copy_into":
        lines.extend(
            [
                f"- Verified external-stage load generated at: `{load_context['generated_at']}`",
                f"- S3 run ID: `{load_context['source_run_id']}`",
                f"- Tables loaded through `COPY INTO`: `{load_context['tables_loaded']}`",
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
    object_rows = [row for row in rows if row["object_type"] != "semantic"]
    semantic_rows = [row for row in rows if row["object_type"] == "semantic"]
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
    for row in object_rows:
        lines.append(
            f"| `{row['object_name']}` | {row['object_type']} | {row['expected_local_rows']} | {row['snowflake_rows']} | {row['status']} |"
        )
    lines.extend(
        [
            "",
            "## Decision-Semantic Checks",
            "",
            "| Check | Expected | Snowflake result | Status |",
            "| --- | ---: | ---: | --- |",
        ]
    )
    for row in semantic_rows:
        lines.append(
            f"| `{row['object_name']}` | {row['expected_local_rows']} | {row['snowflake_rows']} | {row['status']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Table checks reconcile Snowflake row counts to the generated public-safe artifacts. View checks confirm the analytic layer is queryable. Semantic checks verify policy grain, selection uniqueness, simulation-rate and cost bounds, selected-policy parity, safety guardrails, typed MARTS columns, and suppression behavior.",
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
