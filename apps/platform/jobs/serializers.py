from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Optional, Protocol, cast

from django.conf import settings
from rest_framework import serializers
from rest_framework.fields import CharField, SerializerMethodField

from apps.platform.authorization.capabilities import has_capability
from apps.platform.jobs.models import Job
from apps.platform.jobs.telemetry import JobTelemetry, job_telemetry
from packages.udocket_core.json_utils import stringify_pretty


AGENT_LABELS = {
    "transcription": "Transcribe",
    "transcribe": "Transcribe",
    "summary": "Analyze",
    "analyze": "Analyze",
    "timeline": "Timeline",
    "events": "Timeline",
    "graph": "Relationships",
    "relationship": "Relationships",
    "relationships": "Relationships",
}


class JobLike(Protocol):
    id: Any
    case_id: Any
    status: Any
    upload_progress: Any
    mode: str
    language: str
    diarization: bool
    duration_s: Optional[float]
    created_at: Any
    started_at: Any
    finished_at: Any
    error_message: Optional[str]
    transcript_path: Optional[str]


class JobTelemetrySerializer(serializers.Serializer):
    """Enriched job diagnostics payload mirroring worker metadata."""

    # DRF injects `context` at runtime; annotate for type-checkers
    context: Dict[str, Any]

    def to_representation(self, instance: JobLike) -> Dict[str, Any]:
        request = self.context.get("request") if hasattr(self, "context") else None
        ui_mode = bool(self.context.get("ui_mode"))
        user = getattr(request, "user", None)
        dev_open = bool(getattr(settings, "PLATFORM_DEV_OPEN", True))

        allow_audio = dev_open or ui_mode
        allow_transcript = dev_open or ui_mode
        case_id = str(getattr(instance, "case_id", "")) if instance else ""

        if user and getattr(user, "is_authenticated", False) and case_id:
            if not ui_mode:
                allow_audio = has_capability(user, case_id, "artifact.download")
                allow_transcript = has_capability(user, case_id, "artifact.view")
                # Only enforce transcript path capability outside of UI mode
                if allow_transcript and not has_capability(user, case_id, "artifact.field.path.view"):
                    # permit metadata but not raw path
                    allow_transcript_path = False
                else:
                    allow_transcript_path = allow_transcript
            else:
                # In UI mode, mirror allow_transcript and show paths to streamline diagnostics
                allow_transcript_path = allow_transcript
        else:
            allow_transcript_path = allow_transcript
            if not dev_open:
                allow_audio = False
                allow_transcript = False
                allow_transcript_path = False

        telem: JobTelemetry = job_telemetry(cast(Job, instance))
        audio_payload: Dict[str, Any] = telem.audio_payload(include_paths=allow_audio)
        transcript_payload: Dict[str, Any] = telem.transcript_payload(include_paths=allow_transcript_path)
        agent_payload: Dict[str, Any] = telem.agent_payload()
        meta_payload: Dict[str, Any] = dict(telem.meta)
        # Enrich with availability flags for UI gating (e.g., converted WAV download)
        converted_available = False
        converted_job_id = meta_payload.get("converted_audio_job_id") or meta_payload.get("converted_wav_job_id")
        if converted_job_id:
            try:
                converted_job = Job.objects.only("audio_input", "case_id").get(pk=converted_job_id)
                if (
                    str(converted_job.case_id) == str(instance.case_id)
                    and converted_job.audio_input
                ):
                    try:
                        path_candidate = Path(converted_job.audio_input)
                        converted_available = path_candidate.exists()
                        if converted_available:
                            meta_payload.setdefault("converted_wav_path", str(path_candidate))
                    except Exception:
                        converted_available = False
            except Job.DoesNotExist:
                converted_available = False
        if not converted_available:
            try:
                conv_path = meta_payload.get("converted_wav_path")
                if isinstance(conv_path, str) and conv_path:
                    converted_available = Path(conv_path).exists()
            except Exception:
                converted_available = False
        meta_payload["converted_wav_available"] = converted_available

        agent_type = (
            meta_payload.get("agent_type")
            or meta_payload.get("agent_name")
            or meta_payload.get("agent")
            or agent_payload.get("type")
        )
        if not agent_type:
            mode = getattr(instance, "mode", "") or ""
            if mode in (getattr(Job.Mode, "ON_DEMAND", "on-demand"), getattr(Job.Mode, "BATCH", "batch")):
                agent_type = "Transcription"
            elif mode:
                agent_type = mode.replace("_", " ").replace("-", " ").title()
        normalized_agent_type = str(agent_type or "").strip().lower()
        agent_label = None
        meta_agent_label = meta_payload.get("agent_label")
        if isinstance(meta_agent_label, str) and meta_agent_label.strip():
            agent_label = meta_agent_label.strip()
        if not agent_label:
            agent_label = AGENT_LABELS.get(normalized_agent_type)
        if not agent_label and agent_type:
            agent_label = str(agent_type).strip() or None
        if not agent_label and normalized_agent_type:
            agent_label = normalized_agent_type.replace("_", " ").title()
        if not agent_label:
            agent_label = "Unknown"
        agent_payload["type"] = agent_type or "Unknown"
        agent_payload["label"] = agent_label

        if meta_payload:
            if not allow_audio:
                for key in list(meta_payload.keys()):
                    lower = key.lower()
                    if "audio" in lower and "path" in lower:
                        meta_payload.pop(key)
            if not allow_transcript_path:
                for key in list(meta_payload.keys()):
                    lower = key.lower()
                    if "transcript" in lower and "path" in lower:
                        meta_payload.pop(key)

        error_message = instance.error_message
        if error_message and not allow_transcript and not allow_audio:
            # expose minimal error when user lacks artifact rights
            error_message = "Restricted"

        data: Dict[str, Any] = {
            "id": str(instance.id),
            "case_id": str(instance.case_id),
            "status": instance.status,
            "upload_progress": instance.upload_progress,
            "progress_percent": instance.upload_progress,
            "mode": instance.mode,
            "language": instance.language,
            "diarization": instance.diarization,
            "duration_s": instance.duration_s,
            "created_at": instance.created_at,
            "started_at": instance.started_at,
            "finished_at": instance.finished_at,
            "review_status": getattr(instance, "review_status", None),
            "reviewed_at": getattr(instance, "reviewed_at", None),
            "error_message": error_message,
            "audio": audio_payload if (allow_audio or any(audio_payload.values())) else None,
            "transcript": transcript_payload if allow_transcript else None,
            "agent": agent_payload,
            "artifacts": [],
            "agent_label": agent_label,
            "review_comment": getattr(instance, "review_comment", ""),
            "review_activity_id": getattr(instance, "review_activity_id", None),
        }

        reviewer = getattr(instance, "reviewed_by", None)
        if reviewer:
            reviewer_label = (
                getattr(reviewer, "display_name", None)
                or reviewer.get_full_name()
                or getattr(reviewer, "email", None)
                or getattr(reviewer, "username", None)
            )
            data["reviewed_by"] = {
                "id": str(reviewer.pk),
                "label": reviewer_label,
            }
        else:
            data["reviewed_by"] = None

        if allow_transcript:
            transcript_entry: Dict[str, Any] = {
                "type": transcript_payload.get("artifact_type", "TRANSCRIPT"),
                "path": transcript_payload.get("path") if allow_transcript_path else None,
                "download_url": None,
                "title": None,
            }
            # Only expose a download link when a transcript exists and job succeeded
            has_transcript = bool(getattr(instance, "transcript_path", None)) or bool(transcript_payload.get("path"))
            if allow_audio and request is not None and has_transcript and str(instance.status).upper() == "SUCCEEDED":
                try:
                    from rest_framework.reverse import reverse

                    download_href = reverse("job-download", kwargs={"pk": str(instance.id)}, request=request)
                    transcript_entry["download_url"] = download_href
                except Exception:
                    transcript_entry["download_url"] = None
            transcript_entry["title"] = transcript_payload.get("title")
            data["artifacts"].append(transcript_entry)

        log_excerpt = telem.log_excerpt()
        if log_excerpt:
            data["log_excerpt"] = log_excerpt

        data["metadata"] = meta_payload or None
        if meta_payload:
            data["metadata_pretty"] = stringify_pretty(meta_payload)
        else:
            data["metadata_pretty"] = None

        return data


class JobCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = [
            "case",
            "audio_input",
            "mode",
            "diarization",
            "language",
        ]


class JobSerializer(serializers.ModelSerializer):
    # DRF injects this at runtime
    context: Dict[str, Any]
    case_id: CharField = CharField(read_only=True)
    audio_input: SerializerMethodField = SerializerMethodField()
    transcript_path: SerializerMethodField = SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            "id",
            "case",
            "case_id",
            "audio_input",
            "mode",
            "diarization",
            "language",
            "status",
            "upload_progress",
            "error_message",
            "transcript_path",
            "duration_s",
            "created_at",
            "started_at",
            "finished_at",
        ]
        read_only_fields = [
            "status",
            "upload_progress",
            "error_message",
            "transcript_path",
            "duration_s",
            "created_at",
            "started_at",
            "finished_at",
        ]

    def get_audio_input(self, obj: Job) -> str | None:
        request = self.context.get("request") if hasattr(self, "context") else None
        user = getattr(request, "user", None)
        dev_open = bool(getattr(settings, "PLATFORM_DEV_OPEN", True))
        if not user or not getattr(user, "is_authenticated", False):
            return obj.audio_input if dev_open else None
        case_id = str(getattr(obj, "case_id", ""))
        if case_id and has_capability(user, case_id, "artifact.download"):
            return obj.audio_input
        return None

    def get_transcript_path(self, obj: Job) -> str | None:
        request = self.context.get("request") if hasattr(self, "context") else None
        user = getattr(request, "user", None)
        dev_open = bool(getattr(settings, "PLATFORM_DEV_OPEN", True))
        if not user or not getattr(user, "is_authenticated", False):
            return obj.transcript_path or None if dev_open else None
        case_id = str(getattr(obj, "case_id", ""))
        if case_id and has_capability(user, case_id, "artifact.field.path.view"):
            return obj.transcript_path or None
        return None
