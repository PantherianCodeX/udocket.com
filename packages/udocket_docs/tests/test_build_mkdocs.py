from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import pytest

from doc_tools.build import mkdocs as bm
from doc_tools import paths


class DummyCompletedProcess:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_run_mkdocs_invokes_cli_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    called: Dict[str, List[str]] = {}

    def fake_run(cmd, cwd, **kwargs):  # type: ignore[no-untyped-def]
        called["cmd"] = cmd
        called["cwd"] = str(cwd)
        return DummyCompletedProcess()

    monkeypatch.setattr(bm, "REPO_ROOT", tmp_path, raising=False)
    monkeypatch.setattr(paths, "REPO_ROOT", tmp_path, raising=False)
    config = tmp_path / "packages" / "udocket_docs" / "mkdocs.yml"
    config.parent.mkdir(parents=True)
    config.write_text("site_name: docs\n", encoding="utf-8")
    monkeypatch.setattr(bm, "MKDOCS_CONFIG", config)
    monkeypatch.setattr(bm.subprocess, "run", fake_run)  # type: ignore[arg-type]
    monkeypatch.setattr(bm.shutil, "rmtree", lambda *args, **kwargs: None)  # type: ignore[arg-type]

    rc = bm.run_mkdocs(dry_run=False)

    assert rc == 0
    assert called["cmd"][0] == "mkdocs"
    assert "--site-dir" not in called["cmd"]


def test_main_handles_missing_binary(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise FileNotFoundError

    monkeypatch.setattr(bm.subprocess, "run", fake_run)  # type: ignore[arg-type]

    rc = bm.main(["--dry-run"])

    assert rc == 1
    assert "mkdocs binary not found" in capsys.readouterr().err


def test_run_mkdocs_dry_run_cleans_temp(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    called: Dict[str, List[str]] = {}
    temps: list[str] = []
    cleaned: list[str] = []

    def fake_run(cmd, cwd, **kwargs):  # type: ignore[no-untyped-def]
        called["cmd"] = cmd
        return DummyCompletedProcess()

    def fake_mkdtemp(prefix: str) -> str:
        temp_dir = str(tmp_path / "temp-site")
        temps.append(temp_dir)
        return temp_dir

    def fake_rmtree(path: str, ignore_errors: bool = True) -> None:
        cleaned.append(path)

    monkeypatch.setattr(bm, "REPO_ROOT", tmp_path, raising=False)
    monkeypatch.setattr(paths, "REPO_ROOT", tmp_path, raising=False)
    config = tmp_path / "packages" / "udocket_docs" / "mkdocs.yml"
    config.parent.mkdir(parents=True)
    config.write_text("site_name: docs\n", encoding="utf-8")
    monkeypatch.setattr(bm, "MKDOCS_CONFIG", config)
    monkeypatch.setattr(bm.subprocess, "run", fake_run)  # type: ignore[arg-type]
    monkeypatch.setattr(bm.tempfile, "mkdtemp", fake_mkdtemp)
    monkeypatch.setattr(bm.shutil, "rmtree", fake_rmtree)

    rc = bm.run_mkdocs(dry_run=True)

    assert rc == 0
    assert temps
    assert "--site-dir" in called["cmd"]
    site_dir = temps[0]
    assert site_dir in called["cmd"]
    assert cleaned == [site_dir]


def test_run_mkdocs_escalates_anchor_warning(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    output = "INFO - Doc file 'foo' contains a link '../bar#baz', but the doc 'bar' does not contain an anchor '#baz'."

    def fake_run(cmd, cwd, stdout, stderr, text, check):  # type: ignore[no-untyped-def]
        return DummyCompletedProcess(stdout=output)

    monkeypatch.setattr(bm, "REPO_ROOT", tmp_path, raising=False)
    monkeypatch.setattr(paths, "REPO_ROOT", tmp_path, raising=False)
    config = tmp_path / "packages" / "udocket_docs" / "mkdocs.yml"
    config.parent.mkdir(parents=True)
    config.write_text("site_name: docs\n", encoding="utf-8")
    monkeypatch.setattr(bm, "MKDOCS_CONFIG", config)
    monkeypatch.setattr(bm.subprocess, "run", fake_run)  # type: ignore[arg-type]
    monkeypatch.setattr(bm.shutil, "rmtree", lambda *a, **k: None)  # type: ignore[arg-type]

    rc = bm.run_mkdocs(dry_run=False)

    assert rc == 1
