from __future__ import annotations

from datetime import datetime, timedelta, timezone

from packages.common.time import format_utc, utc_now


def test_utc_now_returns_timezone_aware_datetime() -> None:
    value = utc_now()
    assert value.tzinfo is not None
    assert value.tzinfo.utcoffset(value) == timedelta(0)


def test_format_utc_defaults_to_seconds_precision() -> None:
    ts = format_utc()
    assert ts.endswith("Z")
    assert ts.count(".") == 0


def test_format_utc_accepts_naive_datetime_and_normalizes() -> None:
    naive = datetime(2024, 1, 2, 3, 4, 5)
    ts = format_utc(naive, timespec="seconds")
    assert ts == "2024-01-02T03:04:05Z"


def test_format_utc_converts_from_other_timezones() -> None:
    aware = datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    ts = format_utc(aware, timespec="seconds")
    assert ts == "2024-01-01T21:34:05Z"


def test_format_utc_can_preserve_offset_suffix() -> None:
    naive = datetime(2024, 1, 2, 3, 4, 5)
    ts = format_utc(naive, timespec="minutes", z_suffix=False)
    assert ts == "2024-01-02T03:04+00:00"
