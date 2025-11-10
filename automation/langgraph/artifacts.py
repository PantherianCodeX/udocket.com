# pyright: strict
"""Deterministic artifact and ops writers for LangGraph pipelines."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from packages.common.json_utils import JSONObject, coerce_json_object, write_json_object

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from packages.ai.types import JobID


@dataclass(slots=True, frozen=True)
class ArtifactWriteResult:
    """Result emitted after writing an artifact to disk."""

    name: str
    path: Path
    checksum: str


@dataclass(slots=True, frozen=True)
class OpsWriteResult:
    """Result emitted after writing structured ops metadata."""

    path: Path
    payload: JSONObject


def write_json_artifact(
    *,
    case_dir: Path,
    job_id: JobID,
    artifact_name: str,
    payload: Mapping[str, object],
) -> ArtifactWriteResult:
    """Write a JSON artifact under analysis/ using deterministic filenames."""

    path = _next_versioned_path(case_dir / "analysis", job_id, artifact_name, ".json")
    write_json_object(path, payload)
    checksum = _sha256_file(path)
    return ArtifactWriteResult(name=artifact_name, path=path, checksum=checksum)


def write_text_artifact(
    *,
    case_dir: Path,
    job_id: JobID,
    artifact_name: str,
    contents: str,
    extension: str = "md",
) -> ArtifactWriteResult:
    """Write a Markdown/text artifact under analysis/ with versioned filenames."""

    suffix = extension if extension.startswith(".") else f".{extension}"
    path = _next_versioned_path(case_dir / "analysis", job_id, artifact_name, suffix)
    path.write_text(contents, encoding="utf-8")
    checksum = _sha256_file(path)
    return ArtifactWriteResult(name=artifact_name, path=path, checksum=checksum)


def write_ops_record(
    *,
    case_dir: Path,
    job_id: JobID,
    record_name: str,
    payload: Mapping[str, object],
) -> OpsWriteResult:
    """Write a deterministic ops metadata JSON file."""

    ops_dir = case_dir / "ops"
    ops_dir.mkdir(parents=True, exist_ok=True)
    normalized = coerce_json_object(payload)
    path = ops_dir / f"{job_id}__{record_name}.json"
    write_json_object(path, normalized)
    return OpsWriteResult(path=path, payload=normalized)


def append_audit_log(
    *,
    case_dir: Path,
    audit_name: str,
    payload: Mapping[str, object],
) -> Path:
    """Append a JSON line to the shared ops audit stream (ops/<audit_name>.jsonl)."""

    ops_dir = case_dir / "ops"
    ops_dir.mkdir(parents=True, exist_ok=True)
    normalized = coerce_json_object(payload)
    path = ops_dir / f"{audit_name}.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(normalized, ensure_ascii=False))
        handle.write("\n")
    return path


def _next_versioned_path(directory: Path, job_id: JobID, artifact_name: str, suffix: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    version = 1
    suffix_value = suffix if suffix.startswith(".") else f".{suffix}"
    while True:
        filename = f"{job_id}__{artifact_name}_v{version}{suffix_value}"
        candidate = directory / filename
        if not candidate.exists():
            return candidate
        version += 1


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


__all__ = [
    "ArtifactWriteResult",
    "OpsWriteResult",
    "append_audit_log",
    "write_json_artifact",
    "write_ops_record",
    "write_text_artifact",
]
