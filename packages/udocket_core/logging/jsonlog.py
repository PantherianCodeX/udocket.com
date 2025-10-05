from __future__ import annotations

# pyright: strict

from datetime import datetime, timezone
import json
import sys

from packages.udocket_core.json_utils import JSONObject, JSONValue, coerce_json_value


def log(event: str, **kwargs: JSONValue) -> None:
    """Emit a structured JSON log line to stdout."""

    payload: JSONObject = {
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "event": event,
    }
    for key, value in kwargs.items():
        payload[key] = coerce_json_value(value)
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


__all__ = ["log"]
