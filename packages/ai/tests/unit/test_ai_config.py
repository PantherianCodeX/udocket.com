from __future__ import annotations

from typing import TYPE_CHECKING

from packages.ai.config import AISettings, load_settings
from packages.ai.types import LanguageCode, Region

if TYPE_CHECKING:
    import pytest


def test_ai_settings_from_env_defaults() -> None:
    settings = AISettings.from_env({})
    assert settings.providers[0].name == "azure-openai"
    assert settings.providers[0].region == Region("default-region")
    assert settings.default_language == LanguageCode.EN_CA
    assert settings.routes


def test_ai_settings_from_env_honors_env_values() -> None:
    env = {
        "AZURE_OPENAI_REGION": "ca-east",
        "UDOCKET_AI_PROVIDER": "custom-provider",
        "UDOCKET_AI_MODEL": "gpt-pro",
        "AZURE_OPENAI_ENDPOINT": "https://custom.azure.com",
        "UDOCKET_AI_KEY_ENV": "CUSTOM_KEY",
        "UDOCKET_AI_DEFAULT_LANGUAGE": "fr-CA",
    }
    settings = AISettings.from_env(env)
    provider = settings.providers[0]
    assert provider.name == "custom-provider"
    assert provider.default_model == "gpt-pro"
    assert provider.endpoint == "https://custom.azure.com"
    assert provider.api_key_env == "CUSTOM_KEY"
    assert provider.allowed_regions[0].region == Region("ca-east")
    assert settings.default_language == LanguageCode.FR_CA


def test_load_settings_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel = AISettings(providers=(), routes=(), capability_limits=())

    def _fake_from_env(env: object | None = None) -> AISettings:
        assert isinstance(env, dict)
        assert env == {"UDOCKET_AI_PROVIDER": "x"}
        return sentinel

    monkeypatch.setattr(AISettings, "from_env", staticmethod(_fake_from_env))
    result = load_settings({"UDOCKET_AI_PROVIDER": "x"})
    assert result is sentinel
