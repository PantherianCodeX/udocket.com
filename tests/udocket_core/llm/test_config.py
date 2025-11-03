from __future__ import annotations

import json
from pathlib import Path

import pytest

from packages.udocket_core.llm.config import LLMConfigError, load_llm_settings


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

