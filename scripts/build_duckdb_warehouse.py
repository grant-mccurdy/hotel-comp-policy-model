from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import duckdb

from common import (
    COMP_CATALOG_PATH,
    COMP_POLICY_AUDIT_PATH,
    COMP_RECOMMENDATIONS_PATH,
    EXTERNAL_CONTEXT_MODEL_IMPACT_PATH,
    LOCAL_DEMAND_CONTEXT_PATH,
    PROJECT_ROOT,
    PROPER_PUBLIC_CONTEXT_PATH,
    PROPERTY_CONTEXT_PATH,
    PUBLIC_PRICING_CONTEXT_PATH,
    RATE_SHOP_SNAPSHOT_PATH,
    RECOVERY_CASE_MART_PATH,
    REVIEW_RISK_CONTEXT_PATH,
    REPORT_DIR,
    WAREHOUSE_DB_PATH,
    WAREHOUSE_MANIFEST_PATH,
    ensure_dirs,
    utc_now_iso,
    write_json,
)
from generate_synthetic_source_systems import (
    COMP_LEDGER_PATH,
    CRM_PROFILES_PATH,
    OPS_DAILY_PATH,
    PMS_RESERVATIONS_PATH,
    POS_CHARGES_PATH,
    REVIEWS_SURVEYS_PATH,
    SERVICE_TICKETS_PATH,
)


WAREHOUSE_LINEAGE_REPORT = REPORT_DIR / "warehouse-lineage.md"
SQL_QUERY_INVENTORY_REPORT = REPORT_DIR / "sql-query-inventory.md"


CSV_TABLES = [
    ("stg_pms_reservations", PMS_RESERVATIONS_PATH, "Synthetic PMS reservation extract"),
    ("stg_guest_profiles_crm", CRM_PROFILES_PATH, "Synthetic CRM guest profiles with duplicate-profile behavior"),
    ("stg_service_tickets", SERVICE_TICKETS_PATH, "Synthetic service-ticket system with missing IDs and dirty issue labels"),
    ("stg_comp_ledger", COMP_LEDGER_PATH, "Synthetic comp ledger with dirty comp labels and orphan records"),
    ("stg_pos_outlet_charges", POS_CHARGES_PATH, "Synthetic outlet charges for F&B, spa/wellness, and parking behavior"),
    ("stg_reviews_surveys", REVIEWS_SURVEYS_PATH, "Synthetic post-stay review and survey signals"),
    ("stg_ops_daily", OPS_DAILY_PATH, "Synthetic daily operational pressure"),
    ("stg_rate_shop_snapshots", RATE_SHOP_SNAPSHOT_PATH, "Public quoted-rate snapshot sample or API extract"),
    ("stg_property_context", PROPERTY_CONTEXT_PATH, "Public property and competitive-set context"),
    ("stg_proper_public_value_anchors", PROPER_PUBLIC_CONTEXT_PATH, "Observed public Santa Monica Proper value and option anchors"),
    ("stg_review_risk_context", REVIEW_RISK_CONTEXT_PATH, "Public review-risk theme priors by issue category"),
    ("stg_local_demand_context", LOCAL_DEMAND_CONTEXT_PATH, "Local event/weather demand-pressure context"),
    ("mart_public_pricing_context", PUBLIC_PRICING_CONTEXT_PATH, "Daily public pricing context used as comp opportunity-cost input"),
    ("mart_recovery_cases", RECOVERY_CASE_MART_PATH, "Case-level recovery decision mart"),
    ("mart_comp_recommendations", COMP_RECOMMENDATIONS_PATH, "Policy-engine comp recommendation output"),
    ("mart_comp_policy_audit", COMP_POLICY_AUDIT_PATH, "Audit classifications comparing historical/synthetic comp to recommendation"),
    ("mart_external_context_model_impact", EXTERNAL_CONTEXT_MODEL_IMPACT_PATH, "Controlled scenarios showing public-context recommendation impact"),
    ("dim_comp_catalog", COMP_CATALOG_PATH, "Comp type catalog and cost/perceived-value assumptions"),
]


ANALYTIC_SQL = {
    "vw_comp_decision_summary": """
        CREATE OR REPLACE VIEW vw_comp_decision_summary AS
        SELECT
            COUNT(*) AS recovery_cases,
            SUM(CAST(recommended_comp_value AS DOUBLE)) AS recommended_guest_value,
            SUM(CAST(estimated_internal_cost AS DOUBLE)) AS estimated_internal_cost,
            SUM(CAST(internal_cost_low AS DOUBLE)) AS internal_cost_low,
            SUM(CAST(internal_cost_high AS DOUBLE)) AS internal_cost_high,
            SUM(CAST(expected_recovery_value AS DOUBLE)) AS expected_recovery_value,
            MEDIAN(CAST(recommendation_stability AS DOUBLE)) AS median_recommendation_stability,
            SUM(CASE WHEN decision_confidence = 'low' THEN 1 ELSE 0 END) AS low_confidence_cases,
            SUM(CASE WHEN manager_review_flag = 'true' THEN 1 ELSE 0 END) AS manager_review_cases,
            SUM(CASE WHEN CAST(review_risk_score AS DOUBLE) >= 0.70 THEN 1 ELSE 0 END) AS high_review_risk_cases
        FROM mart_comp_recommendations
    """,
    "vw_comp_mix": """
        CREATE OR REPLACE VIEW vw_comp_mix AS
        SELECT
            comp_label,
            COUNT(*) AS cases,
            SUM(CAST(recommended_comp_value AS DOUBLE)) AS recommended_guest_value,
            SUM(CAST(estimated_internal_cost AS DOUBLE)) AS estimated_internal_cost
        FROM mart_comp_recommendations
        GROUP BY comp_label
        ORDER BY recommended_guest_value DESC
    """,
    "vw_manager_review_queue": """
        CREATE OR REPLACE VIEW vw_manager_review_queue AS
        SELECT
            recovery_case_id,
            service_ticket_id,
            guest_tier,
            traveler_segment,
            failure_category,
            severity,
            recovery_need_score,
            review_risk_score,
            recommended_comp_value,
            internal_cost_low,
            internal_cost_high,
            comp_label,
            manager_review_flag,
            decision_confidence,
            recommendation_stability,
            policy_version,
            recommendation_counterfactuals,
            reservation_match_confidence,
            data_quality_flags
        FROM mart_comp_recommendations
        WHERE manager_review_flag = 'true'
           OR decision_confidence <> 'high'
           OR CAST(reservation_match_confidence AS DOUBLE) < 0.75
        ORDER BY CAST(recovery_need_score AS DOUBLE) DESC, CAST(estimated_lifetime_value AS DOUBLE) DESC
    """,
    "vw_audit_decision_signal": """
        CREATE OR REPLACE VIEW vw_audit_decision_signal AS
        SELECT
            audit_class,
            COUNT(*) AS cases,
            SUM(CAST(recommended_comp_value AS DOUBLE)) AS recommended_guest_value,
            SUM(CAST(recommended_internal_cost AS DOUBLE)) AS recommended_internal_cost,
            SUM(CAST(recommended_minus_actual_value AS DOUBLE)) AS recommended_minus_actual_value
        FROM mart_comp_policy_audit
        GROUP BY audit_class
        ORDER BY cases DESC
    """,
    "vw_source_quality_snapshot": """
        CREATE OR REPLACE VIEW vw_source_quality_snapshot AS
        SELECT 'tickets_missing_reservation_id' AS metric, COUNT(*) AS rows
        FROM stg_service_tickets
        WHERE pms_reservation_id IS NULL OR pms_reservation_id = ''
        UNION ALL
        SELECT 'tickets_missing_severity' AS metric, COUNT(*) AS rows
        FROM stg_service_tickets
        WHERE severity_raw IS NULL OR severity_raw = ''
        UNION ALL
        SELECT 'crm_duplicate_profiles' AS metric, COUNT(*) AS rows
        FROM stg_guest_profiles_crm
        WHERE duplicate_profile_flag = 'true'
        UNION ALL
        SELECT 'comp_ledger_orphan_records' AS metric, COUNT(*) AS rows
        FROM stg_comp_ledger
        WHERE service_ticket_id IS NULL OR service_ticket_id = ''
        UNION ALL
        SELECT 'low_confidence_recovery_cases' AS metric, COUNT(*) AS rows
        FROM mart_recovery_cases
        WHERE CAST(reservation_match_confidence AS DOUBLE) > 0
          AND CAST(reservation_match_confidence AS DOUBLE) < 0.75
    """,
    "vw_public_pricing_context": """
        CREATE OR REPLACE VIEW vw_public_pricing_context AS
        SELECT
            context_date,
            target_public_rate,
            comp_set_median_rate,
            public_rate_pressure_index,
            high_demand_rate_flag,
            upgrade_opportunity_cost_proxy,
            refund_cost_pressure,
            rate_context_confidence,
            pricing_provenance
        FROM mart_public_pricing_context
        ORDER BY CAST(public_rate_pressure_index AS DOUBLE) DESC
    """,
    "vw_external_context_sources": """
        CREATE OR REPLACE VIEW vw_external_context_sources AS
        SELECT 'rate_shop_snapshots' AS source_layer, COUNT(*) AS rows FROM stg_rate_shop_snapshots
        UNION ALL
        SELECT 'property_context' AS source_layer, COUNT(*) AS rows FROM stg_property_context
        UNION ALL
        SELECT 'proper_public_value_anchors' AS source_layer, COUNT(*) AS rows FROM stg_proper_public_value_anchors
        UNION ALL
        SELECT 'review_risk_context' AS source_layer, COUNT(*) AS rows FROM stg_review_risk_context
        UNION ALL
        SELECT 'local_demand_context' AS source_layer, COUNT(*) AS rows FROM stg_local_demand_context
    """,
    "vw_external_context_model_impact": """
        CREATE OR REPLACE VIEW vw_external_context_model_impact AS
        SELECT
            comparison_id,
            decision_signal,
            control_comp_code,
            context_comp_code,
            recommendation_changed,
            recommended_value_delta,
            internal_cost_delta,
            context_reason_codes
        FROM mart_external_context_model_impact
        ORDER BY decision_signal
    """,
}


def sql_path(path: Path) -> str:
    return str(path).replace("'", "''")


def load_table(connection: duckdb.DuckDBPyConnection, table_name: str, path: Path) -> int:
    connection.execute(
        f"""
        CREATE OR REPLACE TABLE {table_name} AS
        SELECT *
        FROM read_csv_auto('{sql_path(path)}', header = true, all_varchar = true)
        """
    )
    return int(connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])


def build_warehouse() -> dict[str, object]:
    ensure_dirs()
    connection = duckdb.connect(str(WAREHOUSE_DB_PATH))
    try:
        table_counts = {}
        for table_name, path, _description in CSV_TABLES:
            table_counts[table_name] = load_table(connection, table_name, path)

        for statement in ANALYTIC_SQL.values():
            connection.execute(statement)

        view_counts = {
            view_name: int(connection.execute(f"SELECT COUNT(*) FROM {view_name}").fetchone()[0])
            for view_name in ANALYTIC_SQL
        }
        manifest = {
            "generated_at": utc_now_iso(),
            "warehouse_path": str(WAREHOUSE_DB_PATH.relative_to(PROJECT_ROOT)),
            "tables": table_counts,
            "views": view_counts,
            "source_contract": "CSV source systems -> DuckDB staging tables -> analytics views -> reports",
        }
        write_json(WAREHOUSE_MANIFEST_PATH, manifest)
        return manifest
    finally:
        connection.close()


def render_warehouse_lineage(manifest: dict[str, object]) -> str:
    table_counts = manifest["tables"]
    view_counts = manifest["views"]
    lines = [
        "# DuckDB Warehouse Lineage",
        "",
        "The local DuckDB warehouse provides a SQL inspection layer over the synthetic hotel operating data.",
        "",
        "The database file is generated locally and ignored by Git. Reviewable outputs remain in CSV and Markdown.",
        "",
        "## Source-To-Table Map",
        "",
        "| DuckDB object | Rows | Source purpose |",
        "| --- | ---: | --- |",
    ]
    for table_name, _path, description in CSV_TABLES:
        lines.append(f"| `{table_name}` | {table_counts[table_name]} | {description} |")

    lines.extend(
        [
            "",
            "## Analytics Views",
            "",
            "| View | Rows | Use |",
            "| --- | ---: | --- |",
            f"| `vw_comp_decision_summary` | {view_counts['vw_comp_decision_summary']} | Executive rollup of comp value, cost, recovery value, and manager review volume. |",
            f"| `vw_comp_mix` | {view_counts['vw_comp_mix']} | Comp-type mix by cases, guest-facing value, and internal cost. |",
            f"| `vw_manager_review_queue` | {view_counts['vw_manager_review_queue']} | Manager review queue combining escalation and low-match-confidence cases. |",
            f"| `vw_audit_decision_signal` | {view_counts['vw_audit_decision_signal']} | Audit-class decision signal for under-recovery, over-comping, review, and data-quality holds. |",
            f"| `vw_source_quality_snapshot` | {view_counts['vw_source_quality_snapshot']} | Compact source-quality metrics for messy-data review. |",
            f"| `vw_public_pricing_context` | {view_counts['vw_public_pricing_context']} | Public quoted-rate context used for room-comp opportunity-cost reasoning. |",
            f"| `vw_external_context_sources` | {view_counts['vw_external_context_sources']} | Row counts for public/sample external-context layers. |",
            f"| `vw_external_context_model_impact` | {view_counts['vw_external_context_model_impact']} | Controlled model-impact comparisons for public-context signals. |",
            "",
            "## Rebuild Command",
            "",
            "```bash",
            "make warehouse",
            "```",
            "",
            "## Example SQL",
            "",
            "```sql",
            "SELECT * FROM vw_comp_decision_summary;",
            "SELECT * FROM vw_comp_mix ORDER BY recommended_guest_value DESC;",
            "SELECT * FROM vw_manager_review_queue LIMIT 20;",
            "SELECT * FROM vw_public_pricing_context LIMIT 20;",
            "SELECT * FROM vw_external_context_model_impact;",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def render_query_inventory() -> str:
    lines = [
        "# SQL Query Inventory",
        "",
        "This inventory documents the named SQL views built in the local DuckDB warehouse.",
        "",
    ]
    for view_name, statement in ANALYTIC_SQL.items():
        lines.extend(
            [
                f"## `{view_name}`",
                "",
                "```sql",
                dedent(statement).strip(),
                "```",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    manifest = build_warehouse()
    WAREHOUSE_LINEAGE_REPORT.write_text(render_warehouse_lineage(manifest), encoding="utf-8")
    SQL_QUERY_INVENTORY_REPORT.write_text(render_query_inventory(), encoding="utf-8")
    print(f"Wrote DuckDB warehouse: {WAREHOUSE_DB_PATH.relative_to(PROJECT_ROOT)}")
    print(f"Wrote warehouse manifest: {WAREHOUSE_MANIFEST_PATH.relative_to(PROJECT_ROOT)}")
    print(f"Wrote warehouse lineage: {WAREHOUSE_LINEAGE_REPORT.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
