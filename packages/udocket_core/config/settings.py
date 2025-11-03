from __future__ import annotations

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

from packages.udocket_common.env import load_env_defaults

_PACKAGE_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _PACKAGE_ROOT.parents[1]

def _ensure_env_path(key: str, default: Path) -> None:
    current = os.environ.get(key)
    if not current:
        os.environ[key] = str(default)
        return
    try:
        candidate = Path(current)
    except Exception:
        os.environ[key] = str(default)
        return
    if not candidate.exists():
        os.environ[key] = str(default)


_ensure_env_path("UDOCKET_CORE_DATA_ROOT", _PACKAGE_ROOT / "reference" / "data")
_ensure_env_path("UDOCKET_CORE_LLM_PROVIDERS_PATH", _REPO_ROOT / "config" / "llm_providers.json")
_ensure_env_path("UDOCKET_CORE_LLM_ASSIGNMENTS_PATH", _REPO_ROOT / "config" / "llm_assignments.json")
_ensure_env_path("UDOCKET_CORE_ANALYZE_DEFAULTS_PATH", _REPO_ROOT / "config" / "analyze_defaults.json")

load_env_defaults(
    env_var="UDOCKET_CORE_ENV_FILE",
    default_paths=(
        _PACKAGE_ROOT / ".env",
        _REPO_ROOT / ".env",
    ),
)


class CoreSettings(BaseSettings):
    """Environment configuration for udocket_core package."""

    model_config = SettingsConfigDict(env_prefix="UDOCKET_CORE_", extra="ignore")

    data_root: Path | None = None
    llm_providers_path: Path | None = None
    llm_assignments_path: Path | None = None
    analyze_defaults_path: Path | None = None


core_settings = CoreSettings()

__all__ = ["CoreSettings", "core_settings"]
