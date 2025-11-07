from __future__ import annotations

import json
from pathlib import Path

from doc_tools import hash_and_manifest as ham


def test_hash_and_manifest_generates_manifest(tmp_path: Path) -> None:
    pdf_dir = tmp_path / "out/doc-builds" / "pdf" / "dev"
    pdf_dir.mkdir(parents=True)
    (pdf_dir / "prd.pdf").write_text("prd", encoding="utf-8")

    rc = ham.main(["--output-dir", str(pdf_dir)])

    assert rc == 0
    manifest = json.loads((pdf_dir / "manifest.json").read_text(encoding="utf-8"))
    names = {entry["name"] for entry in manifest["artifacts"]}
    assert names == {"prd.pdf"}
    assert any(entry["sha256"] for entry in manifest["artifacts"])  # hash present


def test_hash_and_manifest_ignores_missing_files(tmp_path: Path) -> None:
    pdf_dir = tmp_path / "out/doc-builds" / "pdf" / "dev"
    pdf_dir.mkdir(parents=True)
    (pdf_dir / "tdd.pdf").write_text("tdd", encoding="utf-8")

    ham.main(["--output-dir", str(pdf_dir)])

    manifest = json.loads((pdf_dir / "manifest.json").read_text(encoding="utf-8"))
    assert {entry["name"] for entry in manifest["artifacts"]} == {"tdd.pdf"}


def test_hash_and_manifest_handles_empty_directory(tmp_path: Path) -> None:
    pdf_dir = tmp_path / "out/doc-builds" / "pdf" / "dev"
    pdf_dir.mkdir(parents=True)

    rc = ham.main(["--output-dir", str(pdf_dir)])

    assert rc == 0
    manifest = json.loads((pdf_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["artifacts"] == []
