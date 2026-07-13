from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
SAMPLE_DIR = PROJECT_ROOT / "data" / "sample"
RAW_SOURCE_DIR = SAMPLE_DIR / "raw_sources"
EXTERNAL_CONTEXT_DIR = SAMPLE_DIR / "external_context"
MART_DIR = PROJECT_ROOT / "data" / "marts"
CONTRACT_DIR = PROJECT_ROOT / "data" / "contracts"
MANIFEST_DIR = PROJECT_ROOT / "data" / "manifests"
REPORT_DIR = PROJECT_ROOT / "reports"
WAREHOUSE_DIR = PROJECT_ROOT / "data" / "warehouse"
SNOWFLAKE_EXTRACT_DIR = WAREHOUSE_DIR / "snowflake_extracts"

BOOKING_SOURCE_URL = (
    "https://raw.githubusercontent.com/rfordatascience/tidytuesday/"
    "main/data/2020/2020-02-11/hotels.csv"
)
BOOKING_RAW_PATH = RAW_DIR / "hotel_booking_demand_tidy_tuesday.csv"
BOOKING_SAMPLE_PATH = SAMPLE_DIR / "booking_stays_sample.csv"
BOOKING_MANIFEST_PATH = MANIFEST_DIR / "hotel_booking_demand_manifest.json"
REVIEW_STUB_MANIFEST_PATH = MANIFEST_DIR / "hotel_review_signals_acquisition_stub.json"
RATE_SHOP_SNAPSHOT_PATH = EXTERNAL_CONTEXT_DIR / "rate_shop_snapshots_sample.csv"
PROPERTY_CONTEXT_PATH = EXTERNAL_CONTEXT_DIR / "property_context_public.csv"
PROPER_PUBLIC_CONTEXT_PATH = EXTERNAL_CONTEXT_DIR / "proper_public_value_anchors.csv"
REVIEW_RISK_CONTEXT_PATH = EXTERNAL_CONTEXT_DIR / "review_risk_context.csv"
LOCAL_DEMAND_CONTEXT_PATH = EXTERNAL_CONTEXT_DIR / "local_demand_context.csv"
PUBLIC_PRICING_CONTEXT_PATH = MART_DIR / "public_pricing_context.csv"
EXTERNAL_CONTEXT_MODEL_IMPACT_PATH = MART_DIR / "external_context_model_impact.csv"
PUBLIC_PRICING_MANIFEST_PATH = MANIFEST_DIR / "public_pricing_manifest.json"
PROPERTY_CONTEXT_MANIFEST_PATH = MANIFEST_DIR / "property_context_manifest.json"
PROPER_PUBLIC_CONTEXT_MANIFEST_PATH = MANIFEST_DIR / "proper_public_value_anchors_manifest.json"
REVIEW_RISK_CONTEXT_MANIFEST_PATH = MANIFEST_DIR / "review_risk_context_manifest.json"
LOCAL_DEMAND_CONTEXT_MANIFEST_PATH = MANIFEST_DIR / "local_demand_context_manifest.json"
SYNTHETIC_GUEST_STAYS_PATH = SAMPLE_DIR / "synthetic_guest_stays.csv"
SYNTHETIC_SERVICE_FAILURES_PATH = SAMPLE_DIR / "synthetic_service_failures.csv"
COMP_CATALOG_PATH = SAMPLE_DIR / "comp_catalog.csv"
RECOVERY_CASE_MART_PATH = MART_DIR / "recovery_case_mart.csv"
COMP_RECOMMENDATIONS_PATH = MART_DIR / "comp_recommendations.csv"
COMP_POLICY_AUDIT_PATH = MART_DIR / "comp_policy_audit.csv"
POLICY_CASE_COMPARISON_PATH = MART_DIR / "policy_case_comparison.csv"
POLICY_DECISION_SUMMARY_PATH = MART_DIR / "policy_decision_summary.csv"
POLICY_SEGMENT_DIAGNOSTICS_PATH = MART_DIR / "policy_segment_diagnostics.csv"
POLICY_UNCERTAINTY_SUMMARY_PATH = MART_DIR / "policy_uncertainty_summary.csv"
POLICY_COMPARISON_MANIFEST_PATH = MANIFEST_DIR / "policy_comparison_manifest.json"
SYNTHETIC_GENERATION_MANIFEST_PATH = MANIFEST_DIR / "synthetic_comp_generation_manifest.json"
WAREHOUSE_DB_PATH = WAREHOUSE_DIR / "hotel_comp_policy.duckdb"
WAREHOUSE_MANIFEST_PATH = MANIFEST_DIR / "duckdb_warehouse_manifest.json"
SNOWFLAKE_POLICY_TRADEOFF_EXTRACT_PATH = SNOWFLAKE_EXTRACT_DIR / "policy_tradeoff.csv"
SNOWFLAKE_EXTRACT_MANIFEST_PATH = SNOWFLAKE_EXTRACT_DIR / "manifest.json"
CLOUD_EXECUTION_EVIDENCE_PATH = MANIFEST_DIR / "cloud_execution_evidence.json"
SNOWFLAKE_LOAD_CONTEXT_PATH = WAREHOUSE_DIR / "snowflake_load_context.json"

REQUIRED_BOOKING_FIELDS = [
    "hotel",
    "lead_time",
    "stays_in_weekend_nights",
    "stays_in_week_nights",
    "is_repeated_guest",
    "reserved_room_type",
    "assigned_room_type",
    "days_in_waiting_list",
    "customer_type",
    "adr",
    "total_of_special_requests",
]


def ensure_dirs() -> None:
    for path in [
        RAW_DIR,
        SAMPLE_DIR,
        RAW_SOURCE_DIR,
        EXTERNAL_CONTEXT_DIR,
        MART_DIR,
        CONTRACT_DIR,
        MANIFEST_DIR,
        REPORT_DIR,
        WAREHOUSE_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def numeric_values(rows: list[dict[str, str]], field: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        raw_value = row.get(field, "")
        if raw_value == "":
            continue
        try:
            values.append(float(raw_value))
        except ValueError:
            continue
    return values


def count_rows(path: Path) -> tuple[int, int, list[str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        rows = sum(1 for _ in reader)
    return rows, len(header), header
