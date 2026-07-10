# Data Acquisition Notes

## Business Question

For a luxury hotel service failure, what guest recovery or compensation tier is
justified given the failure context, guest/stay context, brand risk, and budget
discipline?

## Data Reality

Public hospitality datasets can support booking context, review language,
service-failure taxonomy, public quoted-rate market context, property/amenity
context, and external demand-pressure proxies. They do not appear to expose
actual hotel compensation decisions, manager approval notes, service-recovery
tickets, guest lifetime value, true occupancy, room inventory, contribution
margin, or post-recovery outcomes.

The project therefore uses public data for calibration and synthetic data for
the internal operating signals needed to demonstrate the workflow. The synthetic
layer intentionally preserves real-world messiness: weak join keys, duplicate
CRM profiles, missing service-ticket fields, dirty comp labels, delayed reviews,
and ledger records that do not cleanly point back to a service ticket.

## Stage 1 Sources

### Hotel Booking Demand / TidyTuesday

Role: primary PMS-style booking and stay calibration.

Acquisition path:

```text
https://raw.githubusercontent.com/rfordatascience/tidytuesday/main/data/2020/2020-02-11/hotels.csv
```

Used for ADR, stay length, lead time, special requests, repeated guest flag,
room mismatch, booking changes, waiting-list behavior, customer type, and
seasonality.

### 515K Hotel Reviews Data In Europe

Role: review language and service-failure taxonomy.

Acquisition path is documented as a manual or Kaggle-mediated download because
the full file is large and may require user-local Kaggle access.

Used later for negative review language, reviewer score, tags, hotel reputation
context, and complaint pattern extraction.

### Service Recovery Research

Role: policy assumptions.

Used for outcome vs process failures, speed of recovery, apology, compensation,
and under/over-compensation risk.

### Public Quoted-Rate Context

Role: external market pressure and room-comp opportunity-cost context.

Default acquisition path:

```text
data/sample/external_context/rate_shop_snapshots_sample.csv
```

The default workflow uses a reproducible sample-seed extract with the same field
shape expected from a public rate-shop/API source. If `RATE_SHOP_USE_API=true`
and `SERPAPI_API_KEY` is present, the acquisition script can request Google
Hotels-style public quote snapshots instead.

Captured fields include property name, property role, room/rate plan, quote
amount, total rate, provider context, cancellation flag, hotel class, rating,
review count, amenities, location, nearby-place context, capture method, source
query, and provenance.

Used for public rate pressure, comp-set median rate, target-vs-comp-set index,
refund cost pressure, and room-upgrade opportunity-cost proxies. These fields
must not be described as actual internal Proper Hotels rates, occupancy,
inventory, revenue, margin, or comp policy.

### Public Property Context

Role: property-fit and competitive-set context for comp suitability.

Default acquisition path:

```text
data/sample/external_context/property_context_public.csv
```

The current workflow records public property context for Santa Monica Proper and
a small Santa Monica luxury/lifestyle competitive set. Captured fields include
property role, source URL, public positioning, neighborhood, public room-count
signal when available, rooftop/F&B context, lobby/lounge context, spa/wellness
context, pool/rooftop context, parking/fee-recovery context, and comp-fit
modifiers.

Used for deciding whether a recovery gesture fits the public property
experience. It must not be described as internal room inventory, actual outlet
capacity, margin, staffing, or comp policy.

### Official Santa Monica Proper Value Anchors

Role: observed public option and guest-facing denomination context.

Default acquisition path:

```text
data/sample/external_context/proper_public_value_anchors.csv
```

The dated extract records official source URLs for published property scale,
room categories, eligible suite late checkout, destination and valet fees,
dining credits, return-stay offers, Recovery Suite value, Surya treatment value,
and signature outlets.

These values can calibrate the face value or property fit of a recovery option.
They cannot establish internal marginal cost, contribution margin, availability,
or approved comp policy. Every anchor explicitly marks internal cost as unknown.

### Review-Risk Context

Role: issue-level reputation-risk prior.

Default acquisition path:

```text
data/sample/external_context/review_risk_context.csv
```

The current workflow maps public review themes or sample-seed taxonomy priors to
the service-failure categories in the model. If observed review breakdowns are
available from a public source, the context confidence can increase. Without
observed review context, the file remains a sample-seed prior and is labeled as
such.

Used to adjust review-risk priors by issue type. It must not be described as
actual Proper Hotels review outcomes, internal reputation monitoring, or
post-recovery satisfaction.

### Local Demand Context

Role: event/weather demand-pressure proxy for room-comp opportunity-cost
reasoning.

Default acquisition path:

```text
data/sample/external_context/local_demand_context.csv
```

The current workflow creates reproducible sample-seed demand context for the
modeled year. It includes daily event pressure, weather disruption pressure,
local demand pressure, and confidence/provenance fields. It is designed to be
replaced later by observed public event and weather feeds.

Used to make room upgrades and late checkout more expensive during high-demand
periods. It must not be described as true hotel occupancy, room inventory,
revenue-management demand, or staffing pressure.

## Internal-Only Data Not Available Publicly

- actual compensation amount
- actual recovery tier offered
- manager approval notes
- guest complaint ticket history
- in-stay issue timestamp
- resolution timestamp
- whether the guest accepted the comp
- loyalty status or lifetime value
- post-recovery satisfaction survey
- future return behavior
- staff member or department accountability
- room readiness timestamps
- housekeeping or maintenance workload
- actual occupancy pressure at time of failure
- actual booked ADR and net revenue
- room-type inventory and rate restrictions
- true room, F&B, spa, parking, and upgrade contribution margin
- brand-specific comp rules

These fields must be marked as synthetic, policy-simulated, or unavailable.

## Source-Shaped Synthetic Systems

The prototype creates separate synthetic source files rather than a single clean
modeling table:

- `raw_pms_reservations.csv`: reservation, stay, room, rate, channel, and room-move context.
- `raw_guest_profiles_crm.csv`: loyalty tier, traveler segment, contactability, duplicate profiles, and estimated value proxies.
- `raw_service_tickets.csv`: issue logs, dirty issue labels, missing reservation keys, and free-text complaint notes.
- `raw_comp_ledger.csv`: messy historical comp actions, face value, estimated internal cost, approvals, and orphan rows.
- `raw_pos_outlet_charges.csv`: rooftop/F&B, lounge, spa/wellness, valet, and in-room-dining spend.
- `raw_reviews_surveys.csv`: delayed post-stay review/survey signals and sentiment proxies.
- `raw_ops_daily.csv`: occupancy, housekeeping, front desk, F&B, spa, and maintenance pressure.
- `rate_shop_snapshots_sample.csv`: public quote/sample-seed external rate-shop context.
- `property_context_public.csv`: public property and competitive-set context.
- `proper_public_value_anchors.csv`: official property option and guest-facing value anchors.
- `review_risk_context.csv`: public/sample review-risk priors by issue category.
- `local_demand_context.csv`: sample local event/weather demand-pressure context.

These source systems are normalized into `data/marts/recovery_case_mart.csv`.
The recommendation model consumes the mart, not the raw source files directly.

## Warehouse Layer

The project also builds a local DuckDB warehouse for SQL inspection:

```bash
make duckdb-warehouse
```

The generated database lives at `data/warehouse/hotel_comp_policy.duckdb` and is
ignored by Git. The reviewable warehouse outputs are:

- `reports/warehouse-lineage.md`
- `reports/sql-query-inventory.md`
- `data/manifests/duckdb_warehouse_manifest.json`

The warehouse loads each messy source CSV and external-context CSV into staging
tables, loads the marts as analytic tables, and creates views for executive
rollups, comp mix, manager review queue, audit decision signals,
source-quality snapshots, public pricing context, and external-context
model-impact checks. The warehouse also carries the official public value-anchor
table as a separate provenance layer.

## Snowflake Warehouse Layer

The primary warehouse path loads the public-safe CSV artifacts into Snowflake:

```bash
make all
```

Individual Snowflake commands:

```bash
make snowflake-test
make snowflake-bootstrap
make snowflake-load
make snowflake-validate
make snowflake-extracts
```

This path uses Snowflake CLI for account setup and the Snowflake Python connector
for small-batch table loads. The Python wrapper
in `scripts/load_snowflake_warehouse.py` reads current CSV headers, creates
all-VARCHAR Snowflake tables, loads rows into RAW and MARTS tables, creates mart
and audit views, and writes lineage/validation reports.
`scripts/generate_snowflake_report_extracts.py` then queries the Snowflake views
and writes local ignored extracts plus a reviewable extract report.

The Snowflake path is intended to show a warehouse workflow:

```text
public-safe CSV artifacts
-> RAW and MARTS tables
-> MARTS and AUDIT views
-> validation, query extracts, and executive outputs
```

Snowflake does not change the data boundary. The loaded records are still
synthetic internal hotel operations plus public/sample context, not real hotel
guest records, comp history, rates, occupancy, inventory, revenue, margin, or
proprietary policy.

## Enterprise S3 Data Lake Path

The stronger ingestion architecture adds S3 as the data lake landing zone before
Snowflake:

```text
public-safe CSV artifacts
-> S3 data lake landing prefix with manifests, row counts, and file hashes
-> Snowflake external stage
-> COPY INTO RAW and MARTS tables
-> MARTS and AUDIT views
-> validation, query extracts, and executive outputs
```

Commands:

```bash
export HOTEL_COMP_S3_BUCKET=<your-s3-bucket>
export HOTEL_COMP_S3_PREFIX=hotel-comp-policy-model
make s3-bootstrap
make s3-publish
make snowflake-copy-s3
make snowflake-validate
make snowflake-extracts
```

The bootstrap step creates or verifies:

- S3 bucket with public access blocked, versioning enabled, and AES256 default encryption.
- IAM role and policy that allow Snowflake to read only the project S3 prefix.
- Snowflake storage integration `HOTEL_COMP_S3_INTEGRATION`.
- Snowflake external stage `RAW.S3_PROJECT_CSV_STAGE`.

Current scope: the S3 path mirrors the project CSV contract, so it can land
both source/context artifacts and derived mart artifacts. A stricter production
workflow would land raw operational extracts first, then build marts inside
Snowflake through SQL/dbt-style transformations.

The S3 path is the best enterprise-pattern workflow, but it requires AWS
credentials and Snowflake storage-integration setup. The connector batch-insert
path remains the reliable default for the current small prototype dataset.

## Local DuckDB Fallback

DuckDB remains available for credential-free local review:

```bash
make local-all
```

This fallback creates `data/warehouse/hotel_comp_policy.duckdb`,
`reports/warehouse-lineage.md`, and `reports/sql-query-inventory.md`. It is not
the primary warehouse path.
