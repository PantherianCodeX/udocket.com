# pyright: strict
"""Tests for automation.langgraph.artifacts helpers."""

from __future__ import annotations

from pathlib import Path

from packages.ai.types import JobID

from automation.langgraph.artifacts import (
    ArtifactWriteResult,
    OpsWriteResult,
    append_audit_log,
    write_json_artifact,
    write_ops_record,
    write_text_artifact,
)


def test_write_json_artifact_creates_versioned_file(tmp_path: Path) -> None:
    case_dir = tmp_path
    job_id = JobID("job-123")

    result1 = write_json_artifact(
        case_dir=case_dir,
        job_id=job_id,
        artifact_name="summary",
        payload={"value": 1},
    )
    result2 = write_json_artifact(
        case_dir=case_dir,
        job_id=job_id,
        artifact_name="summary",
        payload={"value": 2},
    )

    assert isinstance(result1, ArtifactWriteResult)
    assert isinstance(result2, ArtifactWriteResult)
    assert result1.path.exists()
    assert result2.path.exists()
    assert result1.path != result2.path
    # Names follow <job_id>__<artifact_name>_v{n}.json
    assert result1.path.name.startswith(f"{job_id}__summary_v1")
    assert result2.path.name.startswith(f"{job_id}__summary_v2")
    assert result1.checksum
    assert result2.checksum


def test_write_text_artifact_uses_extension_and_versions(tmp_path: Path) -> None:
    case_dir = tmp_path
    job_id = JobID("job-456")

    result = write_text_artifact(
        case_dir=case_dir,
        job_id=job_id,
        artifact_name="staff_report",
        contents="report body",
        extension="md",
    )

    assert isinstance(result, ArtifactWriteResult)
    assert result.path.exists()
    assert result.path.suffix == ".md"
    assert result.path.name.startswith(f"{job_id}__staff_report_v1")
    assert result.checksum


def test_write_ops_record_and_append_audit_log(tmp_path: Path) -> None:
    case_dir = tmp_path
    job_id = JobID("job-789")

    ops_result = write_ops_record(
        case_dir=case_dir,
        job_id=job_id,
        record_name="manifest",
        payload={"ok": True},
    )
    assert isinstance(ops_result, OpsWriteResult)
    assert ops_result.path.exists()
    # Path should live under ops/ with deterministic name
    assert ops_result.path.parent.name == "ops"
    assert ops_result.path.name == f"{job_id}__manifest.json"

    audit_path = append_audit_log(
        case_dir=case_dir,
        audit_name="ops_summary",
        payload={"event": "test"},
    )
    assert audit_path.exists()
    assert audit_path.parent.name == "ops"
    assert audit_path.name == "ops_summary.jsonl"

