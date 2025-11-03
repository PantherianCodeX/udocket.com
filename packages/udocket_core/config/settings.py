from __future__ import annotations

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class CoreSettings(BaseSettings):
    """Environment configuration for udocket_core package."""

    model_config = SettingsConfigDict(env_prefix="UDOCKET_CORE_", extra="ignore")

    data_root: Path | None = Field(default=None, alias="DATA_ROOT")
    llm_providers_path: Path | None = Field(default=None, alias="LLM_PROVIDERS_PATH")
    llm_assignments_path: Path | None = Field(default=None, alias="LLM_ASSIGNMENTS_PATH")
    analyze_defaults_path: Path | None = Field(default=None, alias="ANALYZE_DEFAULTS_PATH")


core_settings = CoreSettings()

__all__ = ["CoreSettings", "core_settings"]
