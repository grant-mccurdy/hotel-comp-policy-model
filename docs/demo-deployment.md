# Report And Demo Deployment

The root `index.html` is the canonical stakeholder deliverable. A sanitized static bundle is published through the portfolio GitHub Pages site. The manager decision desk is a supporting local application and is not publicly deployed. Both use synthetic scenarios and public property context only.

## Stakeholder Report

```bash
python3 -m http.server 8000
```

Open `http://127.0.0.1:8000` for local review. The public stakeholder report is available at:

```text
https://grant-mccurdy.github.io/projects/hotel-comp-policy-model/
```

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

The static bundle was published after the release audit and explicit approval.
Publishing the manager application or changing source-repository visibility still
requires separate approval. Neither demonstration needs Snowflake, AWS, API keys,
or internal hotel data at runtime.
