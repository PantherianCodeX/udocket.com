from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime

from packages.common.json_utils import JSONObject, JSONValue, coerce_json_value


def _normalize_value(value: object) -> JSONValue | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return coerce_json_value(value)


@dataclass
class CaseIntakeBuilder:
    """Mutable helper for collecting intake payload information."""

    _payload: dict[str, JSONValue] = field(default_factory=dict)

    def assign(self, key: str, value: object) -> None:
        normalized = _normalize_value(value)
        if normalized is None:
            return
        self._payload[key] = normalized

    def ensure(self, key: str, value: object) -> None:
        if key in self._payload:
            return
        self.assign(key, value)

    def extend(self, items: Iterable[tuple[str, object]]) -> None:
        for key, value in items:
            self.assign(key, value)

    def build(self) -> CaseIntakePayload:
        return CaseIntakePayload(dict(self._payload))


@dataclass(frozen=True)
class CaseIntakePayload:
    """Normalized intake payload."""

    data: JSONObject

    def to_json(self) -> JSONObject:
        return dict(self.data)
