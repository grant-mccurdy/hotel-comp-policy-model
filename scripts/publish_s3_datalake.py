from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

from common import MANIFEST_DIR, PROJECT_ROOT, REPORT_DIR, count_rows, ensure_dirs, sha256_file, utc_now_iso, write_json
from load_snowflake_warehouse import CSV_TABLES


S3_MANIFEST_PATH = MANIFEST_DIR / "s3_datalake_manifest.json"
S3_REPORT_PATH = REPORT_DIR / "s3-datalake-manifest.md"
DEFAULT_PREFIX = "hotel-comp-policy-model"


def default_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def env_or_arg(value: str | None, env_name: str) -> str | None:
    return value or os.environ.get(env_name) or None


def clean_prefix(prefix: str) -> str:
    return prefix.strip("/")


def artifact_zone(schema: str) -> str:
    return "landing" if schema == "RAW" else "model-output"


def object_key(prefix: str, run_id: str, schema: str, table: str, path: Path) -> str:
    zone = artifact_zone(schema)
    return f"{clean_prefix(prefix)}/{zone}/{run_id}/{schema.lower()}/{table.lower()}/{path.name}"


def manifest_key(prefix: str, run_id: str) -> str:
    return f"{clean_prefix(prefix)}/_manifests/{run_id}/s3_datalake_manifest.json"


def latest_manifest_key(prefix: str) -> str:
    return f"{clean_prefix(prefix)}/_manifests/latest.json"


def build_manifest(bucket: str, prefix: str, run_id: str, dry_run: bool) -> dict[str, Any]:
    entries = []
    for schema, table, path, description in CSV_TABLES:
        row_count, column_count, header = count_rows(path)
        zone = artifact_zone(schema)
        key = object_key(prefix, run_id, schema, table, path)
        entries.append(
            {
                "schema": schema,
                "table": table,
                "description": description,
                "local_path": path.relative_to(PROJECT_ROOT).as_posix(),
                "file_name": path.name,
                "row_count": row_count,
                "column_count": column_count,
                "sha256": sha256_file(path),
                "s3_bucket": bucket,
                "s3_key": key,
                "s3_uri": f"s3://{bucket}/{key}",
                "stage_relative_path": f"{zone}/{run_id}/{schema.lower()}/{table.lower()}/{path.name}",
                "storage_zone": zone,
                "artifact_layer": "source_or_context" if schema == "RAW" else "derived_mart",
                "columns": header,
            }
        )

    return {
        "generated_at": utc_now_iso(),
        "dry_run": dry_run,
        "bucket": bucket,
        "prefix": clean_prefix(prefix),
        "run_id": run_id,
        "manifest_key": manifest_key(prefix, run_id),
        "latest_manifest_key": latest_manifest_key(prefix),
        "source_contract": "public-safe source/context artifacts -> S3 landing; generated policy artifacts -> S3 model-output",
        "entries": entries,
    }


def upload_manifest_and_files(manifest: dict[str, Any]) -> None:
    s3 = boto3.client(
        "s3",
        config=Config(
            connect_timeout=10,
            read_timeout=60,
            retries={"max_attempts": 3, "mode": "standard"},
        ),
    )
    bucket = manifest["bucket"]
    for entry in manifest["entries"]:
        path = PROJECT_ROOT / entry["local_path"]
        s3.put_object(
            Bucket=bucket,
            Key=entry["s3_key"],
            Body=path.read_bytes(),
            ServerSideEncryption="AES256",
            ContentType="text/csv",
            Metadata={
                "sha256": entry["sha256"],
                "row-count": str(entry["row_count"]),
                "column-count": str(entry["column_count"]),
                "artifact-layer": entry["artifact_layer"],
            },
        )
        print(f"Uploaded {entry['local_path']} -> {entry['s3_uri']}", flush=True)

    manifest_bytes = S3_MANIFEST_PATH.read_bytes()
    s3.put_object(
        Bucket=bucket,
        Key=manifest["manifest_key"],
        Body=manifest_bytes,
        ServerSideEncryption="AES256",
        ContentType="application/json",
    )
    s3.put_object(
        Bucket=bucket,
        Key=manifest["latest_manifest_key"],
        Body=manifest_bytes,
        ServerSideEncryption="AES256",
        ContentType="application/json",
    )
    print(f"Uploaded manifest -> s3://{bucket}/{manifest['manifest_key']}", flush=True)


def render_report(manifest: dict[str, Any]) -> str:
    public_bucket = "<configured-bucket>"
    lines = [
        "# S3 Data Lake Manifest",
        "",
        f"Generated at: `{manifest['generated_at']}`",
        "",
        f"- Dry run: `{manifest['dry_run']}`",
        f"- Bucket: `{public_bucket}`",
        f"- Prefix: `{manifest['prefix']}`",
        f"- Run ID: `{manifest['run_id']}`",
        f"- Manifest URI: `s3://{public_bucket}/{manifest['manifest_key']}`",
        "",
        "## Data Lake Objects",
        "",
        "| Warehouse table | S3 zone | Layer | Rows | Columns | S3 URI |",
        "| --- | --- | --- | ---: | ---: | --- |",
    ]
    for entry in manifest["entries"]:
        lines.append(
            f"| `{entry['schema']}.{entry['table']}` | `{entry['storage_zone']}` | `{entry['artifact_layer']}` | {entry['row_count']} | {entry['column_count']} | `s3://{public_bucket}/{entry['s3_key']}` |"
        )
    lines.extend(
        [
            "",
            "## Workflow Role",
            "",
            "S3 preserves versioned, public-safe artifacts with row counts, hashes, and provenance before Snowflake loads them into structured warehouse tables.",
            "",
            "Source and context snapshots use the `landing` zone. Python policy-engine outputs use the separate `model-output` zone because bootstrap and sensitivity computation remain appropriately outside SQL. Snowflake types, validates, and serves both layers through governed tables and views.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish generated project artifacts to an S3 data lake landing prefix.")
    parser.add_argument("--bucket", default=None, help="Target S3 bucket. Defaults to HOTEL_COMP_S3_BUCKET.")
    parser.add_argument("--prefix", default=None, help="S3 prefix. Defaults to HOTEL_COMP_S3_PREFIX or hotel-comp-policy-model.")
    parser.add_argument("--run-id", default=None, help="Run identifier. Defaults to UTC timestamp.")
    parser.add_argument("--dry-run", action="store_true", help="Write local manifest/report without uploading to S3.")
    args = parser.parse_args()

    ensure_dirs()
    bucket = env_or_arg(args.bucket, "HOTEL_COMP_S3_BUCKET")
    if not bucket:
        print("ERROR: provide --bucket or set HOTEL_COMP_S3_BUCKET.")
        return 1
    prefix = env_or_arg(args.prefix, "HOTEL_COMP_S3_PREFIX") or DEFAULT_PREFIX
    run_id = args.run_id or os.environ.get("HOTEL_COMP_S3_RUN_ID") or default_run_id()
    manifest = build_manifest(bucket, prefix, run_id, args.dry_run)
    write_json(S3_MANIFEST_PATH, manifest)
    S3_REPORT_PATH.write_text(render_report(manifest), encoding="utf-8")
    print(f"Wrote S3 manifest: {S3_MANIFEST_PATH.relative_to(PROJECT_ROOT)}")
    print(f"Wrote S3 report: {S3_REPORT_PATH.relative_to(PROJECT_ROOT)}")

    if args.dry_run:
        print("Dry run complete: no S3 files uploaded.")
        return 0

    try:
        upload_manifest_and_files(manifest)
    except NoCredentialsError:
        print("ERROR: AWS credentials are not configured. Run `aws login` or configure an AWS profile, then retry.")
        return 1
    except (BotoCoreError, ClientError) as error:
        print(f"ERROR: S3 upload failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
