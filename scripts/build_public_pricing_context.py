from __future__ import annotations

from collections import defaultdict
from statistics import median

from common import (
    PROJECT_ROOT,
    PUBLIC_PRICING_CONTEXT_PATH,
    PUBLIC_PRICING_MANIFEST_PATH,
    RATE_SHOP_SNAPSHOT_PATH,
    REPORT_DIR,
    ensure_dirs,
    read_csv_rows,
    read_json,
    utc_now_iso,
    write_csv,
    write_json,
)
from policy_engine import as_float, clamp


PUBLIC_PRICING_REPORT = REPORT_DIR / "public-pricing-context.md"

FIELDNAMES = [
    "context_date",
    "target_public_rate",
    "comp_set_median_rate",
    "market_median_rate",
    "proper_vs_comp_set_index",
    "public_rate_pressure_index",
    "high_demand_rate_flag",
    "upgrade_opportunity_cost_proxy",
    "refund_cost_pressure",
    "quote_count",
    "target_property_quote_count",
    "comp_set_quote_count",
    "limited_availability_share",
    "free_cancellation_share",
    "target_rating",
    "comp_set_median_rating",
    "target_hotel_class",
    "comp_set_median_hotel_class",
    "target_amenity_count",
    "comp_set_median_amenity_count",
    "rate_context_confidence",
    "pricing_capture_method",
    "pricing_provenance",
    "pricing_context_note",
]


def boolish(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "limited"}


def quantile(values: list[float], q: float) -> float:
    if not values:
        return 0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def median_or_zero(values: list[float]) -> float:
    return float(median(values)) if values else 0.0


def hotel_class_number(value: object) -> float:
    text = str(value or "").lower().replace("-star", "").replace("star", "").strip()
    return as_float(text, 0)


def context_confidence(target_count: int, comp_count: int, quote_count: int, provenance: str) -> float:
    confidence = 0.2
    if target_count:
        confidence += 0.28
    confidence += min(comp_count, 4) * 0.08
    confidence += min(quote_count, 8) * 0.02
    if provenance == "observed_public_market_context":
        confidence += 0.12
    return round(clamp(confidence, 0, 0.95), 3)


def build_context(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    rows_by_date: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        check_in = row.get("check_in_date", "")
        if check_in:
            rows_by_date[check_in].append(row)

    daily_target_rates = []
    precomputed: dict[str, dict[str, float]] = {}
    for context_date, date_rows in rows_by_date.items():
        target_rates = [
            as_float(row.get("quoted_rate_before_taxes"), 0)
            for row in date_rows
            if row.get("property_role") == "target_property" and as_float(row.get("quoted_rate_before_taxes"), 0) > 0
        ]
        comp_rates = [
            as_float(row.get("quoted_rate_before_taxes"), 0)
            for row in date_rows
            if row.get("property_role") == "competitive_set" and as_float(row.get("quoted_rate_before_taxes"), 0) > 0
        ]
        all_rates = [
            as_float(row.get("quoted_rate_before_taxes"), 0)
            for row in date_rows
            if as_float(row.get("quoted_rate_before_taxes"), 0) > 0
        ]
        target_rate = median_or_zero(target_rates) or median_or_zero(all_rates)
        precomputed[context_date] = {
            "target_rate": target_rate,
            "comp_median": median_or_zero(comp_rates),
            "market_median": median_or_zero(all_rates),
        }
        if target_rate:
            daily_target_rates.append(target_rate)

    p10 = quantile(daily_target_rates, 0.1)
    p90 = quantile(daily_target_rates, 0.9)
    denominator = max(p90 - p10, 1)

    context_rows: list[dict[str, object]] = []
    for context_date in sorted(rows_by_date):
        date_rows = rows_by_date[context_date]
        target_rows = [row for row in date_rows if row.get("property_role") == "target_property"]
        comp_rows = [row for row in date_rows if row.get("property_role") == "competitive_set"]
        metrics = precomputed[context_date]
        target_rate = metrics["target_rate"]
        comp_median = metrics["comp_median"]
        market_median = metrics["market_median"]
        pressure = clamp((target_rate - p10) / denominator, 0, 1)
        proper_vs_comp = round(target_rate / comp_median, 3) if comp_median else 1.0
        limited_share = sum(1 for row in date_rows if str(row.get("availability_status", "")).lower() == "limited") / len(date_rows)
        free_cancellation_share = sum(1 for row in date_rows if boolish(row.get("free_cancellation_available"))) / len(date_rows)
        target_rating = median_or_zero([as_float(row.get("overall_rating"), 0) for row in target_rows if as_float(row.get("overall_rating"), 0) > 0])
        comp_rating = median_or_zero([as_float(row.get("overall_rating"), 0) for row in comp_rows if as_float(row.get("overall_rating"), 0) > 0])
        target_class = median_or_zero([hotel_class_number(row.get("extracted_hotel_class") or row.get("hotel_class")) for row in target_rows])
        comp_class = median_or_zero([hotel_class_number(row.get("extracted_hotel_class") or row.get("hotel_class")) for row in comp_rows])
        target_amenities = median_or_zero([as_float(row.get("amenity_count"), 0) for row in target_rows if as_float(row.get("amenity_count"), 0) > 0])
        comp_amenities = median_or_zero([as_float(row.get("amenity_count"), 0) for row in comp_rows if as_float(row.get("amenity_count"), 0) > 0])
        provenance_values = {row.get("provenance", "") for row in date_rows}
        provenance = "observed_public_market_context" if "observed_public_market_context" in provenance_values else "sample_seed_public_rate_shape"
        capture_methods = sorted({row.get("capture_method", "") for row in date_rows if row.get("capture_method")})
        high_demand = pressure >= 0.72 or limited_share >= 0.5 or proper_vs_comp >= 1.18

        context_rows.append(
            {
                "context_date": context_date,
                "target_public_rate": int(round(target_rate)),
                "comp_set_median_rate": int(round(comp_median)),
                "market_median_rate": int(round(market_median)),
                "proper_vs_comp_set_index": proper_vs_comp,
                "public_rate_pressure_index": round(pressure, 3),
                "high_demand_rate_flag": str(high_demand).lower(),
                "upgrade_opportunity_cost_proxy": int(round(target_rate * (0.08 + pressure * 0.22))),
                "refund_cost_pressure": round(0.86 + pressure * 0.42 + max(0, proper_vs_comp - 1) * 0.25, 3),
                "quote_count": len(date_rows),
                "target_property_quote_count": len(target_rows),
                "comp_set_quote_count": len(comp_rows),
                "limited_availability_share": round(limited_share, 3),
                "free_cancellation_share": round(free_cancellation_share, 3),
                "target_rating": round(target_rating, 2),
                "comp_set_median_rating": round(comp_rating, 2),
                "target_hotel_class": round(target_class, 1),
                "comp_set_median_hotel_class": round(comp_class, 1),
                "target_amenity_count": int(round(target_amenities)),
                "comp_set_median_amenity_count": int(round(comp_amenities)),
                "rate_context_confidence": context_confidence(len(target_rows), len(comp_rows), len(date_rows), provenance),
                "pricing_capture_method": ";".join(capture_methods),
                "pricing_provenance": provenance,
                "pricing_context_note": "public quoted pricing context; not internal ADR, occupancy, revenue, margin, or comp policy",
            }
        )
    return context_rows


def render_report(rows: list[dict[str, object]], manifest: dict[str, object]) -> str:
    high_pressure = sum(1 for row in rows if row["high_demand_rate_flag"] == "true")
    avg_pressure = sum(as_float(row["public_rate_pressure_index"], 0) for row in rows) / max(len(rows), 1)
    max_pressure = max(rows, key=lambda row: as_float(row["public_rate_pressure_index"], 0)) if rows else {}
    return "\n".join(
        [
            "# Public Pricing Context",
            "",
            "This layer turns public quoted-rate snapshots into decision modifiers for comp recommendations.",
            "",
            "The pricing fields are public market context or reproducible sample-seed context. They are not internal Proper Hotels ADR, occupancy, inventory, revenue, contribution margin, or comp policy.",
            "",
            "## Source Summary",
            "",
            f"- Acquisition mode: `{manifest.get('acquisition_mode', 'unknown')}`",
            f"- Rate-shop rows: `{manifest.get('row_count', 0)}`",
            f"- Context dates: `{len(rows)}`",
            f"- High-demand context dates: `{high_pressure}`",
            f"- Average public rate pressure index: `{avg_pressure:.3f}`",
            "",
            "## Strongest Public Rate-Pressure Day",
            "",
            f"- Date: `{max_pressure.get('context_date', '')}`",
            f"- Target public rate proxy: `${max_pressure.get('target_public_rate', 0)}`",
            f"- Competitive-set median: `${max_pressure.get('comp_set_median_rate', 0)}`",
            f"- Rate pressure index: `{max_pressure.get('public_rate_pressure_index', 0)}`",
            f"- Upgrade opportunity-cost proxy: `${max_pressure.get('upgrade_opportunity_cost_proxy', 0)}`",
            "",
            "## Decision Use",
            "",
            "- High public rate pressure increases the opportunity cost of room upgrades, late checkout, and partial room refunds.",
            "- The model should prefer high-perceived-value lower-margin gestures when they are suitable for the service failure.",
            "- Severe hotel-responsible cases may still justify refunds despite rate pressure.",
            "",
        ]
    )


def main() -> int:
    ensure_dirs()
    if not RATE_SHOP_SNAPSHOT_PATH.exists():
        print("Missing rate-shop snapshots. Run scripts/acquire_rate_shop_data.py first.")
        return 1
    _, snapshot_rows = read_csv_rows(RATE_SHOP_SNAPSHOT_PATH)
    context_rows = build_context(snapshot_rows)
    write_csv(PUBLIC_PRICING_CONTEXT_PATH, FIELDNAMES, context_rows)
    manifest = read_json(PUBLIC_PRICING_MANIFEST_PATH) if PUBLIC_PRICING_MANIFEST_PATH.exists() else {}
    manifest.update(
        {
            "pricing_context_generated_at": utc_now_iso(),
            "public_pricing_context_path": str(PUBLIC_PRICING_CONTEXT_PATH.relative_to(PROJECT_ROOT)),
            "context_row_count": len(context_rows),
            "context_fields": FIELDNAMES,
        }
    )
    write_json(PUBLIC_PRICING_MANIFEST_PATH, manifest)
    PUBLIC_PRICING_REPORT.write_text(render_report(context_rows, manifest), encoding="utf-8")
    print(f"Wrote public pricing context: {PUBLIC_PRICING_CONTEXT_PATH.relative_to(PROJECT_ROOT)}")
    print(f"Wrote public pricing report: {PUBLIC_PRICING_REPORT.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
