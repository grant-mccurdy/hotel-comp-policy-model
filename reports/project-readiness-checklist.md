# Project Readiness Checklist

| Area | Status | Evidence |
| --- | --- | --- |
| Business decision is explicit | Ready | The root stakeholder report leads with a tiered recovery policy and human-review recommendation. |
| First-click stakeholder deliverable | Ready locally | `index.html` provides one brief, self-contained decision report with worked scenarios and a pilot proposal. |
| Synthetic/public boundary | Ready | README, reports, contracts, and interface distinguish each evidence class. |
| Input validation | Ready | Shared contract rejects impossible and unknown values. |
| Policy provenance | Ready | Versioned JSON policy records assumptions and public anchors. |
| Cost uncertainty | Ready | Every recommendation carries low/mid/high estimated cost. |
| Alternatives and explanations | Ready | Two alternatives and decision-changing counterfactuals are returned. |
| Sensitivity analysis | Ready | ±20% perturbation report and case-level stability are generated. |
| Messy source workflow | Ready | Seven synthetic operating systems preserve realistic quality problems. |
| Observed property context | Ready | Eleven official Santa Monica Proper public anchors are recorded. |
| Local warehouse | Ready | DuckDB builds tables and decision views. |
| Cloud warehouse definitions | Ready | Snowflake tables, views, validation, and extracts are implemented. |
| Manager interface | Ready locally | HTML desk, JSON endpoint, presets, container build, health endpoint, and desktop/mobile layouts are verified. |
| Automated tests | Ready | Unit and randomized policy tests run with `make test`. |
| Standalone repository | Ready | Initial release scope is reviewed; remote visibility remains private pending publication approval. |
| Public deployment | Pending approval | Container is ready; no deployment has been made. |
| S3-to-Snowflake evidence | Ready | Fresh external-stage `COPY INTO` loaded 18 tables; 26 Snowflake table/view checks passed. |

## Release Gate

- [x] `make local-all` passes locally.
- [x] Public-release audit finds no credentials, private paths, or account-scoped infrastructure identifiers.
- [x] Stakeholder [desktop](screenshots/stakeholder-report-desktop.png), [mobile overview](screenshots/stakeholder-report-mobile.png), and [mobile decision](screenshots/stakeholder-report-mobile-decision.png) layouts are reviewed.
- [x] Manager-desk [desktop](screenshots/manager-desk-desktop.png), [mobile input](screenshots/manager-desk-mobile.png), and [mobile recommendation](screenshots/manager-desk-mobile-result.png) layouts are reviewed.
- [x] Repository scope and generated artifacts are reviewed before the first commit.
- [x] Initial commit and private push receive explicit approval.
- [ ] Public repository visibility and hosted deployment receive explicit approval.
