from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from common import count_rows, sha256_file  # noqa: E402
from load_snowflake_from_s3 import (  # noqa: E402
    CSV_TABLES,
    preflight_stage_files,
    verify_manifest_for_load,
)


def build_manifest(*, dry_run: bool = False) -> dict[str, object]:
    bucket = "portfolio-test-bucket"
    prefix = "hotel-comp-policy-model"
    run_id = "20260728T215348Z"
    entries = []
    for schema, table, path, description in CSV_TABLES:
        row_count, column_count, columns = count_rows(path)
        zone = "landing" if schema == "RAW" else "model-output"
        stage_relative_path = (
            f"{zone}/{run_id}/{schema.lower()}/{table.lower()}/{path.name}"
        )
        key = f"{prefix}/{stage_relative_path}"
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
                "stage_relative_path": stage_relative_path,
                "storage_zone": zone,
                "artifact_layer": (
                    "source_or_context" if schema == "RAW" else "derived_mart"
                ),
                "columns": columns,
            }
        )
    return {
        "dry_run": dry_run,
        "bucket": bucket,
        "prefix": prefix,
        "run_id": run_id,
        "entries": entries,
    }


class StageCursor:
    def __init__(
        self,
        manifest: dict[str, object],
        *,
        missing_uri: str | None = None,
    ) -> None:
        self.entries = manifest["entries"]
        self.missing_uri = missing_uri
        self.queries: list[str] = []
        self.rows: list[tuple[str]] = []

    def execute(self, query: str) -> StageCursor:
        self.queries.append(query)
        self.rows = []
        for entry in self.entries:
            if query.endswith(f"/{entry['stage_relative_path']}"):
                if entry["s3_uri"] != self.missing_uri:
                    self.rows = [(entry["s3_uri"],)]
                break
        return self

    def fetchall(self) -> list[tuple[str]]:
        return self.rows


class S3LoaderContractTests(unittest.TestCase):
    def test_current_uploaded_manifest_matches_local_artifacts(self) -> None:
        verify_manifest_for_load(
            build_manifest(),
            historical_manifest=False,
        )

    def test_dry_run_manifest_is_rejected_before_snowflake_mutation(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "dry-run manifest"):
            verify_manifest_for_load(
                build_manifest(dry_run=True),
                historical_manifest=False,
            )

    def test_historical_manifest_can_restore_without_current_checksums(self) -> None:
        manifest = build_manifest()
        manifest["entries"][0]["row_count"] += 1
        manifest["entries"][0]["sha256"] = "0" * 64

        verify_manifest_for_load(
            manifest,
            historical_manifest=True,
        )
        with self.assertRaisesRegex(RuntimeError, "shape mismatch"):
            verify_manifest_for_load(
                manifest,
                historical_manifest=False,
            )

    def test_historical_manifest_still_enforces_s3_paths(self) -> None:
        manifest = build_manifest()
        manifest["entries"][0]["stage_relative_path"] = "landing/wrong.csv"

        with self.assertRaisesRegex(RuntimeError, "stage_relative_path"):
            verify_manifest_for_load(
                manifest,
                historical_manifest=True,
            )

    def test_duplicate_table_entries_are_rejected(self) -> None:
        manifest = build_manifest()
        manifest["entries"].append(dict(manifest["entries"][0]))

        with self.assertRaisesRegex(RuntimeError, "duplicate entry"):
            verify_manifest_for_load(
                manifest,
                historical_manifest=True,
            )

    def test_stage_preflight_resolves_every_manifest_object(self) -> None:
        manifest = build_manifest()
        cursor = StageCursor(manifest)

        preflight_stage_files(cursor, manifest)

        self.assertEqual(len(cursor.queries), len(CSV_TABLES))

    def test_stage_preflight_fails_before_load_when_object_is_missing(self) -> None:
        manifest = build_manifest()
        missing_uri = manifest["entries"][0]["s3_uri"]
        cursor = StageCursor(manifest, missing_uri=missing_uri)

        with self.assertRaisesRegex(RuntimeError, "STG_PMS_RESERVATIONS"):
            preflight_stage_files(cursor, manifest)


if __name__ == "__main__":
    unittest.main()
