from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .common import AnalysisArtifact, ensure_dir, next_versioned, parse_transcript, sha256_file


@dataclass(frozen=True)
class TimelineConfig:
    """Lightweight configuration for timeline generation."""

    schema_version: str = "v1"

    @classmethod
    def from_env(cls) -> "TimelineConfig":  # pragma: no cover - future expansion hook
        return cls()


@dataclass(frozen=True)
class TimelineEvent:
    ts_start: float
    ts_end: Optional[float]
    speaker: Optional[str]
    text: str
    labels: Tuple[str, ...] = ()

    def to_json(self) -> Dict[str, Any]:
        return {
            "ts_start": self.ts_start,
            "ts_end": self.ts_end,
            "speaker": self.speaker,
            "text": self.text,
            "labels": list(self.labels),
        }

    @staticmethod
    def _coerce_ts(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed >= 0 else None

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> Optional["TimelineEvent"]:
        if not isinstance(payload, dict):
            return None
        text = str(payload.get("text") or "").strip()
        if not text:
            return None
        ts_start = cls._coerce_ts(payload.get("ts_start"))
        if ts_start is None:
            return None
        ts_end = cls._coerce_ts(payload.get("ts_end"))
        speaker_val = payload.get("speaker")
        speaker = str(speaker_val).strip() or None if speaker_val is not None else None
        labels_raw = payload.get("labels")
        labels: Tuple[str, ...]
        if isinstance(labels_raw, (list, tuple)):
            labels = tuple(str(label).strip() for label in labels_raw if str(label).strip())
        else:
            labels = ()
        return cls(ts_start=ts_start, ts_end=ts_end, speaker=speaker, text=text, labels=labels)


@dataclass(frozen=True)
class TimelineResult:
    status: str
    timeline_file: Path
    events: Tuple[TimelineEvent, ...]
    checksum: str
    source_transcript: Path
    seed_source: Optional[Path]
    meta_json: Path
    audit_jsonl: Path
    artifacts: Tuple[AnalysisArtifact, ...]


class TimelineAgent:
    def __init__(self, config: Optional[TimelineConfig] = None) -> None:
        self.config = config or TimelineConfig.from_env()

    def build(
        self,
        *,
        case_id: str,
        case_dir: Path,
        job_id: str,
        transcript_path: Path,
        seed_path: Optional[Path] = None,
        seed_events: Optional[Sequence[Dict[str, Any]]] = None,
    ) -> TimelineResult:
        transcript_path = Path(transcript_path)
        if not transcript_path.exists():
            raise FileNotFoundError(f"Transcript not found at {transcript_path}")

        analysis_dir = case_dir / "analysis"
        ops_dir = case_dir / "ops"
        ensure_dir(analysis_dir)
        ensure_dir(ops_dir)

        events = self._resolve_events(transcript_path, seed_path, seed_events)
        timeline_path = next_versioned(analysis_dir / f"{job_id}__timeline_{self.config.schema_version}.json")
        timeline_payload = [event.to_json() for event in events]
        timeline_path.write_text(
            json.dumps(timeline_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        checksum = sha256_file(timeline_path)
        timestamp = (
            datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z")
        )
        meta: Dict[str, Any] = {
            "case_id": case_id,
            "job_id": job_id,
            "timeline_file": timeline_path.name,
            "timeline_path": str(timeline_path),
            "checksum": checksum,
            "events": len(events),
            "source_transcript": str(transcript_path),
            "schema_version": self.config.schema_version,
            "ts": timestamp,
            "status": "ok",
        }
        if seed_path:
            meta["seed_source"] = str(seed_path)

        meta_path = ops_dir / f"{job_id}__timeline_log.json"
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        audit_path = ops_dir / "ops_timeline.jsonl"
        audit_payload = {
            "ts": timestamp,
            "case_id": case_id,
            "job_id": job_id,
            "timeline_file": str(timeline_path),
            "events": len(events),
        }
        if seed_path:
            audit_payload["seed_source"] = str(seed_path)

        with audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(audit_payload, ensure_ascii=False) + "\n")

        artifact = AnalysisArtifact(
            kind="timeline",
            path=timeline_path,
            checksum=checksum,
            metadata={"events": len(events), "source_transcript": str(transcript_path)},
        )

        return TimelineResult(
            status="ok",
            timeline_file=timeline_path,
            events=tuple(events),
            checksum=checksum,
            source_transcript=transcript_path,
            seed_source=seed_path,
            meta_json=meta_path,
            audit_jsonl=audit_path,
            artifacts=(artifact,),
        )

    def _resolve_events(
        self,
        transcript_path: Path,
        seed_path: Optional[Path],
        seed_events: Optional[Sequence[Dict[str, Any]]],
    ) -> List[TimelineEvent]:
        seed_payload: List[TimelineEvent] = []
        if seed_events:
            for raw in seed_events:
                event = TimelineEvent.from_dict(raw)
                if event is not None:
                    seed_payload.append(event)
        elif seed_path and seed_path.exists():
            try:
                payload: Any = json.loads(seed_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict) and "events" in payload:
                payload = payload.get("events")
            if isinstance(payload, Iterable):
                for item in payload:
                    if isinstance(item, dict):
                        event = TimelineEvent.from_dict(item)
                        if event is not None:
                            seed_payload.append(event)

        if seed_payload:
            return sorted(seed_payload, key=lambda evt: (evt.ts_start, evt.ts_end or evt.ts_start))

        parsed = parse_transcript(transcript_path)
        fallback: List[TimelineEvent] = []
        for segment in parsed.segments:
            if segment.ts is None:
                continue
            text = segment.text.strip()
            if not text:
                continue
            fallback.append(
                TimelineEvent(
                    ts_start=float(segment.ts),
                    ts_end=None,
                    speaker=segment.speaker,
                    text=text,
                    labels=(),
                )
            )
        return fallback


__all__ = [
    "TimelineAgent",
    "TimelineConfig",
    "TimelineEvent",
    "TimelineResult",
]

