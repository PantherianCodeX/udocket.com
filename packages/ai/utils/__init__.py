from __future__ import annotations

from .types import LanguageCode


def ensure_language(value: str | LanguageCode | None) -> LanguageCode:
    """Return a supported LanguageCode, defaulting to en-CA."""

    if isinstance(value, LanguageCode):
        return value
    if value is None:
        return LanguageCode.EN_CA
    try:
        return LanguageCode(value)
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise ValueError(f"Unsupported language code: {value}") from exc


__all__ = ["ensure_language"]
