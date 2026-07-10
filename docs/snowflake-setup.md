# Snowflake Setup

Snowflake is the primary warehouse path for this project. DuckDB remains a
credential-free fallback for local review, but the normal project workflow loads
public-safe artifacts into Snowflake, validates row counts and views, and
exports query outputs.

## 1. Install Snowflake CLI

Use a local virtual environment so the system Python stays untouched:

```bash
cd /home/grant/repos/public/hotel-comp-policy-model
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-snowflake.txt
.venv/bin/snow --help
```

## 2. Configure A Local Connection

Create key-pair auth material outside the repo. Do not store Snowflake config
files, private keys, passwords, or tokens in this repository.

```bash
mkdir -p "$HOME/.config/snowflake/keys"
openssl genpkey -algorithm RSA \
  -pkeyopt rsa_keygen_bits:2048 \
  -out "$HOME/.config/snowflake/keys/hotel_comp_policy_model_key.p8"
openssl rsa \
  -in "$HOME/.config/snowflake/keys/hotel_comp_policy_model_key.p8" \
  -pubout \
  -out "$HOME/.config/snowflake/keys/hotel_comp_policy_model_key.pub"
chmod 600 "$HOME/.config/snowflake/keys/hotel_comp_policy_model_key.p8"
```

Convert the public key to the format Snowflake expects:

```bash
openssl rsa \
  -pubin \
  -in "$HOME/.config/snowflake/keys/hotel_comp_policy_model_key.pub" \
  -outform DER | openssl base64 -A
```

In a Snowflake worksheet, run this with the generated public key value:

```sql
ALTER USER <project_user> SET RSA_PUBLIC_KEY = '<public_key_without_header_or_footer>';
```

Verify that Snowflake has the same key fingerprint:

```sql
DESC USER <project_user>;
```

Compare Snowflake's `RSA_PUBLIC_KEY_FP` value to the local key fingerprint:

```bash
openssl rsa \
  -pubin \
  -in "$HOME/.config/snowflake/keys/hotel_comp_policy_model_key.pub" \
  -outform DER 2>/dev/null \
  | openssl dgst -sha256 -binary \
  | openssl base64 -A
```

If `make snowflake-test` reports `JWT token is invalid`, the public key in
Snowflake does not match the private key used by the local CLI profile, or the
public key has not been registered on the configured project user.

Then create or update the Snowflake CLI connection outside the repo:

Example local connection flow:

```bash
snow connection add \
  --connection-name hotel_comp_admin_keypair \
  --account <org-account_identifier> \
  --user <project_user> \
  --authenticator SNOWFLAKE_JWT \
  --private-key-path "$HOME/.config/snowflake/keys/hotel_comp_policy_model_key.p8" \
  --role ACCOUNTADMIN \
  --warehouse HOTEL_COMP_WH \
  --database HOTEL_COMP_POLICY_MODEL \
  --schema RAW

snow connection add \
  --connection-name hotel_comp_dev_keypair \
  --account <org-account_identifier> \
  --user <project_user> \
  --authenticator SNOWFLAKE_JWT \
  --private-key-path "$HOME/.config/snowflake/keys/hotel_comp_policy_model_key.p8" \
  --role HOTEL_COMP_DEV_ROLE \
  --warehouse HOTEL_COMP_WH \
  --database HOTEL_COMP_POLICY_MODEL \
  --schema RAW
```

Use these project defaults when prompted after the initial account setup exists:

```text
admin connection name: hotel_comp_admin_keypair
default connection name: hotel_comp_dev_keypair
authenticator: SNOWFLAKE_JWT
warehouse: HOTEL_COMP_WH
database: HOTEL_COMP_POLICY_MODEL
schema: RAW
```

For the first bootstrap, the connection must have a role that can create a
warehouse, database, schemas, and a project role. After bootstrap, use
`HOTEL_COMP_DEV_ROLE` for normal project work.

Set connector values and the bootstrap grantee outside the repository:

```bash
export SNOWFLAKE_ACCOUNT=<org-account_identifier>
export SNOWFLAKE_USER=<project_user>
export SNOWFLAKE_BOOTSTRAP_USER=<project_user>
```

## 3. Bring Snowflake Online

```bash
SNOWFLAKE_CONNECTION=hotel_comp_dev_keypair make snowflake-test
SNOWFLAKE_ADMIN_CONNECTION=hotel_comp_admin_keypair make snowflake-bootstrap
SNOWFLAKE_CONNECTION=hotel_comp_dev_keypair make snowflake-load
SNOWFLAKE_CONNECTION=hotel_comp_dev_keypair make snowflake-validate
SNOWFLAKE_CONNECTION=hotel_comp_dev_keypair make snowflake-extracts
```

Expected generated reports:

```text
reports/snowflake-warehouse-lineage.md
reports/snowflake-validation.md
reports/snowflake-query-extracts.md
data/manifests/snowflake_warehouse_manifest.json
```

## 4. Automation Boundary

Key-pair auth is appropriate for local development and automation. GitHub
Actions should store the private key in the platform's secret store, not in the
repository.

GitHub Actions should keep Snowflake CI optional until repository secrets are
configured. The manual Snowflake workflow expects these repository secrets:

```text
SNOWFLAKE_ACCOUNT
SNOWFLAKE_USER
SNOWFLAKE_PRIVATE_KEY
SNOWFLAKE_ADMIN_ROLE
SNOWFLAKE_DEV_ROLE
```

Public reviewers can run `make local-all` without any Snowflake account.

## 5. S3 Data Lake To Snowflake

For the enterprise ingestion path, configure AWS credentials outside the repo and
set:

```bash
export HOTEL_COMP_S3_BUCKET=<your-s3-bucket>
export HOTEL_COMP_S3_PREFIX=hotel-comp-policy-model
```

Then run:

```bash
make s3-bootstrap
make enterprise-all
```

The S3 bootstrap creates a private data lake landing bucket/prefix, an IAM
role/policy for Snowflake read access, a Snowflake storage integration, and a
Snowflake external stage. The enterprise load path publishes CSV artifacts to
S3 and uses Snowflake `COPY INTO` from that external stage.

Current scope: the S3 path mirrors the project CSV contract, including
source/context artifacts and derived mart artifacts. A stricter production
version would land raw operational extracts first, then build marts inside
Snowflake.

The current working Snowflake default uses connector batch inserts because local
Snowflake file transfer was unreliable in this environment. The S3 external-stage
path is the stronger production-style architecture once AWS credentials are
configured.
