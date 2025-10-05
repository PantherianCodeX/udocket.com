from __future__ import annotations

"""Helpers to derive enriched job telemetry for UI and API consumers."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional
import hashlib

from django.utils.functional import cached_property

from apps.platform.jobs.models import Job
from apps.platform.operations.storage import ops_dir as storage_ops_dir
from packages.udocket_core.json_utils import read_json_object


def _ops_json_path(job: Job) -> Path:
    return storage_ops_dir(str(job.case_id), job.organization_id) / f"{job.id}_transcription_log.json"


def _ops_log_path(job: Job) -> Path:
    return storage_ops_dir(str(job.case_id), job.organization_id) / f"{job.id}_transcription.log"


def _safe_json_load(path: Path) -> Dict[str, Any]:
    return read_json_object(path)


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
        sha256 = meta.get("audio_sha256")
        remote_sha = meta.get("audio_sha256_remote")
        size_remote = meta.get("audio_size_bytes_remote") or meta.get("audio_size_bytes")
        local_sha = None
        local_size = None
        local_path: Optional[Path] = None
        local_probe: Dict[str, Any] = {}
        if include_paths and audio_input and isinstance(audio_input, str) and audio_input.startswith("/"):
            local_path = Path(audio_input)
            if local_path.exists():
                local_size = local_path.stat().st_size
                if not sha256 and not remote_sha:
                    local_sha = _sha256_file(local_path)
                # Opportunistically probe audio characteristics if not present in metadata
                try:
                    from packages.udocket_core.audio import probe_audio_metadata as _probe

                    probe = _probe(local_path)
                except Exception:
                    probe = {}
                if isinstance(probe, dict):
                    local_probe = probe
        return {
            "path": audio_input,
            "original_name": _original_audio_name(self.job.audio_input) or meta.get("audio_file"),
            "sha256": sha256 or remote_sha or local_sha,
            "remote_sha256": remote_sha or sha256,
            "content_md5_b64": meta.get("audio_content_md5_b64"),
            "size_bytes_remote": size_remote or local_size,
            "size_bytes_local": local_size,
            "duration_s": local_probe.get("audio_duration_s") or meta.get("audio_duration_s") or self.job.duration_s,
            "sample_rate_hz": local_probe.get("audio_sample_rate_hz") or meta.get("audio_sample_rate_hz") or meta.get("sample_rate_hz"),
            "channels": local_probe.get("audio_channels") or meta.get("audio_channels") or meta.get("channels"),
            "bitrate_kbps": local_probe.get("audio_bitrate_kbps") or meta.get("audio_bitrate_kbps") or meta.get("bitrate_kbps"),
            "codec": local_probe.get("audio_codec") or meta.get("audio_codec"),
            "channel_layout": local_probe.get("audio_channel_layout") or meta.get("audio_channel_layout"),
            "mime": meta.get("audio_mime"),
        }

    def transcript_payload(self, *, include_paths: bool) -> Dict[str, Any]:
        meta = self.meta
        transcript_path = self.job.transcript_path if include_paths else None
        transcript_sha = meta.get("transcript_sha256")
        transcript_bytes = meta.get("transcript_bytes")
        avg_conf = meta.get("avg_confidence")
        avg_conf_pct = None
        try:
            if isinstance(avg_conf, (int, float)):
                avg_conf_pct = float(avg_conf) * 100.0
        except Exception:
            avg_conf_pct = None
        if include_paths and transcript_path:
            path = Path(transcript_path)
            if path.exists():
                if transcript_bytes is None:
                    transcript_bytes = path.stat().st_size
                if not transcript_sha:
                    transcript_sha = _sha256_file(path)
        return {
            "path": transcript_path,
            "sha256": transcript_sha,
            "words": meta.get("word_count") or meta.get("transcript_words"),
            "bytes": transcript_bytes,
            "segments": meta.get("segments"),
            "avg_confidence": avg_conf,
            "avg_confidence_pct": avg_conf_pct,
            "language": meta.get("language") or self.job.language,
            "artifact_type": "TRANSCRIPT",
            "title": meta.get("transcript_title"),
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


def analyze_jobs(jobs: Iterable[Job]) -> Dict[str, Any]:
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
        elif status == Job.Status.CANCELLED:
            summary["failed"] += 1
        elif status in (Job.Status.RUNNING, Job.Status.UPLOADING, Job.Status.CANCELLING):
            summary["running"] += 1
        else:
            summary["pending"] += 1
        timestamp = job.finished_at or job.started_at or job.created_at
        if timestamp is not None:
            existing = summary["last_update"]
            if existing is None or timestamp > existing:
                summary["last_update"] = timestamp
    return summary


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
