# pyright: strict

"""UTC time helpers shared across packages."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal, overload

Timespec = Literal[
    "auto",
    "hours",
    "minutes",
    "seconds",
    "milliseconds",
    "microseconds",
]


def utc_now() -> datetime:
    """Return the current UTC datetime as a timezone-aware value."""

    return datetime.now(UTC)


@overload
def format_utc(
    dt: None = ..., *, timespec: Timespec | None = "seconds", z_suffix: bool = True
) -> str: ...


@overload
def format_utc(
    dt: datetime, *, timespec: Timespec | None = "seconds", z_suffix: bool = True
) -> str: ...


def format_utc(
    dt: datetime | None = None,
    *,
    timespec: Timespec | None = "seconds",
    z_suffix: bool = True,
) -> str:
    """Return an ISO-8601 timestamp string for the provided datetime in UTC.

    When *dt* is ``None`` the current UTC time is used. ``timespec`` mirrors the
    ``datetime.isoformat`` argument and defaults to seconds to keep audit logs
    stable. When ``z_suffix`` is true (default), the ``+00:00`` suffix is
    replaced with the canonical ``Z`` UTC marker for readability.
    """

    moment = dt if dt is not None else utc_now()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    else:
        moment = moment.astimezone(UTC)
    iso = moment.isoformat(timespec=timespec) if timespec else moment.isoformat()
    if z_suffix:
        return iso.replace("+00:00", "Z")
    return iso


__all__ = ["Timespec", "utc_now", "format_utc"]
