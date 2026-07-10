from __future__ import annotations

import json
import os
import random
from datetime import date, timedelta
from urllib.parse import urlencode
from urllib.request import urlopen

from common import (
    PROJECT_ROOT,
    PUBLIC_PRICING_MANIFEST_PATH,
    RATE_SHOP_SNAPSHOT_PATH,
    ensure_dirs,
    utc_now_iso,
    write_csv,
    write_json,
)


SERPAPI_ENDPOINT = "https://serpapi.com/search"
RANDOM_SEED = 20260704

PROPERTIES = [
    {
        "property_name": "Santa Monica Proper Hotel",
        "property_role": "target_property",
        "multiplier": 1.0,
        "neighborhood": "Downtown Santa Monica",
        "gps_lat": 34.023,
        "gps_lng": -118.493,
        "hotel_class": "5-star",
        "overall_rating": 4.5,
        "review_count": 740,
        "address": "700 Wilshire Blvd, Santa Monica, CA",
        "description": "Luxury lifestyle hotel with rooftop, dining, wellness, and design-forward guest experience.",
        "amenities": "rooftop pool;rooftop dining;spa/wellness;fitness;restaurant;bar;valet parking;meeting space",
    },
    {
        "property_name": "Shutters on the Beach",
        "property_role": "competitive_set",
        "multiplier": 1.08,
        "neighborhood": "Santa Monica Beach",
        "gps_lat": 34.007,
        "gps_lng": -118.492,
        "hotel_class": "5-star",
        "overall_rating": 4.5,
        "review_count": 1150,
        "address": "1 Pico Blvd, Santa Monica, CA",
        "description": "Luxury beachfront hotel with ocean views, dining, pool, and spa context.",
        "amenities": "beachfront;pool;spa;restaurant;bar;valet parking;ocean views",
    },
    {
        "property_name": "Casa Del Mar Santa Monica",
        "property_role": "competitive_set",
        "multiplier": 1.04,
        "neighborhood": "Santa Monica Beach",
        "gps_lat": 34.007,
        "gps_lng": -118.493,
        "hotel_class": "5-star",
        "overall_rating": 4.5,
        "review_count": 910,
        "address": "1910 Ocean Way, Santa Monica, CA",
        "description": "Luxury beach hotel with oceanfront dining, spa, and pool context.",
        "amenities": "beachfront;pool;spa;restaurant;bar;valet parking;ocean views",
    },
    {
        "property_name": "Fairmont Miramar Hotel & Bungalows",
        "property_role": "competitive_set",
        "multiplier": 0.96,
        "neighborhood": "Ocean Avenue",
        "gps_lat": 34.018,
        "gps_lng": -118.501,
        "hotel_class": "5-star",
        "overall_rating": 4.3,
        "review_count": 1520,
        "address": "101 Wilshire Blvd, Santa Monica, CA",
        "description": "Luxury Santa Monica hotel and bungalow property with dining, pool, spa, and event context.",
        "amenities": "pool;spa;restaurant;bar;bungalows;fitness;valet parking",
    },
    {
        "property_name": "Oceana Santa Monica",
        "property_role": "competitive_set",
        "multiplier": 0.98,
        "neighborhood": "Ocean Avenue",
        "gps_lat": 34.024,
        "gps_lng": -118.510,
        "hotel_class": "5-star",
        "overall_rating": 4.4,
        "review_count": 520,
        "address": "849 Ocean Ave, Santa Monica, CA",
        "description": "Luxury suite-oriented coastal hotel with wellness and ocean-view context.",
        "amenities": "ocean views;pool;restaurant;fitness;suites;wellness;valet parking",
    },
    {
        "property_name": "The Georgian Santa Monica",
        "property_role": "competitive_set",
        "multiplier": 0.82,
        "neighborhood": "Ocean Avenue",
        "gps_lat": 34.013,
        "gps_lng": -118.497,
        "hotel_class": "4-star",
        "overall_rating": 4.2,
        "review_count": 670,
        "address": "1415 Ocean Ave, Santa Monica, CA",
        "description": "Historic boutique/lifestyle Santa Monica hotel with restaurant and ocean-view context.",
        "amenities": "historic hotel;restaurant;bar;ocean views;fitness;valet parking",
    },
]

FIELDNAMES = [
    "captured_at",
    "source",
    "search_query",
    "search_location",
    "property_name",
    "property_role",
    "property_type",
    "property_token",
    "property_id",
    "property_link",
    "details_link",
    "reviews_link",
    "address",
    "phone",
    "property_description",
    "gps_lat",
    "gps_lng",
    "distance_to_target_miles",
    "neighborhood",
    "hotel_class",
    "extracted_hotel_class",
    "overall_rating",
    "review_count",
    "location_rating",
    "amenities",
    "excluded_amenities",
    "amenity_count",
    "nearby_places",
    "nearby_places_count",
    "essential_info",
    "ratings_summary",
    "reviews_breakdown_summary",
    "images_count",
    "check_in_time",
    "check_out_time",
    "check_in_date",
    "check_out_date",
    "length_of_stay",
    "adults",
    "children",
    "room_type",
    "room_type_source",
    "rate_plan",
    "rate_source",
    "provider_count",
    "provider_lowest_name",
    "provider_lowest_rate",
    "provider_prices_summary",
    "free_cancellation_available",
    "deal",
    "quoted_rate_before_taxes",
    "quoted_rate_total",
    "taxes_and_fees",
    "currency",
    "availability_status",
    "capture_method",
    "source_url_or_query",
    "provenance",
    "terms_or_license_note",
    "public_context_use",
]


def env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "y"}


def seasonal_rate_multiplier(stay_date: date) -> float:
    multiplier = 1.0
    if stay_date.month in {5, 6, 7, 8, 9}:
        multiplier += 0.18
    if stay_date.weekday() >= 4:
        multiplier += 0.14
    if stay_date.month == 2 and stay_date.day in {13, 14, 15}:
        multiplier += 0.16
    if stay_date.month == 7 and stay_date.day in {3, 4, 5}:
        multiplier += 0.2
    if stay_date.month == 12 and stay_date.day >= 24:
        multiplier += 0.18
    return multiplier


def as_number(value: object, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def semicolon_join(values: object, limit: int = 12) -> str:
    if not values:
        return ""
    if isinstance(values, list):
        output = []
        for value in values[:limit]:
            if isinstance(value, dict):
                name = value.get("name") or value.get("description") or value.get("type")
                if name:
                    output.append(str(name))
            else:
                output.append(str(value))
        return ";".join(output)
    return str(values)


def summarize_ratings(values: object) -> str:
    if not isinstance(values, list):
        return ""
    output = []
    for value in values[:5]:
        if isinstance(value, dict):
            stars = value.get("stars")
            count = value.get("count")
            if stars is not None and count is not None:
                output.append(f"{stars}_stars:{count}")
    return ";".join(output)


def summarize_review_breakdown(values: object) -> str:
    if not isinstance(values, list):
        return ""
    output = []
    for value in values[:8]:
        if isinstance(value, dict):
            name = value.get("name")
            mentioned = value.get("total_mentioned")
            positive = value.get("positive")
            negative = value.get("negative")
            if name:
                output.append(f"{name}:mentioned={mentioned},positive={positive},negative={negative}")
    return ";".join(output)


def count_values(values: object) -> int:
    if isinstance(values, list):
        return len(values)
    if isinstance(values, str) and values:
        return len(values.split(";"))
    return 0


def safe_source_query(check_in: date, check_out: date) -> str:
    params = {
        "engine": "google_hotels",
        "q": "luxury hotels Santa Monica",
        "gl": "us",
        "hl": "en",
        "currency": "USD",
        "check_in_date": check_in.isoformat(),
        "check_out_date": check_out.isoformat(),
        "adults": "2",
    }
    return urlencode(params)


def sample_seed_snapshots() -> list[dict[str, object]]:
    rng = random.Random(RANDOM_SEED)
    rows: list[dict[str, object]] = []
    captured_at = utc_now_iso()
    start = date(2026, 1, 1)
    for offset in range(365):
        check_in = start + timedelta(days=offset)
        check_out = check_in + timedelta(days=1)
        daily_market_noise = rng.gauss(0, 42)
        base = 650 * seasonal_rate_multiplier(check_in) + daily_market_noise
        for prop in PROPERTIES:
            property_name = str(prop["property_name"])
            property_role = str(prop["property_role"])
            rate = base * as_number(prop["multiplier"], 1) + rng.gauss(0, 36)
            before_taxes = int(round(max(385, min(rate, 1450)) / 5) * 5)
            total = int(round(before_taxes * 1.172 / 5) * 5)
            availability = "limited" if before_taxes >= 920 or (check_in.weekday() >= 4 and before_taxes >= 820) else "available"
            amenities = str(prop["amenities"])
            rows.append(
                {
                    "captured_at": captured_at,
                    "source": "sample_rate_shop_seed",
                    "search_query": "luxury hotels Santa Monica",
                    "search_location": "Santa Monica, California",
                    "property_name": property_name,
                    "property_role": property_role,
                    "property_type": "hotel",
                    "property_token": "",
                    "property_id": "",
                    "property_link": "",
                    "details_link": "",
                    "reviews_link": "",
                    "address": prop["address"],
                    "phone": "",
                    "property_description": prop["description"],
                    "gps_lat": prop["gps_lat"],
                    "gps_lng": prop["gps_lng"],
                    "distance_to_target_miles": 0 if property_role == "target_property" else round(rng.uniform(0.4, 2.2), 2),
                    "neighborhood": prop["neighborhood"],
                    "hotel_class": prop["hotel_class"],
                    "extracted_hotel_class": str(prop["hotel_class"]).replace("-star", ""),
                    "overall_rating": prop["overall_rating"],
                    "review_count": prop["review_count"],
                    "location_rating": round(rng.uniform(8.2, 9.8), 1),
                    "amenities": amenities,
                    "excluded_amenities": "",
                    "amenity_count": count_values(amenities),
                    "nearby_places": "Santa Monica Pier;Third Street Promenade;Palisades Park;Pacific Ocean",
                    "nearby_places_count": 4,
                    "essential_info": "entry room public quote proxy;king/queen room mix unavailable in sample seed",
                    "ratings_summary": "5_stars:sample;4_stars:sample;3_stars:sample",
                    "reviews_breakdown_summary": "rooms:sample;service:sample;location:sample;amenities:sample",
                    "images_count": rng.randrange(8, 25),
                    "check_in_time": "4:00 PM",
                    "check_out_time": "12:00 PM",
                    "check_in_date": check_in.isoformat(),
                    "check_out_date": check_out.isoformat(),
                    "length_of_stay": 1,
                    "adults": 2,
                    "children": 0,
                    "room_type": "entry_public_quote_proxy",
                    "room_type_source": "sample_seed_public_quote_proxy",
                    "rate_plan": "flexible_public_quote_proxy",
                    "rate_source": "sample_seed_rate_shop",
                    "provider_count": rng.randrange(2, 7),
                    "provider_lowest_name": "sample public quote",
                    "provider_lowest_rate": before_taxes,
                    "provider_prices_summary": f"sample public quote:{before_taxes}",
                    "free_cancellation_available": str(rng.random() > 0.28).lower(),
                    "deal": "",
                    "quoted_rate_before_taxes": before_taxes,
                    "quoted_rate_total": total,
                    "taxes_and_fees": total - before_taxes,
                    "currency": "USD",
                    "availability_status": availability,
                    "capture_method": "sample_seed",
                    "source_url_or_query": "sample_seed:no_live_query",
                    "provenance": "sample_seed_public_rate_shape",
                    "terms_or_license_note": "reproducible sample seed; not an observed public quote",
                    "public_context_use": "rate pressure, comp-set comparability, and room-comp opportunity-cost proxy",
                }
            )
    return rows


def lowest_provider(prices: object) -> tuple[str, float, str, bool]:
    if not isinstance(prices, list):
        return "", 0, "", False
    providers = []
    cancellation = False
    for price in prices:
        if not isinstance(price, dict):
            continue
        source = str(price.get("source") or price.get("name") or price.get("provider") or "")
        rate = as_number(
            price.get("extracted_rate_per_night")
            or price.get("extracted_price")
            or price.get("extracted_total_rate")
            or price.get("price"),
            0,
        )
        if str(price.get("free_cancellation", "")).lower() in {"true", "yes", "1"}:
            cancellation = True
        if source or rate:
            providers.append((source, rate))
    providers = [item for item in providers if item[1] > 0]
    providers.sort(key=lambda item: item[1])
    summary = ";".join(f"{source}:{int(rate)}" for source, rate in providers[:8])
    if not providers:
        return "", 0, summary, cancellation
    return providers[0][0], providers[0][1], summary, cancellation


def property_role_for(name: str) -> str:
    normalized = name.lower()
    if "proper" in normalized and "santa monica" in normalized:
        return "target_property"
    return "competitive_set"


def fetch_serpapi_snapshots() -> tuple[list[dict[str, object]], str]:
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        return [], "SERPAPI_API_KEY not present"

    captured_at = utc_now_iso()
    today = date.today()
    query_dates = [today + timedelta(days=days) for days in [14, 21, 28, 35]]
    rows: list[dict[str, object]] = []
    for check_in in query_dates:
        check_out = check_in + timedelta(days=1)
        params = {
            "engine": "google_hotels",
            "q": "luxury hotels Santa Monica",
            "gl": "us",
            "hl": "en",
            "currency": "USD",
            "check_in_date": check_in.isoformat(),
            "check_out_date": check_out.isoformat(),
            "adults": "2",
            "api_key": api_key,
        }
        request_url = f"{SERPAPI_ENDPOINT}?{urlencode(params)}"
        sanitized_query = safe_source_query(check_in, check_out)
        with urlopen(request_url, timeout=30) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8"))
        for item in payload.get("properties", []):
            name = str(item.get("name", ""))
            rate = item.get("rate_per_night", {})
            before_taxes = rate.get("extracted_before_taxes_fees") or rate.get("extracted_lowest")
            total_rate = item.get("total_rate", {})
            total = total_rate.get("extracted_lowest") or before_taxes
            if not name or not before_taxes:
                continue
            total = total or before_taxes
            prices = item.get("prices")
            provider, provider_rate, provider_summary, free_cancellation = lowest_provider(prices)
            amenities = semicolon_join(item.get("amenities"))
            excluded_amenities = semicolon_join(item.get("excluded_amenities"))
            nearby_places = semicolon_join(item.get("nearby_places"))
            essential_info = semicolon_join(item.get("essential_info"))
            ratings_summary = summarize_ratings(item.get("ratings"))
            reviews_breakdown = summarize_review_breakdown(item.get("reviews_breakdown"))
            images = item.get("images")
            gps = item.get("gps_coordinates") if isinstance(item.get("gps_coordinates"), dict) else {}
            property_token = item.get("property_token") or item.get("hotel_id") or ""
            role = property_role_for(name)
            room_type = item.get("room_type") or item.get("room_name") or essential_info or "public_search_result"
            rows.append(
                {
                    "captured_at": captured_at,
                    "source": "serpapi_google_hotels",
                    "search_query": "luxury hotels Santa Monica",
                    "search_location": "Santa Monica, California",
                    "property_name": name,
                    "property_role": role,
                    "property_type": item.get("type") or "hotel",
                    "property_token": property_token,
                    "property_id": item.get("property_id") or item.get("hotel_id") or "",
                    "property_link": item.get("link") or "",
                    "details_link": item.get("serpapi_property_details_link") or item.get("details_link") or "",
                    "reviews_link": item.get("serpapi_google_hotels_reviews_link") or "",
                    "address": item.get("address") or "",
                    "phone": item.get("phone") or "",
                    "property_description": item.get("description") or "",
                    "gps_lat": gps.get("latitude", ""),
                    "gps_lng": gps.get("longitude", ""),
                    "distance_to_target_miles": "",
                    "neighborhood": "",
                    "hotel_class": item.get("hotel_class") or "",
                    "extracted_hotel_class": item.get("extracted_hotel_class") or "",
                    "overall_rating": item.get("overall_rating") or "",
                    "review_count": item.get("reviews") or "",
                    "location_rating": item.get("location_rating") or "",
                    "amenities": amenities,
                    "excluded_amenities": excluded_amenities,
                    "amenity_count": count_values(amenities),
                    "nearby_places": nearby_places,
                    "nearby_places_count": count_values(nearby_places),
                    "essential_info": essential_info,
                    "ratings_summary": ratings_summary,
                    "reviews_breakdown_summary": reviews_breakdown,
                    "images_count": len(images) if isinstance(images, list) else "",
                    "check_in_time": item.get("check_in_time") or "",
                    "check_out_time": item.get("check_out_time") or "",
                    "check_in_date": check_in.isoformat(),
                    "check_out_date": check_out.isoformat(),
                    "length_of_stay": 1,
                    "adults": 2,
                    "children": 0,
                    "room_type": room_type,
                    "room_type_source": "google_hotels_property_result",
                    "rate_plan": "public_search_result",
                    "rate_source": provider or "google_hotels_result",
                    "provider_count": len(prices) if isinstance(prices, list) else "",
                    "provider_lowest_name": provider,
                    "provider_lowest_rate": int(provider_rate) if provider_rate else "",
                    "provider_prices_summary": provider_summary,
                    "free_cancellation_available": str(free_cancellation).lower(),
                    "deal": item.get("deal") or "",
                    "quoted_rate_before_taxes": int(before_taxes),
                    "quoted_rate_total": int(total),
                    "taxes_and_fees": int(total) - int(before_taxes),
                    "currency": "USD",
                    "availability_status": "available",
                    "capture_method": "api",
                    "source_url_or_query": sanitized_query,
                    "provenance": "observed_public_market_context",
                    "terms_or_license_note": "SerpApi Google Hotels result; public quoted market context only",
                    "public_context_use": "rate pressure, comp-set comparability, and room-comp opportunity-cost proxy",
                }
            )
    return rows, "api fetch completed"


def acquire_rows() -> tuple[list[dict[str, object]], dict[str, object]]:
    api_requested = env_flag("RATE_SHOP_USE_API")
    api_key_present = bool(os.getenv("SERPAPI_API_KEY"))
    if api_requested:
        try:
            rows, note = fetch_serpapi_snapshots()
            if rows:
                return rows, {
                    "acquisition_mode": "api",
                    "api_requested": True,
                    "api_key_present": api_key_present,
                    "fallback_used": False,
                    "note": note,
                }
        except Exception as exc:  # noqa: BLE001
            note = f"API fetch failed; used sample seed fallback: {exc.__class__.__name__}"
        else:
            note = "API returned no usable rows; used sample seed fallback"
    else:
        note = "RATE_SHOP_USE_API not enabled; used reproducible sample seed"

    return sample_seed_snapshots(), {
        "acquisition_mode": "sample_seed",
        "api_requested": api_requested,
        "api_key_present": api_key_present,
        "fallback_used": api_requested,
        "note": note,
    }


def main() -> int:
    ensure_dirs()
    rows, metadata = acquire_rows()
    write_csv(RATE_SHOP_SNAPSHOT_PATH, FIELDNAMES, rows)
    write_json(
        PUBLIC_PRICING_MANIFEST_PATH,
        {
            "generated_at": utc_now_iso(),
            "rate_shop_snapshot_path": str(RATE_SHOP_SNAPSHOT_PATH.relative_to(PROJECT_ROOT)),
            "row_count": len(rows),
            "source_family": "public quoted hotel pricing context",
            "public_safety_note": "Rows are public quote context or reproducible sample-seed context; no internal hotel rates, occupancy, revenue, margins, or guest records are used.",
            **metadata,
        },
    )
    print(f"Wrote rate-shop snapshots: {RATE_SHOP_SNAPSHOT_PATH.relative_to(PROJECT_ROOT)}")
    print(f"Wrote pricing manifest: {PUBLIC_PRICING_MANIFEST_PATH.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
