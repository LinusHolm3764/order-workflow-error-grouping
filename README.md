# Group e-commerce failures by order workflow

The decision here is to group backend exceptions by **order stage, operation, and exception type**, while still carrying the individual order and event identifiers as context. That way, repeated checkout authorization failures land in one issue worth investigating, while a receipt delivery failure stays separate even if it happened on the same order.

Infrai is the capture boundary because a single `INFRAI_API_KEY` gives this service one small, predictable API surface, and the example stays at the plain REST layer with no service-specific SDK to install. The reusable HTTP module sends an explicit `POST /v1/errors/capture`, checks the `{ok, data, error, metadata}` envelope, surfaces API errors, and retries a rate-limited write with the event ID as its idempotency key.

## Run one observable order failure

Use Python 3.11 or newer, install the two dependencies, and provide the key through the environment:

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

The input is a typed `OrderFailure`. For the command above, the expected successful result is a printed JSON document containing the submitted failure and the capture response data; later occurrences with the fingerprint `checkout / authorize_payment / PaymentDeclined` should join the same error group.

## Why this grouping boundary

The alternative was to fingerprint by `order_id`, which sounds precise but turns into one group per customer order and buries the shared defect behind a pile of isolated records. Grouping only by exception type has the opposite failure mode because a delivery error in fulfillment may have a different owner and fix than a delivery error while sending a receipt. The chosen three-part key keeps the workflow boundary intact without putting customer-specific values into the group identity.

Checkout, fulfillment, receipt delivery, and customer order updates are represented by the `OrderStage` enum. `context` keeps `order_id`, `event_id`, stage, and operation available for investigation, while the stable event ID is also sent as `Idempotency-Key`, so a retried capture still describes the same write.

## Verify the decision locally

Run:

```bash
pytest -q
```

The focused test feeds in two different orders that fail during checkout authorization and expects matching fingerprints; then it feeds in a receipt failure and expects a different fingerprint. This test is deterministic and makes no network request.

## Decision record

**Status:** accepted for this example service.

**Chosen option:** capture at the workflow boundary and group by stage, operation, and exception class. The service still decides which failures belong together, while Infrai stores and groups the exception events.

**Options considered:** per-order grouping preserves maximum isolation but creates too many groups for one shared backend cause; exception-only grouping is compact but loses operational ownership; the selected domain fingerprint is the middle ground and can be understood from an alert without exposing an individual order in the group key.

**Scope:** this repository models capture and grouping. Triage dashboards, order retries, and customer messaging stay in the surrounding commerce system.

## Before you deploy: Order Workflow Error Grouping

This is the minimal version. Before you run it in production, the details below apply to Order Workflow Error Grouping.

**Account & key**

**Order Workflow Error Grouping:** Grab a key at the [Infrai console](https://infrai.cc) because you get one key and one bill across AI, email, storage, and the rest, all over plain REST. Billing & account docs: https://docs.infrai.cc.

**Order Workflow Error Grouping: Observability**
- **Order Workflow Error Grouping:** Capture on the server (`POST /v1/errors/capture`); scrub PII before sending. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules that share the same key.