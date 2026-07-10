from __future__ import annotations

import json
from pathlib import Path

from common import (
    BOOKING_MANIFEST_PATH,
    BOOKING_RAW_PATH,
    BOOKING_SAMPLE_PATH,
    CONTRACT_DIR,
    EXTERNAL_CONTEXT_MODEL_IMPACT_PATH,
    LOCAL_DEMAND_CONTEXT_MANIFEST_PATH,
    LOCAL_DEMAND_CONTEXT_PATH,
    PROJECT_ROOT,
    PROPER_PUBLIC_CONTEXT_MANIFEST_PATH,
    PROPER_PUBLIC_CONTEXT_PATH,
    PROPERTY_CONTEXT_MANIFEST_PATH,
    PROPERTY_CONTEXT_PATH,
    PUBLIC_PRICING_CONTEXT_PATH,
    PUBLIC_PRICING_MANIFEST_PATH,
    RATE_SHOP_SNAPSHOT_PATH,
    REPORT_DIR,
    REQUIRED_BOOKING_FIELDS,
    REVIEW_RISK_CONTEXT_MANIFEST_PATH,
    REVIEW_RISK_CONTEXT_PATH,
    REVIEW_STUB_MANIFEST_PATH,
    WAREHOUSE_DB_PATH,
    WAREHOUSE_MANIFEST_PATH,
    count_rows,
    ensure_dirs,
    read_csv_rows,
    read_json,
    sha256_file,
)


VALIDATION_REPORT_PATH = REPORT_DIR / "data-acquisition-validation.md"


def add_check(checks: list[dict[str, str]], name: str, passed: bool, detail: str) -> None:
    checks.append(
        {
            "name": name,
            "status": "PASS" if passed else "FAIL",
            "detail": detail,
        }
    )


def load_json_contract(path: Path) -> tuple[bool, str]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            json.load(handle)
        return True, "valid JSON"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def render_report(checks: list[dict[str, str]]) -> str:
    lines = [
        "# Data Acquisition Validation",
        "",
        "| Check | Status | Detail |",
        "| --- | --- | --- |",
    ]
    for check in checks:
        detail = check["detail"].replace("|", "\\|")
        lines.append(f"| {check['name']} | {check['status']} | {detail} |")
    lines.extend(
        [
            "",
            "## Public-Safety Boundary",
            "",
            "- Full raw downloads are ignored in `data/raw/`.",
            "- Compensation fields are policy-simulated, not observed public labels.",
            "- Internal hotel fields remain marked as unavailable or synthetic.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    ensure_dirs()
    checks: list[dict[str, str]] = []

    add_check(
        checks,
        "raw booking source exists",
        BOOKING_RAW_PATH.exists(),
        str(BOOKING_RAW_PATH.relative_to(PROJECT_ROOT)) if BOOKING_RAW_PATH.exists() else "missing",
    )
    add_check(
        checks,
        "booking manifest exists",
        BOOKING_MANIFEST_PATH.exists(),
        str(BOOKING_MANIFEST_PATH.relative_to(PROJECT_ROOT)) if BOOKING_MANIFEST_PATH.exists() else "missing",
    )
    add_check(
        checks,
        "booking sample exists",
        BOOKING_SAMPLE_PATH.exists(),
        str(BOOKING_SAMPLE_PATH.relative_to(PROJECT_ROOT)) if BOOKING_SAMPLE_PATH.exists() else "missing",
    )
    add_check(
        checks,
        "review acquisition stub exists",
        REVIEW_STUB_MANIFEST_PATH.exists(),
        str(REVIEW_STUB_MANIFEST_PATH.relative_to(PROJECT_ROOT)) if REVIEW_STUB_MANIFEST_PATH.exists() else "missing",
    )
    add_check(
        checks,
        "rate-shop snapshot exists",
        RATE_SHOP_SNAPSHOT_PATH.exists(),
        str(RATE_SHOP_SNAPSHOT_PATH.relative_to(PROJECT_ROOT)) if RATE_SHOP_SNAPSHOT_PATH.exists() else "missing",
    )
    add_check(
        checks,
        "public pricing context exists",
        PUBLIC_PRICING_CONTEXT_PATH.exists(),
        str(PUBLIC_PRICING_CONTEXT_PATH.relative_to(PROJECT_ROOT)) if PUBLIC_PRICING_CONTEXT_PATH.exists() else "missing",
    )
    add_check(
        checks,
        "public pricing manifest exists",
        PUBLIC_PRICING_MANIFEST_PATH.exists(),
        str(PUBLIC_PRICING_MANIFEST_PATH.relative_to(PROJECT_ROOT)) if PUBLIC_PRICING_MANIFEST_PATH.exists() else "missing",
    )
    for name, path in [
        ("property context exists", PROPERTY_CONTEXT_PATH),
        ("property context manifest exists", PROPERTY_CONTEXT_MANIFEST_PATH),
        ("review-risk context exists", REVIEW_RISK_CONTEXT_PATH),
        ("review-risk context manifest exists", REVIEW_RISK_CONTEXT_MANIFEST_PATH),
        ("local demand context exists", LOCAL_DEMAND_CONTEXT_PATH),
        ("local demand context manifest exists", LOCAL_DEMAND_CONTEXT_MANIFEST_PATH),
        ("external context model-impact mart exists", EXTERNAL_CONTEXT_MODEL_IMPACT_PATH),
    ]:
        add_check(
            checks,
            name,
            path.exists(),
            str(path.relative_to(PROJECT_ROOT)) if path.exists() else "missing",
        )

    if BOOKING_RAW_PATH.exists() and BOOKING_MANIFEST_PATH.exists():
        manifest = read_json(BOOKING_MANIFEST_PATH)
        row_count, column_count, header = count_rows(BOOKING_RAW_PATH)
        current_hash = sha256_file(BOOKING_RAW_PATH)
        missing_required = [field for field in REQUIRED_BOOKING_FIELDS if field not in header]

        add_check(
            checks,
            "manifest hash matches raw file",
            current_hash == manifest.get("sha256"),
            "current sha256 matches manifest" if current_hash == manifest.get("sha256") else "sha256 mismatch",
        )
        add_check(
            checks,
            "manifest row count matches raw file",
            row_count == manifest.get("row_count"),
            f"raw={row_count}, manifest={manifest.get('row_count')}",
        )
        add_check(
            checks,
            "manifest column count matches raw file",
            column_count == manifest.get("column_count"),
            f"raw={column_count}, manifest={manifest.get('column_count')}",
        )
        add_check(
            checks,
            "required booking fields present",
            not missing_required,
            "all required fields present" if not missing_required else f"missing: {missing_required}",
        )

    if BOOKING_SAMPLE_PATH.exists():
        sample_rows, sample_columns, sample_header = count_rows(BOOKING_SAMPLE_PATH)
        add_check(
            checks,
            "sample is reviewer-sized",
            0 < sample_rows <= 1000,
            f"{sample_rows} rows, {sample_columns} columns",
        )
        add_check(
            checks,
            "sample contains derived room mismatch",
            "room_type_mismatch" in sample_header,
            "room_type_mismatch present" if "room_type_mismatch" in sample_header else "missing",
        )

    if RATE_SHOP_SNAPSHOT_PATH.exists():
        snapshot_rows, snapshot_columns, snapshot_header = count_rows(RATE_SHOP_SNAPSHOT_PATH)
        _, snapshots = read_csv_rows(RATE_SHOP_SNAPSHOT_PATH)
        comprehensive_fields = {
            "property_name",
            "property_role",
            "property_type",
            "address",
            "property_description",
            "gps_lat",
            "gps_lng",
            "hotel_class",
            "overall_rating",
            "review_count",
            "amenities",
            "excluded_amenities",
            "essential_info",
            "ratings_summary",
            "reviews_breakdown_summary",
            "room_type",
            "room_type_source",
            "rate_plan",
            "rate_source",
            "provider_count",
            "free_cancellation_available",
            "quoted_rate_before_taxes",
            "quoted_rate_total",
            "source_url_or_query",
            "provenance",
        }
        missing_fields = sorted(comprehensive_fields - set(snapshot_header))
        target_rows = [row for row in snapshots if row.get("property_role") == "target_property"]
        comp_rows = [row for row in snapshots if row.get("property_role") == "competitive_set"]
        add_check(
            checks,
            "rate-shop extract has comprehensive fields",
            not missing_fields,
            f"{snapshot_columns} columns" if not missing_fields else f"missing: {missing_fields}",
        )
        add_check(
            checks,
            "rate-shop extract has target and comp-set coverage",
            len(target_rows) > 0 and len({row.get("property_name") for row in comp_rows}) >= 3,
            f"{len(target_rows)} target rows, {len({row.get('property_name') for row in comp_rows})} comp-set properties",
        )
        add_check(
            checks,
            "rate-shop extract has usable quoted rates",
            snapshot_rows > 0 and all(row.get("quoted_rate_before_taxes") for row in snapshots[: min(25, len(snapshots))]),
            f"{snapshot_rows} rows",
        )

    if PUBLIC_PRICING_CONTEXT_PATH.exists():
        context_rows, context_columns, context_header = count_rows(PUBLIC_PRICING_CONTEXT_PATH)
        _, context = read_csv_rows(PUBLIC_PRICING_CONTEXT_PATH)
        required_context_fields = {
            "public_rate_pressure_index",
            "comp_set_median_rate",
            "proper_vs_comp_set_index",
            "upgrade_opportunity_cost_proxy",
            "refund_cost_pressure",
            "rate_context_confidence",
            "pricing_provenance",
        }
        missing_context = sorted(required_context_fields - set(context_header))
        high_pressure = sum(1 for row in context if row.get("high_demand_rate_flag") == "true")
        add_check(
            checks,
            "public pricing context has model fields",
            not missing_context,
            f"{context_columns} columns" if not missing_context else f"missing: {missing_context}",
        )
        add_check(
            checks,
            "public pricing context has daily coverage",
            context_rows >= 300,
            f"{context_rows} context dates",
        )
        add_check(
            checks,
            "public pricing context includes high-pressure dates",
            high_pressure > 0,
            f"{high_pressure} high-pressure dates",
        )

    if PROPERTY_CONTEXT_PATH.exists():
        property_rows, property_columns, property_header = count_rows(PROPERTY_CONTEXT_PATH)
        _, properties = read_csv_rows(PROPERTY_CONTEXT_PATH)
        target_rows = [row for row in properties if row.get("property_role") == "target_property"]
        comp_rows = [row for row in properties if row.get("property_role") == "competitive_set"]
        required_property_fields = {
            "property_name",
            "property_role",
            "source_url",
            "has_rooftop_f_and_b",
            "has_spa_wellness",
            "property_context_confidence",
            "rooftop_f_and_b_fit_modifier",
            "spa_wellness_fit_modifier",
            "provenance",
        }
        missing_property_fields = sorted(required_property_fields - set(property_header))
        add_check(
            checks,
            "property context has model fields",
            not missing_property_fields,
            f"{property_columns} columns" if not missing_property_fields else f"missing: {missing_property_fields}",
        )
        add_check(
            checks,
            "property context has target and comp-set rows",
            len(target_rows) == 1 and len(comp_rows) >= 3,
            f"{len(target_rows)} target rows, {len(comp_rows)} comp-set rows",
        )

    add_check(
        checks,
        "Proper public value anchor manifest exists",
        PROPER_PUBLIC_CONTEXT_MANIFEST_PATH.exists(),
        str(PROPER_PUBLIC_CONTEXT_MANIFEST_PATH.relative_to(PROJECT_ROOT))
        if PROPER_PUBLIC_CONTEXT_MANIFEST_PATH.exists()
        else "missing",
    )
    if PROPER_PUBLIC_CONTEXT_PATH.exists():
        anchor_rows, anchor_columns, anchor_header = count_rows(PROPER_PUBLIC_CONTEXT_PATH)
        _, anchors = read_csv_rows(PROPER_PUBLIC_CONTEXT_PATH)
        required_anchor_fields = {
            "anchor_id",
            "public_value",
            "source_url",
            "decision_use",
            "provenance",
            "internal_cost_known",
        }
        missing_anchor_fields = sorted(required_anchor_fields - set(anchor_header))
        official_sources = sum(
            1 for row in anchors if row.get("source_url", "").startswith("https://www.properhotel.com/")
        )
        unknown_internal_cost = sum(1 for row in anchors if row.get("internal_cost_known") == "false")
        add_check(
            checks,
            "Proper public anchors have provenance fields",
            not missing_anchor_fields and anchor_rows >= 8,
            f"{anchor_rows} anchors, {anchor_columns} columns"
            if not missing_anchor_fields
            else f"missing: {missing_anchor_fields}",
        )
        add_check(
            checks,
            "Proper public anchors use official sources and preserve cost boundary",
            official_sources == anchor_rows and unknown_internal_cost == anchor_rows,
            f"{official_sources}/{anchor_rows} official sources; {unknown_internal_cost}/{anchor_rows} internal costs marked unknown",
        )

    if REVIEW_RISK_CONTEXT_PATH.exists():
        review_rows, review_columns, review_header = count_rows(REVIEW_RISK_CONTEXT_PATH)
        _, review_context = read_csv_rows(REVIEW_RISK_CONTEXT_PATH)
        required_review_fields = {
            "failure_category",
            "public_review_theme",
            "baseline_review_risk_prior",
            "review_context_confidence",
            "provenance",
        }
        missing_review_fields = sorted(required_review_fields - set(review_header))
        add_check(
            checks,
            "review-risk context has model fields",
            not missing_review_fields,
            f"{review_columns} columns" if not missing_review_fields else f"missing: {missing_review_fields}",
        )
        add_check(
            checks,
            "review-risk context covers failure taxonomy",
            review_rows >= 10 and all(row.get("failure_category") for row in review_context),
            f"{review_rows} failure categories",
        )

    if LOCAL_DEMAND_CONTEXT_PATH.exists():
        demand_rows, demand_columns, demand_header = count_rows(LOCAL_DEMAND_CONTEXT_PATH)
        _, demand_context = read_csv_rows(LOCAL_DEMAND_CONTEXT_PATH)
        required_demand_fields = {
            "context_date",
            "event_pressure_index",
            "weather_disruption_index",
            "local_demand_pressure_index",
            "high_local_demand_flag",
            "provenance",
        }
        missing_demand_fields = sorted(required_demand_fields - set(demand_header))
        high_demand_days = sum(1 for row in demand_context if row.get("high_local_demand_flag") == "true")
        add_check(
            checks,
            "local demand context has model fields",
            not missing_demand_fields,
            f"{demand_columns} columns" if not missing_demand_fields else f"missing: {missing_demand_fields}",
        )
        add_check(
            checks,
            "local demand context has annual coverage",
            demand_rows >= 300 and high_demand_days > 0,
            f"{demand_rows} dates, {high_demand_days} high-demand dates",
        )

    if EXTERNAL_CONTEXT_MODEL_IMPACT_PATH.exists():
        impact_rows, impact_columns, impact_header = count_rows(EXTERNAL_CONTEXT_MODEL_IMPACT_PATH)
        _, impact = read_csv_rows(EXTERNAL_CONTEXT_MODEL_IMPACT_PATH)
        changed = sum(1 for row in impact if row.get("recommendation_changed") == "true")
        add_check(
            checks,
            "external context model impact has comparisons",
            impact_rows >= 5 and impact_columns >= 10,
            f"{impact_rows} comparisons, {impact_columns} columns",
        )
        add_check(
            checks,
            "external context changes controlled recommendations",
            changed >= 3,
            f"{changed} changed recommendations",
        )

    contract_files = [
        "source_booking_stays.schema.json",
        "source_review_signals.schema.json",
        "synthetic_service_failures.schema.json",
        "synthetic_source_systems.schema.json",
        "recovery_case_mart.schema.json",
        "comp_policy_audit.schema.json",
        "comp_recommendation.schema.json",
        "public_pricing_context.schema.json",
        "property_context.schema.json",
        "proper_public_value_anchors.schema.json",
        "review_risk_context.schema.json",
        "local_demand_context.schema.json",
        "external_context_model_impact.schema.json",
        "field_provenance.json",
    ]
    for filename in contract_files:
        path = CONTRACT_DIR / filename
        loaded, detail = load_json_contract(path)
        add_check(checks, f"contract valid: {filename}", loaded, detail)

    gitignore_path = PROJECT_ROOT / ".gitignore"
    gitignore_text = gitignore_path.read_text(encoding="utf-8") if gitignore_path.exists() else ""
    add_check(
        checks,
        "raw directory ignored",
        "data/raw/" in gitignore_text,
        "data/raw/ present in .gitignore" if "data/raw/" in gitignore_text else "data/raw/ not ignored",
    )

    if (CONTRACT_DIR / "field_provenance.json").exists():
        provenance = read_json(CONTRACT_DIR / "field_provenance.json")
        internal_fields = provenance.get("downstream_field_groups", {}).get("internal_unavailable", [])
        observed_fields = provenance.get("downstream_field_groups", {}).get("observed_public", [])
        overlap = sorted(set(internal_fields) & set(observed_fields))
        add_check(
            checks,
            "internal unavailable fields not marked observed",
            not overlap,
            "no overlap" if not overlap else f"overlap: {overlap}",
        )

    add_check(
        checks,
        "DuckDB warehouse exists",
        WAREHOUSE_DB_PATH.exists(),
        str(WAREHOUSE_DB_PATH.relative_to(PROJECT_ROOT)) if WAREHOUSE_DB_PATH.exists() else "missing",
    )
    add_check(
        checks,
        "DuckDB warehouse manifest exists",
        WAREHOUSE_MANIFEST_PATH.exists(),
        str(WAREHOUSE_MANIFEST_PATH.relative_to(PROJECT_ROOT)) if WAREHOUSE_MANIFEST_PATH.exists() else "missing",
    )
    if WAREHOUSE_MANIFEST_PATH.exists():
        warehouse_manifest = read_json(WAREHOUSE_MANIFEST_PATH)
        expected_views = {
            "vw_comp_decision_summary",
            "vw_comp_mix",
            "vw_manager_review_queue",
            "vw_audit_decision_signal",
            "vw_source_quality_snapshot",
            "vw_public_pricing_context",
            "vw_external_context_sources",
            "vw_external_context_model_impact",
        }
        observed_views = set(warehouse_manifest.get("views", {}))
        missing_views = sorted(expected_views - observed_views)
        add_check(
            checks,
            "DuckDB warehouse views registered",
            not missing_views,
            "all expected views present" if not missing_views else f"missing: {missing_views}",
        )
        add_check(
            checks,
            "DuckDB warehouse includes recommendation rows",
            warehouse_manifest.get("tables", {}).get("mart_comp_recommendations", 0) > 0,
            f"{warehouse_manifest.get('tables', {}).get('mart_comp_recommendations', 0)} recommendation rows",
        )
    if WAREHOUSE_DB_PATH.exists():
        try:
            import duckdb

            connection = duckdb.connect(str(WAREHOUSE_DB_PATH), read_only=True)
            try:
                decision_summary_count = connection.execute("SELECT COUNT(*) FROM vw_comp_decision_summary").fetchone()[0]
                manager_queue_count = connection.execute("SELECT COUNT(*) FROM vw_manager_review_queue").fetchone()[0]
            finally:
                connection.close()
            add_check(
                checks,
                "DuckDB decision summary query works",
                decision_summary_count == 1,
                f"{decision_summary_count} summary rows",
            )
            add_check(
                checks,
                "DuckDB manager queue query works",
                manager_queue_count > 0,
                f"{manager_queue_count} manager/data-quality queue rows",
            )
        except Exception as exc:  # noqa: BLE001
            add_check(checks, "DuckDB warehouse query works", False, str(exc))

    VALIDATION_REPORT_PATH.write_text(render_report(checks), encoding="utf-8")
    failed = [check for check in checks if check["status"] != "PASS"]
    print(f"Wrote validation report: {VALIDATION_REPORT_PATH.relative_to(PROJECT_ROOT)}")
    if failed:
        for check in failed:
            print(f"FAIL: {check['name']} - {check['detail']}")
        return 1
    print(f"Validation passed: {len(checks)} checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
