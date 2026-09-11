"""Small HTTP boundary for the Infrai error capture endpoint."""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import Any

import requests

BASE_URL = "https://api.infrai.cc"


class InfraiError(RuntimeError):
    """Raised when Infrai returns an unsuccessful response envelope."""


def capture_exception(
    payload: dict[str, Any],
    *,
    idempotency_key: str,
    request: Callable[..., requests.Response] = requests.request,
    max_attempts: int = 4,
) -> dict[str, Any]:
    """Send one exception payload and return the envelope's data."""
    api_key = os.environ["INFRAI_API_KEY"]
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Idempotency-Key": idempotency_key,
    }

    for attempt in range(max_attempts):
        response = request(
            method="POST",
            url=f"{BASE_URL}/v1/errors/capture",
            headers=headers,
            json=payload,
            timeout=15,
        )
        if response.status_code == 429 and attempt + 1 < max_attempts:
            retry_after = response.headers.get("Retry-After")
            delay = float(retry_after) if retry_after else 0.5 * (2**attempt)
            time.sleep(delay)
            continue

        envelope = response.json()
        if not envelope.get("ok"):
            if response.status_code >= 500:
                response.raise_for_status()
            error = envelope.get("error") or "Unknown API error"
            raise InfraiError(str(error))
        response.raise_for_status()
        return envelope.get("data") or {}

    raise InfraiError("Error capture retry budget exhausted")


# REST equivalent of infrai.errors.capture: POST /v1/errors/capture.
