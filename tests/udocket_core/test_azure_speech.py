from __future__ import annotations

import pytest

from packages.udocket_core.agents.common.azure_speech import _iso8601_to_seconds


def test_iso8601_parses_batch_fractional_seconds() -> None:
    assert _iso8601_to_seconds("PT0.9S") == pytest.approx(0.9)


def test_iso8601_parses_minutes_and_seconds() -> None:
    assert _iso8601_to_seconds("PT1M2.5S") == pytest.approx(62.5)


def test_iso8601_parses_days_and_hours() -> None:
    assert _iso8601_to_seconds("P1DT2H") == pytest.approx(93600.0)


def test_iso8601_keeps_colon_format_support() -> None:
    assert _iso8601_to_seconds("00:01:02.500") == pytest.approx(62.5)


def test_iso8601_rejects_invalid_format() -> None:
    with pytest.raises(ValueError):
        _iso8601_to_seconds("not-a-duration")
