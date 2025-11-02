from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

import pytest

from doc_tools import manage_docs as md


class DummyResult:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode


def _ctx(*, dry_run: bool = False) -> md.RunContext:
    return md.RunContext(dry_run=dry_run, targets=[])


def test_run_task_success(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[list[str]] = []

    def fake_run(cmd: List[str], cwd: Path, env: dict[str, str], check: bool) -> DummyResult:
        called.append(cmd)
        return DummyResult()

    monkeypatch.setattr(md.subprocess, "run", fake_run, raising=False)
    task = md.Task(name="echo", category="lint", builder=lambda ctx: ["echo", "hello"])

    assert md.run_task(task, _ctx()) is True
    assert called == [["echo", "hello"]]


def test_run_task_optional_missing(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise FileNotFoundError

    monkeypatch.setattr(md.subprocess, "run", fake_run, raising=False)
    task = md.Task(name="optional", category="lint", builder=lambda ctx: ["missing"], optional=True, install_hint="hint")

    assert md.run_task(task, _ctx()) is True
    captured = capsys.readouterr()
    assert "Skipping optional task" in captured.out


def test_run_task_required_missing(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise FileNotFoundError

    monkeypatch.setattr(md.subprocess, "run", fake_run, raising=False)
    task = md.Task(name="required", category="lint", builder=lambda ctx: ["missing"], install_hint="install me")

    assert md.run_task(task, _ctx()) is False
    captured = capsys.readouterr()
    assert "command not found" in captured.out
    assert "install me" in captured.out


def test_run_task_failure(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise md.subprocess.CalledProcessError(returncode=7, cmd=["fail"])

    monkeypatch.setattr(md.subprocess, "run", fake_run, raising=False)
    task = md.Task(name="required", category="lint", builder=lambda ctx: ["fail"])

    assert md.run_task(task, _ctx()) is False
    captured = capsys.readouterr()
    assert "failed with exit code 7" in captured.out


def test_organise_tasks_filters_categories(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_tasks = [
        md.Task(name="lint", category="lint", builder=lambda ctx: ["true"]),
        md.Task(name="sync", category="sync", builder=lambda ctx: ["true"]),
    ]
    monkeypatch.setattr(md, "TASKS", fake_tasks, raising=False)

    filtered = md.organise_tasks(["sync"])

    assert [task.name for task in filtered] == ["sync"]


def test_determine_categories_defaults() -> None:
    args = argparse.Namespace(lint=False, sync=False, build=False, pdf=False, all=False)
    assert md.determine_categories(args) == ["lint"]


def test_determine_categories_all_flag() -> None:
    args = argparse.Namespace(lint=False, sync=False, build=False, pdf=False, all=True)
    assert md.determine_categories(args) == ["lint", "sync", "build", "pdf"]


def test_resolve_targets_filters_missing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    existing = tmp_path / "docs"
    existing.mkdir()

    resolved = md.resolve_targets([str(existing), "missing-dir"])

    captured = capsys.readouterr()
    assert existing in resolved
    assert "does not exist" in captured.err


def test_main_list(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    rc = md.main(["--list"])

    captured = capsys.readouterr()
    assert rc == 0
    assert "Available tasks" in captured.out


def test_main_runs_tasks(monkeypatch: pytest.MonkeyPatch) -> None:
    executed: list[str] = []

    def fake_organise(categories: List[str]) -> list[md.Task]:
        return [md.Task(name="demo", category=categories[0], builder=lambda ctx: ["true"])]

    def fake_run(task: md.Task, ctx: md.RunContext) -> bool:
        executed.append(task.name)
        return True

    monkeypatch.setattr(md, "organise_tasks", fake_organise, raising=False)
    monkeypatch.setattr(md, "run_task", fake_run, raising=False)

    rc = md.main(["--lint", "--dry-run"])

    assert rc == 0
    assert executed == ["demo"]


def test_main_failure_counts_errors(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    attempts: list[str] = []

    def fake_organise(categories: List[str]) -> list[md.Task]:
        return [md.Task(name="bad", category=categories[0], builder=lambda ctx: ["false"])]

    def fake_run(task: md.Task, ctx: md.RunContext) -> bool:
        attempts.append(task.name)
        return False

    monkeypatch.setattr(md, "organise_tasks", fake_organise, raising=False)
    monkeypatch.setattr(md, "run_task", fake_run, raising=False)

    rc = md.main(["--lint", "--dry-run"])

    captured = capsys.readouterr()
    assert rc == 1
    assert attempts == ["bad"]
    assert "task(s) failed" in captured.out


def test_main_requires_tdd_doc(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(md, "REPO_ROOT", tmp_path, raising=False)
    monkeypatch.setattr(md, "organise_tasks", lambda categories: [], raising=False)

    rc = md.main(["--lint"])

    captured = capsys.readouterr()
    assert rc == 2
    assert "missing documentation anchor" in captured.err


def test_builder_commands_cover_branches(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(md, "REPO_ROOT", tmp_path, raising=False)

    structure_dir = tmp_path / "docs"
    structure_dir.mkdir(parents=True)
    config_dir = tmp_path / "packages" / "udocket_docs" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    service_dir = structure_dir / "platform"
    ops_dir = structure_dir / "ops"
    service_dir.mkdir(parents=True, exist_ok=True)
    ops_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(md.paths, "DOCS_ROOT", structure_dir, raising=False)
    monkeypatch.setattr(md.paths, "CONFIG_ROOT", config_dir, raising=False)
    monkeypatch.setattr(md.paths, "SERVICE_ROOTS", [service_dir], raising=False)

    monkeypatch.setattr(md, "DOCS_DIR", structure_dir, raising=False)
    monkeypatch.setattr(md, "CONFIG_DIR", config_dir, raising=False)
    md.STRUCTURE_DIRS = [service_dir, ops_dir]
    monkeypatch.setattr(
        md,
        "VALE_CI_CONFIG",
        str((config_dir / "vale-ci.ini").relative_to(tmp_path)),
        raising=False,
    )

    ctx = md.RunContext(dry_run=False, targets=[structure_dir])
    dry_ctx = md.RunContext(dry_run=True, targets=[structure_dir])

    assert md.builder_runbook_check(ctx)[-1] == "--check"
    assert md.builder_diagram_check(ctx)[-1] == "--check"
    assert md.builder_api_error_codes_check(ctx)[-1] == "--check"

    structure_cmd = md.builder_check_structure(ctx)
    assert "doc_tools.check_structure" in structure_cmd
    assert str(structure_dir) in structure_cmd

    assert md.builder_check_appendices(ctx)[-1] == "doc_tools.check_appendices"

    markdown_cmd = md.builder_markdownlint(ctx)
    assert markdown_cmd[0] == "npx"

    assert md.builder_vale_sync(ctx)[0] == "vale"
    assert "--config" in md.builder_vale(ctx)

    assert md.builder_check_settings(ctx)[-1] == "doc_tools.check_settings_keys"
    assert md.builder_check_links(ctx)[-1] == "doc_tools.check_links"

    sync_cmd = md.builder_sync_doc_controls(ctx)
    assert sync_cmd[-1] == str(structure_dir)
    sync_dry_cmd = md.builder_sync_doc_controls(dry_ctx)
    assert sync_dry_cmd[-1] == "--dry-run"

    assets_cmd = md.builder_sync_doc_assets(ctx)
    assert assets_cmd[-1] == "doc_tools.sync.doc_assets"
    assets_dry_cmd = md.builder_sync_doc_assets(dry_ctx)
    assert assets_dry_cmd[-1] == "--dry-run"

    assert md.builder_runbook_update(ctx) == [md.PYTHON, "-m", "doc_tools.build.runbook_catalog"]
    assert md.builder_runbook_update(dry_ctx)[-1] == "--check"

    assert md.builder_diagram_update(ctx) == [md.PYTHON, "-m", "doc_tools.build.diagram_index"]
    assert md.builder_diagram_update(dry_ctx)[-1] == "--check"

    assert md.builder_slo_update(ctx) == [md.PYTHON, "-m", "doc_tools.build.slo_index"]
    assert md.builder_slo_update(dry_ctx)[-1] == "--check"

    assert md.builder_api_error_update(ctx) == [md.PYTHON, "-m", "doc_tools.build.api_error_codes"]
    assert md.builder_api_error_update(dry_ctx)[-1] == "--check"

    mkdocs_cmd = md.builder_mkdocs(ctx)
    assert mkdocs_cmd[-1] != "--dry-run"
    mkdocs_dry_cmd = md.builder_mkdocs(dry_ctx)
    assert mkdocs_dry_cmd[-1] == "--dry-run"

    assert md.builder_pdf_tdd(dry_ctx) is None
    pdf_cmd = md.builder_pdf_tdd(ctx)
    assert pdf_cmd == [md.PYTHON, "-m", "doc_tools.pdf_build", "--target", "tdd"]

    assert md.builder_pdf_prd(dry_ctx) is None
    pdf_prd_cmd = md.builder_pdf_prd(ctx)
    assert pdf_prd_cmd == [md.PYTHON, "-m", "doc_tools.pdf_build", "--target", "prd"]
