from __future__ import annotations

import pytest

from packages.udocket_core.llm.config import (
    LLMProvider,
    LLMProviderModel,
    LLMSettings,
    LLMStageAssignment,
)

from apps.platform.ui.views.presenters import cases as presenters


def _build_settings() -> LLMSettings:
    providers = {
        "azure": LLMProvider(
            name="azure",
            display_name="Azure",
            env_requirements=["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY"],
            models={
                "gpt-4o-mini": LLMProviderModel(
                    name="gpt-4o-mini",
                    label="GPT-4o Mini",
                    cost_tier="standard",
                    max_output_tokens=4000,
                ),
                "gpt-4o": LLMProviderModel(
                    name="gpt-4o",
                    label="GPT-4o",
                    cost_tier="premium",
                    max_output_tokens=8000,
                ),
            },
        ),
        "local": LLMProvider(
            name="local",
            display_name="Local",
            env_requirements=[],
            models={
                "offline_v1": LLMProviderModel(
                    name="offline_v1",
                    label="Offline",
                    cost_tier="free",
                    max_output_tokens=2000,
                )
            },
        ),
        "openai": LLMProvider(
            name="openai",
            display_name="OpenAI",
            env_requirements=["OPENAI_API_KEY"],
            models={
                "gpt-4o-mini": LLMProviderModel(
                    name="gpt-4o-mini",
                    label="GPT-4o Mini",
                    cost_tier="standard",
                    max_output_tokens=4000,
                )
            },
        ),
    }

    assignments = {
        "summarize.context_builder": LLMStageAssignment(
            stage_key="summarize.context_builder",
            providers=["azure", "local"],
            model="gpt-4o-mini",
        ),
        "summarize.qa_and_finalize": LLMStageAssignment(
            stage_key="summarize.qa_and_finalize",
            providers=["azure", "local"],
            model="gpt-4o-mini",
        ),
    }

    return LLMSettings(providers=providers, assignments=assignments)


@pytest.fixture()
def llm_settings(monkeypatch) -> LLMSettings:
    # Ensure supported providers report as available for the cache when env vars exist.
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.canadacentral.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    settings = _build_settings()
    # Clear any unrelated env so unsupported providers stay unavailable
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    return settings


def test_build_provider_cache_marks_supported_and_unsupported(llm_settings):
    cache = presenters._build_provider_cache(
        llm_settings=llm_settings,
        provider_catalog={},
        provider_credentials={},
    )

    assert set(cache.keys()) == {"azure", "local", "openai"}

    azure_entry = cache["azure"]
    assert azure_entry["available"] is True
    assert azure_entry["unavailable_reason"] == ""

    local_entry = cache["local"]
    assert local_entry["available"] is True

    openai_entry = cache["openai"]
    assert openai_entry["available"] is False
    assert openai_entry["unavailable_reason"] == "Not supported yet"


def test_build_llm_stage_configs_uses_defaults_and_overrides(llm_settings):
    provider_cache = presenters._build_provider_cache(
        llm_settings=llm_settings,
        provider_catalog={},
        provider_credentials={},
    )

    # No overrides: should use assignment defaults and enable local fallback
    stage_defs = [
        {"key": "summarize.context_builder", "label": "Context", "description": "Context stage"},
        {"key": "summarize.qa_and_finalize", "label": "QA", "description": "QA stage"},
    ]

    configs = presenters._build_llm_stage_configs(
        stage_defs=stage_defs,
        llm_settings=llm_settings,
        overrides={},
        provider_cache=provider_cache,
    )

    assert len(configs) == 2
    first = configs[0]
    assert first["selected_provider"] == "azure"
    assert first["selected_fallbacks"] == ["local"]
    assert first["allow_offline_default"] is True
    assert first["description"] == "Context stage"
    # Providers should include every cache entry so the UI can surface unsupported options.
    assert [entry["value"] for entry in first["providers"]] == ["azure", "local", "openai"]

    # Apply overrides and ensure they take precedence.
    overrides = {
        "summarize.context_builder": {
            "provider": "local",
            "fallbacks": ["azure"],
            "model": "offline_v1",
            "allow_offline_fallback": True,
        }
    }

    configs_with_override = presenters._build_llm_stage_configs(
        stage_defs=stage_defs,
        llm_settings=llm_settings,
        overrides=overrides,
        provider_cache=provider_cache,
    )

    override_entry = configs_with_override[0]
    assert override_entry["selected_provider"] == "local"
    assert override_entry["selected_fallbacks"] == ["azure"]
    assert override_entry["selected_model"] == "offline_v1"
    assert override_entry["allow_offline_default"] is True
