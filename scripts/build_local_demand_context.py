from __future__ import annotations

import random
from datetime import date, timedelta

from common import (
    LOCAL_DEMAND_CONTEXT_MANIFEST_PATH,
    LOCAL_DEMAND_CONTEXT_PATH,
    REPORT_DIR,
    ensure_dirs,
    utc_now_iso,
    write_csv,
    write_json,
)
from policy_engine import clamp


LOCAL_DEMAND_REPORT = REPORT_DIR / "local-demand-context.md"
RANDOM_SEED = 20260704

FIELDNAMES = [
    "captured_at",
    "context_date",
    "event_pressure_index",
    "weather_disruption_index",
    "local_demand_pressure_index",
    "high_local_demand_flag",
    "event_count",
    "primary_event_context",
    "weather_signal",
    "demand_context_confidence",
    "provenance",
    "public_context_use",
    "demand_context_note",
]


def event_context_for(day: date) -> tuple[float, int, str]:
    if day.month == 7 and day.day in {3, 4, 5}:
        return 0.92, 4, "holiday_coastal_demand"
    if day.month == 2 and day.day in {13, 14, 15}:
        return 0.82, 3, "holiday_romance_weekend"
    if day.month == 12 and day.day >= 24:
        return 0.78, 3, "year_end_holiday_travel"
    if day.month in {6, 7, 8, 9} and day.weekday() >= 4:
        return 0.7, 2, "summer_weekend_beach_demand"
    if day.weekday() >= 4:
        return 0.48, 1, "weekend_leisure_demand"
    return 0.22, 0, "baseline_local_demand"


def weather_context_for(rng: random.Random, day: date) -> tuple[float, str]:
    if day.month in {1, 2, 3, 12} and rng.random() < 0.22:
        return round(rng.uniform(0.42, 0.72), 3), "coastal_rain_or_wind_proxy"
    if day.month in {7, 8, 9} and rng.random() < 0.16:
        return round(rng.uniform(0.25, 0.45), 3), "heat_or_beach_crowding_proxy"
    return round(rng.uniform(0.02, 0.18), 3), "normal_weather_proxy"


def build_rows() -> list[dict[str, object]]:
    ensure_dirs()
    rng = random.Random(RANDOM_SEED)
    captured_at = utc_now_iso()
    rows: list[dict[str, object]] = []
    start = date(2026, 1, 1)
    for offset in range(365):
        context_date = start + timedelta(days=offset)
        event_pressure, event_count, primary_event = event_context_for(context_date)
        weather_pressure, weather_signal = weather_context_for(rng, context_date)
        demand_pressure = clamp(event_pressure * 0.68 + weather_pressure * 0.22 + rng.uniform(0.02, 0.12), 0, 1)
        rows.append(
            {
                "captured_at": captured_at,
                "context_date": context_date.isoformat(),
                "event_pressure_index": round(event_pressure, 3),
                "weather_disruption_index": round(weather_pressure, 3),
                "local_demand_pressure_index": round(demand_pressure, 3),
                "high_local_demand_flag": str(demand_pressure >= 0.68).lower(),
                "event_count": event_count,
                "primary_event_context": primary_event,
                "weather_signal": weather_signal,
                "demand_context_confidence": 0.32,
                "provenance": "sample_seed_local_demand_context",
                "public_context_use": "daily external demand-pressure modifier for room-comp opportunity-cost reasoning",
                "demand_context_note": "Sample-seed event/weather pressure proxy; replace with observed Ticketmaster/NOAA or other public feeds for production-grade public context.",
            }
        )
    return rows


def render_report(rows: list[dict[str, object]]) -> str:
    high_days = [row for row in rows if row["high_local_demand_flag"] == "true"]
    max_day = max(rows, key=lambda row: float(row["local_demand_pressure_index"]))
    return "\n".join(
        [
            "# Local Demand Context",
            "",
            "This layer provides daily event/weather pressure proxies for external demand context.",
            "",
            "The current version is sample-seed context, not observed occupancy, internal revenue, or live event/weather truth.",
            "",
            "## Source Summary",
            "",
            f"- Context dates: `{len(rows)}`",
            f"- High local-demand dates: `{len(high_days)}`",
            f"- Strongest context date: `{max_day['context_date']}`",
            f"- Strongest local demand pressure: `{max_day['local_demand_pressure_index']}`",
            f"- Strongest context label: `{max_day['primary_event_context']}`",
            "",
            "## Decision Use",
            "",
            "- Add external pressure to room-upgrade and late-checkout opportunity-cost reasoning.",
            "- Support explanation when the model preserves room inventory value.",
            "- Keep the distinction clear between public demand context and true hotel occupancy.",
            "",
        ]
    )


def main() -> int:
    ensure_dirs()
    rows = build_rows()
    write_csv(LOCAL_DEMAND_CONTEXT_PATH, FIELDNAMES, rows)
    write_json(
        LOCAL_DEMAND_CONTEXT_MANIFEST_PATH,
        {
            "generated_at": utc_now_iso(),
            "source_family": "local_demand_context",
            "local_demand_context_path": "data/sample/external_context/local_demand_context.csv",
            "row_count": len(rows),
            "fields": FIELDNAMES,
            "public_safety_note": "Sample-seed public-context proxy only; no internal occupancy, inventory, or revenue data.",
        },
    )
    LOCAL_DEMAND_REPORT.write_text(render_report(rows), encoding="utf-8")
    print(f"Wrote local demand context: {LOCAL_DEMAND_CONTEXT_PATH.relative_to(LOCAL_DEMAND_CONTEXT_PATH.parents[2])}")
    print(f"Wrote local demand report: {LOCAL_DEMAND_REPORT.relative_to(LOCAL_DEMAND_REPORT.parents[1])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
