from __future__ import annotations

"""Helpers to derive enriched job telemetry for UI and API consumers."""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from django.utils.functional import cached_property

from apps.platform.jobs.models import Job
from apps.platform.operations.storage import ops_dir as storage_ops_dir


def _ops_json_path(job: Job) -> Path:
    return storage_ops_dir(str(job.case_id), job.organization_id) / f"{job.id}_transcription_log.json"


def _ops_log_path(job: Job) -> Path:
    return storage_ops_dir(str(job.case_id), job.organization_id) / f"{job.id}_transcription.log"


def _safe_json_load(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _safe_text_load(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return None


def _original_audio_name(audio_input: str | None) -> Optional[str]:
    if not audio_input:
        return None
    try:
        base = str(audio_input).rstrip("/\\")
        name = base.split("/")[-1].split("\\")[-1]
        if "__" in name:
            after = name.split("__", 1)[-1]
            return after or name
        return name
    except Exception:
        return None


@dataclass
class JobTelemetry:
    job: Job

    @cached_property
    def meta(self) -> Dict[str, Any]:
        return _safe_json_load(_ops_json_path(self.job))

    @cached_property
    def log_text(self) -> Optional[str]:
        return _safe_text_load(_ops_log_path(self.job))

    def audio_payload(self, *, include_paths: bool) -> Dict[str, Any]:
        audio_input = self.job.audio_input if include_paths else None
        meta = self.meta
        return {
            "path": audio_input,
            "original_name": _original_audio_name(self.job.audio_input),
            "sha256": meta.get("audio_sha256"),
            "remote_sha256": meta.get("audio_sha256_remote"),
            "content_md5_b64": meta.get("audio_content_md5_b64"),
            "size_bytes_remote": meta.get("audio_size_bytes_remote"),
            "duration_s": meta.get("audio_duration_s") or self.job.duration_s,
            "sample_rate_hz": meta.get("sample_rate_hz"),
            "channels": meta.get("audio_channels"),
            "bitrate_kbps": meta.get("audio_bitrate_kbps"),
            "mime": meta.get("audio_mime"),
        }

    def transcript_payload(self, *, include_paths: bool) -> Dict[str, Any]:
        meta = self.meta
        transcript_path = self.job.transcript_path if include_paths else None
        return {
            "path": transcript_path,
            "sha256": meta.get("transcript_sha256"),
            "words": meta.get("word_count") or meta.get("transcript_words"),
            "bytes": meta.get("transcript_bytes"),
            "segments": meta.get("segments"),
            "avg_confidence": meta.get("avg_confidence"),
            "language": meta.get("language") or self.job.language,
            "artifact_type": "TRANSCRIPT",
        }

    def agent_payload(self) -> Dict[str, Any]:
        meta = self.meta
        return {
            "status": meta.get("status"),
            "attempts_used": meta.get("attempts_used"),
            "region": meta.get("azure_region"),
            "diarization_enabled": meta.get("diarization_enabled"),
            "diarization_speakers": meta.get("num_speakers"),
            "azure_transcription_url": meta.get("azure_transcription_url"),
            "timestamp_utc": meta.get("timestamp_utc"),
        }

    def log_excerpt(self) -> Optional[str]:
        text = self.log_text
        if not text:
            return None
        sample = text.strip().splitlines()[-20:]
        return "\n".join(sample) if sample else text


def job_telemetry(job: Job) -> JobTelemetry:
    if isinstance(job, JobTelemetry):  # pragma: no cover - defensive
        return job
    if hasattr(job, "_telemetry"):
        return getattr(job, "_telemetry")
    payload = JobTelemetry(job=job)
    setattr(job, "_telemetry", payload)
    return payload


def summarize_jobs(jobs: Iterable[Job]) -> Dict[str, Any]:
    summary = {
        "total": 0,
        "succeeded": 0,
        "failed": 0,
        "running": 0,
        "pending": 0,
        "last_update": None,
    }
    for job in jobs:
        summary["total"] += 1
        status = job.status
        if status == Job.Status.SUCCEEDED:
            summary["succeeded"] += 1
        elif status == Job.Status.FAILED:
            summary["failed"] += 1
        elif status == Job.Status.RUNNING:
            summary["running"] += 1
        else:
            summary["pending"] += 1
        timestamp = job.finished_at or job.started_at or job.created_at
        if timestamp is not None:
            existing = summary["last_update"]
            if existing is None or timestamp > existing:
                summary["last_update"] = timestamp
    return summary
