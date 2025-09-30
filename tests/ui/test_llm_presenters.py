from __future__ import annotations

import pytest

from packages.udocket_core.llm.config import (
    LLMProvider,
    LLMProviderModel,
    LLMSettings,
    LLMStageAssignment,
)

from apps.platform.ui.views.presenters import cases as presenters
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
        "summarize.context_builder": LLMStageAssignment(
            stage_key="summarize.context_builder",
            providers=["azure"],
            model="gpt-4o-mini",
        ),
        "summarize.qa_and_finalize": LLMStageAssignment(
            stage_key="summarize.qa_and_finalize",
            providers=["azure"],
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
    assert azure_entry["available"] is True
    assert azure_entry["unavailable_reason"] == ""

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
    assert custom_entry["configured"] is True
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
    stage_defs = [
        {"key": "summarize.context_builder", "label": "Context", "description": "Context stage"},
        {"key": "summarize.qa_and_finalize", "label": "QA", "description": "QA stage"},
    ]

    configs = presenters._build_llm_stage_configs(
        stage_defs=stage_defs,
        llm_settings=llm_settings,
        stage_map={},
        provider_registry=provider_registry,
    )

    assert len(configs) == 2
    first = configs[0]
    assert first["selected_provider"] == "azure"
    assert "allow_offline_default" not in first
    assert first["description"] == "Context stage"
    # Providers should include every cache entry so the UI can surface unsupported options.
    assert [entry["value"] for entry in first["providers"]] == ["azure", "openai"]

    # Apply overrides and ensure they take precedence.
    stage_map = {
        "summarize.context_builder": {
            "provider": "azure",
            "model": "gpt-4o",
        }
    }

    configs_with_override = presenters._build_llm_stage_configs(
        stage_defs=stage_defs,
        llm_settings=llm_settings,
        stage_map=stage_map,
        provider_registry=provider_registry,
    )

    override_entry = configs_with_override[0]
    assert override_entry["selected_provider"] == "azure"
    assert override_entry["selected_model"] == "gpt-4o"
