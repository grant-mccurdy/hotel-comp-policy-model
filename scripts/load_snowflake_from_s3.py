from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from common import MANIFEST_DIR, PROJECT_ROOT, ensure_dirs, read_json, utc_now_iso, write_json
from load_snowflake_warehouse import (
    CSV_TABLES,
    SNOWFLAKE_DATABASE,
    connector_connection,
    execute_sql_file,
    fq,
    table_ddl,
)


S3_LOAD_MANIFEST_PATH = MANIFEST_DIR / "snowflake_s3_copy_manifest.json"
DEFAULT_INTEGRATION = "HOTEL_COMP_S3_INTEGRATION"
DEFAULT_STAGE = "S3_PROJECT_CSV_STAGE"
DEFAULT_S3_MANIFEST_PATH = MANIFEST_DIR / "s3_datalake_manifest.json"


def integration_name() -> str:
    return os.environ.get("SNOWFLAKE_S3_INTEGRATION", DEFAULT_INTEGRATION)


def stage_name() -> str:
    return os.environ.get("SNOWFLAKE_S3_STAGE", DEFAULT_STAGE)


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"Missing S3 manifest at {path}. Run `make s3-publish` first.")
    return read_json(path)


def entry_lookup(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {f"{entry['schema']}.{entry['table']}": entry for entry in manifest["entries"]}


def create_stage_sql(manifest: dict[str, Any]) -> str:
    url = f"s3://{manifest['bucket']}/{manifest['prefix']}/raw/{manifest['run_id']}/"
    return f"""
CREATE OR REPLACE STAGE {SNOWFLAKE_DATABASE}.RAW.{stage_name()}
  URL = '{url}'
  STORAGE_INTEGRATION = {integration_name()}
  FILE_FORMAT = {SNOWFLAKE_DATABASE}.RAW.CSV_WITH_HEADER
  COMMENT = 'S3 data lake external stage for hotel comp policy model artifacts.';
""".strip()


def copy_into_sql(schema: str, table: str, stage_relative_path: str, file_name: str) -> str:
    folder = stage_relative_path.rsplit("/", 1)[0]
    return f"""
COPY INTO {fq(schema, table)}
FROM @{SNOWFLAKE_DATABASE}.RAW.{stage_name()}/{folder}/
FILE_FORMAT = (FORMAT_NAME = {SNOWFLAKE_DATABASE}.RAW.CSV_WITH_HEADER)
PATTERN = '.*{file_name}'
ON_ERROR = 'ABORT_STATEMENT';
""".strip()


def run_s3_copy(manifest: dict[str, Any]) -> dict[str, int]:
    entries = entry_lookup(manifest)
    loaded_counts: dict[str, int] = {}
    connection = connector_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(f"USE DATABASE {SNOWFLAKE_DATABASE}")
        cursor.execute("CREATE SCHEMA IF NOT EXISTS RAW")
        cursor.execute("CREATE SCHEMA IF NOT EXISTS MARTS")
        cursor.execute("CREATE SCHEMA IF NOT EXISTS AUDIT")
        cursor.execute(
            f"""
            CREATE OR REPLACE FILE FORMAT {SNOWFLAKE_DATABASE}.RAW.CSV_WITH_HEADER
              TYPE = CSV
              SKIP_HEADER = 1
              FIELD_OPTIONALLY_ENCLOSED_BY = '"'
              EMPTY_FIELD_AS_NULL = FALSE
              NULL_IF = ();
            """
        )
        cursor.execute(create_stage_sql(manifest))
        for schema, table, path, description in CSV_TABLES:
            key = f"{schema}.{table}"
            entry = entries[key]
            print(f"Loading {key} from {entry['s3_uri']}: {description}")
            cursor.execute(table_ddl(schema, table, path))
            cursor.execute(f"TRUNCATE TABLE {fq(schema, table)}")
            cursor.execute(copy_into_sql(schema, table, entry["stage_relative_path"], entry["file_name"]))
            result = cursor.fetchall()
            rows_loaded = sum(int(row[3] or 0) for row in result)
            loaded_counts[key] = rows_loaded
            print(f"Loaded {rows_loaded} rows into {key}")
    finally:
        cursor.close()
        connection.close()

    execute_sql_file(PROJECT_ROOT / "sql" / "snowflake" / "02_create_views.sql")
    return loaded_counts


def main() -> int:
    parser = argparse.ArgumentParser(description="Load Snowflake RAW/MARTS tables from the S3 data lake external stage.")
    parser.add_argument("--manifest", default=str(DEFAULT_S3_MANIFEST_PATH), help="Local S3 data lake manifest path.")
    args = parser.parse_args()
    ensure_dirs()

    try:
        manifest = load_manifest(Path(args.manifest))
        loaded_counts = run_s3_copy(manifest)
    except Exception as error:
        print(f"ERROR: Snowflake S3 COPY load failed: {error}")
        return 1

    output = {
        "generated_at": utc_now_iso(),
        "load_method": "s3_external_stage_copy_into",
        "source_manifest": str(Path(args.manifest).relative_to(PROJECT_ROOT)),
        "s3_bucket": manifest["bucket"],
        "s3_prefix": manifest["prefix"],
        "s3_run_id": manifest["run_id"],
        "snowflake_database": SNOWFLAKE_DATABASE,
        "snowflake_integration": integration_name(),
        "snowflake_stage": f"RAW.{stage_name()}",
        "tables_loaded": loaded_counts,
    }
    write_json(S3_LOAD_MANIFEST_PATH, output)
    print(f"Wrote Snowflake S3 load manifest: {S3_LOAD_MANIFEST_PATH.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
