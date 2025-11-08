from __future__ import annotations

import os
from pathlib import Path

import pytest

from packages.common import env as env_module
from packages.common.env import load_env_defaults, reset_env_loader_state


@pytest.fixture(autouse=True)
def _reset_env(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_env_loader_state()
    for key in list(os.environ.keys()):
        if key.startswith("TEST_ENV_"):
            monkeypatch.delenv(key, raising=False)


# Reference the fixture symbol so type checkers mark it as used.
_ = _reset_env


def test_parse_env_file_handles_missing(tmp_path: Path) -> None:
    missing = tmp_path / "absent.env"
    assert env_module._parse_env_file(missing) == {}


def test_parse_env_file_skips_invalid_lines(tmp_path: Path) -> None:
    env_file = tmp_path / "mixed.env"
    env_file.write_text("# comment\nINVALID\nKEY=value\n=skip\n", encoding="utf-8")

    parsed = env_module._parse_env_file(env_file)

    assert parsed == {"KEY": "value"}


def test_load_env_defaults_prefers_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    override = tmp_path / "override.env"
    override.write_text("TEST_ENV_ALPHA=override\n", encoding="utf-8")
    fallback = tmp_path / "fallback.env"
    fallback.write_text("TEST_ENV_ALPHA=fallback\n", encoding="utf-8")

    monkeypatch.setenv("TEST_ENV_FILE", str(override))

    load_env_defaults(env_var="TEST_ENV_FILE", default_paths=(fallback,))

    assert os.environ["TEST_ENV_ALPHA"] == "override"


def test_load_env_defaults_applies_first_available(tmp_path: Path) -> None:
    env_file = tmp_path / "defaults.env"
    env_file.write_text("TEST_ENV_BETA=beta\n", encoding="utf-8")

    load_env_defaults(env_var="TEST_ENV_FILE_MISSING", default_paths=(env_file,))

    assert os.environ["TEST_ENV_BETA"] == "beta"


def test_load_env_defaults_ignores_missing_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = tmp_path / "missing.env"
    monkeypatch.delenv("TEST_ENV_EPSILON", raising=False)

    load_env_defaults(env_var="TEST_ENV_FILE", default_paths=(missing,))

    assert "TEST_ENV_EPSILON" not in os.environ


def test_load_env_defaults_does_not_override_existing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / "defaults.env"
    env_file.write_text("TEST_ENV_GAMMA=fallback\n", encoding="utf-8")
    monkeypatch.setenv("TEST_ENV_GAMMA", "existing")

    load_env_defaults(env_var="TEST_ENV_FILE", default_paths=(env_file,))

    assert os.environ["TEST_ENV_GAMMA"] == "existing"


def test_load_env_defaults_is_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = tmp_path / "defaults.env"
    env_file.write_text("TEST_ENV_DELTA=initial\n", encoding="utf-8")

    load_env_defaults(env_var="TEST_ENV_FILE", default_paths=(env_file,))

    assert os.environ["TEST_ENV_DELTA"] == "initial"

    monkeypatch.setenv("TEST_ENV_DELTA", "updated")
    load_env_defaults(env_var="TEST_ENV_FILE", default_paths=(env_file,))

    assert os.environ["TEST_ENV_DELTA"] == "updated"
