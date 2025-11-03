from __future__ import annotations

# pyright: strict

"""Helpers for loading `.env` style configuration files."""

import os
from pathlib import Path
from typing import Iterable


_LOADED_KEYS: set[tuple[str, tuple[Path, ...]]] = set()


def _parse_env_file(path: Path) -> dict[str, str]:
    """Return key/value pairs parsed from a dotenv-style file."""

    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    overrides: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep:
            continue
        key_name = key.strip()
        if not key_name:
            continue
        overrides[key_name] = value.strip()
    return overrides


def load_env_defaults(*, env_var: str, default_paths: Iterable[Path]) -> None:
    """Set default environment values from the first available dotenv file.

    The loader checks the override ``env_var`` first (allowing callers to point at
    custom files) before falling back to the provided ``default_paths`` sequence.
    Parsed variables are only applied when they are not already present in the
    current process environment.
    """

    override_path = os.getenv(env_var)
    candidates: list[Path] = []
    if override_path:
        candidates.append(Path(override_path).expanduser())
    for default in default_paths:
        candidates.append(default.expanduser())

    normalized: tuple[Path, ...] = tuple(path.resolve() for path in candidates)
    cache_key = (env_var, normalized)
    if cache_key in _LOADED_KEYS:
        return
    _LOADED_KEYS.add(cache_key)

    for env_path in normalized:
        if not env_path.is_file():
            continue
        for key, value in _parse_env_file(env_path).items():
            os.environ.setdefault(key, value)


def reset_env_loader_state() -> None:
    """Clear cached loader state (useful for tests)."""

    _LOADED_KEYS.clear()


__all__ = ["load_env_defaults", "reset_env_loader_state"]
