from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from common import (
    LOCAL_DEMAND_CONTEXT_PATH,
    PROPERTY_CONTEXT_PATH,
    PUBLIC_PRICING_CONTEXT_PATH,
    RECOVERY_CASE_MART_PATH,
    REVIEW_RISK_CONTEXT_PATH,
    REPORT_DIR,
    ensure_dirs,
    read_csv_rows,
    write_csv,
)
from generate_synthetic_source_systems import (
    COMP_LEDGER_PATH,
    CRM_PROFILES_PATH,
    ISSUE_DIRTY_LABELS,
    OPS_DAILY_PATH,
    PMS_RESERVATIONS_PATH,
    POS_CHARGES_PATH,
    REVIEWS_SURVEYS_PATH,
    SERVICE_TICKETS_PATH,
    COMP_DIRTY_LABELS,
)
from policy_engine import as_float, clamp


DATA_LINEAGE_REPORT = REPORT_DIR / "data-lineage.md"


def reverse_lookup(source: dict[str, list[str]]) -> dict[str, str]:
    output = {}
    for normalized, labels in source.items():
        for label in labels:
            output[label.lower()] = normalized
    return output


ISSUE_NORMALIZER = reverse_lookup(ISSUE_DIRTY_LABELS)
COMP_NORMALIZER = reverse_lookup(COMP_DIRTY_LABELS)


def parse_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value[:10])
    except ValueError:
        return None


def in_stay_window(ticket: dict[str, str], pms: dict[str, str]) -> bool:
    opened = parse_date(ticket.get("opened_timestamp", ""))
    arrival = parse_date(pms.get("arrival_date", ""))
    departure = parse_date(pms.get("departure_date", ""))
    if not opened or not arrival or not departure:
        return False
    return arrival <= opened <= departure


def best_crm_profile(profiles: list[dict[str, str]]) -> dict[str, str] | None:
    if not profiles:
        return None
    return sorted(profiles, key=lambda row: as_float(row.get("profile_quality_score"), 0), reverse=True)[0]


def match_reservation(
    ticket: dict[str, str],
    pms_by_id: dict[str, dict[str, str]],
    pms_by_guest_key: dict[str, list[dict[str, str]]],
    pms_by_room: dict[str, list[dict[str, str]]],
) -> tuple[dict[str, str] | None, float, str]:
    pms_id = ticket.get("pms_reservation_id", "")
    if pms_id and pms_id in pms_by_id:
        return pms_by_id[pms_id], 1.0, "direct_pms_reservation_id"

    guest_key = ticket.get("guest_lookup_key", "")
    if guest_key:
        candidates = [row for row in pms_by_guest_key.get(guest_key, []) if in_stay_window(ticket, row)]
        if candidates:
            return candidates[0], 0.78, "guest_key_date_window"

    room = ticket.get("room_number_proxy", "")
    if room:
        candidates = [row for row in pms_by_room.get(room, []) if in_stay_window(ticket, row)]
        if candidates:
            return candidates[0], 0.58, "room_date_window"

    return None, 0.0, "unmatched"


def match_crm(
    ticket: dict[str, str],
    pms: dict[str, str] | None,
    crm_by_id: dict[str, list[dict[str, str]]],
    crm_by_guest_key: dict[str, list[dict[str, str]]],
) -> tuple[dict[str, str] | None, float, str]:
    for candidate_id in [ticket.get("crm_guest_id", ""), pms.get("crm_guest_id", "") if pms else ""]:
        if candidate_id and candidate_id in crm_by_id:
            return best_crm_profile(crm_by_id[candidate_id]), 0.95, "direct_crm_id"

    guest_key = ticket.get("guest_lookup_key", "") or (pms.get("guest_lookup_key", "") if pms else "")
    if guest_key and guest_key in crm_by_guest_key:
        return best_crm_profile(crm_by_guest_key[guest_key]), 0.72, "guest_key_profile_match"

    return None, 0.0, "unmatched"


def ledger_for_ticket(
    ticket: dict[str, str],
    pms: dict[str, str] | None,
    ledger_by_ticket: dict[str, list[dict[str, str]]],
    ledger_by_pms: dict[str, list[dict[str, str]]],
) -> tuple[list[dict[str, str]], float, str]:
    ticket_id = ticket.get("service_ticket_id", "")
    if ticket_id and ledger_by_ticket.get(ticket_id):
        return ledger_by_ticket[ticket_id], 1.0, "direct_ticket_id"
    pms_id = pms.get("pms_reservation_id", "") if pms else ticket.get("pms_reservation_id", "")
    if pms_id and ledger_by_pms.get(pms_id):
        return ledger_by_pms[pms_id], 0.62, "reservation_level_comp_match"
    return [], 0.0, "no_comp_record"


def pos_aggregates(pos_rows: list[dict[str, str]]) -> dict[str, dict[str, float]]:
    aggregates: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for row in pos_rows:
        pms_id = row.get("pms_reservation_id", "")
        if not pms_id:
            continue
        amount = as_float(row.get("charge_amount"), 0)
        outlet = row.get("outlet", "")
        aggregates[pms_id]["total_onsite_spend"] += amount
        if outlet in {"calabra_rooftop", "palma_lobby_lounge", "in_room_dining"}:
            aggregates[pms_id]["f_and_b_spend"] += amount
        if outlet == "spa_wellness":
            aggregates[pms_id]["spa_wellness_spend"] += amount
        if outlet == "valet_parking":
            aggregates[pms_id]["parking_spend"] += amount
    return aggregates


def review_for_case(ticket: dict[str, str], pms: dict[str, str] | None, reviews_by_pms: dict[str, list[dict[str, str]]], reviews_by_guest: dict[str, list[dict[str, str]]]) -> dict[str, str] | None:
    pms_id = pms.get("pms_reservation_id", "") if pms else ticket.get("pms_reservation_id", "")
    if pms_id and reviews_by_pms.get(pms_id):
        return sorted(reviews_by_pms[pms_id], key=lambda row: as_float(row.get("post_stay_score"), 10))[0]
    guest_key = ticket.get("guest_lookup_key", "") or (pms.get("guest_lookup_key", "") if pms else "")
    if guest_key and reviews_by_guest.get(guest_key):
        return sorted(reviews_by_guest[guest_key], key=lambda row: as_float(row.get("post_stay_score"), 10))[0]
    return None


def default_pricing_context() -> dict[str, str]:
    return {
        "target_public_rate": "0",
        "comp_set_median_rate": "0",
        "market_median_rate": "0",
        "proper_vs_comp_set_index": "1",
        "public_rate_pressure_index": "0.5",
        "high_demand_rate_flag": "false",
        "upgrade_opportunity_cost_proxy": "0",
        "refund_cost_pressure": "1",
        "quote_count": "0",
        "target_property_quote_count": "0",
        "comp_set_quote_count": "0",
        "limited_availability_share": "0",
        "free_cancellation_share": "0",
        "rate_context_confidence": "0",
        "pricing_capture_method": "missing",
        "pricing_provenance": "missing_public_pricing_context",
        "pricing_context_note": "no public pricing context available; model used fallback values",
    }


def default_property_context() -> dict[str, str]:
    return {
        "property_name": "Santa Monica Proper Hotel",
        "has_rooftop_f_and_b": "false",
        "has_lobby_lounge": "false",
        "has_spa_wellness": "false",
        "has_pool_or_rooftop": "false",
        "has_parking_or_fee_recovery_context": "false",
        "has_beachfront_or_ocean_context": "false",
        "property_context_confidence": "0",
        "rooftop_f_and_b_fit_modifier": "1",
        "spa_wellness_fit_modifier": "1",
        "lobby_lounge_fit_modifier": "1",
        "parking_fee_fit_modifier": "1",
        "late_checkout_fit_modifier": "1",
        "room_upgrade_fit_modifier": "1",
        "brand_experience_weight": "0.5",
        "provenance": "missing_public_property_context",
    }


def default_review_context(failure_category: str) -> dict[str, str]:
    return {
        "failure_category": failure_category,
        "baseline_review_risk_prior": "0.55",
        "review_context_confidence": "0",
        "provenance": "missing_public_review_context",
    }


def default_demand_context() -> dict[str, str]:
    return {
        "event_pressure_index": "0",
        "weather_disruption_index": "0",
        "local_demand_pressure_index": "0.35",
        "high_local_demand_flag": "false",
        "demand_context_confidence": "0",
        "provenance": "missing_local_demand_context",
    }


def load_pricing_context_by_date() -> dict[str, dict[str, str]]:
    if not PUBLIC_PRICING_CONTEXT_PATH.exists():
        return {}
    _, rows = read_csv_rows(PUBLIC_PRICING_CONTEXT_PATH)
    return {row["context_date"]: row for row in rows}


def load_target_property_context() -> dict[str, str]:
    if not PROPERTY_CONTEXT_PATH.exists():
        return default_property_context()
    _, rows = read_csv_rows(PROPERTY_CONTEXT_PATH)
    target_rows = [row for row in rows if row.get("property_role") == "target_property"]
    return target_rows[0] if target_rows else default_property_context()


def load_review_context_by_category() -> dict[str, dict[str, str]]:
    if not REVIEW_RISK_CONTEXT_PATH.exists():
        return {}
    _, rows = read_csv_rows(REVIEW_RISK_CONTEXT_PATH)
    return {row["failure_category"]: row for row in rows}


def load_demand_context_by_date() -> dict[str, dict[str, str]]:
    if not LOCAL_DEMAND_CONTEXT_PATH.exists():
        return {}
    _, rows = read_csv_rows(LOCAL_DEMAND_CONTEXT_PATH)
    return {row["context_date"]: row for row in rows}


def derive_guest_value_score(stay_value: float, estimated_ltv: float, loyalty_tier: str, special_requests: float) -> float:
    tier_component = {
        "new_guest": 0.22,
        "returning_guest": 0.42,
        "loyalty_guest": 0.62,
        "vip_guest": 0.82,
        "event_or_suite_guest": 0.88,
    }.get(loyalty_tier, 0.3)
    return round(clamp(tier_component * 0.46 + min(stay_value / 5200, 1) * 0.24 + min(estimated_ltv / 22000, 1) * 0.22 + min(special_requests / 5, 1) * 0.08, 0, 1), 3)


def severity_from_ticket(ticket: dict[str, str]) -> tuple[int, bool]:
    raw = ticket.get("severity_raw", "")
    if raw:
        return int(as_float(raw, 3)), False
    issue = normalize_issue(ticket.get("issue_code_raw", ""))
    inferred = {
        "room_readiness_delay": 3,
        "room_assignment_expectation_gap": 3,
        "housekeeping_miss": 3,
        "maintenance_issue": 3,
        "noise_disruption": 2,
        "billing_or_fee_dispute": 2,
        "f_and_b_service_lapse": 2,
        "rooftop_pool_access_issue": 2,
        "spa_wellness_service_issue": 3,
        "valet_or_parking_delay": 2,
    }.get(issue, 2)
    return inferred, True


def normalize_issue(label: str) -> str:
    return ISSUE_NORMALIZER.get(label.lower(), "unknown_issue")


def normalize_comp(label: str) -> str:
    return COMP_NORMALIZER.get(label.lower(), "unknown_comp")


def build_mart() -> list[dict[str, object]]:
    _, pms_rows = read_csv_rows(PMS_RESERVATIONS_PATH)
    _, crm_rows = read_csv_rows(CRM_PROFILES_PATH)
    _, ticket_rows = read_csv_rows(SERVICE_TICKETS_PATH)
    _, ledger_rows = read_csv_rows(COMP_LEDGER_PATH)
    _, pos_rows = read_csv_rows(POS_CHARGES_PATH)
    _, review_rows = read_csv_rows(REVIEWS_SURVEYS_PATH)
    _, ops_rows = read_csv_rows(OPS_DAILY_PATH)
    pricing_by_date = load_pricing_context_by_date()
    target_property_context = load_target_property_context()
    review_context_by_category = load_review_context_by_category()
    demand_by_date = load_demand_context_by_date()

    pms_by_id = {row["pms_reservation_id"]: row for row in pms_rows}
    pms_by_guest_key: dict[str, list[dict[str, str]]] = defaultdict(list)
    pms_by_room: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in pms_rows:
        pms_by_guest_key[row["guest_lookup_key"]].append(row)
        pms_by_room[row["room_number_proxy"]].append(row)

    crm_by_id: dict[str, list[dict[str, str]]] = defaultdict(list)
    crm_by_guest_key: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in crm_rows:
        crm_by_id[row["crm_guest_id"]].append(row)
        crm_by_guest_key[row["guest_lookup_key"]].append(row)

    ledger_by_ticket: dict[str, list[dict[str, str]]] = defaultdict(list)
    ledger_by_pms: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in ledger_rows:
        if row.get("service_ticket_id"):
            ledger_by_ticket[row["service_ticket_id"]].append(row)
        if row.get("pms_reservation_id"):
            ledger_by_pms[row["pms_reservation_id"]].append(row)

    pos_by_pms = pos_aggregates(pos_rows)
    reviews_by_pms: dict[str, list[dict[str, str]]] = defaultdict(list)
    reviews_by_guest: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in review_rows:
        if row.get("pms_reservation_id"):
            reviews_by_pms[row["pms_reservation_id"]].append(row)
        if row.get("guest_lookup_key"):
            reviews_by_guest[row["guest_lookup_key"]].append(row)
    ops_by_date = {row["service_date"]: row for row in ops_rows}

    mart_rows: list[dict[str, object]] = []
    for index, ticket in enumerate(ticket_rows, start=1):
        pms, reservation_confidence, reservation_method = match_reservation(ticket, pms_by_id, pms_by_guest_key, pms_by_room)
        crm, crm_confidence, crm_method = match_crm(ticket, pms, crm_by_id, crm_by_guest_key)
        comp_rows, comp_confidence, comp_method = ledger_for_ticket(ticket, pms, ledger_by_ticket, ledger_by_pms)
        review = review_for_case(ticket, pms, reviews_by_pms, reviews_by_guest)
        service_date = ticket.get("opened_timestamp", "")[:10]
        ops = ops_by_date.get(service_date, {})
        pricing_context = pricing_by_date.get(service_date, default_pricing_context())
        demand_context = demand_by_date.get(service_date, default_demand_context())

        severity, severity_inferred = severity_from_ticket(ticket)
        failure_category = normalize_issue(ticket.get("issue_code_raw", ""))
        review_context = review_context_by_category.get(failure_category, default_review_context(failure_category))
        comp_value = sum(as_float(row.get("face_value"), 0) for row in comp_rows if row.get("approval_status") != "rejected")
        comp_cost = sum(as_float(row.get("estimated_internal_cost"), 0) for row in comp_rows if row.get("approval_status") != "rejected")
        comp_codes = sorted({normalize_comp(row.get("comp_action_raw", "")) for row in comp_rows})
        raw_comp_labels = sorted({row.get("comp_action_raw", "") for row in comp_rows if row.get("comp_action_raw", "")})

        stay_value = as_float(pms.get("stay_value"), 0) if pms else 0
        nightly_rate = as_float(pms.get("nightly_rate"), 0) if pms else 0
        estimated_ltv_raw = as_float(crm.get("estimated_lifetime_value"), 0) if crm else 0
        ltv_imputed = estimated_ltv_raw <= 0
        estimated_ltv = estimated_ltv_raw if estimated_ltv_raw > 0 else max(stay_value * 1.8, 0)
        loyalty_tier = crm.get("loyalty_tier", "unknown_guest") if crm else "unknown_guest"
        special_requests = as_float(pms.get("special_requests_count"), 0) if pms else 0
        guest_value_score = derive_guest_value_score(stay_value, estimated_ltv, loyalty_tier, special_requests)
        pos = pos_by_pms.get(pms.get("pms_reservation_id", "") if pms else "", {})
        post_stay_score = as_float(review.get("post_stay_score"), 0) if review else 0
        sentiment = as_float(review.get("sentiment_intensity"), severity / 5) if review else round(severity / 5, 3)
        base_review_risk = clamp((10 - post_stay_score) / 9 if post_stay_score else severity / 5 * 0.72, 0, 1)
        review_prior = as_float(review_context.get("baseline_review_risk_prior"), 0.55)
        review_context_confidence = as_float(review_context.get("review_context_confidence"), 0)
        review_risk = round(
            clamp(
                base_review_risk * (1 - min(review_context_confidence, 0.45))
                + review_prior * min(review_context_confidence, 0.45),
                0,
                1,
            ),
            3,
        )
        hotel_responsibility = round(
            clamp(
                {
                    "room_readiness_delay": 0.88,
                    "room_assignment_expectation_gap": 0.74,
                    "housekeeping_miss": 0.9,
                    "maintenance_issue": 0.78,
                    "f_and_b_service_lapse": 0.7,
                    "spa_wellness_service_issue": 0.74,
                    "valet_or_parking_delay": 0.62,
                    "billing_or_fee_dispute": 0.55,
                    "noise_disruption": 0.48,
                    "rooftop_pool_access_issue": 0.64,
                }.get(failure_category, 0.5)
                + (0.05 if severity >= 4 else 0),
                0,
                1,
            ),
            3,
        )
        repeat_comp_count_proxy = sum(1 for row in ledger_rows if row.get("guest_lookup_key") and row.get("guest_lookup_key") == ticket.get("guest_lookup_key"))
        repeat_comp_review_risk = round(
            clamp(repeat_comp_count_proxy / 5 + (0.12 if reservation_confidence < 0.7 else 0), 0, 1),
            3,
        )
        resolution_delay = 90 if ticket.get("closed_timestamp") else 360
        if ticket.get("opened_timestamp") and ticket.get("closed_timestamp"):
            try:
                resolution_delay = max(5, int((datetime.fromisoformat(ticket["closed_timestamp"]) - datetime.fromisoformat(ticket["opened_timestamp"])).total_seconds() // 60))
            except ValueError:
                resolution_delay = 120

        mart_rows.append(
            {
                "recovery_case_id": f"case_{index:05d}",
                "service_ticket_id": ticket["service_ticket_id"],
                "pms_reservation_id": pms.get("pms_reservation_id", "") if pms else "",
                "crm_guest_id": crm.get("crm_guest_id", "") if crm else "",
                "reservation_match_confidence": reservation_confidence,
                "reservation_match_method": reservation_method,
                "crm_match_confidence": crm_confidence,
                "crm_match_method": crm_method,
                "comp_match_confidence": comp_confidence,
                "comp_match_method": comp_method,
                "guest_tier": loyalty_tier,
                "traveler_segment": crm.get("traveler_segment", "unknown_segment") if crm else "unknown_segment",
                "nightly_rate": int(nightly_rate),
                "stay_value": int(stay_value),
                "estimated_lifetime_value": int(estimated_ltv),
                "guest_value_score": guest_value_score,
                "repeat_comp_review_risk": repeat_comp_review_risk,
                "arrival_date": pms.get("arrival_date", "") if pms else "",
                "service_date": service_date,
                "booking_channel_proxy": pms.get("booking_channel_proxy", "") if pms else "",
                "room_type_mismatch": str((pms.get("reserved_room_type_proxy") != pms.get("assigned_room_type_proxy")) if pms else False).lower(),
                "room_move_count": pms.get("room_move_count", "") if pms else "",
                "special_requests_count": int(special_requests),
                "failure_category": failure_category,
                "issue_code_raw": ticket.get("issue_code_raw", ""),
                "failure_type": "outcome" if failure_category in {"room_readiness_delay", "room_assignment_expectation_gap", "housekeeping_miss", "maintenance_issue"} else "process",
                "severity": severity,
                "severity_inferred_flag": str(severity_inferred).lower(),
                "hotel_responsibility_score": hotel_responsibility,
                "reported_in_stay": ticket.get("reported_in_stay", "false"),
                "resolution_delay_minutes": resolution_delay,
                "complaint_sentiment_intensity": sentiment,
                "review_risk_score": review_risk,
                "post_stay_score": post_stay_score,
                "actual_comp_codes_normalized": ";".join(comp_codes),
                "actual_comp_labels_raw": ";".join(raw_comp_labels),
                "actual_comp_face_value": int(comp_value),
                "actual_comp_internal_cost": int(comp_cost),
                "total_onsite_spend": int(pos.get("total_onsite_spend", 0)),
                "f_and_b_spend": int(pos.get("f_and_b_spend", 0)),
                "spa_wellness_spend": int(pos.get("spa_wellness_spend", 0)),
                "parking_spend": int(pos.get("parking_spend", 0)),
                "occupancy_pressure": as_float(ops.get("occupancy_rate"), 0.65),
                "housekeeping_pressure": as_float(ops.get("housekeeping_pressure"), 0.5),
                "front_desk_queue_pressure": as_float(ops.get("front_desk_queue_pressure"), 0.5),
                "food_beverage_capacity_pressure": as_float(ops.get("food_beverage_capacity_pressure"), 0.5),
                "spa_capacity_pressure": as_float(ops.get("spa_capacity_pressure"), 0.5),
                "target_property_name": target_property_context.get("property_name", "Santa Monica Proper Hotel"),
                "has_rooftop_f_and_b": target_property_context.get("has_rooftop_f_and_b", "false"),
                "has_lobby_lounge": target_property_context.get("has_lobby_lounge", "false"),
                "has_spa_wellness": target_property_context.get("has_spa_wellness", "false"),
                "has_pool_or_rooftop": target_property_context.get("has_pool_or_rooftop", "false"),
                "has_parking_or_fee_recovery_context": target_property_context.get("has_parking_or_fee_recovery_context", "false"),
                "has_beachfront_or_ocean_context": target_property_context.get("has_beachfront_or_ocean_context", "false"),
                "property_context_confidence": as_float(target_property_context.get("property_context_confidence"), 0),
                "rooftop_f_and_b_fit_modifier": as_float(target_property_context.get("rooftop_f_and_b_fit_modifier"), 1),
                "spa_wellness_fit_modifier": as_float(target_property_context.get("spa_wellness_fit_modifier"), 1),
                "lobby_lounge_fit_modifier": as_float(target_property_context.get("lobby_lounge_fit_modifier"), 1),
                "parking_fee_fit_modifier": as_float(target_property_context.get("parking_fee_fit_modifier"), 1),
                "late_checkout_fit_modifier": as_float(target_property_context.get("late_checkout_fit_modifier"), 1),
                "room_upgrade_fit_modifier": as_float(target_property_context.get("room_upgrade_fit_modifier"), 1),
                "brand_experience_weight": as_float(target_property_context.get("brand_experience_weight"), 0.5),
                "property_context_provenance": target_property_context.get("provenance", "missing_public_property_context"),
                "public_review_risk_prior": review_prior,
                "review_context_confidence": review_context_confidence,
                "review_context_provenance": review_context.get("provenance", "missing_public_review_context"),
                "event_pressure_index": as_float(demand_context.get("event_pressure_index"), 0),
                "weather_disruption_index": as_float(demand_context.get("weather_disruption_index"), 0),
                "local_demand_pressure_index": as_float(demand_context.get("local_demand_pressure_index"), 0.35),
                "high_local_demand_flag": demand_context.get("high_local_demand_flag", "false"),
                "demand_context_confidence": as_float(demand_context.get("demand_context_confidence"), 0),
                "demand_context_provenance": demand_context.get("provenance", "missing_local_demand_context"),
                "target_public_rate": int(as_float(pricing_context.get("target_public_rate"), 0)),
                "comp_set_median_rate": int(as_float(pricing_context.get("comp_set_median_rate"), 0)),
                "market_median_rate": int(as_float(pricing_context.get("market_median_rate"), 0)),
                "proper_vs_comp_set_index": as_float(pricing_context.get("proper_vs_comp_set_index"), 1),
                "public_rate_pressure_index": as_float(pricing_context.get("public_rate_pressure_index"), 0.5),
                "high_demand_rate_flag": pricing_context.get("high_demand_rate_flag", "false"),
                "upgrade_opportunity_cost_proxy": int(as_float(pricing_context.get("upgrade_opportunity_cost_proxy"), 0)),
                "refund_cost_pressure": as_float(pricing_context.get("refund_cost_pressure"), 1),
                "pricing_quote_count": int(as_float(pricing_context.get("quote_count"), 0)),
                "rate_context_confidence": as_float(pricing_context.get("rate_context_confidence"), 0),
                "pricing_provenance": pricing_context.get("pricing_provenance", "missing_public_pricing_context"),
                "data_quality_flags": ";".join(
                    flag
                    for flag, present in [
                        ("unmatched_reservation", pms is None),
                        ("low_reservation_match_confidence", 0 < reservation_confidence < 0.75),
                        ("unmatched_crm_profile", crm is None),
                        ("severity_inferred", severity_inferred),
                        ("ltv_imputed", ltv_imputed),
                        ("no_review_or_survey", review is None),
                        ("no_comp_record", not comp_rows),
                        ("missing_public_pricing_context", pricing_context.get("pricing_provenance") == "missing_public_pricing_context"),
                        ("missing_public_property_context", target_property_context.get("provenance") == "missing_public_property_context"),
                        ("missing_public_review_context", review_context.get("provenance") == "missing_public_review_context"),
                        ("missing_local_demand_context", demand_context.get("provenance") == "missing_local_demand_context"),
                    ]
                    if present
                ),
            }
        )
    return mart_rows


def write_lineage_report(mart_rows: list[dict[str, object]]) -> None:
    low_match = sum(1 for row in mart_rows if as_float(row["reservation_match_confidence"]) < 0.75)
    inferred_severity = sum(1 for row in mart_rows if row["severity_inferred_flag"] == "true")
    no_comp = sum(1 for row in mart_rows if "no_comp_record" in str(row["data_quality_flags"]))
    report = "\n".join(
        [
            "# Data Lineage",
            "",
            "The comp recommendation model consumes a curated recovery-case mart, not clean source rows.",
            "",
            "```text",
            "raw_pms_reservations",
            "+ raw_guest_profiles_crm",
            "+ raw_service_tickets",
            "+ raw_comp_ledger",
            "+ raw_pos_outlet_charges",
            "+ raw_reviews_surveys",
            "+ raw_ops_daily",
            "+ public_pricing_context",
            "+ public_property_context",
            "+ review_risk_context",
            "+ local_demand_context",
            "-> identity and reservation matching",
            "-> dirty issue and comp taxonomy normalization",
            "-> public quoted-rate, property, review, and local-demand context joins",
            "-> source-quality flags and match confidence",
            "-> data/marts/recovery_case_mart.csv",
            "-> comp recommendation model",
            "```",
            "",
            "## Mart Quality Signals",
            "",
            f"- Recovery cases: `{len(mart_rows)}`",
            f"- Low reservation-match confidence cases: `{low_match}`",
            f"- Cases with inferred severity: `{inferred_severity}`",
            f"- Cases with no historical comp record: `{no_comp}`",
            "",
            "These issues are intentionally retained because the business problem is partly a data-wrangling problem.",
            "",
        ]
    )
    DATA_LINEAGE_REPORT.write_text(report, encoding="utf-8")


def main() -> int:
    ensure_dirs()
    required_sources = [
        PMS_RESERVATIONS_PATH,
        CRM_PROFILES_PATH,
        SERVICE_TICKETS_PATH,
        COMP_LEDGER_PATH,
        POS_CHARGES_PATH,
        REVIEWS_SURVEYS_PATH,
        OPS_DAILY_PATH,
    ]
    missing = [str(path) for path in required_sources if not path.exists()]
    if missing:
        print("Missing raw source systems. Run scripts/generate_synthetic_source_systems.py first.")
        return 1
    mart_rows = build_mart()
    write_csv(RECOVERY_CASE_MART_PATH, list(mart_rows[0].keys()), mart_rows)
    write_lineage_report(mart_rows)
    print(f"Wrote recovery-case mart: {RECOVERY_CASE_MART_PATH.relative_to(RECOVERY_CASE_MART_PATH.parents[1])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
