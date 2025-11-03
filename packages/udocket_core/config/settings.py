from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from packages.udocket_common.env import load_env_defaults

_PACKAGE_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _PACKAGE_ROOT.parents[1]

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

    data_root: Path | None = Field(default=None, alias="DATA_ROOT")
    llm_providers_path: Path | None = Field(default=None, alias="LLM_PROVIDERS_PATH")
    llm_assignments_path: Path | None = Field(default=None, alias="LLM_ASSIGNMENTS_PATH")
    analyze_defaults_path: Path | None = Field(default=None, alias="ANALYZE_DEFAULTS_PATH")


core_settings = CoreSettings()

__all__ = ["CoreSettings", "core_settings"]
