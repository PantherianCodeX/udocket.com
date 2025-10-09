from __future__ import annotations

# pyright: strict

from dataclasses import dataclass, field
from typing import Mapping

LogDict = dict[str, object]


def _empty_log_dict() -> LogDict:
    return {}


def _set_if_present(payload: LogDict, key: str, value: object | None) -> None:
    if value is not None:
        payload[key] = value


def build_extra(
    *,
    event: str | None = None,
    component: str | None = None,
    case_id: str | None = None,
    job_id: str | None = None,
    artifact_id: str | int | None = None,
    organization_id: str | None = None,
    task_id: str | None = None,
    **fields: object,
) -> LogDict:
    """Construct a logging ``extra`` dictionary with standard fields."""

    payload: LogDict = {}
    _set_if_present(payload, "event", event)
    _set_if_present(payload, "component", component)
    _set_if_present(payload, "case_id", case_id)
    _set_if_present(payload, "job_id", job_id)
    _set_if_present(payload, "artifact_id", artifact_id)
    _set_if_present(payload, "organization_id", organization_id)
    _set_if_present(payload, "task_id", task_id)
    for key, value in fields.items():
        _set_if_present(payload, key, value)
    return payload


def extend_extra(base: Mapping[str, object] | None = None, **fields: object) -> LogDict:
    """Extend an existing ``extra`` payload with additional fields."""

    payload: LogDict = dict(base) if base is not None else {}
    for key, value in fields.items():
        if value is None:
            payload.pop(key, None)
        else:
            payload[key] = value
    return payload


@dataclass(frozen=True)
class LogContext:
    """Reusable logging context that preserves structured ``extra`` fields."""

    values: LogDict = field(default_factory=_empty_log_dict)

    def __post_init__(self) -> None:
        normalized: LogDict = {}
        for key, value in self.values.items():
            if value is not None:
                normalized[key] = value
        object.__setattr__(self, "values", normalized)

    @classmethod
    def from_defaults(
        cls,
        *,
        component: str | None = None,
        case_id: str | None = None,
        job_id: str | None = None,
        artifact_id: str | int | None = None,
        organization_id: str | None = None,
        task_id: str | None = None,
        event: str | None = None,
        **fields: object,
    ) -> "LogContext":
        defaults = build_extra(
            component=component,
            case_id=case_id,
            job_id=job_id,
            artifact_id=artifact_id,
            organization_id=organization_id,
            task_id=task_id,
            event=event,
            **fields,
        )
        return cls(values=defaults)

    def bind(self, **fields: object) -> "LogContext":
        """Return a new ``LogContext`` with merged values."""

        merged = extend_extra(self.values, **fields)
        return LogContext(values=merged)

    def extra(self, **fields: object) -> LogDict:
        """Generate an ``extra`` payload for the active context."""

        return extend_extra(self.values, **fields)


__all__ = ["LogContext", "build_extra", "extend_extra"]
