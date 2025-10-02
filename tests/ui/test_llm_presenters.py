from __future__ import annotations

import pytest

from packages.udocket_core.llm.config import (
    LLMProvider,
    LLMProviderModel,
    LLMSettings,
    LLMStageAssignment,
)

from apps.platform.ui.views.presenters import analysis_llm
from apps.platform.operations.llm import build_provider_registry


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
        "analyze.context_builder": LLMStageAssignment(
            stage_key="analyze.context_builder",
            providers=["azure"],
            model="gpt-4o-mini",
            target="summary",
            label="Context Builder",
            description="Collects intake context",
        ),
        "analyze.qa_and_finalize": LLMStageAssignment(
            stage_key="analyze.qa_and_finalize",
            providers=["azure"],
            model="gpt-4o-mini",
            target="summary",
            label="QA",
            description="QA stage",
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


def test_build_provider_registry_marks_supported_and_unsupported(llm_settings):
    registry = build_provider_registry(
        organization_id=None,
        llm_settings=llm_settings,
        provider_catalog={},
        provider_credentials={},
        supported_providers=["azure"],
    )

    assert set(registry.keys()) == {"azure", "openai"}

    azure_entry = registry["azure"]
    assert azure_entry["supported"] is True
    assert azure_entry["status"] == "not_configured"
    assert azure_entry["enabled"] is False

    openai_entry = registry["openai"]
    assert openai_entry["available"] is False
    assert openai_entry["unavailable_reason"] == "Not supported yet"


def test_build_provider_registry_includes_credential_only_provider(llm_settings):
    credentials = {
        "custom": {
            "display_name": "Custom Provider",
            "endpoint": "https://api.custom.example",
            "models": [
                {
                    "name": "custom-model",
                    "label": "Custom Model",
                    "cost_tier": "standard",
                }
            ],
        }
    }

    registry = build_provider_registry(
        organization_id=None,
        llm_settings=llm_settings,
        provider_catalog={},
        provider_credentials=credentials,
        supported_providers=["azure"],
    )

    assert set(registry.keys()) == {"azure", "openai", "custom"}
    custom_entry = registry["custom"]
    assert custom_entry["available"] is True
    assert custom_entry["configured"] is False
    assert custom_entry["label"] == "Custom Provider"
    assert custom_entry["models"][0]["value"] == "custom-model"


def test_build_llm_stage_configs_uses_defaults_and_overrides(llm_settings):
    provider_registry = build_provider_registry(
        organization_id=None,
        llm_settings=llm_settings,
        provider_catalog={},
        provider_credentials={},
        supported_providers=["azure", "openai"],
    )

    # No overrides: should use assignment defaults
    configs = analysis_llm.build_llm_stage_configs(
        target="summary",
        llm_settings=llm_settings,
        stage_map={},
        provider_registry=provider_registry,
    )

    context_entry = next(cfg for cfg in configs if cfg["key"] == "analyze.context_builder")
    assert context_entry["selected_provider"] == "azure"
    assert context_entry["profile"] is not None
    # Providers should include every cache entry so the UI can surface unsupported options.
    assert [entry["value"] for entry in context_entry["providers"]] == ["azure", "openai"]
    assert context_entry["selected_max_tokens"] is None
    assert context_entry["selected_options"] == {}

    # Apply overrides and ensure they take precedence.
    stage_map = {
        "analyze.context_builder": {
            "provider": "azure",
            "model": "gpt-4o",
            "max_tokens": 6400,
            "options": {"temperature": 0.4},
        }
    }

    configs_with_override = analysis_llm.build_llm_stage_configs(
        target="summary",
        llm_settings=llm_settings,
        stage_map=stage_map,
        provider_registry=provider_registry,
    )

    override_entry = next(cfg for cfg in configs_with_override if cfg["key"] == "analyze.context_builder")
    assert override_entry["selected_provider"] == "azure"
    assert override_entry["selected_model"] == "gpt-4o"
    assert override_entry["selected_max_tokens"] == 6400
    assert override_entry["selected_options"].get("temperature") == 0.4
