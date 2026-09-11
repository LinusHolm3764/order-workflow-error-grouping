"""Capture failures from the customer order lifecycle with stable grouping."""

from __future__ import annotations

import argparse
import json
import traceback
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from infrai_errors import capture_exception


class OrderStage(str, Enum):
    CHECKOUT = "checkout"
    FULFILLMENT = "fulfillment"
    RECEIPT = "receipt"
    CUSTOMER_UPDATE = "customer_update"


@dataclass(frozen=True)
class OrderFailure:
    """Typed input produced by an e-commerce workflow boundary."""

    event_id: str
    order_id: str
    stage: OrderStage
    operation: str
    exception_type: str
    message: str


def grouping_fingerprint(failure: OrderFailure) -> list[str]:
    """Group by workflow location and exception class, never by order ID."""
    return [failure.stage.value, failure.operation, failure.exception_type]


def capture_order_failure(failure: OrderFailure) -> dict[str, Any]:
    """Turn a domain failure into the exception payload used for grouping."""
    exception_text = (
        f"{failure.exception_type}: {failure.message}\n"
        f"order stage: {failure.stage.value}; operation: {failure.operation}"
    )
    payload = {
        "title": f"{failure.stage.value}: {failure.operation} failed",
        "message": failure.message,
        "level": "error",
        "fingerprint": grouping_fingerprint(failure),
        "exception": exception_text,
        "context": {
            "order_id": failure.order_id,
            "stage": failure.stage.value,
            "operation": failure.operation,
            "event_id": failure.event_id,
        },
    }
    return capture_exception(payload, idempotency_key=failure.event_id)


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture one failed order operation")
    parser.add_argument("--event-id", required=True)
    parser.add_argument("--order-id", required=True)
    parser.add_argument("--stage", required=True, choices=[stage.value for stage in OrderStage])
    parser.add_argument("--operation", required=True)
    parser.add_argument("--exception-type", required=True)
    parser.add_argument("--message", required=True)
    args = parser.parse_args()
    failure = OrderFailure(
        event_id=args.event_id,
        order_id=args.order_id,
        stage=OrderStage(args.stage),
        operation=args.operation,
        exception_type=args.exception_type,
        message=args.message,
    )
    result = capture_order_failure(failure)
    print(json.dumps({"captured": asdict(failure), "result": result}, indent=2))


if __name__ == "__main__":
    main()
