from __future__ import annotations

from pathlib import Path
from typing import List

import pytest

from scripts.docs import lint_docs as ld


class DummyResult:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode


def test_run_task_success(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[list[str]] = []

    def fake_run(cmd: List[str], cwd: Path, env: dict[str, str], check: bool) -> DummyResult:
        called.append(cmd)
        return DummyResult()

    monkeypatch.setattr(ld.subprocess, "run", fake_run)  # type: ignore[arg-type]
    task = ld.Task(name="echo", cmd=["echo", "hello"])

    assert ld.run_task(task) is True
    assert called == [["echo", "hello"]]


def test_run_task_optional_missing(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise FileNotFoundError

    monkeypatch.setattr(ld.subprocess, "run", fake_run)  # type: ignore[arg-type]
    task = ld.Task(name="optional", cmd=["missing"], optional=True, install_hint="hint")

    assert ld.run_task(task) is True
    captured = capsys.readouterr()
    assert "Skipping optional task" in captured.out


def test_run_task_required_missing(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise FileNotFoundError

    monkeypatch.setattr(ld.subprocess, "run", fake_run)  # type: ignore[arg-type]
    task = ld.Task(name="required", cmd=["missing"], optional=False, install_hint="install me")

    assert ld.run_task(task) is False
    captured = capsys.readouterr()
    assert "command not found" in captured.out
    assert "install me" in captured.out


def test_run_task_failure(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise ld.subprocess.CalledProcessError(returncode=7, cmd=["fail"])  # type: ignore[attr-defined]

    monkeypatch.setattr(ld.subprocess, "run", fake_run)  # type: ignore[arg-type]
    task = ld.Task(name="required", cmd=["fail"])

    assert ld.run_task(task) is False
    captured = capsys.readouterr()
    assert "failed with exit code 7" in captured.out


def test_build_tasks_contains_expected_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    tasks = ld.build_tasks([Path("docs/src")])

    names = [task.name for task in tasks]
    assert "build_runbook_catalog.py --check" in names
    assert "build_diagram_index.py --check" in names
    assert any(task.env and task.env.get("STRICT_DOCS") == "1" for task in tasks)


def test_resolve_targets_filters_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    existing = tmp_path / "docs"
    existing.mkdir()

    resolved = ld.resolve_targets([str(existing), "missing-dir"])

    captured = capsys.readouterr()
    assert existing in resolved
    assert "does not exist" in captured.err


def test_main_checks_missing_doc(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ld, "TDD_DOC", tmp_path / "absent.md")
    monkeypatch.setattr(ld.sys, "argv", ["lint_docs.py"])

    assert ld.main() == 2


def test_main_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    doc = tmp_path / "docs" / "src"
    doc.mkdir(parents=True)
    tdd = doc / "overview" / "tdd.md"
    tdd.parent.mkdir(parents=True, exist_ok=True)
    tdd.write_text("content", encoding="utf-8")
    monkeypatch.setattr(ld, "TDD_DOC", tdd)

    recorded: list[str] = []

    def fake_build_tasks(_targets: list[Path]) -> list[ld.Task]:
        return [ld.Task(name="first", cmd=["ok"])]

    def fake_run_task(task: ld.Task) -> bool:
        recorded.append(task.name)
        return True

    monkeypatch.setattr(ld, "build_tasks", fake_build_tasks)
    monkeypatch.setattr(ld, "run_task", fake_run_task)
    monkeypatch.setattr(ld.sys, "argv", ["lint_docs.py"])

    rc = ld.main()

    assert rc == 0
    assert recorded == ["first"]
    assert "All documentation lint tasks passed." in capsys.readouterr().out


def test_main_failure_counts_errors(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    doc = tmp_path / "docs" / "src"
    doc.mkdir(parents=True)
    tdd = doc / "overview" / "tdd.md"
    tdd.parent.mkdir(parents=True, exist_ok=True)
    tdd.write_text("content", encoding="utf-8")
    monkeypatch.setattr(ld, "TDD_DOC", tdd)

    monkeypatch.setattr(ld, "build_tasks", lambda targets: [ld.Task(name="fail", cmd=["nope"])])
    monkeypatch.setattr(ld, "run_task", lambda task: False)
    monkeypatch.setattr(ld.sys, "argv", ["lint_docs.py"])

    rc = ld.main()

    captured = capsys.readouterr()
    assert rc == 1
    assert "Documentation lint failed" in captured.out
