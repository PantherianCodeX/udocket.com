# Copyright (c) 2025 uDocket Inc. All rights reserved.

from __future__ import annotations

from packages.ai.config.translator import ai_settings_from_llm
from packages.ai.types import AgentTask
from packages.core.llm.config import LLMProvider, LLMProviderModel, LLMSettings, LLMStageAssignment


def _provider(models: dict[str, LLMProviderModel] | None = None) -> LLMProvider:
    if models is None:
        models = {
            "gpt-lite": LLMProviderModel(
                name="gpt-lite",
                label="GPT Lite",
                cost_tier="standard",
                default_enabled=True,
            ),
        }
    return LLMProvider(
        name="azure",
        display_name="Azure",
        models=models,
        default_endpoint="https://example.region.azure.com",
        env_requirements=["AZURE_KEY"],
    )


def _assignment(
    *,
    stage_key: str = "compose.timeline",
    providers: list[str] | None = None,
    model: str = "gpt-lite",
    target: str = "compose",
) -> LLMStageAssignment:
    return LLMStageAssignment(
        stage_key=stage_key,
        providers=providers if providers is not None else ["azure"],
        model=model,
        target=target,
    )


def _sample_llm_settings() -> LLMSettings:
    provider = _provider()
    assignment = _assignment()
    return LLMSettings(
        providers={provider.name: provider},
        assignments={assignment.stage_key: assignment},
    )


def test_ai_settings_from_llm_translates_provider() -> None:
    ai_settings = ai_settings_from_llm(_sample_llm_settings())
    assert len(ai_settings.providers) == 1
    account = ai_settings.providers[0]
    assert account.name == "azure"
    assert account.endpoint == "https://example.region.azure.com"
    assert account.allowed_regions


def test_ai_settings_from_llm_routes() -> None:
    ai_settings = ai_settings_from_llm(_sample_llm_settings())
    assert len(ai_settings.routes) == 1
    route = ai_settings.routes[0]
    assert route.provider == "azure"
    assert route.model == "gpt-lite"
    assert route.task is AgentTask.GENERATE


def test_ai_settings_from_llm_skips_provider_without_models() -> None:
    provider = _provider(models={})
    settings = LLMSettings(
        providers={provider.name: provider},
        assignments={},
    )
    ai_settings = ai_settings_from_llm(settings)
    assert ai_settings.providers == ()


def test_ai_settings_from_llm_skips_unknown_stage() -> None:
    provider = _provider()
    assignment = _assignment(stage_key="unknown.stage", target="unknown")
    settings = LLMSettings(
        providers={provider.name: provider},
        assignments={assignment.stage_key: assignment},
    )
    ai_settings = ai_settings_from_llm(settings)
    assert ai_settings.routes == ()


def test_ai_settings_from_llm_uses_provider_list_for_model_name() -> None:
    provider = _provider()
    assignment = _assignment(model="", providers=["azure"])
    settings = LLMSettings(
        providers={provider.name: provider},
        assignments={assignment.stage_key: assignment},
    )
    ai_settings = ai_settings_from_llm(settings)
    assert ai_settings.routes[0].model == "azure"


def test_ai_settings_from_llm_drops_assignments_without_models() -> None:
    provider = _provider()
    assignment = _assignment(model="", providers=[])
    settings = LLMSettings(
        providers={provider.name: provider},
        assignments={assignment.stage_key: assignment},
    )
    ai_settings = ai_settings_from_llm(settings)
    assert ai_settings.routes == ()


_STAGE_CASES: tuple[tuple[str, AgentTask], ...] = (
    ("compose.timeline", AgentTask.GENERATE),
    ("case.timeline", AgentTask.EXTRACT),
    ("case.entity", AgentTask.EXTRACT),
    ("case.summary", AgentTask.GENERATE),
    ("context.helper", AgentTask.CHAT),
    ("case.qa", AgentTask.EVAL),
    ("case.atoms", AgentTask.ATOMS),
)


def test_ai_settings_from_llm_maps_stage_to_task() -> None:
    provider = _provider()
    for stage_key, expected_task in _STAGE_CASES:
        assignment = _assignment(stage_key=stage_key, target=stage_key.split(".", 1)[0])
        settings = LLMSettings(
            providers={provider.name: provider},
            assignments={assignment.stage_key: assignment},
        )
        ai_settings = ai_settings_from_llm(settings)
        assert ai_settings.routes[0].task == expected_task
