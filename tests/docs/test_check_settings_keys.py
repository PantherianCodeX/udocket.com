from __future__ import annotations

from pathlib import Path

import pytest

from scripts.docs import check_settings_keys as csk


class fake_completed:
    def __init__(self, returncode: int, stderr: str = "") -> None:
        self.returncode = returncode
        self.stderr = stderr


def test_extract_keys_parses_lines() -> None:
    text = "- foo.bar — description\n- skip_this — desc\n"

    keys = csk.extract_keys(text)

    assert keys == ["foo.bar", "skip_this"]


def test_find_missing_handles_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    outputs: list[list[str]] = []

    def fake_run(cmd, stdout, stderr, text):  # type: ignore[no-untyped-def]
        outputs.append(cmd)
        return fake_completed(0)

    monkeypatch.setattr(csk.subprocess, "run", fake_run)  # type: ignore[arg-type]

    assert csk.find_missing(["foo.bar"], set()) == []
    assert outputs and "foo.bar" in outputs[0]


def test_find_missing_collects_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        return fake_completed(1)

    monkeypatch.setattr(csk.subprocess, "run", fake_run)  # type: ignore[arg-type]

    assert csk.find_missing(["foo.bar"], set()) == ["foo.bar"]


def test_find_missing_raises_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        return fake_completed(2, stderr="boom")

    monkeypatch.setattr(csk.subprocess, "run", fake_run)  # type: ignore[arg-type]

    with pytest.raises(RuntimeError):
        csk.find_missing(["foo.bar"], set())


def test_main_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    doc = tmp_path / "docs" / "src" / "overview"
    doc.mkdir(parents=True)
    doc_path = doc / "tdd.md"
    doc_path.write_text("- foo.bar — description\n", encoding="utf-8")
    monkeypatch.setattr(csk, "DOC_PATH", doc_path)
    skip_file = tmp_path / "docs" / "settings_key_skip.txt"
    skip_file.parent.mkdir(parents=True, exist_ok=True)
    skip_file.write_text("foo.bar\n", encoding="utf-8")
    monkeypatch.setattr(csk, "SKIP_FILE", skip_file)
    monkeypatch.setattr(csk, "find_missing", lambda keys, skip: [])

    rc = csk.main()

    captured = capsys.readouterr()
    assert rc == 0
    assert "All documented settings keys were found" in captured.out


def test_main_reports_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    doc = tmp_path / "docs" / "src" / "overview"
    doc.mkdir(parents=True)
    doc_path = doc / "tdd.md"
    doc_path.write_text("- foo.bar — description\n", encoding="utf-8")
    monkeypatch.setattr(csk, "DOC_PATH", doc_path)
    monkeypatch.setattr(csk, "SKIP_FILE", tmp_path / "missing.txt")
    monkeypatch.setattr(csk, "find_missing", lambda keys, skip: keys)

    rc = csk.main()

    captured = capsys.readouterr()
    assert rc == 1
    assert "Settings keys documented but not found" in captured.out
