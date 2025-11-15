from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from automation.langgraph import api_refactor
from packages.devops.readiness.manifest import build_manifest, write_manifest, write_manifest_gaps

MANIFEST_MAP = Path("specs/002-ai-refactor-plan/manifest_map.toml")


def test_manifest_generator_writes_records_and_gaps(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.jsonl"
    gaps_path = tmp_path / "manifest_gaps.json"

    records, gaps = build_manifest(MANIFEST_MAP)
    write_manifest(manifest_path, records)
    write_manifest_gaps(gaps_path, gaps)

    assert manifest_path.exists()
    loaded = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines()]
    assert len(loaded) == len(records)
    for entry in loaded:
        assert "signed_at" in entry
        assert len(entry["record_hash"]) == 64
    assert gaps_path.exists()
    assert json.loads(gaps_path.read_text(encoding="utf-8")) == gaps


def test_manifest_endpoint_respects_token_and_status(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest_path = tmp_path / "manifest.jsonl"
    records, _gaps = build_manifest(MANIFEST_MAP)
    write_manifest(manifest_path, records)

    token = "test-ops-token"
    monkeypatch.setenv(api_refactor.OPS_TOKEN_ENV, token)

    response = api_refactor.manifest_endpoint(token, manifest_path)
    assert len(response) == len(records)

    in_progress = [entry for entry in response if entry.get("status") == "in_progress"]
    filtered = api_refactor.manifest_endpoint(token, manifest_path, status="in_progress")
    assert filtered == in_progress

    with pytest.raises(PermissionError):
        api_refactor.manifest_endpoint("invalid", manifest_path)
