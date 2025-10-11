from __future__ import annotations

# pyright: strict

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, cast

from packages.udocket_core.json_utils import JSONObject, JSONValue, coerce_json_object, coerce_str

from .state import ComposeState, compose_state_from_json, serialize_compose_state

LATEST_MANIFEST = "latest.json"


@dataclass(slots=True)
class ComposeRunSnapshot:
    stage: str
    sequence: int
    path: Path
    state: ComposeState


@dataclass(slots=True)
class ComposeRun:
    case_id: str
    job_id: str
    snapshot_dir: Path
    logger: logging.Logger
    enabled: bool = True
    _sequence: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self._sequence = self._discover_latest_sequence()

    def reset(self) -> None:
        """Remove existing snapshots when starting a fresh run."""
        if not self.snapshot_dir.exists():
            self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        for path in self.snapshot_dir.glob("*.json"):
            try:
                path.unlink()
            except Exception:
                self.logger.debug(
                    "compose.run.reset.failed",
                    extra={"path": str(path)},
                    exc_info=True,
                )
        self._sequence = 0

    def record(self, stage: str, state: ComposeState) -> None:
        if not self.enabled:
            return
        self._sequence += 1
        snapshot_payload = serialize_compose_state(state)
        envelope: JSONObject = {
            "case_id": self.case_id,
            "job_id": self.job_id,
            "stage": stage,
            "sequence": self._sequence,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "state": snapshot_payload,
        }
        filename = f"{self._sequence:04d}_{stage.replace('.', '-')}.json"
        target = self.snapshot_dir / filename
        try:
            target.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            self.logger.warning(
                "compose.run.snapshot_failed",
                extra={"stage": stage, "path": str(target)},
                exc_info=True,
            )
            return
        timestamp = coerce_str(envelope.get("timestamp")) or datetime.now(tz=timezone.utc).isoformat()
        self._write_manifest(stage=stage, sequence=self._sequence, filename=filename, timestamp=timestamp)

    def restore_latest(self) -> ComposeRunSnapshot | None:
        manifest_path = self.snapshot_dir / LATEST_MANIFEST
        if not manifest_path.exists():
            return None
        try:
            manifest_raw = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest_map: dict[str, JSONValue] = {}
            if isinstance(manifest_raw, Mapping):
                manifest_mapping = cast(Mapping[Any, Any], manifest_raw)
                for key, value in manifest_mapping.items():
                    manifest_map[str(key)] = cast(JSONValue, value)
            manifest = coerce_json_object(manifest_map)
        except Exception:
            self.logger.warning(
                "compose.run.manifest_read_failed",
                extra={"path": str(manifest_path)},
                exc_info=True,
            )
            return None
        filename = coerce_str(manifest.get("path")) or ""
        if not filename:
            return None
        snapshot_path = self.snapshot_dir / filename
        if not snapshot_path.exists():
            return None
        try:
            snapshot_raw = json.loads(snapshot_path.read_text(encoding="utf-8"))
            snapshot_map: dict[str, JSONValue] = {}
            if isinstance(snapshot_raw, Mapping):
                snapshot_mapping = cast(Mapping[Any, Any], snapshot_raw)
                for key, value in snapshot_mapping.items():
                    snapshot_map[str(key)] = cast(JSONValue, value)
            snapshot = coerce_json_object(snapshot_map)
        except Exception:
            self.logger.warning(
                "compose.run.snapshot_read_failed",
                extra={"path": str(snapshot_path)},
                exc_info=True,
            )
            return None
        state_payload = snapshot.get("state")
        if not isinstance(state_payload, Mapping):
            return None
        state = compose_state_from_json(coerce_json_object(state_payload))
        sequence = _int_from_json(manifest.get("sequence")) or _int_from_json(snapshot.get("sequence"))
        stage = coerce_str(manifest.get("stage")) or coerce_str(snapshot.get("stage")) or "unknown"
        self._sequence = max(self._sequence, sequence)
        return ComposeRunSnapshot(stage=stage, sequence=sequence, path=snapshot_path, state=state)

    def _write_manifest(self, *, stage: str, sequence: int, filename: str, timestamp: str) -> None:
        manifest_path = self.snapshot_dir / LATEST_MANIFEST
        payload: JSONObject = {
            "case_id": self.case_id,
            "job_id": self.job_id,
            "stage": stage,
            "sequence": sequence,
            "path": filename,
            "timestamp": timestamp,
        }
        try:
            manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            self.logger.debug(
                "compose.run.manifest_write_failed",
                extra={"path": str(manifest_path)},
                exc_info=True,
            )

    def _discover_latest_sequence(self) -> int:
        max_sequence = 0
        for path in self.snapshot_dir.glob("*.json"):
            if path.name == LATEST_MANIFEST:
                continue
            prefix = path.stem.split("_", 1)[0]
            try:
                candidate = int(prefix)
            except ValueError:
                continue
            if candidate > max_sequence:
                max_sequence = candidate
        return max_sequence


def _int_from_json(value: JSONValue | None) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return 0
    return 0


__all__ = ["ComposeRun", "ComposeRunSnapshot"]
