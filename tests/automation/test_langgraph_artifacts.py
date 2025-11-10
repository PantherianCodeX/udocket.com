from __future__ import annotations

import json
from typing import TYPE_CHECKING

from automation.langgraph.artifacts import (
    append_audit_log,
    write_json_artifact,
    write_ops_record,
    write_text_artifact,
)
from packages.ai.types import JobID

if TYPE_CHECKING:
    from pathlib import Path


def test_write_json_artifact_versions(tmp_path: Path) -> None:
    result = write_json_artifact(
        case_dir=tmp_path,
        job_id=JobID("job-21"),
        artifact_name="summary",
        payload={"status": "ok"},
    )
    assert result.path.exists()
    assert result.path.name == "job-21__summary_v1.json"
    second = write_json_artifact(
        case_dir=tmp_path,
        job_id=JobID("job-21"),
        artifact_name="summary",
        payload={"status": "ok"},
    )
    assert second.path.name == "job-21__summary_v2.json"


def test_write_text_artifact(tmp_path: Path) -> None:
    result = write_text_artifact(
        case_dir=tmp_path,
        job_id=JobID("job-22"),
        artifact_name="summary_md",
        contents="# Summary",
    )
    assert result.path.exists()
    assert result.path.suffix == ".md"


def test_write_ops_record(tmp_path: Path) -> None:
    result = write_ops_record(
        case_dir=tmp_path,
        job_id=JobID("job-23"),
        record_name="summary_log",
        payload={"status": "ok"},
    )
    assert result.path.exists()
    assert result.path.name == "job-23__summary_log.json"
    data = json.loads(result.path.read_text(encoding="utf-8"))
    assert data["status"] == "ok"


def test_append_audit_log(tmp_path: Path) -> None:
    path = append_audit_log(
        case_dir=tmp_path,
        audit_name="ops_summary",
        payload={"event": "done"},
    )
    assert path.exists()
    contents = path.read_text(encoding="utf-8").strip().splitlines()
    assert json.loads(contents[0])["event"] == "done"
