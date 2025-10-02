from __future__ import annotations

from datetime import datetime, timezone
import json
import sys
from typing import Any, Dict


def log(event: str, **kwargs: Any) -> None:
    """Emit a structured JSON log line to stdout."""

    payload: Dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "event": event,
    }
    payload.update(kwargs)
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


__all__ = ["log"]
