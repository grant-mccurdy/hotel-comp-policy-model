# AWS S3 To Snowflake Setup

This project supports an enterprise-style ingestion path:

```text
public-safe CSV artifacts
-> S3 data lake landing zone
-> Snowflake external stage
-> COPY INTO warehouse tables
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
```

## Architecture Notes

S3 is the data lake landing zone. It stores public-safe CSV artifacts with row
counts, hashes, and run IDs. The current implementation mirrors the project CSV
contract, so it lands source/context artifacts and derived mart artifacts. A
stricter production version would land raw operational extracts first and build
all marts inside Snowflake.

Snowflake is the warehouse. It loads those files into structured `RAW` and
`MARTS` tables, then exposes `MARTS` and `AUDIT` views for decision artifacts.

The current default Snowflake path still uses connector batch inserts because
local Snowflake file transfer was unreliable in this environment. The S3 path is
the better production-style workflow once AWS credentials are configured.
