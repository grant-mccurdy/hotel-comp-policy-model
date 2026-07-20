# Report And Decision Desk Deployment

The portal project brief is the canonical portfolio route, the generated root `index.html` is the stakeholder decision report, and the Cloudflare Python Worker is the public synthetic decision-desk runtime. None of these interfaces accepts real guest data.

## Stakeholder Brief

```bash
python3 -m http.server 8000
```

Open `http://127.0.0.1:8000`. The currently published brief remains at:

```text
https://grant-mccurdy.github.io/projects/hotel-comp-policy-model.html
```

The deeper generated report is published separately at `https://grant-mccurdy.github.io/projects/hotel-comp-policy-model/`. Local generated output may be newer until publication is explicitly approved.

## Cloudflare Decision Desk

Build the checksummed runtime bundle and embedded UI before starting the Worker:

```bash
make runtime-bundle
make worker-ui
cd cloudflare
uv sync
uv run pywrangler dev
```

Verify `/healthz`, submit a synthetic scenario to `POST /v1/recommend`, and test the guided interface at `/`. Workers AI narrative extraction accesses a remote model even during local Worker development and can incur usage; the structured form and recommendation endpoint do not require narrative extraction.

The public configuration has no D1 binding and no persistence route. `cloudflare/migrations/0001_shadow_log.sql` is a future authenticated shadow-environment contract only.

Dry-run the deployment package without changing live state:

```bash
uv run pywrangler deploy --dry-run
```

An actual Worker deployment, custom route, D1 resource, Access application, commit, push, or GitHub Pages update requires separate approval.

## Local Python Fallback

```bash
python3 scripts/manager_app.py
```

Open `http://127.0.0.1:8765`. Its `/recommend.json` route uses the same versioned decision response as the Worker.
