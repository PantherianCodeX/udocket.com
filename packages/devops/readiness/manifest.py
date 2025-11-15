"""Implementation manifest helpers for Feature 002."""

from __future__ import annotations

import hashlib
import json
import tomllib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Sequence
from uuid import UUID

from packages.common.agents.stage_map import StageKey
from packages.common.types import (
    ArtifactOwner,
    ImplementationBlueprintRecord,
    ImplementationStatus,
    LaneID,
    StageExecutionRecord,
)


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _resolve_path(raw_path: str) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    return Path.cwd() / candidate


def _parse_stage_execution(entry: Mapping[str, object]) -> StageExecutionRecord:
    telemetry_raw = entry.get("telemetry_refs") or []
    telemetry_refs = tuple(UUID(token) for token in telemetry_raw)
    residency_id = entry.get("residency_ledger_id")
    return StageExecutionRecord(
        run_id=UUID(entry["run_id"]),
        lane_id=LaneID(entry["lane_id"]),
        stage_key=StageKey(entry["stage_key"]),
        status=ImplementationStatus(entry["status"]),
        started_at=_parse_datetime(entry["started_at"]),
        completed_at=_parse_datetime(entry["completed_at"]) if entry.get("completed_at") else None,
        token_usage=int(entry["token_usage"]) if entry.get("token_usage") is not None else None,
        telemetry_refs=telemetry_refs,
        residency_ledger_id=UUID(residency_id) if residency_id else None,
    )


@dataclass(frozen=True)
class ManifestArtifactSpec:
    artifact_id: str
    artifact_path: Path
    target_repo_path: Path
    owner: ArtifactOwner
    status: ImplementationStatus
    dependencies: tuple[str, ...]
    critical_path: bool
    evidence_refs: tuple[UUID, ...]
    stage_executions: tuple[StageExecutionRecord, ...]


def load_manifest_map(map_path: Path) -> tuple[ManifestArtifactSpec, ...]:
    with map_path.open("rb") as handle:
        payload = tomllib.load(handle)
    entries = payload.get("artifacts") or payload.get("entries") or []
    specs: list[ManifestArtifactSpec] = []
    for entry in entries:
        artifact_id = entry["id"]
        artifact_path = _resolve_path(entry["artifact_path"])
        target_repo_path = _resolve_path(entry["target_repo_path"])
        owner = ArtifactOwner(entry["owner"])
        status = ImplementationStatus(entry["status"])
        dependencies = tuple(entry.get("dependencies") or [])
        critical_path = bool(entry.get("critical_path", False))
        evidence_refs = tuple(UUID(ref) for ref in entry.get("evidence_refs") or [])
        stage_exec_data = entry.get("stage_executions") or []
        stage_executions = tuple(_parse_stage_execution(raw) for raw in stage_exec_data)
        specs.append(
            ManifestArtifactSpec(
                artifact_id=artifact_id,
                artifact_path=artifact_path,
                target_repo_path=target_repo_path,
                owner=owner,
                status=status,
                dependencies=dependencies,
                critical_path=critical_path,
                evidence_refs=evidence_refs,
                stage_executions=stage_executions,
            )
        )
    return tuple(specs)


def _sha256(path: Path) -> str:
    with path.open("rb") as handle:
        digest = hashlib.sha256(handle.read()).hexdigest()
    return digest


def _relative_to_root(path: Path) -> Path:
    try:
        return path.relative_to(Path.cwd())
    except ValueError:
        return path


def build_manifest(map_path: Path) -> tuple[list[ImplementationBlueprintRecord], list[dict[str, object]]]:
    specs = load_manifest_map(map_path)
    records: list[ImplementationBlueprintRecord] = []
    for spec in specs:
        if not spec.artifact_path.exists():
            raise FileNotFoundError(spec.artifact_path)
        record = ImplementationBlueprintRecord(
            artifact_path=_relative_to_root(spec.artifact_path),
            artifact_sha256=_sha256(spec.artifact_path),
            target_repo_path=_relative_to_root(spec.target_repo_path),
            owner=spec.owner,
            status=spec.status,
            evidence_refs=spec.evidence_refs,
            dependencies=spec.dependencies,
            critical_path=spec.critical_path,
            stage_executions=spec.stage_executions,
        )
        records.append(record)
    verify_manifest_records(records)
    gaps = detect_manifest_gaps(specs)
    return records, gaps


def detect_manifest_gaps(specs: Iterable[ManifestArtifactSpec]) -> list[dict[str, object]]:
    specs_by_id = {spec.artifact_id: spec for spec in specs}
    gaps: list[dict[str, object]] = []

    for spec in specs:
        for dependency in spec.dependencies:
            if dependency not in specs_by_id:
                gaps.append(
                    {
                        "artifact_id": spec.artifact_id,
                        "issue": "missing_dependency",
                        "details": f"Dependency '{dependency}' is not defined in the manifest map.",
                        "blocked": True,
                    }
                )

    visited: set[str] = set()
    stack: list[str] = []

    def _visit(node: str) -> None:
        if node in stack:
            cycle_start = stack.index(node)
            cycle = stack[cycle_start:] + [node]
            gaps.append(
                {
                    "artifact_id": node,
                    "issue": "dependency_cycle",
                    "details": " -> ".join(cycle),
                    "blocked": True,
                }
            )
            return
        if node in visited:
            return
        stack.append(node)
        spec = specs_by_id.get(node)
        if spec:
            for dep in spec.dependencies:
                if dep in specs_by_id:
                    _visit(dep)
        stack.pop()
        visited.add(node)

    for artifact_id in specs_by_id:
        _visit(artifact_id)

    return gaps


def record_to_dict(record: ImplementationBlueprintRecord) -> dict[str, object]:
    return {
        "artifact_path": record.artifact_path.as_posix(),
        "artifact_sha256": record.artifact_sha256,
        "target_repo_path": record.target_repo_path.as_posix(),
        "owner": record.owner.value,
        "status": record.status.value,
        "evidence_refs": [str(ref) for ref in record.evidence_refs],
        "dependencies": list(record.dependencies),
        "critical_path": record.critical_path,
        "stage_executions": [
            {
                "run_id": str(entry.run_id),
                "lane_id": entry.lane_id.value,
                "stage_key": entry.stage_key.value,
                "status": entry.status.value,
                "started_at": entry.started_at.isoformat(),
                "completed_at": entry.completed_at.isoformat() if entry.completed_at else None,
                "token_usage": entry.token_usage,
                "telemetry_refs": [str(token) for token in entry.telemetry_refs],
                "residency_ledger_id": str(entry.residency_ledger_id) if entry.residency_ledger_id else None,
            }
            for entry in record.stage_executions
        ],
    }


def sign_manifest_records(records: Sequence[ImplementationBlueprintRecord]) -> list[dict[str, object]]:
    signed: list[dict[str, object]] = []
    for record in records:
        payload = record_to_dict(record)
        payload["signed_at"] = datetime.now(timezone.utc).isoformat()
        payload_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        payload["record_hash"] = payload_hash
        signed.append(payload)
    return signed


def verify_manifest_records(records: Sequence[ImplementationBlueprintRecord]) -> None:
    for record in records:
        artifact = Path.cwd() / record.artifact_path
        if not artifact.exists():
            raise FileNotFoundError(f"Manifest artifact missing: {artifact}")
        calculated = _sha256(artifact)
        if calculated != record.artifact_sha256:
            raise ValueError(
                f"Manifest hash mismatch for {artifact}; expected {record.artifact_sha256}, got {calculated}"
            )


def write_manifest(path: Path, records: Sequence[ImplementationBlueprintRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    signed = sign_manifest_records(records)
    with path.open("w", encoding="utf-8") as handle:
        for record in signed:
            handle.write(json.dumps(record, separators=(",", ":")) + "\n")


def write_manifest_gaps(path: Path, gaps: Sequence[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(list(gaps), handle, separators=(",", ":"), ensure_ascii=False)
