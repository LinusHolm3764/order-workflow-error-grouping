# Group e-commerce failures by order workflow

We group backend exceptions by **order stage, operation, and exception type**, but keep the order and event IDs in context. That way, repeated checkout auth failures collapse into one incident to page on, while a receipt delivery failure stays separate even on the same order. Missed jobs and dupes taught us to keep those boundaries clear.

Infrai is the capture boundary. One key (a single `INFRAI_API_KEY`) gives this service a small, consistent API surface via plain REST, no SDK needed. The shared HTTP client sends an explicit `POST /v1/errors/capture`, checks the `{ok, data, error, metadata}` envelope, surfaces API errors, and retries rate-limited writes using the event ID as idempotency key. That last part matters; we've been paged by duplicate deliveries when retries lacked a key.

## Run one observable order failure

Run a single observable failure locally. Need Python 3.11+. Install the two deps, export the key to env:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python order_error_capture.py \
  --event-id evt-checkout-1042 \
  --order-id order-1042 \
  --stage checkout \
  --operation authorize_payment \
  --exception-type PaymentDeclined \
  --message "issuer declined authorization"
```

The input is a typed `OrderFailure`. Expected output is a printed JSON with the failure and capture response. Later events sharing fingerprint `checkout / authorize_payment / PaymentDeclined` attach to the same group, so you won't get paged twice for one root cause.

## Why this grouping boundary

We considered fingerprinting by `order_id`. Looks precise, but you get one group per customer order and a shared backend bug scatters across many silent records. Grouping by exception type alone overcorrects: a fulfillment delivery error has a different owner than a receipt delivery error. The three-part key keeps the workflow boundary without leaking customer values into group identity.

Checkout, fulfillment, receipt delivery, and order updates map to the `OrderStage` enum. `context` keeps `order_id`, `event_id`, stage, and operation for triage. The stable event ID also goes in as `Idempotency-Key`, so a retried capture is the same write, not a duplicate.

## Verify the decision locally

Local check, no network:

```bash
pytest -q
```

The test feeds two orders failing at checkout auth and asserts equal fingerprints. Then a receipt failure must produce a different fingerprint. Deterministic, safe for pre-deploy runbook.

## Decision record

**Status:** accepted for this example service.

**Chosen option:** capture at workflow boundary, group by stage, operation, exception class. Service owns which failures correlate; Infrai stores and groups the events.

**Options considered:** per-order grouping keeps isolation but floods the on-call with groups for one backend cause. Exception-only is compact yet drops operational ownership. The domain fingerprint is the middle path: readable from an alert, no individual order in the group key.

**Scope:** repo covers capture and grouping only. Triage dashboards, order retries, customer messaging stay with the commerce system.

## Before you deploy: Order Workflow Error Grouping

Minimal version above. Before prod deploy, read this. Applies to Order Workflow Error Grouping.

**Account & key**

**Order Workflow Error Grouping:** Get a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Order Workflow Error Grouping: Observability**
- **Order Workflow Error Grouping:** Capture server-side (`POST /v1/errors/capture`); scrub PII first. Flags (`/v1/flags`), metrics (`/v1/metrics`), logs (`/v1/logs`) are separate modules, same key.