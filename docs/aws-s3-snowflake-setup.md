# AWS S3 To Snowflake Setup

This project supports an enterprise-style ingestion path:

```text
source/context CSV artifacts -> S3 landing/{run_id}
Python policy outputs -> S3 model-output/{run_id}
-> Snowflake external stage
-> COPY INTO source-faithful RAW and typed MARTS tables
-> MARTS/AUDIT views
-> validation and query extracts
```

## Prerequisites

- AWS CLI authenticated outside the repository.
- Snowflake key-pair auth working for `hotel_comp_admin_keypair` and `hotel_comp_dev_keypair`.
- No AWS credentials, Snowflake keys, or local cloud config committed to Git.

## Commands

Set a globally unique bucket name:

```bash
export HOTEL_COMP_S3_BUCKET=<your-globally-unique-bucket>
export HOTEL_COMP_S3_PREFIX=hotel-comp-policy-model
```

Preview the data lake landing manifest without uploading:

```bash
make s3-plan
```

Create the S3 bucket, IAM role/policy, Snowflake storage integration, and trust
relationship:

```bash
make s3-bootstrap
```

Publish generated artifacts to S3:

```bash
make s3-publish
```

Load Snowflake from S3:

```bash
make snowflake-copy-s3
make snowflake-validate
make snowflake-extracts
```

Run the full enterprise path:

```bash
make enterprise-all
```

## Generated Artifacts

```text
data/manifests/s3_datalake_manifest.json
data/manifests/s3_snowflake_integration_manifest.json
data/manifests/snowflake_s3_copy_manifest.json
reports/s3-datalake-manifest.md
reports/snowflake-validation.md
reports/snowflake-query-extracts.md
reports/engineering-evidence.md
data/manifests/cloud_execution_evidence.json
```

## Architecture Notes

S3 stores immutable public-safe artifacts with row counts, hashes, object
metadata, and run IDs. Source/context snapshots use `landing/{run_id}`. Python
bootstrap, policy-comparison, and sensitivity outputs use
`model-output/{run_id}` so derived artifacts are not mislabeled as raw data.

Snowflake is the warehouse. `RAW` preserves source-shaped text and missingness.
Curated `MARTS` use the versioned `snowflake_mart_types` contract, then expose
`MARTS` and `AUDIT` views for decision artifacts.

Connector batch inserts remain a convenient direct-load option. The
`enterprise-all` path is the authoritative cloud-evidence workflow because it
uses the S3 manifest, external stage, semantic validation, and report extracts.
