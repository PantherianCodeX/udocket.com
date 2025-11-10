from __future__ import annotations

from packages.ai.types import LanguageCode

_ERROR_UNSUPPORTED_LANGUAGE = "Unsupported language code: {value}"


def ensure_language(value: str | LanguageCode | None) -> LanguageCode:
    """Return a supported LanguageCode, defaulting to en-CA."""
    if isinstance(value, LanguageCode):
        return value
    if value is None:
        return LanguageCode.EN_CA
    try:
        return LanguageCode(value)
    except ValueError as exc:  # pragma: no cover - defensive guard
        message = _ERROR_UNSUPPORTED_LANGUAGE.format(value=value)
        raise ValueError(message) from exc


__all__ = ["ensure_language"]
