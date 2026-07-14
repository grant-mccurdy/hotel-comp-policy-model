# Public Release Audit

Generated at: `2026-07-14T18:29:37+00:00`

## Summary

- Files scanned: `156`
- Release status: `NO BLOCKERS FOUND`
- Blockers: `0`

## Automated Checks

| Check | Status | Detail |
| --- | --- | --- |
| Secret-like token patterns | PASS | 0 hits |
| Private workspace paths | PASS | 0 hits |
| Account-scoped infrastructure identifiers | PASS | 0 hits |
| Credential-like files | PASS | none found |
| data/raw/ ignored | PASS | .gitignore rule present |
| data/warehouse/ ignored | PASS | .gitignore rule present |
| .env ignored | PASS | .gitignore rule present |
| python cache ignored | PASS | .gitignore rule present |
| Snowflake local config ignored | PASS | .gitignore rule present |
| Quarto and renv caches ignored | PASS | .gitignore rule present |

## Public-Safety Boundary

- Internal hotel records, guest PII, real comp history, internal rates, occupancy, revenue, margin, inventory, and proprietary policy are not included.
- Full public-source downloads remain outside Git under `data/raw/`.
- The local DuckDB database remains outside Git under `data/warehouse/`.
- Snowflake connection files, private keys, and key-pair auth material must remain outside Git.
- Live API credentials are not required for the default workflow and should remain outside the repository.

## Manual Review Items

- Confirm generated reports continue to frame the project as a synthetic prototype.
- Confirm references to Santa Monica Proper or Proper Hotels are public-context framing, not claims of internal access.
- Confirm any future live API extraction writes only public-safe, non-secret outputs.
