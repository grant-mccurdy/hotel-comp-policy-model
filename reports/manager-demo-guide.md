# Manager Decision Desk

This supporting prototype demonstrates the proposed manager interaction. The stakeholder brief remains the primary deliverable.

## Start

```bash
make runtime-bundle
cd cloudflare
uv run pywrangler dev
```

Open the local URL printed by Wrangler. The public-mode interface is synthetic-only and stateless.

## Scenario Walkthrough

Use a synthetic room-readiness delay and review the suggested structured incident fields before confirming them. The recommendation exposes:

- the recovery gesture and modeled guest-facing value;
- estimated marginal-cost range;
- service-recovery floor and relationship adjustment;
- delivery timing and manager-note template;
- decision reasons and limited stability interpretation;
- approval path and required confirmations;
- two feasible alternatives.

Uncheck recovery options to confirm the selected gesture always remains in the available set. Increase the repeat-comp review signal to confirm it triggers manager review without lowering the recovery floor.

## API Contract

- `POST /v1/recommend` returns the versioned decision response.
- `POST /v1/intake/parse` suggests bounded fields from synthetic narrative input.
- `GET /healthz` returns the runtime bundle identity and disabled-persistence status.

Invalid scenarios return HTTP `422`. Obvious email, phone, reservation, and confirmation identifiers are rejected by the public narrative endpoint. If narrative extraction is unavailable, the structured form remains usable.

## Boundary

The desk is not connected to a hotel PMS, CRM, inventory system, comp ledger, approved policy, or internal margin data. Input-sensitivity stability is not a probability that the recommendation will recover a guest. Persistent operational logging is not active in public mode.
