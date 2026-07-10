# Manager Decision Desk

## Start

```bash
python3 scripts/manager_app.py
```

Open `http://127.0.0.1:8765`.

Reference captures: [desktop decision desk](screenshots/manager-desk-desktop.png), [mobile inputs](screenshots/manager-desk-mobile.png), and [mobile recommendation](screenshots/manager-desk-mobile-result.png).

## Scenario Walkthrough

Use the four presets to compare arrival delay, dining lapse, suite recovery, and parking friction. The result shows:

- recommended recovery and guest-facing amount;
- estimated internal-cost range;
- manager approval path;
- decision confidence and stability;
- policy drivers;
- decision-changing counterfactuals;
- two closest alternatives.

Changing room-availability pressure should make upgrades or late checkout less attractive. A prior comp pattern routes the case to review rather than reducing recovery automatically.

## JSON Contract

`/recommend.json` returns the same validated recommendation contract used by the HTML desk and batch pipeline. Invalid values return HTTP `422` with field errors. `/healthz` returns service status.

## Boundary

The desk uses synthetic scenarios and public property context. It is not connected to a hotel PMS, CRM, inventory system, comp ledger, or approved operating policy.
