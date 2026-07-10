from __future__ import annotations

from common import (
    PROPERTY_CONTEXT_MANIFEST_PATH,
    PROPERTY_CONTEXT_PATH,
    REPORT_DIR,
    ensure_dirs,
    utc_now_iso,
    write_csv,
    write_json,
)


PROPERTY_CONTEXT_REPORT = REPORT_DIR / "property-context-profile.md"

FIELDNAMES = [
    "captured_at",
    "source_family",
    "property_name",
    "property_role",
    "competitive_set_group",
    "source_url",
    "source_summary",
    "market",
    "neighborhood",
    "distance_to_target_miles",
    "hotel_class_proxy",
    "room_count_public",
    "has_rooftop_f_and_b",
    "has_lobby_lounge",
    "has_spa_wellness",
    "has_fitness",
    "has_pool_or_rooftop",
    "has_parking_or_fee_recovery_context",
    "has_beachfront_or_ocean_context",
    "has_events_spaces",
    "property_context_confidence",
    "rooftop_f_and_b_fit_modifier",
    "spa_wellness_fit_modifier",
    "lobby_lounge_fit_modifier",
    "parking_fee_fit_modifier",
    "late_checkout_fit_modifier",
    "room_upgrade_fit_modifier",
    "brand_experience_weight",
    "provenance",
    "public_context_use",
    "property_context_note",
]


def bool_text(value: bool) -> str:
    return str(value).lower()


def build_rows() -> list[dict[str, object]]:
    captured_at = utc_now_iso()
    rows = [
        {
            "property_name": "Santa Monica Proper Hotel",
            "property_role": "target_property",
            "competitive_set_group": "santa_monica_luxury_lifestyle",
            "source_url": "https://www.properhotel.com/santa-monica/",
            "source_summary": "Official site describes 262 rooms and suites, Calabra rooftop, Palma, Surya Spa, recovery suites, fitness, pool/rooftop, and events spaces.",
            "market": "Santa Monica, California",
            "neighborhood": "Downtown Santa Monica",
            "distance_to_target_miles": 0.0,
            "hotel_class_proxy": "luxury_lifestyle",
            "room_count_public": 262,
            "has_rooftop_f_and_b": True,
            "has_lobby_lounge": True,
            "has_spa_wellness": True,
            "has_fitness": True,
            "has_pool_or_rooftop": True,
            "has_parking_or_fee_recovery_context": True,
            "has_beachfront_or_ocean_context": True,
            "has_events_spaces": True,
            "property_context_confidence": 0.88,
            "brand_experience_weight": 0.92,
        },
        {
            "property_name": "Shutters on the Beach",
            "property_role": "competitive_set",
            "competitive_set_group": "santa_monica_luxury_beachfront",
            "source_url": "https://www.shuttersonthebeach.com/",
            "source_summary": "Official site describes a luxury oceanfront resort with direct beach access, dining, wellness, spa, fitness, and resort-style amenities.",
            "market": "Santa Monica, California",
            "neighborhood": "Santa Monica Beach",
            "distance_to_target_miles": 1.3,
            "hotel_class_proxy": "luxury_beachfront",
            "room_count_public": "",
            "has_rooftop_f_and_b": False,
            "has_lobby_lounge": True,
            "has_spa_wellness": True,
            "has_fitness": True,
            "has_pool_or_rooftop": True,
            "has_parking_or_fee_recovery_context": True,
            "has_beachfront_or_ocean_context": True,
            "has_events_spaces": True,
            "property_context_confidence": 0.78,
            "brand_experience_weight": 0.88,
        },
        {
            "property_name": "Hotel Casa del Mar",
            "property_role": "competitive_set",
            "competitive_set_group": "santa_monica_luxury_beachfront",
            "source_url": "https://www.hotelcasadelmar.com/",
            "source_summary": "Official site describes oceanfront dining, spa, fitness, romantic/coastal wellness experiences, hotel credit, and valet-parking offer language.",
            "market": "Santa Monica, California",
            "neighborhood": "Santa Monica Beach",
            "distance_to_target_miles": 1.4,
            "hotel_class_proxy": "luxury_beachfront",
            "room_count_public": "",
            "has_rooftop_f_and_b": False,
            "has_lobby_lounge": True,
            "has_spa_wellness": True,
            "has_fitness": True,
            "has_pool_or_rooftop": True,
            "has_parking_or_fee_recovery_context": True,
            "has_beachfront_or_ocean_context": True,
            "has_events_spaces": True,
            "property_context_confidence": 0.8,
            "brand_experience_weight": 0.9,
        },
        {
            "property_name": "Fairmont Miramar Hotel & Bungalows",
            "property_role": "competitive_set",
            "competitive_set_group": "santa_monica_luxury_resort",
            "source_url": "https://www.fairmont-miramar.com/",
            "source_summary": "Official site describes bungalows, restaurants, lobby lounge, wellness, gym/studio, spa, pool, events, and Santa Monica beach context.",
            "market": "Santa Monica, California",
            "neighborhood": "Ocean Avenue",
            "distance_to_target_miles": 0.7,
            "hotel_class_proxy": "luxury_resort",
            "room_count_public": "",
            "has_rooftop_f_and_b": False,
            "has_lobby_lounge": True,
            "has_spa_wellness": True,
            "has_fitness": True,
            "has_pool_or_rooftop": True,
            "has_parking_or_fee_recovery_context": True,
            "has_beachfront_or_ocean_context": True,
            "has_events_spaces": True,
            "property_context_confidence": 0.8,
            "brand_experience_weight": 0.9,
        },
        {
            "property_name": "The Georgian",
            "property_role": "competitive_set",
            "competitive_set_group": "santa_monica_lifestyle_boutique",
            "source_url": "https://www.thegeorgian.com/",
            "source_summary": "Official site describes oceanfront Santa Monica positioning, rooms/suites, dining, curated experiences, and private events.",
            "market": "Santa Monica, California",
            "neighborhood": "Ocean Avenue",
            "distance_to_target_miles": 0.9,
            "hotel_class_proxy": "lifestyle_boutique",
            "room_count_public": "",
            "has_rooftop_f_and_b": False,
            "has_lobby_lounge": True,
            "has_spa_wellness": False,
            "has_fitness": False,
            "has_pool_or_rooftop": False,
            "has_parking_or_fee_recovery_context": True,
            "has_beachfront_or_ocean_context": True,
            "has_events_spaces": True,
            "property_context_confidence": 0.68,
            "brand_experience_weight": 0.76,
        },
    ]
    for row in rows:
        row["captured_at"] = captured_at
        row["source_family"] = "public_property_context"
        row["provenance"] = "observed_public_property_context"
        row["public_context_use"] = "comp suitability, brand-context reasoning, and external-market comparability"
        row["property_context_note"] = (
            "Public/inferred property context only; not internal inventory, margin, service policy, staffing, or comp authorization data."
        )
        row["rooftop_f_and_b_fit_modifier"] = 1.22 if row["has_rooftop_f_and_b"] else (1.06 if row["has_lobby_lounge"] else 0.96)
        row["spa_wellness_fit_modifier"] = 1.18 if row["has_spa_wellness"] else 0.88
        row["lobby_lounge_fit_modifier"] = 1.12 if row["has_lobby_lounge"] else 0.94
        row["parking_fee_fit_modifier"] = 1.04 if row["has_parking_or_fee_recovery_context"] else 0.92
        row["late_checkout_fit_modifier"] = 1.04 if row["has_pool_or_rooftop"] or row["has_beachfront_or_ocean_context"] else 0.98
        row["room_upgrade_fit_modifier"] = 1.08 if row["hotel_class_proxy"].startswith("luxury") else 1.0
        for field in [
            "has_rooftop_f_and_b",
            "has_lobby_lounge",
            "has_spa_wellness",
            "has_fitness",
            "has_pool_or_rooftop",
            "has_parking_or_fee_recovery_context",
            "has_beachfront_or_ocean_context",
            "has_events_spaces",
        ]:
            row[field] = bool_text(bool(row[field]))
    return rows


def render_report(rows: list[dict[str, object]]) -> str:
    target = next(row for row in rows if row["property_role"] == "target_property")
    comp_count = sum(1 for row in rows if row["property_role"] == "competitive_set")
    return "\n".join(
        [
            "# Property Context Profile",
            "",
            "This layer turns public property context into comp-suitability modifiers.",
            "",
            "It is not internal hotel inventory, margin, staffing, occupancy, comp-policy, or guest-record data.",
            "",
            "## Target Property Context",
            "",
            f"- Property: `{target['property_name']}`",
            f"- Public room-count signal: `{target['room_count_public']}`",
            f"- Rooftop/F&B context: `{target['has_rooftop_f_and_b']}`",
            f"- Spa/wellness context: `{target['has_spa_wellness']}`",
            f"- Pool/rooftop context: `{target['has_pool_or_rooftop']}`",
            f"- Brand-experience weight: `{target['brand_experience_weight']}`",
            "",
            "## Coverage",
            "",
            f"- Competitive-set properties: `{comp_count}`",
            f"- Source family: `public_property_context`",
            f"- Provenance: `observed_public_property_context`",
            "",
            "## Decision Use",
            "",
            "- Strengthen comp options that fit the public property experience.",
            "- Penalize options that do not fit the property context.",
            "- Preserve public-safety boundaries by keeping all true cost, inventory, and policy fields out of this layer.",
            "",
        ]
    )


def main() -> int:
    ensure_dirs()
    rows = build_rows()
    write_csv(PROPERTY_CONTEXT_PATH, FIELDNAMES, rows)
    write_json(
        PROPERTY_CONTEXT_MANIFEST_PATH,
        {
            "generated_at": utc_now_iso(),
            "source_family": "public_property_context",
            "property_context_path": "data/sample/external_context/property_context_public.csv",
            "row_count": len(rows),
            "fields": FIELDNAMES,
            "public_safety_note": "Public property context only; no internal hotel data, costs, inventory, or policies.",
        },
    )
    PROPERTY_CONTEXT_REPORT.write_text(render_report(rows), encoding="utf-8")
    print(f"Wrote property context: {PROPERTY_CONTEXT_PATH.relative_to(PROPERTY_CONTEXT_PATH.parents[2])}")
    print(f"Wrote property context report: {PROPERTY_CONTEXT_REPORT.relative_to(PROPERTY_CONTEXT_REPORT.parents[1])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
