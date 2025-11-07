from __future__ import annotations

import json
from pathlib import Path

import pytest

from packages.core.llm.config import (
    LLMConfigError,
    LLMProvider,
    LLMSettings,
    LLMStageAssignment,
    load_llm_settings,
    validate_llm_settings,
)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_load_llm_settings_missing_provider_file(tmp_path: Path) -> None:
    assignments_path = tmp_path / "assignments.json"
    _write_json(
        assignments_path,
        {
            "stages": {
                "demo.stage": {
                    "providers": ["demo"],
                    "model": "demo-model",
                }
            }
        },
    )

    missing_providers_path = tmp_path / "providers.json"

    with pytest.raises(LLMConfigError, match="not found"):
        load_llm_settings(providers_path=missing_providers_path, assignments_path=assignments_path)


def test_load_llm_settings_requires_providers_and_stages(tmp_path: Path) -> None:
    providers_path = tmp_path / "providers.json"
    _write_json(providers_path, {"providers": {}})

    assignments_path = tmp_path / "assignments.json"
    _write_json(assignments_path, {"stages": {}})

    with pytest.raises(LLMConfigError, match="No providers"):
        load_llm_settings(providers_path=providers_path, assignments_path=assignments_path)

    # Populate providers but leave stages empty to assert the second guard.
    _write_json(
        providers_path,
        {
            "providers": {
                "demo": {
                    "display_name": "Demo",
                    "models": {
                        "demo-model": {
                            "label": "Demo",
                            "cost_tier": "standard",
                        }
                    },
                }
            }
        },
    )

    with pytest.raises(LLMConfigError, match="No stage assignments"):
        load_llm_settings(providers_path=providers_path, assignments_path=assignments_path)


def _write_minimal_providers(path: Path) -> None:
    _write_json(
        path,
        {
            "providers": {
                "demo": {
                    "display_name": "Demo",
                    "models": {
                        "demo-model": {
                            "label": "Demo",
                            "cost_tier": "standard",
                        }
                    },
                }
            }
        },
    )


def _write_minimal_assignments(path: Path, providers: list[str], model: str) -> None:
    _write_json(
        path,
        {
            "stages": {
                "demo.stage": {
                    "providers": providers,
                    "model": model,
                }
            }
        },
    )


def test_load_llm_settings_errors_on_unknown_provider(tmp_path: Path) -> None:
    providers_path = tmp_path / "providers.json"
    _write_minimal_providers(providers_path)

    assignments_path = tmp_path / "assignments.json"
    _write_minimal_assignments(assignments_path, ["missing"], "demo-model")

    with pytest.raises(LLMConfigError, match="unknown provider 'missing'"):
        load_llm_settings(providers_path=providers_path, assignments_path=assignments_path)


def test_load_llm_settings_errors_on_unknown_model(tmp_path: Path) -> None:
    providers_path = tmp_path / "providers.json"
    _write_minimal_providers(providers_path)

    assignments_path = tmp_path / "assignments.json"
    _write_minimal_assignments(assignments_path, ["demo"], "missing-model")

    with pytest.raises(LLMConfigError, match="unknown model 'missing-model'"):
        load_llm_settings(providers_path=providers_path, assignments_path=assignments_path)


def test_validate_llm_settings_requires_model(tmp_path: Path) -> None:
    providers_path = tmp_path / "providers.json"
    _write_minimal_providers(providers_path)

    assignments_path = tmp_path / "assignments.json"
    _write_json(
        assignments_path,
        {
            "stages": {
                "demo.stage": {
                    "providers": ["demo"],
                    # model omitted on purpose
                }
            }
        },
    )

    with pytest.raises(LLMConfigError, match="must define a model"):
        load_llm_settings(providers_path=providers_path, assignments_path=assignments_path)


def test_validate_llm_settings_detects_provider_without_models() -> None:
    settings = LLMSettings(providers={}, assignments={})
    # Manually craft a provider with no models for direct validation.
    provider = LLMProvider(
        name="demo",
        display_name="Demo",
        models={},
        env_requirements=[],
        api_kind="openai",
        default_endpoint="",
        requires_api_key=True,
        description="",
        category="creator",
        hosted_creators=[],
    )
    assignment = LLMStageAssignment(stage_key="demo.stage", providers=["demo"], model="demo-model")
    settings = LLMSettings(providers={"demo": provider}, assignments={"demo.stage": assignment})

    with pytest.raises(LLMConfigError, match="no models configured"):
        validate_llm_settings(settings)
