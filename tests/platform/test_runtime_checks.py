from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from apps.platform.config import runtime_checks
from apps.platform.config.runtime_checks import RuntimeConfigurationError, validate_runtime_configuration


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_validate_runtime_configuration_missing_providers(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    storage_root = tmp_path / "storage"
    storage_root.mkdir()

    monkeypatch.setattr(runtime_checks, "ensure_storage_root", lambda: storage_root)
    monkeypatch.setattr(runtime_checks, "resolve_llm_providers_path", lambda: tmp_path / "providers.json")
    monkeypatch.setattr(runtime_checks, "resolve_llm_assignments_path", lambda: tmp_path / "assignments.json")
    monkeypatch.setattr(runtime_checks, "resolve_analyze_defaults_path", lambda: tmp_path / "analyze_defaults.json")

    with pytest.raises(RuntimeConfigurationError, match="LLM providers configuration"):
        validate_runtime_configuration()


def test_validate_runtime_configuration_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    storage_root = tmp_path / "storage"
    storage_root.mkdir()

    providers_path = tmp_path / "providers.json"
    assignments_path = tmp_path / "assignments.json"
    analyze_defaults_path = tmp_path / "analyze_defaults.json"

    _write_json(
        providers_path,
        {
            "providers": {
                "demo": {
                    "display_name": "Demo",
                    "description": "",
                    "category": "test",
                    "models": {
                        "demo-model": {
                            "label": "Demo",
                            "cost_tier": "standard",
                            "default_enabled": True,
                            "options": {},
                        }
                    },
                }
            }
        },
    )
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
    _write_json(analyze_defaults_path, {})

    monkeypatch.setattr(runtime_checks, "ensure_storage_root", lambda: storage_root)
    monkeypatch.setattr(runtime_checks, "resolve_llm_providers_path", lambda: providers_path)
    monkeypatch.setattr(runtime_checks, "resolve_llm_assignments_path", lambda: assignments_path)
    monkeypatch.setattr(runtime_checks, "resolve_analyze_defaults_path", lambda: analyze_defaults_path)

    caplog.set_level(logging.INFO, logger="apps.platform.runtime_checks")

    validate_runtime_configuration()

    matching = [
        record
        for record in caplog.records
        if record.name == "apps.platform.runtime_checks"
        and record.levelno == logging.INFO
        and "Runtime configuration validated" in record.getMessage()
    ]
    assert matching
    record = matching[-1]
    assert record.storage_root == str(storage_root)
    assert record.llm_providers_path == str(providers_path)
    assert record.llm_assignments_path == str(assignments_path)
    assert record.analyze_defaults_path == str(analyze_defaults_path)


def test_validate_runtime_configuration_skips_via_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UDOCKET_SKIP_RUNTIME_CHECKS", "1")
    runtime_checks.validate_runtime_configuration()


def test_validate_runtime_configuration_skips_for_collectstatic(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    storage_root = tmp_path / "storage"
    storage_root.mkdir()

    monkeypatch.setattr(runtime_checks, "ensure_storage_root", lambda: storage_root)
    monkeypatch.setattr(runtime_checks, "resolve_llm_providers_path", lambda: tmp_path / "providers.json")
    monkeypatch.setattr(runtime_checks, "resolve_llm_assignments_path", lambda: tmp_path / "assignments.json")
    monkeypatch.setattr(runtime_checks, "resolve_analyze_defaults_path", lambda: tmp_path / "analyze_defaults.json")
    monkeypatch.setattr(runtime_checks, "_current_management_command", lambda: "collectstatic")

    runtime_checks.validate_runtime_configuration()


def test_validate_runtime_configuration_invokes_loader_once(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    storage_root = tmp_path / "storage"
    storage_root.mkdir()

    providers_path = tmp_path / "providers.json"
    assignments_path = tmp_path / "assignments.json"
    analyze_defaults_path = tmp_path / "analyze_defaults.json"

    providers_path.write_text("{}", encoding="utf-8")
    assignments_path.write_text("{}", encoding="utf-8")
    analyze_defaults_path.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(runtime_checks, "ensure_storage_root", lambda: storage_root)
    monkeypatch.setattr(runtime_checks, "resolve_llm_providers_path", lambda: providers_path)
    monkeypatch.setattr(runtime_checks, "resolve_llm_assignments_path", lambda: assignments_path)
    monkeypatch.setattr(runtime_checks, "resolve_analyze_defaults_path", lambda: analyze_defaults_path)

    call_count = 0

    def _mock_loader(*_: object, **__: object) -> object:
        nonlocal call_count
        call_count += 1
        return object()

    monkeypatch.setattr(runtime_checks, "load_llm_settings", _mock_loader)

    validate_runtime_configuration()
    assert call_count == 1
