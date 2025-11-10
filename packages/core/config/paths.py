from __future__ import annotations

from pathlib import Path

from config.paths import resolve_config_dir

from .settings import CoreSettings, core_settings

_PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def _settings(cfg: CoreSettings | None = None) -> CoreSettings:
    return cfg or core_settings


def resolve_package_root() -> Path:
    return _PACKAGE_ROOT


def resolve_data_root(cfg: CoreSettings | None = None) -> Path:
    settings = _settings(cfg)
    value = settings.data_root
    if value:
        return Path(value).expanduser()
    return resolve_package_root() / "reference" / "data"


def resolve_llm_providers_path(cfg: CoreSettings | None = None) -> Path:
    settings = _settings(cfg)
    value = settings.llm_providers_path
    if value:
        return Path(value).expanduser()
    return resolve_config_dir() / "ai" / "llm_providers.json"


def resolve_llm_assignments_path(cfg: CoreSettings | None = None) -> Path:
    settings = _settings(cfg)
    value = settings.llm_assignments_path
    if value:
        return Path(value).expanduser()
    return resolve_config_dir() / "ai" / "llm_assignments.json"


def resolve_analyze_defaults_path(cfg: CoreSettings | None = None) -> Path:
    settings = _settings(cfg)
    value = settings.analyze_defaults_path
    if value:
        return Path(value).expanduser()
    return resolve_config_dir() / "services" / "analyze" / "defaults.json"


# Convenience constants so callers can avoid repeated resolution
DATA_ROOT: Path = resolve_data_root()
LLM_PROVIDERS_PATH: Path = resolve_llm_providers_path()
LLM_ASSIGNMENTS_PATH: Path = resolve_llm_assignments_path()
ANALYZE_DEFAULTS_PATH: Path = resolve_analyze_defaults_path()


__all__ = [
    "resolve_package_root",
    "resolve_data_root",
    "resolve_llm_providers_path",
    "resolve_llm_assignments_path",
    "resolve_analyze_defaults_path",
    "DATA_ROOT",
    "LLM_PROVIDERS_PATH",
    "LLM_ASSIGNMENTS_PATH",
    "ANALYZE_DEFAULTS_PATH",
]
