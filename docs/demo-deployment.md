# Report And Demo Deployment

The root `index.html` is the canonical stakeholder deliverable. The manager decision desk is a supporting interactive application. Neither is deployed automatically, and both use synthetic scenarios and public property context only.

## Stakeholder Report

```bash
python3 -m http.server 8000
```

Open `http://127.0.0.1:8000`. The report has no runtime dependencies and can later be hosted as a static site after publication approval.

The generated `index.html` can also be opened directly without starting a server.

## Manager Desk

```bash
python3 scripts/manager_app.py
```

Open `http://127.0.0.1:8765` and verify `http://127.0.0.1:8765/healthz`.

## Container

```bash
docker build -t hotel-comp-policy-model .
docker run --rm -p 8765:8765 hotel-comp-policy-model
```

Any public deployment should occur only after the release audit passes and the
repository owner explicitly approves publication. The application does not need
Snowflake, AWS, API keys, or internal hotel data for the scenario demonstration.
