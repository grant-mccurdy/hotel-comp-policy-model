from __future__ import annotations

from common import (
    PROPER_PUBLIC_CONTEXT_MANIFEST_PATH,
    PROPER_PUBLIC_CONTEXT_PATH,
    REPORT_DIR,
    ensure_dirs,
    utc_now_iso,
    write_csv,
    write_json,
)


REPORT_PATH = REPORT_DIR / "proper-public-context.md"

FIELDNAMES = [
    "anchor_id",
    "captured_at",
    "property_name",
    "anchor_category",
    "public_value",
    "numeric_value",
    "unit",
    "source_url",
    "source_summary",
    "decision_use",
    "confidence",
    "provenance",
    "internal_cost_known",
    "public_safety_note",
]


def build_rows() -> list[dict[str, object]]:
    captured_at = utc_now_iso()
    base = {
        "captured_at": captured_at,
        "property_name": "Santa Monica Proper Hotel",
        "confidence": 0.95,
        "provenance": "observed_public_official_property_source",
        "internal_cost_known": "false",
        "public_safety_note": "Observed public context only; no internal cost, margin, inventory, guest record, or approved comp policy.",
    }
    rows = [
        {
            "anchor_id": "proper_room_count",
            "anchor_category": "property_scale",
            "public_value": "262 guest rooms and suites",
            "numeric_value": 262,
            "unit": "rooms_and_suites",
            "source_url": "https://www.properhotel.com/santa-monica/about/",
            "source_summary": "The official property overview describes 262 guest rooms and suites.",
            "decision_use": "property scale and synthetic operating-volume context",
        },
        {
            "anchor_id": "proper_room_types",
            "anchor_category": "room_inventory_context",
            "public_value": "rooms, suites, connecting rooms, wellness rooms",
            "numeric_value": "",
            "unit": "published_room_type_categories",
            "source_url": "https://www.properhotel.com/santa-monica/rooms/",
            "source_summary": "The official rooms page publishes standard rooms, suites, connecting configurations, and wellness-oriented rooms.",
            "decision_use": "room-upgrade option taxonomy without claiming live availability",
        },
        {
            "anchor_id": "proper_suite_late_checkout",
            "anchor_category": "suite_benefit",
            "public_value": "guaranteed 2 PM late checkout for published eligible suite perks",
            "numeric_value": 14,
            "unit": "local_hour",
            "source_url": "https://www.properhotel.com/santa-monica/rooms/",
            "source_summary": "The official rooms page lists guaranteed 2 PM late checkout among suite perks, subject to published exclusions.",
            "decision_use": "evidence that late checkout fits the property experience when operationally available",
        },
        {
            "anchor_id": "proper_destination_fee",
            "anchor_category": "published_guest_fee",
            "public_value": "$63.36 including tax",
            "numeric_value": 63.36,
            "unit": "USD_per_night",
            "source_url": "https://www.properhotel.com/santa-monica/compendium/",
            "source_summary": "The official guest compendium publishes a daily destination amenity fee including tax.",
            "decision_use": "guest-facing denomination anchor for a destination-fee waiver",
        },
        {
            "anchor_id": "proper_valet_fee",
            "anchor_category": "published_guest_fee",
            "public_value": "$84.96 including tax",
            "numeric_value": 84.96,
            "unit": "USD_per_night",
            "source_url": "https://www.properhotel.com/santa-monica/compendium/",
            "source_summary": "The official guest compendium publishes the overnight valet parking fee including tax.",
            "decision_use": "guest-facing denomination anchor for a valet or parking waiver",
        },
        {
            "anchor_id": "proper_dining_credit",
            "anchor_category": "published_offer_credit",
            "public_value": "$100 dining credit per stay",
            "numeric_value": 100,
            "unit": "USD_per_stay",
            "source_url": "https://www.properhotel.com/santa-monica/offers/stay-again-save-again/",
            "source_summary": "An official return-stay offer publishes a $100 dining credit per stay.",
            "decision_use": "guest-facing denomination anchor for Palma or Calabra dining recovery",
        },
        {
            "anchor_id": "proper_return_offer",
            "anchor_category": "published_return_offer",
            "public_value": "up to 10% off plus $100 dining credit",
            "numeric_value": 100,
            "unit": "USD_credit_plus_discount",
            "source_url": "https://www.properhotel.com/santa-monica/offers/stay-again-save-again/",
            "source_summary": "The official return-stay offer combines a public rate discount with a dining credit.",
            "decision_use": "evidence that relationship-preserving future-stay gestures fit current public merchandising",
        },
        {
            "anchor_id": "proper_recovery_suite_value",
            "anchor_category": "published_wellness_value",
            "public_value": "$195 published package value",
            "numeric_value": 195,
            "unit": "USD_per_session",
            "source_url": "https://www.properhotel.com/santa-monica/offers/movement-recovery/",
            "source_summary": "An official wellness package publishes a value for a Recovery Suite session.",
            "decision_use": "guest-facing denomination anchor for wellness recovery",
        },
        {
            "anchor_id": "proper_surya_treatment_value",
            "anchor_category": "published_wellness_value",
            "public_value": "$368 published package value",
            "numeric_value": 368,
            "unit": "USD_per_treatment",
            "source_url": "https://www.properhotel.com/santa-monica/offers/movement-recovery/",
            "source_summary": "An official wellness package publishes a value for one Surya Spa treatment including specified fees.",
            "decision_use": "guest-facing denomination anchor for spa recovery",
        },
        {
            "anchor_id": "proper_surya_discount",
            "anchor_category": "published_guest_benefit",
            "public_value": "15% hotel-guest discount on Surya Spa treatments",
            "numeric_value": 15,
            "unit": "percent",
            "source_url": "https://www.properhotel.com/santa-monica/surya-spa/",
            "source_summary": "The official spa page publishes a hotel-guest treatment discount.",
            "decision_use": "property-fit context; not an internal cost-rate estimate",
        },
        {
            "anchor_id": "proper_signature_outlets",
            "anchor_category": "property_experience",
            "public_value": "Calabra rooftop and Palma lobby lounge",
            "numeric_value": "",
            "unit": "published_outlets",
            "source_url": "https://www.properhotel.com/santa-monica/about/",
            "source_summary": "The official overview identifies Calabra and Palma as signature dining experiences.",
            "decision_use": "property-specific recovery gesture labeling and fit",
        },
    ]
    return [{**base, **row} for row in rows]


def render_report(rows: list[dict[str, object]]) -> str:
    lines = [
        "# Santa Monica Proper Public Context",
        "",
        "Observed public facts from official property pages calibrate guest-facing recovery denominations and option fit.",
        "They do not reveal internal cost, margin, availability, or approved comp policy.",
        "",
        f"- Public anchors: `{len(rows)}`",
        f"- Captured at: `{rows[0]['captured_at']}`",
        "",
        "| Anchor | Public value | Decision use | Source |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| `{row['anchor_id']}` | {row['public_value']} | {row['decision_use']} | [official page]({row['source_url']}) |"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "Public prices establish plausible guest-facing denominations. Estimated internal-cost ranges remain policy assumptions until property accounting data is available.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    ensure_dirs()
    rows = build_rows()
    write_csv(PROPER_PUBLIC_CONTEXT_PATH, FIELDNAMES, rows)
    write_json(
        PROPER_PUBLIC_CONTEXT_MANIFEST_PATH,
        {
            "generated_at": utc_now_iso(),
            "source_family": "official_santa_monica_proper_public_context",
            "path": "data/sample/external_context/proper_public_value_anchors.csv",
            "row_count": len(rows),
            "fields": FIELDNAMES,
            "public_safety_note": "Observed public property facts only; no internal costs, policies, inventory, or guest records.",
        },
    )
    REPORT_PATH.write_text(render_report(rows), encoding="utf-8")
    print(f"Wrote Proper public context: {PROPER_PUBLIC_CONTEXT_PATH}")
    print(f"Wrote Proper public context report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
