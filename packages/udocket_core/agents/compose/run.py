from __future__ import annotations

# pyright: strict

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, cast

from ...utils.json import JSONObject, JSONValue, coerce_json_object, coerce_str

from .logging_utils import ComposeLogContext, format_run_message

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
    log_context: ComposeLogContext = field(default_factory=lambda: ComposeLogContext(case_id="unknown", job_id="unknown"))
    enabled: bool = True
    _sequence: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self._sequence = self._discover_latest_sequence()
        if self.log_context.case_id == "unknown":
            self.log_context = ComposeLogContext(case_id=self.case_id, job_id=self.job_id)

    def _log_event(self, level: int, event: str, extra: Mapping[str, object] | None = None) -> None:
        payload: dict[str, object] = {"case_id": self.case_id, "job_id": self.job_id}
        if extra:
            payload.update(dict(extra))
        try:
            serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
            message = format_run_message(self.log_context, event, payload)
            self.logger.log(
                level,
                message,
                extra={
                    "compose": payload,
                    "event": event,
                    "component": "compose.run",
                    "serialized": serialized,
                },
            )
        except Exception:  # pragma: no cover - defensive
            self.logger.debug("compose.run.logging_failed", exc_info=True)

    def reset(self) -> None:
        """Remove existing snapshots when starting a fresh run."""
        if not self.snapshot_dir.exists():
            self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self._log_event(logging.INFO, "compose.run.reset_begin", {"snapshot_dir": str(self.snapshot_dir)})
        for path in self.snapshot_dir.glob("*.json"):
            try:
                path.unlink()
            except Exception:
                self._log_event(logging.DEBUG, "compose.run.reset_failed", {"path": str(path)})
        self._sequence = 0
        self._log_event(logging.INFO, "compose.run.reset_complete", {"snapshot_dir": str(self.snapshot_dir)})

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
            self._log_event(logging.WARNING, "compose.run.snapshot_failed", {"stage": stage, "path": str(target)})
            return
        timestamp = coerce_str(envelope.get("timestamp")) or datetime.now(tz=timezone.utc).isoformat()
        self._write_manifest(stage=stage, sequence=self._sequence, filename=filename, timestamp=timestamp)
        # self._log_event(logging.INFO, "compose.run.snapshot_recorded", {"stage": stage, "sequence": self._sequence, "path": str(target)})

    def restore_latest(self) -> ComposeRunSnapshot | None:
        manifest_path = self.snapshot_dir / LATEST_MANIFEST
        if not manifest_path.exists():
            self._log_event(logging.DEBUG, "compose.run.restore_manifest_missing", {"snapshot_dir": str(self.snapshot_dir)})
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
            self._log_event(logging.WARNING, "compose.run.manifest_read_failed", {"path": str(manifest_path)})
            return None
        filename = coerce_str(manifest.get("path")) or ""
        if not filename:
            self._log_event(logging.DEBUG, "compose.run.restore_manifest_empty", {"path": str(manifest_path)})
            return None
        snapshot_path = self.snapshot_dir / filename
        if not snapshot_path.exists():
            self._log_event(logging.DEBUG, "compose.run.restore_snapshot_missing", {"path": str(snapshot_path)})
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
            self._log_event(logging.WARNING, "compose.run.snapshot_read_failed", {"path": str(snapshot_path)})
            return None
        state_payload = snapshot.get("state")
        if not isinstance(state_payload, Mapping):
            return None
        state = compose_state_from_json(coerce_json_object(state_payload))
        sequence = _int_from_json(manifest.get("sequence")) or _int_from_json(snapshot.get("sequence"))
        stage = coerce_str(manifest.get("stage")) or coerce_str(snapshot.get("stage")) or "unknown"
        self._sequence = max(self._sequence, sequence)
        self._log_event(
            logging.INFO,
            "compose.run.snapshot_restored",
            {"stage": stage, "sequence": sequence, "path": str(snapshot_path)},
        )
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
            self._log_event(logging.DEBUG, "compose.run.manifest_write_failed", {"path": str(manifest_path)})
        # else:
        #     self._log_event(
        #         logging.INFO,
        #         "compose.run.manifest_written",
        #         {"stage": stage, "sequence": sequence, "path": str(manifest_path)},
        #     )

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
