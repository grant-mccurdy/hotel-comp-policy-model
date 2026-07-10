from __future__ import annotations

import argparse
import random
import urllib.request
from pathlib import Path

from common import (
    BOOKING_MANIFEST_PATH,
    BOOKING_RAW_PATH,
    BOOKING_SAMPLE_PATH,
    BOOKING_SOURCE_URL,
    REQUIRED_BOOKING_FIELDS,
    REVIEW_STUB_MANIFEST_PATH,
    count_rows,
    ensure_dirs,
    read_csv_rows,
    sha256_file,
    utc_now_iso,
    write_csv,
    write_json,
)


SAMPLE_ROWS = 1000
SAMPLE_SEED = 20260703


def download_file(url: str, destination: Path, force: bool) -> None:
    if destination.exists() and not force:
        return
    request = urllib.request.Request(url, headers={"User-Agent": "hotel-comp-policy-model/0.1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        destination.write_bytes(response.read())


def write_booking_sample() -> int:
    header, rows = read_csv_rows(BOOKING_RAW_PATH)
    rng = random.Random(SAMPLE_SEED)
    sample_size = min(SAMPLE_ROWS, len(rows))
    selected_indices = sorted(rng.sample(range(len(rows)), sample_size))

    sample_rows = []
    for sample_id, source_index in enumerate(selected_indices, start=1):
        row = dict(rows[source_index])
        row["source_row_number"] = source_index + 2
        row["room_type_mismatch"] = str(
            row.get("reserved_room_type", "") != row.get("assigned_room_type", "")
        ).lower()
        row["stay_nights"] = str(
            int(float(row.get("stays_in_weekend_nights") or 0))
            + int(float(row.get("stays_in_week_nights") or 0))
        )
        row["sample_row_id"] = f"booking_sample_{sample_id:04d}"
        sample_rows.append(row)

    sample_fields = ["sample_row_id", "source_row_number", *header, "stay_nights", "room_type_mismatch"]
    write_csv(BOOKING_SAMPLE_PATH, sample_fields, sample_rows)
    return sample_size


def write_review_stub_manifest() -> None:
    write_json(
        REVIEW_STUB_MANIFEST_PATH,
        {
            "source_name": "515K Hotel Reviews Data in Europe",
            "source_url": "https://www.kaggle.com/datasets/jiashenliu/515k-hotel-reviews-data-in-europe",
            "acquisition_status": "documented_not_downloaded",
            "expected_local_raw_path": "data/raw/Hotel_Reviews.csv",
            "git_policy": "raw full file ignored",
            "stage1_role": "service-failure taxonomy and review-risk language calibration",
            "notes": [
                "The full review dataset is large and may require local Kaggle access.",
                "Stage 1 validates the contract and acquisition path without requiring the full file.",
                "Do not commit the raw review file."
            ],
            "recorded_at": utc_now_iso(),
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Acquire Hotel Booking Demand source data.")
    parser.add_argument("--force", action="store_true", help="Redownload the raw source file.")
    args = parser.parse_args()

    ensure_dirs()
    download_file(BOOKING_SOURCE_URL, BOOKING_RAW_PATH, args.force)
    row_count, column_count, header = count_rows(BOOKING_RAW_PATH)
    sample_count = write_booking_sample()

    missing_required = [field for field in REQUIRED_BOOKING_FIELDS if field not in header]
    manifest = {
        "source_name": "Hotel Booking Demand / TidyTuesday hotels.csv",
        "original_source": "Antonio, Almeida and Nunes (2019), Hotel booking demand datasets",
        "source_url": BOOKING_SOURCE_URL,
        "retrieved_at": utc_now_iso(),
        "local_raw_path": "data/raw/hotel_booking_demand_tidy_tuesday.csv",
        "raw_git_policy": "ignored",
        "sample_path": "data/sample/booking_stays_sample.csv",
        "sample_rows": sample_count,
        "sample_seed": SAMPLE_SEED,
        "row_count": row_count,
        "column_count": column_count,
        "sha256": sha256_file(BOOKING_RAW_PATH),
        "required_fields": REQUIRED_BOOKING_FIELDS,
        "missing_required_fields": missing_required,
        "columns": header,
        "stage1_role": "PMS-style booking and stay context calibration",
        "public_safety_note": "Source is public and anonymized; full raw download remains out of Git.",
    }
    write_json(BOOKING_MANIFEST_PATH, manifest)
    write_review_stub_manifest()

    if missing_required:
        print(f"Downloaded source, but required fields are missing: {missing_required}")
        return 1

    print(f"Acquired booking source: {row_count} rows, {column_count} columns")
    print(f"Wrote sample: {BOOKING_SAMPLE_PATH.relative_to(BOOKING_SAMPLE_PATH.parents[2])}")
    print(f"Wrote manifest: {BOOKING_MANIFEST_PATH.relative_to(BOOKING_MANIFEST_PATH.parents[2])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
