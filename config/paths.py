from __future__ import annotations

import contextlib
import os
from pathlib import Path
from typing import Protocol, cast, runtime_checkable

from packages.common.repo import REPO_ROOT

DEFAULT_APP_ROOT = Path(os.environ.get("APP_ROOT", str(REPO_ROOT))).expanduser()


@runtime_checkable
class SettingsProtocol(Protocol):
    APP_ROOT: Path | None
    STORAGE_ROOT: Path | None


def _get_settings(config: SettingsProtocol | None = None) -> SettingsProtocol:
    if config is not None:
        return config
    from config.settings import settings  # noqa: PLC0415  # avoid import cycle at import time

    return settings


def _django_storage_root() -> Path | None:
    try:
        from django.conf import settings as django_settings  # noqa: PLC0415  # optional dependency
    except ModuleNotFoundError:
        return None
    except RuntimeError:
        return None

    storage_root = cast("str | Path | None", getattr(django_settings, "STORAGE_ROOT", None))
    if not storage_root:
        return None
    try:
        return Path(storage_root).expanduser()
    except (TypeError, ValueError, OSError):
        return None


def resolve_repo_root() -> Path:
    """Return the repository root inferred from this module location."""

    return REPO_ROOT


def resolve_app_root(config: SettingsProtocol | None = None) -> Path:
    cfg = _get_settings(config)
    value = cfg.APP_ROOT
    if value:
        candidate = Path(value).expanduser()
        if candidate.exists():
            return candidate
    return DEFAULT_APP_ROOT


def resolve_storage_root(config: SettingsProtocol | None = None) -> Path:
    cfg = _get_settings(config)
    if config is None:
        django_storage = _django_storage_root()
        if django_storage is not None:
            return django_storage
    value = cfg.STORAGE_ROOT
    if value:
        return Path(value).expanduser()
    return resolve_app_root(cfg) / "storage"


def ensure_storage_root(config: SettingsProtocol | None = None) -> Path:
    root = resolve_storage_root(config)
    with contextlib.suppress(OSError, PermissionError):
        root.mkdir(parents=True, exist_ok=True)
    return root


def resolve_media_root(config: SettingsProtocol | None = None) -> Path:
    return resolve_storage_root(config) / "media"


def resolve_config_dir(config: SettingsProtocol | None = None) -> Path:
    return resolve_app_root(config) / "config"


__all__ = [
    "REPO_ROOT",
    "ensure_storage_root",
    "resolve_app_root",
    "resolve_config_dir",
    "resolve_media_root",
    "resolve_repo_root",
    "resolve_storage_root",
]
