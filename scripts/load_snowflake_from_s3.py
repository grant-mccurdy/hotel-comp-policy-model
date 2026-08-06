from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from typing import Any

from common import (
    MANIFEST_DIR,
    PROJECT_ROOT,
    SNOWFLAKE_LOAD_CONTEXT_PATH,
    count_rows,
    ensure_dirs,
    read_json,
    sha256_file,
    utc_now_iso,
    write_json,
)
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
RUN_ID_PATTERN = re.compile(r"^\d{8}T\d{6}Z$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def integration_name() -> str:
    return os.environ.get("SNOWFLAKE_S3_INTEGRATION", DEFAULT_INTEGRATION)


def stage_name() -> str:
    return os.environ.get("SNOWFLAKE_S3_STAGE", DEFAULT_STAGE)


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"Missing S3 manifest at {path}. Run `make s3-publish` first.")
    return read_json(path)


def entry_lookup(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw_entries = manifest.get("entries")
    if not isinstance(raw_entries, list):
        raise RuntimeError("S3 manifest entries must be a list")

    entries: dict[str, dict[str, Any]] = {}
    for entry in raw_entries:
        if not isinstance(entry, dict):
            raise RuntimeError("S3 manifest entries must be objects")
        schema = entry.get("schema")
        table = entry.get("table")
        if not isinstance(schema, str) or not isinstance(table, str):
            raise RuntimeError("S3 manifest entries require schema and table names")
        key = f"{schema}.{table}"
        if key in entries:
            raise RuntimeError(f"S3 manifest contains duplicate entry: {key}")
        entries[key] = entry
    return entries


def verify_manifest_contract(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    bucket = manifest.get("bucket")
    prefix = manifest.get("prefix")
    run_id = manifest.get("run_id")
    if not isinstance(bucket, str) or not bucket:
        raise RuntimeError("S3 manifest requires a bucket")
    if not isinstance(prefix, str) or not prefix or prefix != prefix.strip("/"):
        raise RuntimeError("S3 manifest requires a normalized prefix")
    if not isinstance(run_id, str) or not RUN_ID_PATTERN.fullmatch(run_id):
        raise RuntimeError("S3 manifest run_id must use YYYYMMDDTHHMMSSZ")

    entries = entry_lookup(manifest)
    expected_keys = {f"{schema}.{table}" for schema, table, _path, _description in CSV_TABLES}
    if set(entries) != expected_keys:
        missing = sorted(expected_keys - entries.keys())
        extra = sorted(entries.keys() - expected_keys)
        raise RuntimeError(f"S3 manifest contract mismatch; missing={missing}, extra={extra}")

    for schema, table, path, _description in CSV_TABLES:
        entry = entries[f"{schema}.{table}"]
        zone = "landing" if schema == "RAW" else "model-output"
        local_path = path.relative_to(PROJECT_ROOT).as_posix()
        stage_relative_path = (
            f"{zone}/{run_id}/{schema.lower()}/{table.lower()}/{path.name}"
        )
        s3_key = f"{prefix}/{stage_relative_path}"
        expected_fields = {
            "local_path": local_path,
            "file_name": path.name,
            "s3_bucket": bucket,
            "s3_key": s3_key,
            "s3_uri": f"s3://{bucket}/{s3_key}",
            "stage_relative_path": stage_relative_path,
            "storage_zone": zone,
        }
        for field, expected_value in expected_fields.items():
            if entry.get(field) != expected_value:
                raise RuntimeError(
                    f"S3 manifest contract mismatch for {schema}.{table}: {field}"
                )

        row_count = entry.get("row_count")
        column_count = entry.get("column_count")
        columns = entry.get("columns")
        checksum = entry.get("sha256")
        if not isinstance(row_count, int) or isinstance(row_count, bool) or row_count < 0:
            raise RuntimeError(f"S3 manifest has invalid row count for {schema}.{table}")
        if (
            not isinstance(column_count, int)
            or isinstance(column_count, bool)
            or column_count < 1
        ):
            raise RuntimeError(f"S3 manifest has invalid column count for {schema}.{table}")
        if not isinstance(columns, list) or len(columns) != column_count:
            raise RuntimeError(f"S3 manifest has invalid columns for {schema}.{table}")
        if not isinstance(checksum, str) or not SHA256_PATTERN.fullmatch(checksum):
            raise RuntimeError(f"S3 manifest has invalid checksum for {schema}.{table}")
    return entries


def verify_manifest_for_load(
    manifest: dict[str, Any],
    *,
    historical_manifest: bool,
) -> None:
    if manifest.get("dry_run") is not False:
        raise RuntimeError(
            "Refusing to load a dry-run manifest because its S3 objects are not evidenced as uploaded"
        )

    entries = verify_manifest_contract(manifest)
    if historical_manifest:
        return

    for schema, table, path, _description in CSV_TABLES:
        entry = entries[f"{schema}.{table}"]
        row_count, column_count, _header = count_rows(path)
        if row_count != int(entry["row_count"]) or column_count != int(entry["column_count"]):
            raise RuntimeError(f"S3 manifest shape mismatch for {schema}.{table}")
        if sha256_file(path) != entry["sha256"]:
            raise RuntimeError(f"S3 manifest checksum mismatch for {schema}.{table}")


def verify_local_manifest(manifest: dict[str, Any]) -> None:
    verify_manifest_for_load(manifest, historical_manifest=False)


def display_manifest_path(path: Path) -> str:
    resolved_path = path.resolve()
    try:
        return resolved_path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return resolved_path.as_posix()


def create_stage_sql(manifest: dict[str, Any]) -> str:
    url = f"s3://{manifest['bucket']}/{manifest['prefix']}/"
    return f"""
CREATE OR REPLACE STAGE {SNOWFLAKE_DATABASE}.RAW.{stage_name()}
  URL = '{url}'
  STORAGE_INTEGRATION = {integration_name()}
  FILE_FORMAT = {SNOWFLAKE_DATABASE}.RAW.CSV_WITH_HEADER
  COMMENT = 'S3 data lake external stage for hotel comp policy model artifacts.';
""".strip()


def copy_into_sql(schema: str, table: str, stage_relative_path: str, file_name: str) -> str:
    folder = stage_relative_path.rsplit("/", 1)[0]
    file_format = "CSV_WITH_HEADER" if schema == "RAW" else "MART_CSV_WITH_HEADER"
    return f"""
COPY INTO {fq(schema, table)}
FROM @{SNOWFLAKE_DATABASE}.RAW.{stage_name()}/{folder}/
FILE_FORMAT = (FORMAT_NAME = {SNOWFLAKE_DATABASE}.RAW.{file_format})
PATTERN = '.*{file_name}'
ON_ERROR = 'ABORT_STATEMENT';
""".strip()


def preflight_stage_files(cursor: Any, manifest: dict[str, Any]) -> None:
    entries = entry_lookup(manifest)
    missing: list[str] = []
    for schema, table, _path, _description in CSV_TABLES:
        key = f"{schema}.{table}"
        entry = entries[key]
        cursor.execute(
            f"LIST @{SNOWFLAKE_DATABASE}.RAW.{stage_name()}/"
            f"{entry['stage_relative_path']}"
        )
        staged_uris = {
            str(row[0])
            for row in cursor.fetchall()
            if row and row[0] is not None
        }
        if entry["s3_uri"] not in staged_uris:
            missing.append(key)
    if missing:
        raise RuntimeError(
            "Snowflake external stage preflight could not resolve manifest "
            f"objects for: {', '.join(missing)}"
        )
    print(f"Verified {len(entries)} manifest objects through the Snowflake stage")


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
        cursor.execute(
            f"""
            CREATE OR REPLACE FILE FORMAT {SNOWFLAKE_DATABASE}.RAW.MART_CSV_WITH_HEADER
              TYPE = CSV
              SKIP_HEADER = 1
              FIELD_OPTIONALLY_ENCLOSED_BY = '"'
              EMPTY_FIELD_AS_NULL = TRUE
              NULL_IF = ('', 'NULL', 'null');
            """
        )
        cursor.execute(create_stage_sql(manifest))
        preflight_stage_files(cursor, manifest)
        for schema, table, path, description in CSV_TABLES:
            key = f"{schema}.{table}"
            entry = entries[key]
            print(f"Loading {key} from {entry['s3_uri']}: {description}")
            cursor.execute(table_ddl(schema, table, path))
            cursor.execute(f"TRUNCATE TABLE {fq(schema, table)}")
            cursor.execute(copy_into_sql(schema, table, entry["stage_relative_path"], entry["file_name"]))
            result = cursor.fetchall()
            rows_loaded = sum(int(row[3] or 0) for row in result)
            expected_rows = int(entry["row_count"])
            if rows_loaded != expected_rows:
                raise RuntimeError(
                    f"Snowflake COPY row-count mismatch for {key}: "
                    f"expected {expected_rows}, loaded {rows_loaded}"
                )
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
    parser.add_argument(
        "--historical-manifest",
        action="store_true",
        help=(
            "Allow a previously uploaded manifest whose checksums no longer "
            "match current local files. Structural and path checks still apply."
        ),
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate the manifest contract without connecting to Snowflake.",
    )
    args = parser.parse_args()
    ensure_dirs()
    manifest_path = Path(args.manifest)

    try:
        manifest = load_manifest(manifest_path)
        verify_manifest_for_load(
            manifest,
            historical_manifest=args.historical_manifest,
        )
        if args.validate_only:
            print(
                "Validated Snowflake S3 load manifest: "
                f"{display_manifest_path(manifest_path)}"
            )
            return 0
        loaded_counts = run_s3_copy(manifest)
    except Exception as error:
        print(f"ERROR: Snowflake S3 COPY load failed: {error}")
        return 1

    output = {
        "generated_at": utc_now_iso(),
        "load_method": "s3_external_stage_copy_into",
        "source_manifest": display_manifest_path(manifest_path),
        "s3_bucket": manifest["bucket"],
        "s3_prefix": manifest["prefix"],
        "s3_run_id": manifest["run_id"],
        "snowflake_database": SNOWFLAKE_DATABASE,
        "snowflake_integration": integration_name(),
        "snowflake_stage": f"RAW.{stage_name()}",
        "tables_loaded": loaded_counts,
    }
    write_json(S3_LOAD_MANIFEST_PATH, output)
    write_json(
        SNOWFLAKE_LOAD_CONTEXT_PATH,
        {
            "generated_at": output["generated_at"],
            "load_method": output["load_method"],
            "source_run_id": output["s3_run_id"],
            "tables_loaded": len(loaded_counts),
        },
    )
    print(f"Wrote Snowflake S3 load manifest: {S3_LOAD_MANIFEST_PATH.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
