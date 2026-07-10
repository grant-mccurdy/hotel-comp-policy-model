# Source System Quality Report

This report is intentionally not clean. The synthetic source systems preserve realistic hotel-data problems before the recovery-case mart normalizes them.

| Source issue | Count |
| --- | ---: |
| PMS reservations | 1600 |
| CRM profiles, including duplicates | 1725 |
| Duplicate CRM profiles | 125 |
| Service tickets | 430 |
| Tickets missing direct PMS reservation ID | 53 |
| Tickets missing severity | 60 |
| Dirty issue-code labels | 40 |
| Comp ledger entries | 281 |
| Comp ledger entries without ticket ID | 64 |
| Dirty comp-action labels | 39 |
| Delayed review/survey records | 128 |

The downstream mart should retain match confidence and source-quality flags rather than hiding this messiness.
