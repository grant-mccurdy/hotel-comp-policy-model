from __future__ import annotations

import random
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

from common import (
    BOOKING_SAMPLE_PATH,
    COMP_CATALOG_PATH,
    RAW_SOURCE_DIR,
    REPORT_DIR,
    SYNTHETIC_GENERATION_MANIFEST_PATH,
    ensure_dirs,
    read_csv_rows,
    utc_now_iso,
    write_csv,
    write_json,
)
from generate_synthetic_comp_data import (
    RANDOM_SEED,
    comp_catalog,
    generate_failures,
    generate_stays,
    weighted_choice,
)
from policy_engine import as_float, clamp


PMS_RESERVATIONS_PATH = RAW_SOURCE_DIR / "raw_pms_reservations.csv"
CRM_PROFILES_PATH = RAW_SOURCE_DIR / "raw_guest_profiles_crm.csv"
SERVICE_TICKETS_PATH = RAW_SOURCE_DIR / "raw_service_tickets.csv"
COMP_LEDGER_PATH = RAW_SOURCE_DIR / "raw_comp_ledger.csv"
POS_CHARGES_PATH = RAW_SOURCE_DIR / "raw_pos_outlet_charges.csv"
REVIEWS_SURVEYS_PATH = RAW_SOURCE_DIR / "raw_reviews_surveys.csv"
OPS_DAILY_PATH = RAW_SOURCE_DIR / "raw_ops_daily.csv"


ISSUE_DIRTY_LABELS = {
    "room_readiness_delay": ["room_not_ready", "checkin wait", "late room", "arrival delay"],
    "room_assignment_expectation_gap": ["wrong room", "room type mismatch", "view issue", "upgrade expectation"],
    "housekeeping_miss": ["housekeeping", "room clean issue", "hk miss", "linen/turndown"],
    "maintenance_issue": ["engineering", "maintenance", "room equipment", "facilities issue"],
    "noise_disruption": ["noise", "sleep disruption", "neighbor noise", "street noise"],
    "billing_or_fee_dispute": ["billing", "fee dispute", "charge question", "folio issue"],
    "f_and_b_service_lapse": ["fb service", "restaurant issue", "dining delay", "order problem"],
    "rooftop_pool_access_issue": ["pool access", "rooftop issue", "pool wait", "cabana issue"],
    "spa_wellness_service_issue": ["spa issue", "wellness service", "treatment delay", "spa recovery"],
    "valet_or_parking_delay": ["valet wait", "parking", "car delay", "arrival valet"],
}

COMP_DIRTY_LABELS = {
    "manager_note": ["Manager Note", "GM follow-up", "Personal apology", "No dollar comp"],
    "amenity_gesture": ["Amenity", "Welcome amenity", "In-room gesture", "Bottle/amenity"],
    "late_checkout": ["Late checkout", "4pm checkout", "Extended departure", "Late CO"],
    "parking_fee_waiver": ["Parking waiver", "Valet comp", "Destination fee waive", "Parking/Dest fee"],
    "lobby_lounge_credit": ["Lounge credit", "Palma credit", "Bar credit", "Lobby F&B"],
    "rooftop_f_and_b_credit": ["F&B", "Food Credit", "Calabra recovery", "Rooftop credit", "Restaurant credit"],
    "spa_wellness_credit": ["Spa credit", "Wellness credit", "Treatment recovery", "Surya-style credit"],
    "room_upgrade": ["Upgrade", "Room move upgrade", "Suite upgrade", "View upgrade"],
    "partial_room_refund": ["Refund", "Room rate adjustment", "Partial night", "Rate credit"],
    "future_stay_credit": ["Future stay", "Return credit", "Comeback offer", "Future night credit"],
}


def make_guest_lookup_key(index: int) -> str:
    return f"guest_key_{index:05d}"


def parse_date(value: object) -> date:
    return datetime.fromisoformat(str(value)).date()


def build_pms_reservations(stays: list[dict[str, object]], rng: random.Random) -> list[dict[str, object]]:
    rows = []
    for index, stay in enumerate(stays, start=1):
        arrival = parse_date(stay["arrival_date"])
        departure = arrival + timedelta(days=int(stay["stay_nights"]))
        channel = str(stay["booking_channel_proxy"])
        masked_email = channel == "ota" and rng.random() < 0.62
        room_move_count = 1 if stay["room_type_mismatch"] == "true" and rng.random() < 0.55 else 0
        if rng.random() < 0.04:
            room_move_count += 1
        rows.append(
            {
                "pms_reservation_id": f"PMS{index:06d}",
                "stay_id": stay["stay_id"],
                "crm_guest_id": f"CRM{index:06d}",
                "guest_lookup_key": make_guest_lookup_key(index),
                "email_key": "" if masked_email or rng.random() < 0.08 else f"guest{index:06d}@example.invalid",
                "ota_masked_email_flag": str(masked_email).lower(),
                "arrival_date": arrival.isoformat(),
                "departure_date": departure.isoformat(),
                "room_number_proxy": str(300 + rng.randrange(1, 180)),
                "reserved_room_type_proxy": stay["reserved_room_type_proxy"],
                "assigned_room_type_proxy": stay["assigned_room_type_proxy"],
                "room_move_count": room_move_count,
                "nightly_rate": stay["nightly_rate"],
                "stay_value": stay["stay_value"],
                "booking_channel_proxy": channel,
                "special_requests_count": stay["special_requests_count"],
                "reservation_status": "stayed",
                "pms_source_loaded_at": (arrival - timedelta(days=rng.randrange(1, 30))).isoformat(),
            }
        )
    return rows


def build_crm_profiles(pms_rows: list[dict[str, object]], stays_by_id: dict[str, dict[str, object]], rng: random.Random) -> list[dict[str, object]]:
    rows = []
    for pms in pms_rows:
        stay = stays_by_id[str(pms["stay_id"])]
        rows.append(
            {
                "crm_guest_id": pms["crm_guest_id"],
                "guest_lookup_key": pms["guest_lookup_key"],
                "email_key": pms["email_key"] if rng.random() > 0.1 else "",
                "loyalty_tier": stay["guest_tier"],
                "traveler_segment": stay["traveler_segment"],
                "estimated_lifetime_value": stay["estimated_lifetime_value"] if rng.random() > 0.09 else "",
                "profile_quality_score": round(rng.uniform(0.72, 0.99), 3),
                "duplicate_profile_flag": "false",
                "contactable_flag": str(pms["email_key"] != "").lower(),
                "last_profile_update_date": (parse_date(pms["arrival_date"]) - timedelta(days=rng.randrange(0, 180))).isoformat(),
            }
        )
        if rng.random() < 0.07:
            rows.append(
                {
                    "crm_guest_id": f"{pms['crm_guest_id']}_DUP",
                    "guest_lookup_key": pms["guest_lookup_key"],
                    "email_key": "",
                    "loyalty_tier": weighted_choice(
                        rng,
                        [("new_guest", 0.4), ("returning_guest", 0.3), ("loyalty_guest", 0.2), ("vip_guest", 0.1)],
                    ),
                    "traveler_segment": stay["traveler_segment"],
                    "estimated_lifetime_value": "",
                    "profile_quality_score": round(rng.uniform(0.35, 0.68), 3),
                    "duplicate_profile_flag": "true",
                    "contactable_flag": "false",
                    "last_profile_update_date": (parse_date(pms["arrival_date"]) - timedelta(days=rng.randrange(90, 500))).isoformat(),
                }
            )
    return rows


def build_service_tickets(
    failures: list[dict[str, object]],
    pms_by_stay: dict[str, dict[str, object]],
    rng: random.Random,
) -> list[dict[str, object]]:
    rows = []
    for index, failure in enumerate(failures, start=1):
        pms = pms_by_stay[str(failure["stay_id"])]
        arrival = parse_date(pms["arrival_date"])
        opened = arrival + timedelta(days=rng.randrange(0, max(1, int((parse_date(pms["departure_date"]) - arrival).days))))
        close_delay = timedelta(minutes=int(as_float(failure["resolution_delay_minutes"], 45)))
        missing_reservation = rng.random() < 0.14
        missing_crm = rng.random() < 0.19
        missing_severity = rng.random() < 0.13
        rows.append(
            {
                "service_ticket_id": f"TKT{index:06d}",
                "pms_reservation_id": "" if missing_reservation else pms["pms_reservation_id"],
                "crm_guest_id": "" if missing_crm else pms["crm_guest_id"],
                "guest_lookup_key": pms["guest_lookup_key"] if rng.random() > 0.08 else "",
                "room_number_proxy": pms["room_number_proxy"] if rng.random() > 0.16 else "",
                "opened_timestamp": f"{opened.isoformat()}T{rng.randrange(7, 23):02d}:{rng.randrange(0, 60):02d}:00",
                "closed_timestamp": f"{opened.isoformat()}T{min(23, 8 + int(close_delay.seconds // 3600)):02d}:{rng.randrange(0, 60):02d}:00",
                "department_raw": weighted_choice(
                    rng,
                    [
                        ("front_desk", 0.24),
                        ("rooms", 0.21),
                        ("housekeeping", 0.18),
                        ("engineering", 0.13),
                        ("food_beverage", 0.14),
                        ("spa_wellness", 0.05),
                        ("valet", 0.05),
                    ],
                ),
                "issue_code_raw": rng.choice(ISSUE_DIRTY_LABELS[str(failure["failure_category"])]),
                "severity_raw": "" if missing_severity else failure["severity"],
                "reported_in_stay": failure["reported_in_stay"],
                "guest_notes_text": failure["guest_complaint_text"],
                "ticket_status": weighted_choice(rng, [("closed", 0.78), ("manager_review", 0.12), ("open", 0.05), ("merged_duplicate", 0.05)]),
                "source_loaded_at": (opened + timedelta(days=rng.randrange(0, 4))).isoformat(),
            }
        )
    return rows


def choose_historical_comp(rng: random.Random, severity: int, issue_code_raw: str) -> str:
    if severity >= 5:
        return weighted_choice(rng, [("partial_room_refund", 0.38), ("future_stay_credit", 0.2), ("rooftop_f_and_b_credit", 0.22), ("spa_wellness_credit", 0.12), ("room_upgrade", 0.08)])
    if severity >= 4:
        return weighted_choice(rng, [("rooftop_f_and_b_credit", 0.33), ("spa_wellness_credit", 0.16), ("room_upgrade", 0.15), ("partial_room_refund", 0.14), ("lobby_lounge_credit", 0.12), ("late_checkout", 0.1)])
    if "parking" in issue_code_raw or "valet" in issue_code_raw:
        return "parking_fee_waiver"
    return weighted_choice(rng, [("manager_note", 0.12), ("amenity_gesture", 0.24), ("late_checkout", 0.14), ("lobby_lounge_credit", 0.16), ("rooftop_f_and_b_credit", 0.2), ("parking_fee_waiver", 0.08), ("room_upgrade", 0.06)])


def build_comp_ledger(
    tickets: list[dict[str, object]],
    pms_rows: list[dict[str, object]],
    rng: random.Random,
) -> list[dict[str, object]]:
    rows = []
    catalog_by_code = {str(row["comp_code"]): row for row in comp_catalog()}
    for ticket in tickets:
        severity = int(as_float(ticket["severity_raw"], rng.choice([2, 3, 4])))
        if rng.random() > (0.22 + severity * 0.12):
            continue
        code = choose_historical_comp(rng, severity, str(ticket["issue_code_raw"]))
        catalog = catalog_by_code[code]
        default_value = int(as_float(catalog["face_value_default"], 0))
        value = int(round(clamp(default_value * rng.uniform(0.75, 1.45), as_float(catalog["face_value_min"], 0), as_float(catalog["face_value_max"], default_value)) / 5) * 5)
        cost = int(round(value * as_float(catalog["estimated_internal_cost_rate"], 0)))
        rows.append(
            {
                "comp_ledger_id": f"CMP{len(rows) + 1:06d}",
                "service_ticket_id": ticket["service_ticket_id"] if rng.random() > 0.18 else "",
                "pms_reservation_id": ticket["pms_reservation_id"] if rng.random() > 0.1 else "",
                "guest_lookup_key": ticket["guest_lookup_key"] if rng.random() > 0.2 else "",
                "comp_action_raw": rng.choice(COMP_DIRTY_LABELS[code]),
                "face_value": value,
                "estimated_internal_cost": cost,
                "approval_status": weighted_choice(rng, [("approved", 0.72), ("manager_override", 0.12), ("pending", 0.08), ("rejected", 0.08)]),
                "approver_role": weighted_choice(rng, [("front_office_manager", 0.36), ("guest_experience_manager", 0.3), ("rooms_director", 0.16), ("general_manager", 0.08), ("night_manager", 0.1)]),
                "posted_date": str(ticket["opened_timestamp"])[:10],
                "ledger_loaded_at": (datetime.fromisoformat(str(ticket["opened_timestamp"])) + timedelta(days=rng.randrange(0, 7))).isoformat(),
            }
        )
    for _ in range(24):
        pms = rng.choice(pms_rows)
        code = weighted_choice(rng, [("rooftop_f_and_b_credit", 0.3), ("parking_fee_waiver", 0.2), ("amenity_gesture", 0.18), ("lobby_lounge_credit", 0.14), ("partial_room_refund", 0.1), ("room_upgrade", 0.08)])
        catalog = catalog_by_code[code]
        value = int(as_float(catalog["face_value_default"], 0))
        rows.append(
            {
                "comp_ledger_id": f"CMP{len(rows) + 1:06d}",
                "service_ticket_id": "",
                "pms_reservation_id": pms["pms_reservation_id"] if rng.random() > 0.35 else "",
                "guest_lookup_key": pms["guest_lookup_key"] if rng.random() > 0.25 else "",
                "comp_action_raw": rng.choice(COMP_DIRTY_LABELS[code]),
                "face_value": value,
                "estimated_internal_cost": int(round(value * as_float(catalog["estimated_internal_cost_rate"], 0))),
                "approval_status": "approved",
                "approver_role": "front_office_manager",
                "posted_date": pms["arrival_date"],
                "ledger_loaded_at": pms["arrival_date"],
            }
        )
    return rows


def build_pos_charges(pms_rows: list[dict[str, object]], rng: random.Random) -> list[dict[str, object]]:
    outlets = [
        ("calabra_rooftop", 0.31, 190),
        ("palma_lobby_lounge", 0.22, 95),
        ("spa_wellness", 0.11, 260),
        ("valet_parking", 0.16, 70),
        ("mini_bar_amenity", 0.08, 45),
        ("in_room_dining", 0.12, 130),
    ]
    rows = []
    for pms in pms_rows:
        charges = rng.randrange(0, 5)
        arrival = parse_date(pms["arrival_date"])
        for _ in range(charges):
            outlet, _, mean_amount = weighted_choice_obj(rng, [(item, item[1]) for item in outlets])
            amount = int(round(clamp(rng.lognormvariate(4.1, 0.6) / 60 * mean_amount, 18, 900) / 5) * 5)
            rows.append(
                {
                    "pos_charge_id": f"POS{len(rows) + 1:07d}",
                    "pms_reservation_id": pms["pms_reservation_id"] if rng.random() > 0.04 else "",
                    "guest_lookup_key": pms["guest_lookup_key"] if rng.random() > 0.1 else "",
                    "outlet": outlet,
                    "charge_amount": amount,
                    "charge_timestamp": (arrival + timedelta(days=rng.randrange(0, max(1, int((parse_date(pms["departure_date"]) - arrival).days))))).isoformat(),
                    "void_or_adjustment_flag": str(rng.random() < 0.05).lower(),
                }
            )
    return rows


def weighted_choice_obj(rng: random.Random, choices: list[tuple[tuple[str, float, int], float]]) -> tuple[str, float, int]:
    total = sum(weight for _, weight in choices)
    pick = rng.uniform(0, total)
    cumulative = 0.0
    for value, weight in choices:
        cumulative += weight
        if pick <= cumulative:
            return value
    return choices[-1][0]


def build_reviews_surveys(
    tickets: list[dict[str, object]],
    pms_by_reservation: dict[str, dict[str, object]],
    rng: random.Random,
) -> list[dict[str, object]]:
    rows = []
    for ticket in tickets:
        if rng.random() > 0.48:
            continue
        pms_id = str(ticket.get("pms_reservation_id", ""))
        pms = pms_by_reservation.get(pms_id)
        departure = parse_date(pms["departure_date"]) if pms else datetime.fromisoformat(str(ticket["opened_timestamp"])).date() + timedelta(days=1)
        severity = as_float(ticket.get("severity_raw"), 3)
        score = round(clamp(9.2 - severity * rng.uniform(0.65, 1.15) + rng.gauss(0, 0.55), 1, 10), 1)
        rows.append(
            {
                "review_id": f"REV{len(rows) + 1:06d}",
                "pms_reservation_id": pms_id if rng.random() > 0.22 else "",
                "guest_lookup_key": ticket["guest_lookup_key"] if rng.random() > 0.18 else "",
                "review_date": (departure + timedelta(days=rng.randrange(1, 21))).isoformat(),
                "survey_or_review_source": weighted_choice(rng, [("post_stay_survey", 0.48), ("public_review_proxy", 0.32), ("guest_email_reply", 0.2)]),
                "post_stay_score": score,
                "negative_text": ticket["guest_notes_text"],
                "sentiment_intensity": round(clamp(severity / 5 + rng.gauss(0, 0.12), 0, 1), 3),
                "review_loaded_at": (departure + timedelta(days=rng.randrange(2, 28))).isoformat(),
            }
        )
    return rows


def build_ops_daily(rng: random.Random) -> list[dict[str, object]]:
    rows = []
    start = date(2026, 1, 1)
    for offset in range(365):
        service_date = start + timedelta(days=offset)
        seasonal = 0.22 if service_date.month in {5, 6, 7, 8, 9} else 0
        weekend = 0.08 if service_date.weekday() >= 4 else 0
        occupancy = round(clamp(rng.betavariate(5, 2.3) + seasonal + weekend - 0.16, 0.32, 0.99), 3)
        rows.append(
            {
                "service_date": service_date.isoformat(),
                "occupancy_rate": occupancy,
                "housekeeping_pressure": round(clamp(occupancy + rng.gauss(0, 0.08), 0, 1), 3),
                "front_desk_queue_pressure": round(clamp(occupancy * 0.82 + rng.gauss(0, 0.12), 0, 1), 3),
                "maintenance_backlog": rng.randrange(0, 16),
                "food_beverage_capacity_pressure": round(clamp(occupancy * 0.74 + weekend + rng.gauss(0, 0.11), 0, 1), 3),
                "spa_capacity_pressure": round(clamp(occupancy * 0.58 + seasonal + rng.gauss(0, 0.1), 0, 1), 3),
            }
        )
    return rows


def write_source_quality_report(
    pms: list[dict[str, object]],
    crm: list[dict[str, object]],
    tickets: list[dict[str, object]],
    ledger: list[dict[str, object]],
    reviews: list[dict[str, object]],
) -> None:
    missing_ticket_pms = sum(1 for row in tickets if not row["pms_reservation_id"])
    missing_ticket_severity = sum(1 for row in tickets if not row["severity_raw"])
    duplicate_profiles = sum(1 for row in crm if row["duplicate_profile_flag"] == "true")
    orphan_ledger = sum(1 for row in ledger if not row["service_ticket_id"])
    delayed_reviews = sum(1 for row in reviews if row["review_loaded_at"] > row["review_date"])
    dirty_comp_labels = len(set(row["comp_action_raw"] for row in ledger))
    dirty_issue_labels = len(set(row["issue_code_raw"] for row in tickets))
    report = "\n".join(
        [
            "# Source System Quality Report",
            "",
            "This report is intentionally not clean. The synthetic source systems preserve realistic hotel-data problems before the recovery-case mart normalizes them.",
            "",
            "| Source issue | Count |",
            "| --- | ---: |",
            f"| PMS reservations | {len(pms)} |",
            f"| CRM profiles, including duplicates | {len(crm)} |",
            f"| Duplicate CRM profiles | {duplicate_profiles} |",
            f"| Service tickets | {len(tickets)} |",
            f"| Tickets missing direct PMS reservation ID | {missing_ticket_pms} |",
            f"| Tickets missing severity | {missing_ticket_severity} |",
            f"| Dirty issue-code labels | {dirty_issue_labels} |",
            f"| Comp ledger entries | {len(ledger)} |",
            f"| Comp ledger entries without ticket ID | {orphan_ledger} |",
            f"| Dirty comp-action labels | {dirty_comp_labels} |",
            f"| Delayed review/survey records | {delayed_reviews} |",
            "",
            "The downstream mart should retain match confidence and source-quality flags rather than hiding this messiness.",
            "",
        ]
    )
    (REPORT_DIR / "source-system-quality-report.md").write_text(report, encoding="utf-8")


def main() -> int:
    ensure_dirs()
    if not BOOKING_SAMPLE_PATH.exists():
        print("Missing booking sample. Run scripts/acquire_booking_data.py first.")
        return 1
    rng = random.Random(RANDOM_SEED + 10)
    _, booking_rows = read_csv_rows(BOOKING_SAMPLE_PATH)
    stays = generate_stays(booking_rows)
    failures = generate_failures(stays)
    stays_by_id = {str(stay["stay_id"]): stay for stay in stays}
    pms = build_pms_reservations(stays, rng)
    pms_by_stay = {str(row["stay_id"]): row for row in pms}
    crm = build_crm_profiles(pms, stays_by_id, rng)
    tickets = build_service_tickets(failures, pms_by_stay, rng)
    ledger = build_comp_ledger(tickets, pms, rng)
    pos = build_pos_charges(pms, rng)
    reviews = build_reviews_surveys(tickets, {str(row["pms_reservation_id"]): row for row in pms}, rng)
    ops = build_ops_daily(rng)
    catalog = comp_catalog()

    write_csv(PMS_RESERVATIONS_PATH, list(pms[0].keys()), pms)
    write_csv(CRM_PROFILES_PATH, list(crm[0].keys()), crm)
    write_csv(SERVICE_TICKETS_PATH, list(tickets[0].keys()), tickets)
    write_csv(COMP_LEDGER_PATH, list(ledger[0].keys()), ledger)
    write_csv(POS_CHARGES_PATH, list(pos[0].keys()), pos)
    write_csv(REVIEWS_SURVEYS_PATH, list(reviews[0].keys()), reviews)
    write_csv(OPS_DAILY_PATH, list(ops[0].keys()), ops)
    write_csv(COMP_CATALOG_PATH, list(catalog[0].keys()), catalog)
    write_source_quality_report(pms, crm, tickets, ledger, reviews)
    write_json(
        SYNTHETIC_GENERATION_MANIFEST_PATH,
        {
            "generated_at": utc_now_iso(),
            "random_seed": RANDOM_SEED + 10,
            "raw_source_dir": "data/sample/raw_sources",
            "source_systems": {
                "pms_reservations": len(pms),
                "guest_profiles_crm": len(crm),
                "service_tickets": len(tickets),
                "comp_ledger": len(ledger),
                "pos_outlet_charges": len(pos),
                "reviews_surveys": len(reviews),
                "ops_daily": len(ops),
            },
            "messiness_intentionally_simulated": [
                "missing reservation IDs in service tickets",
                "missing CRM IDs",
                "duplicate CRM profiles",
                "dirty issue labels",
                "dirty comp labels",
                "comp ledger rows without ticket IDs",
                "delayed review and survey records",
                "masked OTA-style contact fields",
            ],
            "public_safety_note": "All generated source-system rows are synthetic and unaffiliated with any real hotel operator.",
        },
    )
    print(f"Wrote messy source systems to {RAW_SOURCE_DIR.relative_to(RAW_SOURCE_DIR.parents[1])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
