from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


GUEST_TIER_SCORE = {
    "new_guest": 0.25,
    "returning_guest": 0.45,
    "loyalty_guest": 0.65,
    "vip_guest": 0.85,
    "event_or_suite_guest": 0.9,
}

FAILURE_CATEGORIES = {
    "room_readiness_delay",
    "room_assignment_expectation_gap",
    "housekeeping_miss",
    "maintenance_issue",
    "noise_disruption",
    "billing_or_fee_dispute",
    "f_and_b_service_lapse",
    "rooftop_pool_access_issue",
    "spa_wellness_service_issue",
    "valet_or_parking_delay",
}

FAILURE_TYPES = {"outcome", "process"}

COMP_CODES = {
    "manager_note",
    "amenity_gesture",
    "late_checkout",
    "parking_fee_waiver",
    "lobby_lounge_credit",
    "rooftop_f_and_b_credit",
    "spa_wellness_credit",
    "room_upgrade",
    "partial_room_refund",
    "future_stay_credit",
}


class ScenarioValidationError(ValueError):
    def __init__(self, errors: dict[str, str]):
        self.errors = errors
        detail = "; ".join(f"{field}: {message}" for field, message in sorted(errors.items()))
        super().__init__(detail)


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def derive_guest_value_score(guest_tier: str, stay_value: float, estimated_lifetime_value: float) -> float:
    tier_component = GUEST_TIER_SCORE.get(guest_tier, 0.3)
    return round(
        clamp(
            tier_component * 0.5
            + min(stay_value / 5500, 1) * 0.25
            + min(estimated_lifetime_value / 22000, 1) * 0.25,
            0,
            1,
        ),
        3,
    )


def _first(mapping: Mapping[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        value = mapping.get(name)
        if value not in (None, ""):
            return value
    return default


def _number(
    mapping: Mapping[str, Any],
    errors: dict[str, str],
    field: str,
    aliases: tuple[str, ...],
    default: float,
    minimum: float,
    maximum: float,
) -> float:
    raw = _first(mapping, field, *aliases, default=default)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        errors[field] = "must be numeric"
        return default
    if not minimum <= value <= maximum:
        errors[field] = f"must be between {minimum:g} and {maximum:g}"
    return value


def _boolean(
    mapping: Mapping[str, Any],
    errors: dict[str, str],
    field: str,
    aliases: tuple[str, ...] = (),
    default: bool = False,
) -> bool:
    raw = _first(mapping, field, *aliases, default=default)
    if isinstance(raw, bool):
        return raw
    normalized = str(raw).strip().lower()
    if normalized in {"1", "true", "yes", "y"}:
        return True
    if normalized in {"0", "false", "no", "n"}:
        return False
    errors[field] = "must be true or false"
    return default


def _string_list(
    mapping: Mapping[str, Any],
    errors: dict[str, str],
    field: str,
    default: tuple[str, ...],
) -> tuple[str, ...]:
    raw = _first(mapping, field, default=default)
    if isinstance(raw, str):
        values = [value.strip() for value in raw.replace(";", ",").split(",") if value.strip()]
    elif isinstance(raw, (list, tuple, set)):
        values = [str(value).strip() for value in raw if str(value).strip()]
    else:
        errors[field] = "must be a list or comma-separated string"
        return default
    if "manager_note" not in values:
        values.insert(0, "manager_note")
    unknown = sorted(set(values) - COMP_CODES)
    if unknown:
        errors[field] = f"contains unknown comp codes: {', '.join(unknown)}"
    if not values:
        errors[field] = "must include at least one available recovery option"
    return tuple(dict.fromkeys(values))


@dataclass(frozen=True)
class ScenarioInput:
    guest_tier: str
    traveler_segment: str
    stay_value: float
    estimated_lifetime_value: float
    nightly_rate: float
    guest_value_score: float
    repeat_comp_review_risk: float
    failure_category: str
    failure_type: str
    severity: int
    hotel_responsibility: float
    reported_in_stay: bool
    resolution_delay_minutes: int
    sentiment_intensity: float
    review_risk: float
    occupancy_pressure: float
    public_rate_pressure: float
    high_demand_rate: bool
    upgrade_opportunity_cost: float
    refund_cost_pressure: float
    rate_context_confidence: float
    pricing_provenance: str
    has_rooftop_f_and_b: bool
    has_lobby_lounge: bool
    has_spa_wellness: bool
    has_pool_or_rooftop: bool
    has_parking_or_fee_recovery_context: bool
    property_context_confidence: float
    rooftop_f_and_b_fit_modifier: float
    spa_wellness_fit_modifier: float
    lobby_lounge_fit_modifier: float
    parking_fee_fit_modifier: float
    late_checkout_fit_modifier: float
    room_upgrade_fit_modifier: float
    review_context_confidence: float
    local_demand_pressure: float
    high_local_demand: bool
    demand_context_confidence: float
    available_comp_codes: tuple[str, ...]
    availability_confirmed: bool

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "ScenarioInput":
        errors: dict[str, str] = {}
        guest_tier = str(_first(mapping, "guest_tier", default="")).strip()
        if guest_tier not in GUEST_TIER_SCORE:
            errors["guest_tier"] = f"must be one of {', '.join(sorted(GUEST_TIER_SCORE))}"
        traveler_segment = str(_first(mapping, "traveler_segment", default="general_leisure")).strip()
        if not traveler_segment:
            errors["traveler_segment"] = "must not be blank"
        failure_category = str(_first(mapping, "failure_category", default="")).strip()
        if failure_category not in FAILURE_CATEGORIES:
            errors["failure_category"] = f"must be one of {', '.join(sorted(FAILURE_CATEGORIES))}"
        failure_type = str(_first(mapping, "failure_type", default="outcome")).strip()
        if failure_type not in FAILURE_TYPES:
            errors["failure_type"] = "must be outcome or process"

        stay_value = _number(mapping, errors, "stay_value", (), 0, 0, 100000)
        lifetime_value = _number(mapping, errors, "estimated_lifetime_value", (), 0, 0, 1000000)
        nightly_rate = _number(mapping, errors, "nightly_rate", (), 650, 0, 25000)
        severity_value = _number(mapping, errors, "severity", (), 1, 1, 5)
        if severity_value != int(severity_value):
            errors["severity"] = "must be a whole number from 1 through 5"
        guest_value_raw = _first(mapping, "guest_value_score", default=None)
        if guest_value_raw in (None, ""):
            guest_value_score = derive_guest_value_score(guest_tier, stay_value, lifetime_value)
        else:
            guest_value_score = _number(mapping, errors, "guest_value_score", (), 0, 0, 1)

        values = {
            "repeat_comp_review_risk": _number(
                mapping,
                errors,
                "repeat_comp_review_risk",
                ("repeat_comp_abuse_risk",),
                0.05,
                0,
                1,
            ),
            "hotel_responsibility": _number(
                mapping,
                errors,
                "hotel_responsibility",
                ("hotel_responsibility_score",),
                0.5,
                0,
                1,
            ),
            "resolution_delay_minutes": _number(mapping, errors, "resolution_delay_minutes", (), 90, 0, 10080),
            "sentiment_intensity": _number(
                mapping,
                errors,
                "sentiment_intensity",
                ("complaint_sentiment_intensity",),
                0.5,
                0,
                1,
            ),
            "review_risk": _number(mapping, errors, "review_risk", ("review_risk_score",), 0.5, 0, 1),
            "occupancy_pressure": _number(mapping, errors, "occupancy_pressure", (), 0.5, 0, 1),
            "public_rate_pressure": _number(
                mapping,
                errors,
                "public_rate_pressure",
                ("public_rate_pressure_index",),
                0.5,
                0,
                1,
            ),
            "upgrade_opportunity_cost": _number(
                mapping,
                errors,
                "upgrade_opportunity_cost",
                ("upgrade_opportunity_cost_proxy",),
                0,
                0,
                10000,
            ),
            "refund_cost_pressure": _number(mapping, errors, "refund_cost_pressure", (), 1, 0, 3),
            "rate_context_confidence": _number(mapping, errors, "rate_context_confidence", (), 0, 0, 1),
            "property_context_confidence": _number(mapping, errors, "property_context_confidence", (), 0, 0, 1),
            "rooftop_f_and_b_fit_modifier": _number(mapping, errors, "rooftop_f_and_b_fit_modifier", (), 1, 0.5, 2),
            "spa_wellness_fit_modifier": _number(mapping, errors, "spa_wellness_fit_modifier", (), 1, 0.5, 2),
            "lobby_lounge_fit_modifier": _number(mapping, errors, "lobby_lounge_fit_modifier", (), 1, 0.5, 2),
            "parking_fee_fit_modifier": _number(mapping, errors, "parking_fee_fit_modifier", (), 1, 0.5, 2),
            "late_checkout_fit_modifier": _number(mapping, errors, "late_checkout_fit_modifier", (), 1, 0.5, 2),
            "room_upgrade_fit_modifier": _number(mapping, errors, "room_upgrade_fit_modifier", (), 1, 0.5, 2),
            "review_context_confidence": _number(mapping, errors, "review_context_confidence", (), 0, 0, 1),
            "local_demand_pressure": _number(
                mapping,
                errors,
                "local_demand_pressure",
                ("local_demand_pressure_index",),
                0.35,
                0,
                1,
            ),
            "demand_context_confidence": _number(mapping, errors, "demand_context_confidence", (), 0, 0, 1),
        }
        booleans = {
            "reported_in_stay": _boolean(mapping, errors, "reported_in_stay", default=True),
            "high_demand_rate": _boolean(mapping, errors, "high_demand_rate", ("high_demand_rate_flag",)),
            "has_rooftop_f_and_b": _boolean(mapping, errors, "has_rooftop_f_and_b", default=True),
            "has_lobby_lounge": _boolean(mapping, errors, "has_lobby_lounge", default=True),
            "has_spa_wellness": _boolean(mapping, errors, "has_spa_wellness", default=True),
            "has_pool_or_rooftop": _boolean(mapping, errors, "has_pool_or_rooftop", default=True),
            "has_parking_or_fee_recovery_context": _boolean(
                mapping,
                errors,
                "has_parking_or_fee_recovery_context",
                default=True,
            ),
            "high_local_demand": _boolean(mapping, errors, "high_local_demand", ("high_local_demand_flag",)),
            "availability_confirmed": _boolean(mapping, errors, "availability_confirmed", default=False),
        }
        available_comp_codes = _string_list(
            mapping,
            errors,
            "available_comp_codes",
            tuple(sorted(COMP_CODES)),
        )
        if errors:
            raise ScenarioValidationError(errors)

        return cls(
            guest_tier=guest_tier,
            traveler_segment=traveler_segment,
            stay_value=stay_value,
            estimated_lifetime_value=lifetime_value,
            nightly_rate=nightly_rate,
            guest_value_score=guest_value_score,
            repeat_comp_review_risk=values["repeat_comp_review_risk"],
            failure_category=failure_category,
            failure_type=failure_type,
            severity=int(severity_value),
            hotel_responsibility=values["hotel_responsibility"],
            reported_in_stay=booleans["reported_in_stay"],
            resolution_delay_minutes=int(values["resolution_delay_minutes"]),
            sentiment_intensity=values["sentiment_intensity"],
            review_risk=values["review_risk"],
            occupancy_pressure=values["occupancy_pressure"],
            public_rate_pressure=values["public_rate_pressure"],
            high_demand_rate=booleans["high_demand_rate"],
            upgrade_opportunity_cost=values["upgrade_opportunity_cost"],
            refund_cost_pressure=values["refund_cost_pressure"],
            rate_context_confidence=values["rate_context_confidence"],
            pricing_provenance=str(_first(mapping, "pricing_provenance", default="unavailable_public_rate_context")),
            has_rooftop_f_and_b=booleans["has_rooftop_f_and_b"],
            has_lobby_lounge=booleans["has_lobby_lounge"],
            has_spa_wellness=booleans["has_spa_wellness"],
            has_pool_or_rooftop=booleans["has_pool_or_rooftop"],
            has_parking_or_fee_recovery_context=booleans["has_parking_or_fee_recovery_context"],
            property_context_confidence=values["property_context_confidence"],
            rooftop_f_and_b_fit_modifier=values["rooftop_f_and_b_fit_modifier"],
            spa_wellness_fit_modifier=values["spa_wellness_fit_modifier"],
            lobby_lounge_fit_modifier=values["lobby_lounge_fit_modifier"],
            parking_fee_fit_modifier=values["parking_fee_fit_modifier"],
            late_checkout_fit_modifier=values["late_checkout_fit_modifier"],
            room_upgrade_fit_modifier=values["room_upgrade_fit_modifier"],
            review_context_confidence=values["review_context_confidence"],
            local_demand_pressure=values["local_demand_pressure"],
            high_local_demand=booleans["high_local_demand"],
            demand_context_confidence=values["demand_context_confidence"],
            available_comp_codes=available_comp_codes,
            availability_confirmed=booleans["availability_confirmed"],
        )

    def to_engine_inputs(self) -> tuple[dict[str, Any], dict[str, Any]]:
        stay = {
            "guest_tier": self.guest_tier,
            "traveler_segment": self.traveler_segment,
            "stay_value": self.stay_value,
            "estimated_lifetime_value": self.estimated_lifetime_value,
            "nightly_rate": self.nightly_rate,
            "guest_value_score": self.guest_value_score,
            "repeat_comp_review_risk": self.repeat_comp_review_risk,
        }
        failure = {
            "failure_category": self.failure_category,
            "failure_type": self.failure_type,
            "severity": self.severity,
            "hotel_responsibility_score": self.hotel_responsibility,
            "reported_in_stay": self.reported_in_stay,
            "resolution_delay_minutes": self.resolution_delay_minutes,
            "complaint_sentiment_intensity": self.sentiment_intensity,
            "review_risk_score": self.review_risk,
            "occupancy_pressure": self.occupancy_pressure,
            "public_rate_pressure_index": self.public_rate_pressure,
            "high_demand_rate_flag": self.high_demand_rate,
            "upgrade_opportunity_cost_proxy": self.upgrade_opportunity_cost,
            "refund_cost_pressure": self.refund_cost_pressure,
            "rate_context_confidence": self.rate_context_confidence,
            "pricing_provenance": self.pricing_provenance,
            "has_rooftop_f_and_b": self.has_rooftop_f_and_b,
            "has_lobby_lounge": self.has_lobby_lounge,
            "has_spa_wellness": self.has_spa_wellness,
            "has_pool_or_rooftop": self.has_pool_or_rooftop,
            "has_parking_or_fee_recovery_context": self.has_parking_or_fee_recovery_context,
            "property_context_confidence": self.property_context_confidence,
            "rooftop_f_and_b_fit_modifier": self.rooftop_f_and_b_fit_modifier,
            "spa_wellness_fit_modifier": self.spa_wellness_fit_modifier,
            "lobby_lounge_fit_modifier": self.lobby_lounge_fit_modifier,
            "parking_fee_fit_modifier": self.parking_fee_fit_modifier,
            "late_checkout_fit_modifier": self.late_checkout_fit_modifier,
            "room_upgrade_fit_modifier": self.room_upgrade_fit_modifier,
            "review_context_confidence": self.review_context_confidence,
            "local_demand_pressure_index": self.local_demand_pressure,
            "high_local_demand_flag": self.high_local_demand,
            "demand_context_confidence": self.demand_context_confidence,
            "available_comp_codes": list(self.available_comp_codes),
            "availability_confirmed": self.availability_confirmed,
        }
        return stay, failure
