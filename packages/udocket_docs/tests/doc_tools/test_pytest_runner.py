from __future__ import annotations

from typing import List

import pytest

from doc_tools import pytest_runner


def test_pytest_runner_uses_default(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[list[str]] = []

    def fake_main(args: List[str]) -> int:
        captured.append(args)
        return 0

    monkeypatch.setattr(pytest_runner.pytest, "main", fake_main)
    rc = pytest_runner.main([])

    assert rc == 0
    assert captured == [[pytest_runner.DEFAULT_TARGET]]


def test_pytest_runner_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[list[str]] = []

    def fake_main(args: List[str]) -> int:
        captured.append(args)
        return 0

    monkeypatch.setattr(pytest_runner.pytest, "main", fake_main)
    monkeypatch.setenv(pytest_runner.ENV_VAR, "pkg::test_case -k keywords")

    rc = pytest_runner.main([])

    assert rc == 0
    assert captured == [["pkg::test_case", "-k", "keywords"]]


def test_pytest_runner_supports_coverage_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[list[str]] = []

    def fake_main(args: List[str]) -> int:
        captured.append(args)
        return 0

    monkeypatch.setattr(pytest_runner.pytest, "main", fake_main)
    monkeypatch.setenv(pytest_runner.ENV_VAR, "")

    rc = pytest_runner.main(["--coverage", "extra_test"])

    assert rc == 0
    expected = [*(f"--cov={module}" for module in pytest_runner.COVERAGE_MODULES), "--cov-report=term-missing", "extra_test"]
    assert captured == [expected]
