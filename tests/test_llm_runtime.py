from __future__ import annotations

from typing import Dict

import pytest

from packages.udocket_core.llm.config import LLMProvider, LLMProviderModel
from packages.udocket_core.llm.runtime import build_provider_runtime_config
from tests._typing import MonkeyPatch


def _azure_provider(model: LLMProviderModel) -> LLMProvider:
    return LLMProvider(
        name="azure",
        display_name="Azure",
        models={model.name: model},
        env_requirements=["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY"],
        api_kind="azure_openai",
        default_endpoint="https://example-canadacentral.openai.azure.com",
        requires_api_key=True,
    )


def _credential_payload(models: Dict[str, object]) -> Dict[str, object]:
    return {
        "endpoint": "https://example-canadacentral.openai.azure.com",
        "api_key": "test-key",
        "models": [models],
    }


def test_build_provider_runtime_config_prefers_credential_model_options() -> None:
    model = LLMProviderModel(
        name="gpt-5-mini",
        label="GPT-5 Mini",
        cost_tier="standard",
        options={"temperature": 1.0},
    )
    provider = _azure_provider(model)
    credential_payload = _credential_payload(
        {
            "name": "gpt-5-mini",
            "options": {"azure_deployment": "mini-deployment"},
        }
    )

    runtime_cfg = build_provider_runtime_config(
        provider=provider,
        model_name="gpt-5-mini",
        credential_payload=credential_payload,
        options=None,
    )

    assert runtime_cfg.options["azure_deployment"] == "mini-deployment"
    # ensure other model defaults remain available
    assert runtime_cfg.options["temperature"] == 1.0


@pytest.mark.parametrize("env_value", ["", "actual-deployment"])
def test_build_provider_runtime_config_uses_model_deployment_env(monkeypatch: MonkeyPatch, env_value: str) -> None:
    monkeypatch.delenv("AZURE_OPENAI_DEPLOYMENT_TEST", raising=False)
    if env_value:
        monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT_TEST", env_value)
    model = LLMProviderModel(
        name="gpt-5",
        label="GPT-5",
        cost_tier="standard",
        deployment_env="AZURE_OPENAI_DEPLOYMENT_TEST",
    )
    provider = _azure_provider(model)

    runtime_cfg = build_provider_runtime_config(
        provider=provider,
        model_name="gpt-5",
        credential_payload={
            "endpoint": "https://example-canadacentral.openai.azure.com",
            "api_key": "test-key",
        },
        options=None,
    )

    expected = env_value if env_value else "AZURE_OPENAI_DEPLOYMENT_TEST"
    assert runtime_cfg.options["azure_deployment"] == expected