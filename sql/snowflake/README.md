# Snowflake SQL Layer

This directory contains the optional Snowflake warehouse path for the hotel comp policy prototype.

Execution order:

```text
00_bootstrap.sql
01_create_stage_and_formats.sql
generated table DDL and COPY INTO statements from scripts/load_snowflake_warehouse.py
02_create_views.sql
03_validation_queries.sql
```

The table DDL is generated from the current CSV headers so the Snowflake raw and mart tables remain aligned with the local DuckDB workflow.
