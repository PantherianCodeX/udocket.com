from __future__ import annotations

from typing import Any, Dict, Mapping, cast

JobTelemetryPayload = Dict[str, Any]
JobRow = Dict[str, Any]


def _as_dict(payload: Any) -> Dict[str, Any]:
    if isinstance(payload, Mapping):
        mapping = cast(Mapping[Any, Any], payload)
        result: Dict[str, Any] = {}
        for key, value in mapping.items():
            result[str(key)] = value
        return result
    return {}
