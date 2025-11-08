from __future__ import annotations

import argparse
from pathlib import Path

import pytest

import doc_tools.create_adr as cad


def test_next_identifier_handles_existing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "docs" / "src" / "adr"
    target.mkdir(parents=True)
    (target / "ADR-0003-example.md").write_text("existing", encoding="utf-8")
    (target / "ADR-0010-other.md").write_text("existing", encoding="utf-8")
    monkeypatch.setattr(cad, "ADR_DIR", target)

    assert cad.next_identifier() == 11


def test_build_content_includes_metadata() -> None:
    content = cad.build_content(
        ident=5,
        title="Data Residency Plan",
        status="Accepted",
        deciders=["Alice", "Bob"],
        tags=["residency", "privacy"],
        date="2025-10-31",
    )

    assert "ADR-0005 — Data Residency Plan" in content
    assert "Status" in content
    assert "Alice, Bob" in content
    assert "residency, privacy" in content


def test_main_dry_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "docs" / "src" / "adr"
    monkeypatch.setattr(cad, "ADR_DIR", target)

    rc = cad.main(["Background Worker Topology", "--dry-run"])

    captured = capsys.readouterr()
    assert rc == 0
    assert "would write" in captured.out
    assert not any(target.glob("ADR-*.md"))


def test_main_creates_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    target = tmp_path / "docs" / "src" / "adr"
    monkeypatch.setattr(cad, "ADR_DIR", target)

    rc = cad.main(["Guardian Quarantine Enhancements", "--status", "Proposed", "--deciders", "Alice,Bob"])

    assert rc == 0
    created = next(target.glob("ADR-*.md"))
    text = created.read_text(encoding="utf-8")
    assert "Guardian Quarantine Enhancements" in text
    assert "Alice, Bob" in text


def test_main_refuses_overwrite(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "docs" / "src" / "adr"
    target.mkdir(parents=True)
    existing = target / "ADR-0001-existing-adr.md"
    existing.write_text("content", encoding="utf-8")

    monkeypatch.setattr(cad, "ADR_DIR", target)
    monkeypatch.setattr(cad, "next_identifier", lambda: 1)

    rc = cad.main(["Existing ADR"])

    captured = capsys.readouterr()
    assert rc == 1
    assert "already exists" in captured.err
