from __future__ import annotations

from typing import Any, Dict, Mapping

JobTelemetryPayload = Dict[str, Any]
JobRow = Dict[str, Any]


def _as_dict(payload: Any) -> Dict[str, Any]:
    if isinstance(payload, Mapping):
        result: Dict[str, Any] = {str(key): value for key, value in payload.items()}
        return result
    return {}
