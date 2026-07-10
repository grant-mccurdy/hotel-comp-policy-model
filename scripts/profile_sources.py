from __future__ import annotations

from collections import Counter
from statistics import mean, median

from common import (
    BOOKING_RAW_PATH,
    MANIFEST_DIR,
    REPORT_DIR,
    REQUIRED_BOOKING_FIELDS,
    ensure_dirs,
    numeric_values,
    read_csv_rows,
    write_json,
)


PROFILE_JSON_PATH = MANIFEST_DIR / "hotel_booking_demand_profile.json"
PROFILE_MD_PATH = REPORT_DIR / "data-acquisition-profile.md"


def summarize_numeric(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {
            "count": 0,
            "min": None,
            "mean": None,
            "median": None,
            "max": None,
        }
    ordered = sorted(values)
    return {
        "count": len(values),
        "min": round(ordered[0], 4),
        "mean": round(mean(ordered), 4),
        "median": round(median(ordered), 4),
        "max": round(ordered[-1], 4),
    }


def top_counts(rows: list[dict[str, str]], field: str, limit: int = 8) -> list[dict[str, str | int]]:
    counts = Counter(row.get(field, "") or "<blank>" for row in rows)
    return [{"value": value, "count": count} for value, count in counts.most_common(limit)]


def room_type_mismatch_rate(rows: list[dict[str, str]]) -> float:
    if not rows:
        return 0.0
    mismatch_count = sum(
        1
        for row in rows
        if row.get("reserved_room_type", "") != row.get("assigned_room_type", "")
    )
    return round(mismatch_count / len(rows), 6)


def render_markdown(profile: dict) -> str:
    numeric_lines = []
    for field, summary in profile["numeric_summaries"].items():
        numeric_lines.append(
            "| {field} | {count} | {min} | {mean} | {median} | {max} |".format(
                field=field,
                count=summary["count"],
                min=summary["min"],
                mean=summary["mean"],
                median=summary["median"],
                max=summary["max"],
            )
        )

    categorical_sections = []
    for field, counts in profile["categorical_counts"].items():
        lines = [f"### `{field}`", "", "| Value | Count |", "| --- | ---: |"]
        for item in counts:
            lines.append(f"| `{item['value']}` | {item['count']} |")
        categorical_sections.append("\n".join(lines))

    return "\n".join(
        [
            "# Data Acquisition Profile",
            "",
            "## Booking Source",
            "",
            f"- Rows: `{profile['row_count']}`",
            f"- Columns: `{profile['column_count']}`",
            f"- Required fields present: `{profile['required_fields_present']}`",
            f"- Room type mismatch rate: `{profile['room_type_mismatch_rate']}`",
            "",
            "## Numeric Summaries",
            "",
            "| Field | Count | Min | Mean | Median | Max |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
            *numeric_lines,
            "",
            "## Categorical Counts",
            "",
            *categorical_sections,
            "",
            "## Notes",
            "",
            "- `adr` can include unusual values in this public dataset; downstream transforms should flag rather than silently drop them.",
            "- `room_type_mismatch` is derived from reserved vs assigned room type and is a useful service-friction proxy, not proof of a service failure.",
            "- The booking source has no compensation labels.",
            "",
        ]
    )


def main() -> int:
    ensure_dirs()
    if not BOOKING_RAW_PATH.exists():
        print("Missing raw booking source. Run scripts/acquire_booking_data.py first.")
        return 1

    header, rows = read_csv_rows(BOOKING_RAW_PATH)
    required_fields_present = all(field in header for field in REQUIRED_BOOKING_FIELDS)

    numeric_fields = [
        "lead_time",
        "stays_in_weekend_nights",
        "stays_in_week_nights",
        "days_in_waiting_list",
        "adr",
        "total_of_special_requests",
        "booking_changes",
    ]
    categorical_fields = [
        "hotel",
        "customer_type",
        "is_repeated_guest",
        "reserved_room_type",
        "assigned_room_type",
        "market_segment",
    ]

    profile = {
        "row_count": len(rows),
        "column_count": len(header),
        "required_fields_present": required_fields_present,
        "missing_required_fields": [field for field in REQUIRED_BOOKING_FIELDS if field not in header],
        "room_type_mismatch_rate": room_type_mismatch_rate(rows),
        "numeric_summaries": {
            field: summarize_numeric(numeric_values(rows, field)) for field in numeric_fields
        },
        "categorical_counts": {field: top_counts(rows, field) for field in categorical_fields},
    }

    write_json(PROFILE_JSON_PATH, profile)
    PROFILE_MD_PATH.write_text(render_markdown(profile), encoding="utf-8")
    print(f"Wrote profile: {PROFILE_MD_PATH.relative_to(PROFILE_MD_PATH.parents[1])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
