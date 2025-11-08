from __future__ import annotations

from collections.abc import Mapping

# pyright: strict
# pyright: reportUnknownArgumentType=false, reportUnknownVariableType=false
from typing import Any

JobTelemetryPayload = dict[str, Any]
JobRow = dict[str, Any]


def as_dict(payload: Any) -> dict[str, Any]:
    if isinstance(payload, Mapping):
        result: dict[str, Any] = {str(key): value for key, value in payload.items()}
        return result
    return {}
