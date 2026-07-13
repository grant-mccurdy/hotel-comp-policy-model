# Project Readiness Checklist

| Area | Status | Evidence |
| --- | --- | --- |
| Business decision is explicit | Ready | The root stakeholder report recommends a four-week, minimum-50-case shadow validation of the generated Guardrailed Recovery candidate. |
| First-click stakeholder deliverable | Ready locally; hosted refresh pending | The generated report contains the decision, worked scenarios, shadow-validation proposal, and engineering-evidence link. |
| Synthetic/public boundary | Ready | README, reports, contracts, and interface distinguish each evidence class. |
| Input validation | Ready | Shared contract rejects impossible and unknown values. |
| Policy provenance | Ready | Versioned JSON policy records assumptions and public anchors. |
| Cost uncertainty | Ready | Every recommendation carries low/mid/high estimated cost. |
| Alternatives and explanations | Ready | Manager outputs include alternatives, reason codes, approval paths, and conditions requiring confirmation. |
| Policy comparison | Ready | Five rules are evaluated against the same 430 synthetic cases using one recovery reference. |
| Sensitivity analysis | Ready | A 10,000-draw paired bootstrap and 5,000 coherent shared-world assumption-stress draws rerun the guardrails and selection rule. |
| Messy source workflow | Ready | Seven synthetic operating systems preserve realistic quality problems. |
| Observed property context | Ready | Eleven official Santa Monica Proper public anchors are recorded. |
| Local warehouse | Ready | DuckDB builds tables and decision views. |
| Cloud warehouse execution | Ready | The current build loaded 22 S3 artifacts into Snowflake, queried 12 views, and passed 46 structural and semantic checks. |
| Manager interface | Ready locally | HTML desk, JSON endpoint, presets, container build, health endpoint, and desktop/mobile layouts are verified. |
| Automated tests | Ready | Unit and randomized policy tests run with `make test`. |
| Remote CI | Ready | GitHub Actions completed the local fallback workflow from a clean checkout. |
| Standalone repository | Ready | Initial release scope is reviewed; source-repository visibility remains private by design. |
| Public deployment | Refresh pending | The existing static host must be republished with the current decision and engineering-evidence bundle. |
| S3-to-Snowflake evidence | Ready | Separate landing/model-output zones, typed MARTS, external-stage loading, report extracts, and sanitized execution evidence are current. |

## Release Gate

- [x] `make local-all` passes locally.
- [x] Public-release audit finds no credentials, private paths, or account-scoped infrastructure identifiers.
- [x] Stakeholder [desktop](screenshots/stakeholder-report-desktop.png), [mobile overview](screenshots/stakeholder-report-mobile.png), and [mobile decision](screenshots/stakeholder-report-mobile-decision.png) layouts are reviewed.
- [x] Manager-desk [desktop](screenshots/manager-desk-desktop.png), [mobile input](screenshots/manager-desk-mobile.png), and [mobile recommendation](screenshots/manager-desk-mobile-result.png) layouts are reviewed.
- [x] Repository scope and generated artifacts are reviewed before the first commit.
- [x] Clean-checkout GitHub Actions validation passes.
- [x] Initial commit and private push receive explicit approval.
- [ ] Current sanitized stakeholder and engineering-evidence bundle is published and inspected at the live URL.
- [ ] Source-repository public visibility receives separate approval if later needed.
