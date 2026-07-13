.PHONY: acquire acquire-pricing pricing-context proper-context property-context review-context demand-context external-context profile synthesize sources mart recommend compare-policies sensitivity audit artifacts duckdb-warehouse warehouse reports model-impact demo manager-app test validate validate-acquisition validate-comp public-audit snowflake-docs snowflake-test snowflake-bootstrap snowflake-load snowflake-validate snowflake-extracts snowflake-all s3-plan s3-bootstrap s3-publish snowflake-copy-s3 enterprise-all local-all cloud-all all

PYTHON ?= python3
SNOWFLAKE_CONNECTION ?= hotel_comp_dev_keypair
SNOWFLAKE_ADMIN_CONNECTION ?= hotel_comp_admin_keypair
HOTEL_COMP_S3_BUCKET ?=
HOTEL_COMP_S3_PREFIX ?= hotel-comp-policy-model

all: cloud-all

cloud-all: artifacts warehouse reports demo test validate public-audit

enterprise-all: artifacts s3-publish snowflake-copy-s3 snowflake-validate snowflake-extracts reports demo test validate public-audit

local-all: artifacts duckdb-warehouse reports demo test validate public-audit snowflake-docs

artifacts: acquire profile acquire-pricing external-context sources mart recommend compare-policies sensitivity audit model-impact

acquire:
	$(PYTHON) scripts/acquire_booking_data.py

acquire-pricing:
	$(PYTHON) scripts/acquire_rate_shop_data.py

pricing-context:
	$(PYTHON) scripts/build_public_pricing_context.py

property-context:
	$(PYTHON) scripts/build_property_context.py

proper-context:
	$(PYTHON) scripts/build_proper_public_context.py

review-context:
	$(PYTHON) scripts/build_review_risk_context.py

demand-context:
	$(PYTHON) scripts/build_local_demand_context.py

external-context: pricing-context proper-context property-context review-context demand-context

profile:
	$(PYTHON) scripts/profile_sources.py

sources:
	$(PYTHON) scripts/generate_synthetic_source_systems.py

mart:
	$(PYTHON) scripts/build_recovery_case_mart.py

recommend:
	$(PYTHON) scripts/generate_synthetic_comp_data.py

compare-policies:
	$(PYTHON) scripts/evaluate_policy_strategies.py

sensitivity:
	$(PYTHON) scripts/generate_policy_sensitivity_report.py

audit:
	$(PYTHON) scripts/audit_comp_policy.py

synthesize: sources mart recommend audit

duckdb-warehouse:
	$(PYTHON) scripts/build_duckdb_warehouse.py

warehouse: snowflake-all

reports:
	$(PYTHON) scripts/generate_reports.py

model-impact:
	$(PYTHON) scripts/generate_external_context_model_impact.py

demo:
	$(PYTHON) scripts/run_demo_scenarios.py

manager-app:
	$(PYTHON) scripts/manager_app.py

validate: validate-acquisition validate-comp

validate-acquisition:
	$(PYTHON) scripts/validate_data_acquisition.py

validate-comp:
	$(PYTHON) scripts/validate_comp_model.py

test:
	$(PYTHON) -m unittest discover -s tests -v

public-audit:
	$(PYTHON) scripts/public_release_audit.py

snowflake-docs:
	$(PYTHON) scripts/load_snowflake_warehouse.py lineage

snowflake-test:
	SNOWFLAKE_CONNECTION=$(SNOWFLAKE_CONNECTION) $(PYTHON) scripts/load_snowflake_warehouse.py test

snowflake-bootstrap:
	SNOWFLAKE_CONNECTION=$(SNOWFLAKE_ADMIN_CONNECTION) $(PYTHON) scripts/load_snowflake_warehouse.py bootstrap

snowflake-load:
	SNOWFLAKE_CONNECTION=$(SNOWFLAKE_CONNECTION) $(PYTHON) scripts/load_snowflake_warehouse.py load

snowflake-validate:
	SNOWFLAKE_CONNECTION=$(SNOWFLAKE_CONNECTION) $(PYTHON) scripts/load_snowflake_warehouse.py validate

snowflake-extracts:
	SNOWFLAKE_CONNECTION=$(SNOWFLAKE_CONNECTION) $(PYTHON) scripts/generate_snowflake_report_extracts.py

snowflake-all:
	SNOWFLAKE_CONNECTION=$(SNOWFLAKE_ADMIN_CONNECTION) $(PYTHON) scripts/load_snowflake_warehouse.py bootstrap
	SNOWFLAKE_CONNECTION=$(SNOWFLAKE_CONNECTION) $(PYTHON) scripts/load_snowflake_warehouse.py load
	SNOWFLAKE_CONNECTION=$(SNOWFLAKE_CONNECTION) $(PYTHON) scripts/load_snowflake_warehouse.py validate
	SNOWFLAKE_CONNECTION=$(SNOWFLAKE_CONNECTION) $(PYTHON) scripts/generate_snowflake_report_extracts.py

s3-plan:
	HOTEL_COMP_S3_BUCKET=$(HOTEL_COMP_S3_BUCKET) HOTEL_COMP_S3_PREFIX=$(HOTEL_COMP_S3_PREFIX) $(PYTHON) scripts/publish_s3_datalake.py --dry-run

s3-bootstrap:
	HOTEL_COMP_S3_BUCKET=$(HOTEL_COMP_S3_BUCKET) HOTEL_COMP_S3_PREFIX=$(HOTEL_COMP_S3_PREFIX) SNOWFLAKE_CONNECTION=$(SNOWFLAKE_ADMIN_CONNECTION) $(PYTHON) scripts/bootstrap_s3_snowflake_integration.py

s3-publish:
	HOTEL_COMP_S3_BUCKET=$(HOTEL_COMP_S3_BUCKET) HOTEL_COMP_S3_PREFIX=$(HOTEL_COMP_S3_PREFIX) $(PYTHON) scripts/publish_s3_datalake.py

snowflake-copy-s3:
	HOTEL_COMP_S3_BUCKET=$(HOTEL_COMP_S3_BUCKET) HOTEL_COMP_S3_PREFIX=$(HOTEL_COMP_S3_PREFIX) SNOWFLAKE_CONNECTION=$(SNOWFLAKE_CONNECTION) $(PYTHON) scripts/load_snowflake_from_s3.py
