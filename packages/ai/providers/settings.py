from __future__ import annotations

# pyright: strict

"""Provider configuration dataclasses derived from AI settings."""

from dataclasses import dataclass

from ..types import AllowedRegion, Region
from ..types.identifiers import ProviderName


@dataclass(slots=True, frozen=True)
class ProviderConfig:
    """Base configuration extracted from AI settings."""

    name: ProviderName
    region: Region
    allowed_regions: tuple[AllowedRegion, ...]


@dataclass(slots=True, frozen=True)
class AzureOpenAIConfig(ProviderConfig):
    """Azure OpenAI-specific configuration."""

    endpoint: str
    deployment: str
    api_key_env: str


__all__ = ["ProviderConfig", "AzureOpenAIConfig"]
