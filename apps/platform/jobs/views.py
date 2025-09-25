from __future__ import annotations

import json
import hashlib
import logging
import os
import uuid
from typing import Any, Dict, Iterable, Optional, Set

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from apps.platform.authorization.access_policies import JobAccessPolicy
from django.conf import settings
from rest_framework.response import Response
from django.http import FileResponse, Http404
import requests

log = logging.getLogger("apps.platform.jobs.views")
from pathlib import Path

from apps.platform.authorization.capabilities import has_capability
from apps.platform.artifacts.models import CaseArtifact
from apps.platform.cases.models import Case
from apps.platform.jobs.models import Job
from apps.platform.jobs.serializers import (
    JobCreateSerializer,
    JobSerializer,
    JobTelemetrySerializer,
)
from apps.platform.jobs.telemetry import job_telemetry
from apps.platform.config.celery import app as celery_app
from apps.platform.operations.tasks import transcribe_job
from apps.platform.operations.channels import send_job_update
from apps.platform.operations.audit import emit as audit_emit
from django.db import transaction
from apps.platform.operations.tasks import summarize_job, timeline_job, graph_job
from apps.platform.tenancy import scope_jobs
from apps.platform.operations.storage import ensure_case_dirs, ops_dir as storage_ops_dir
from apps.platform.operations.utils import update_job_meta, append_job_log
from apps.platform.operations.models import TaskRun
from packages.udocket_core.audio import probe_audio_metadata


def _derive_audio_filename(path_obj: Path | None, meta: Dict[str, Any], fallback: str) -> str:
    def _clean(value: Any) -> str:
        if not isinstance(value, str):
            return ""
        candidate = value.strip()
        if not candidate:
            return ""
        candidate = candidate.split("?")[0].split("#")[0].rstrip("/\\")
        candidate = candidate.split("/")[-1].split("\\")[-1]
        return candidate

    candidates: list[str] = []
    meta_keys = (
        "source_audio_file",
        "audio_file",
        "original_audio_file",
        "original_file",
        "original_name",
        "converted_audio_file",
    )
    for key in meta_keys:
        cleaned = _clean(meta.get(key))
        if cleaned:
            candidates.append(cleaned)

    if path_obj is not None:
        name = path_obj.name
        if "__" in name:
            cleaned = _clean(name.split("__", 1)[-1])
            if cleaned:
                candidates.append(cleaned)
        cleaned_base = _clean(name)
        if cleaned_base:
            candidates.append(cleaned_base)

    cleaned_fallback = _clean(fallback)
    if cleaned_fallback:
        candidates.append(cleaned_fallback)

    for candidate in candidates:
        if candidate:
            return candidate
    return fallback or "audio"


def _sha256_file(path: Path) -> Optional[str]:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except Exception:
        return None


class JobViewSet(viewsets.ModelViewSet):
    queryset = Job.objects.all()
    serializer_class = JobSerializer
    permission_classes = [JobAccessPolicy]

    def get_serializer_class(self):  # type: ignore[override]
        if self.action in ("create", "transcribe"):
            return JobCreateSerializer
        return JobSerializer

    def get_queryset(self):  # type: ignore[override]
        qs = super().get_queryset().select_related("case", "case__organization", "reviewed_by")
        user = getattr(self.request, "user", None)
        return scope_jobs(qs, user)

    def create(self, request, *args, **kwargs):  # type: ignore[override]
        """Create a job and immediately enqueue transcription."""
        ser = JobCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data
        if v.get("diarization") and v.get("mode") != Job.Mode.BATCH:
            return Response({"detail": "Diarization is only supported in batch mode."}, status=status.HTTP_400_BAD_REQUEST)
        job = Job.objects.create(**v)
        audio_input_value = job.audio_input or ""
        force_wav_conversion = str(request.data.get("force_wav") or "").lower() in {"1", "true", "yes", "on"}
        # Enqueue task
        transcribe_job.delay(
            case_id=str(job.case_id),
            job_id=str(job.id),
            audio_input=job.audio_input,
            mode=job.mode,
            diarization=job.diarization,
            language=job.language,
            force_wav_conversion=force_wav_conversion,
        )
        out = JobSerializer(instance=job)
        headers = {"Location": f"/api/v1/jobs/{job.id}/"}
        audit_emit(
            request,
            case_id=str(job.case_id),
            event="job.created",
            data={"job_id": str(job.id), "mode": job.mode, "force_wav_conversion": force_wav_conversion},
        )
        return Response(out.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=["get"], url_path="status")
    def status(self, request, pk=None):
        """Lightweight status endpoint used by UI polling.

        Returns only fields required for live update to avoid heavy serialization
        and reduce the chance of serialization-related errors.
        """
        job = self.get_object()
        payload = {
            "id": str(job.id),
            "status": job.status,
            "upload_progress": job.upload_progress,
            "progress_percent": job.upload_progress,
            "transcript_path": job.transcript_path,
            "finished_at": job.finished_at,
            "review_status": job.review_status,
            "review_comment": job.review_comment,
            "reviewed_at": job.reviewed_at,
            "reviewed_by": self._user_label(job.reviewed_by),
            "review_activity_id": str(job.review_activity_id) if job.review_activity_id else None,
        }
        return Response(payload)

    @action(detail=False, methods=["get"], url_path="status/bulk")
    def bulk_status(self, request):
        """Return status payloads for multiple jobs in a single response.

        Expects a comma-delimited ``ids`` query parameter and respects tenancy
        constraints through ``scope_jobs``.
        """

        ids_param = (request.query_params.get("ids") or "").strip()
        if not ids_param:
            return Response({"detail": "Parameter 'ids' is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            job_ids = [uuid.UUID(part.strip()) for part in ids_param.split(",") if part.strip()]
        except (ValueError, AttributeError):
            return Response({"detail": "Parameter 'ids' must contain valid UUIDs."}, status=status.HTTP_400_BAD_REQUEST)

        if not job_ids:
            return Response([], status=status.HTTP_200_OK)

        qs = self.get_queryset().filter(pk__in=job_ids)
        case_id_param = request.query_params.get("case_id")
        if case_id_param:
            try:
                uuid.UUID(case_id_param)
            except ValueError:
                return Response({"detail": "Parameter 'case_id' must be a valid UUID."}, status=status.HTTP_400_BAD_REQUEST)
            qs = qs.filter(case_id=case_id_param)

        payloads: list[dict[str, Any]] = []
        for job in qs:
            payloads.append(
                {
                    "id": str(job.id),
                    "status": job.status,
                    "upload_progress": job.upload_progress,
                    "progress_percent": job.upload_progress,
                    "transcript_path": job.transcript_path,
                    "finished_at": job.finished_at,
                    "review_status": job.review_status,
                    "review_comment": job.review_comment,
                    "reviewed_at": job.reviewed_at,
                    "reviewed_by": self._user_label(job.reviewed_by),
                    "review_activity_id": str(job.review_activity_id) if job.review_activity_id else None,
                }
            )

        return Response(payloads)

    def _can_review(self, request, job: Job) -> bool:
        user = getattr(request, "user", None)
        if getattr(settings, "PLATFORM_DEV_OPEN", False):
            return True
        if not user or not getattr(user, "is_authenticated", False):
            return False
        if job.case.reviewer_id and str(user.id) == str(job.case.reviewer_id):
            return True
        return has_capability(user, str(job.case_id), "case.update")

    @staticmethod
    def _user_label(user) -> str:
        if not user:
            return ""
        return (
            getattr(user, "display_name", None)
            or user.get_full_name()
            or getattr(user, "email", None)
            or getattr(user, "username", None)
            or str(user.pk)
        )

    def _artifact_defaults(self, job: Job, checksum: str, activity_id: uuid.UUID, reviewer) -> dict:
        return {
            "case_fk": job.case,
            "organization": job.organization,
            "job_id": str(job.id),
            "path": job.transcript_path or "",
            "checksum": checksum,
            "schema_version": "v1",
            "metadata": {
                "activity_uuid": str(activity_id),
                "approved_by": self._user_label(reviewer),
                "approved_at": timezone.now().isoformat(),
            },
        }

    def _ensure_approval_artifact(self, job: Job, reviewer) -> None:
        if not job.transcript_path:
            return
        base_artifact = (
            CaseArtifact.objects.filter(case_id=str(job.case_id), job_id=str(job.id), type="TRANSCRIPT")
            .order_by("-created_at")
            .first()
        )
        checksum = base_artifact.checksum if base_artifact else ""
        if not checksum and os.path.exists(job.transcript_path):
            import hashlib

            digest = hashlib.sha256()
            try:
                with open(job.transcript_path, "rb") as fh:
                    for chunk in iter(lambda: fh.read(65536), b""):
                        digest.update(chunk)
                checksum = digest.hexdigest()
            except Exception:
                checksum = ""

        CaseArtifact.objects.update_or_create(
            case_id=str(job.case_id),
            type="TRANSCRIPT_APPROVED",
            title=f"{job.id}__approval",
            defaults=self._artifact_defaults(job, checksum, job.review_activity_id, reviewer),
        )

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        job = self.get_object()
        if not self._can_review(request, job):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        if job.status != Job.Status.SUCCEEDED:
            return Response({"detail": "Job must succeed before approval."}, status=status.HTTP_400_BAD_REQUEST)
        if not job.transcript_path:
            return Response({"detail": "Transcript not available."}, status=status.HTTP_400_BAD_REQUEST)

        comment = (request.data.get("comment") or "").strip()
        activity_id = job.review_activity_id or uuid.uuid4()
        reviewer = getattr(request, "user", None)
        job.review_status = Job.ReviewStatus.APPROVED
        job.reviewed_at = timezone.now()
        job.reviewed_by = reviewer if reviewer and getattr(reviewer, "is_authenticated", False) else None
        job.review_comment = comment
        job.review_activity_id = activity_id
        job.save(update_fields=["review_status", "reviewed_at", "reviewed_by", "review_comment", "review_activity_id"])

        try:
            self._ensure_approval_artifact(job, reviewer)
        except Exception:
            pass

        audit_emit(request, case_id=str(job.case_id), event="job.approved", data={"job_id": str(job.id), "activity_uuid": str(activity_id)})
        response_payload = {
            "job_id": str(job.id),
            "status": job.status,
            "review_status": job.review_status,
            "reviewed_at": job.reviewed_at,
            "reviewed_by": self._user_label(job.reviewed_by),
            "review_comment": job.review_comment,
            "review_activity_id": str(activity_id),
        }
        send_job_update(
            str(job.id),
            event="job.review",
            status=job.status,
            case_id=str(job.case_id),
            review_status=job.review_status,
            reviewed_at=job.reviewed_at.isoformat() if job.reviewed_at else None,
            reviewed_by=response_payload["reviewed_by"],
            review_comment=job.review_comment,
            review_activity_id=str(activity_id),
        )
        return Response(response_payload)

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        job = self.get_object()
        if not self._can_review(request, job):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        comment = (request.data.get("comment") or "").strip()
        activity_id = uuid.uuid4()
        reviewer = getattr(request, "user", None)
        job.review_status = Job.ReviewStatus.REJECTED
        job.reviewed_at = timezone.now()
        job.reviewed_by = reviewer if reviewer and getattr(reviewer, "is_authenticated", False) else None
        job.review_comment = comment
        job.review_activity_id = activity_id
        job.save(update_fields=["review_status", "reviewed_at", "reviewed_by", "review_comment", "review_activity_id"])

        CaseArtifact.objects.filter(
            case_id=str(job.case_id),
            job_id=str(job.id),
            type="TRANSCRIPT_APPROVED",
        ).delete()

        audit_emit(request, case_id=str(job.case_id), event="job.rejected", data={"job_id": str(job.id), "activity_uuid": str(activity_id)})
        response_payload = {
            "job_id": str(job.id),
            "status": job.status,
            "review_status": job.review_status,
            "reviewed_at": job.reviewed_at,
            "reviewed_by": self._user_label(job.reviewed_by),
            "review_comment": job.review_comment,
            "review_activity_id": str(activity_id),
        }
        send_job_update(
            str(job.id),
            event="job.review",
            status=job.status,
            case_id=str(job.case_id),
            review_status=job.review_status,
            reviewed_at=job.reviewed_at.isoformat() if job.reviewed_at else None,
            reviewed_by=response_payload["reviewed_by"],
            review_comment=job.review_comment,
            review_activity_id=str(activity_id),
        )
        return Response(response_payload)

    @action(detail=True, methods=["get"], url_path="detail", url_name="detail")
    def telemetry(self, request, pk=None):
        """Return enriched job telemetry mixing model fields and ops metadata."""

        job = self.get_object()
        serializer = JobTelemetrySerializer(job, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        job = self.get_object()
        if not job.transcript_path:
            raise Http404
        audit_emit(request, case_id=str(job.case_id), event="job.download_transcript", data={"job_id": str(job.id)})
        return FileResponse(open(job.transcript_path, "rb"), filename=f"{job.id}__transcript.txt", content_type="text/plain", as_attachment=True)

    @action(detail=True, methods=["get"], url_path="download-audio")
    def download_audio(self, request, pk=None):
        job = self.get_object()
        converted = str(request.query_params.get("converted", "")).lower() in {"1", "true", "yes"}
        org_id = getattr(getattr(job, "case", None), "organization_id", None) or getattr(job, "organization_id", None)
        job_meta: Dict[str, Any] = {}
        if org_id is not None:
            job_meta_path = storage_ops_dir(str(job.case_id), org_id) / f"{job.id}_transcription_log.json"
            if job_meta_path.exists():
                try:
                    job_meta = json.loads(job_meta_path.read_text(encoding="utf-8"))
                except Exception:
                    job_meta = {}
        path_obj: Optional[Path] = None
        active_meta: Dict[str, Any] = job_meta
        if converted:
            meta = job_meta
            converted_job_id = meta.get("converted_audio_job_id") or meta.get("converted_wav_job_id")
            converted_meta: Dict[str, Any] = {}
            # Fast-path: if this job itself produced a converted audio file, prefer it
            if path_obj is None and getattr(job, "audio_input", None):
                try:
                    candidate = Path(getattr(job, "audio_input"))
                    if candidate.exists():
                        path_obj = candidate
                except Exception:
                    path_obj = None
            if converted_job_id:
                try:
                    converted_job = Job.objects.get(pk=converted_job_id)
                    if str(converted_job.case_id) == str(job.case_id) and converted_job.audio_input:
                        candidate = Path(converted_job.audio_input)
                        if candidate.exists():
                            path_obj = candidate
                    if org_id is not None:
                        converted_meta_path = storage_ops_dir(str(job.case_id), org_id) / f"{converted_job_id}_transcription_log.json"
                        if converted_meta_path.exists():
                            try:
                                converted_meta = json.loads(converted_meta_path.read_text(encoding="utf-8"))
                            except Exception:
                                converted_meta = {}
                except Job.DoesNotExist:
                    path_obj = None
            if path_obj is None:
                converted_path = meta.get("converted_wav_path")
                if not converted_path:
                    raise Http404
                path_obj = Path(converted_path)
            active_meta = converted_meta or meta or {}
        else:
            audio_path = getattr(job, "audio_input", None)
            if not audio_path or not str(audio_path).startswith("/"):
                # Try resolving via metadata in case source path is stored there
                audio_path = (job_meta.get("source_audio_path") or job_meta.get("audio_path") or "")
                if not audio_path or not str(audio_path).startswith("/"):
                    raise Http404
            path_obj = Path(audio_path)
            active_meta = job_meta
        if not path_obj.exists():
            raise Http404
        storage_root = Path(settings.STORAGE_ROOT).resolve()
        try:
            if not path_obj.resolve().is_relative_to(storage_root):
                raise Http404
        except AttributeError:
            # Python < 3.9 compatibility: fallback check
            resolved = path_obj.resolve()
            if not str(resolved).startswith(str(storage_root)):
                raise Http404
        audit_emit(
            request,
            case_id=str(job.case_id),
            event="job.download_audio",
            data={"job_id": str(job.id), "converted": converted},
        )
        filename = _derive_audio_filename(path_obj, active_meta, path_obj.name or f"{job.id}_audio")
        return FileResponse(path_obj.open("rb"), filename=filename, as_attachment=True)

    @action(detail=True, methods=["post"], url_path="verify-hash")
    def verify_hash(self, request, pk=None):
        job = self.get_object()

        target = str(request.data.get("target") or "").strip().lower()
        scope = str(request.data.get("scope") or "current").strip().lower()
        if target not in {"audio", "transcript"}:
            return Response({"detail": "Unsupported target."}, status=status.HTTP_400_BAD_REQUEST)
        if target == "audio" and scope not in {"current", "source", "converted"}:
            return Response({"detail": "Unsupported audio scope."}, status=status.HTTP_400_BAD_REQUEST)

        telemetry = job_telemetry(job)
        meta = telemetry.meta if isinstance(telemetry.meta, dict) else {}

        storage_root = Path(settings.STORAGE_ROOT).resolve()

        def _resolve_path(candidate: Optional[str]) -> Optional[Path]:
            if not candidate:
                return None
            try:
                path = Path(candidate).expanduser()
                if not path.exists():
                    return None
                resolved = path.resolve()
                try:
                    resolved.relative_to(storage_root)
                except ValueError:
                    if not str(resolved).startswith(str(storage_root)):
                        return None
                return resolved
            except Exception:
                return None

        expected_hash: Optional[str] = None
        path_obj: Optional[Path] = None

        if target == "audio":
            if scope == "source":
                path_obj = _resolve_path(meta.get("source_audio_path"))
                expected_hash = meta.get("source_audio_sha256")
                if path_obj is None and meta.get("source_job_id"):
                    try:
                        source_job = Job.objects.get(pk=meta.get("source_job_id"))
                        path_obj = _resolve_path(getattr(source_job, "audio_input", None))
                        if expected_hash is None:
                            source_meta = job_telemetry(source_job).meta or {}
                            if isinstance(source_meta, dict):
                                expected_hash = source_meta.get("audio_sha256")
                    except Job.DoesNotExist:
                        path_obj = None
            elif scope == "converted":
                path_obj = _resolve_path(meta.get("converted_wav_path") or getattr(job, "audio_input", None))
                expected_hash = meta.get("converted_audio_sha256") or meta.get("audio_sha256")
            else:
                path_obj = _resolve_path(getattr(job, "audio_input", None))
                expected_hash = meta.get("audio_sha256")
        else:  # transcript
            path_obj = _resolve_path(getattr(job, "transcript_path", None))
            expected_hash = meta.get("transcript_sha256")

        if path_obj is None or not path_obj.exists():
            return Response({"detail": "File not found for verification."}, status=status.HTTP_404_NOT_FOUND)

        observed_hash = _sha256_file(path_obj)
        size_bytes: Optional[int]
        try:
            size_bytes = path_obj.stat().st_size
        except Exception:
            size_bytes = None

        result: str
        if observed_hash is None:
            result = "error"
        elif expected_hash:
            result = "match" if observed_hash.lower() == str(expected_hash).lower() else "mismatch"
        else:
            result = "computed"

        payload = {
            "target": target,
            "scope": scope if target == "audio" else None,
            "path": str(path_obj),
            "expected": expected_hash,
            "observed": observed_hash,
            "result": result,
            "size_bytes": size_bytes,
        }
        return Response(payload)

    @action(detail=True, methods=["post"], url_path="refresh-audio")
    def refresh_audio(self, request, pk=None):
        job = self.get_object()
        audio_input = getattr(job, "audio_input", None)
        if not audio_input:
            return Response({"detail": "Job has no audio input."}, status=status.HTTP_400_BAD_REQUEST)

        path = Path(str(audio_input))
        if not path.exists():
            return Response({"detail": "Audio file is unavailable."}, status=status.HTTP_404_NOT_FOUND)

        try:
            meta = probe_audio_metadata(path) or {}
        except Exception as exc:  # noqa: BLE001
            return Response({"detail": f"Unable to probe audio: {exc}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        sha256_val = _sha256_file(path)
        try:
            size_bytes = path.stat().st_size
        except Exception:  # noqa: BLE001
            size_bytes = None

        updates: Dict[str, Any] = {}
        for key, value in meta.items():
            if value is not None:
                updates[key] = value
        if sha256_val:
            updates["audio_sha256"] = sha256_val
        if size_bytes is not None:
            updates["audio_size_bytes"] = size_bytes

        update_job_meta(str(job.case_id), getattr(job, "organization_id", None), str(job.id), updates)

        dirty_fields: list[str] = []
        duration_val = meta.get("audio_duration_s")
        if duration_val is not None:
            try:
                job.duration_s = float(duration_val)
                dirty_fields.append("duration_s")
            except Exception:  # noqa: BLE001
                pass
        bitrate_val = meta.get("audio_bitrate_kbps")
        if bitrate_val is not None:
            try:
                job.audio_bitrate_kbps = int(bitrate_val)
                dirty_fields.append("audio_bitrate_kbps")
            except Exception:  # noqa: BLE001
                pass
        channels_val = meta.get("audio_channels")
        if channels_val is not None:
            try:
                job.audio_channels = int(channels_val)
                dirty_fields.append("audio_channels")
            except Exception:  # noqa: BLE001
                pass
        sample_rate_val = meta.get("audio_sample_rate_hz")
        if sample_rate_val is not None:
            try:
                job.sample_rate_hz = int(sample_rate_val)
                dirty_fields.append("sample_rate_hz")
            except Exception:  # noqa: BLE001
                pass

        if dirty_fields:
            try:
                job.save(update_fields=dirty_fields)
            except Exception:  # noqa: BLE001
                job.save()

        refreshed_payload = job_telemetry(job).audio_payload(include_paths=True)
        return Response({"audio": refreshed_payload})

    @action(detail=True, methods=["post"], url_path="mark-corrupted")
    def mark_corrupted(self, request, pk=None):
        job = self.get_object()
        now = timezone.now()
        if job.status != Job.Status.CORRUPTED:
            job.status = Job.Status.CORRUPTED
            job.finished_at = job.finished_at or now
            job.error_message = job.error_message or "Hash verification failed"
            job.save(update_fields=["status", "finished_at", "error_message"])
            append_job_log(
                str(job.case_id),
                getattr(job, "organization_id", None),
                str(job.id),
                "Job marked as corrupted after hash verification mismatch",
                level="error",
            )
            try:
                send_job_update(
                    str(job.id),
                    event="job.corrupted",
                    status=Job.Status.CORRUPTED,
                    case_id=str(job.case_id),
                )
            except Exception:
                log.exception("job corrupted update emit failed", extra={"job_id": job.id})

        serializer = JobTelemetrySerializer(job, context={"request": request, "ui_mode": True})
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        job = self.get_object()
        if job.status not in {Job.Status.PENDING, Job.Status.RUNNING, Job.Status.CANCELLING, Job.Status.UPLOADING}:
            return Response({"detail": "Job is not cancellable."}, status=status.HTTP_400_BAD_REQUEST)
        case_id = str(job.case_id)
        org_id = str(job.organization_id) if getattr(job, "organization_id", None) else None
        job_id_str = str(job.id)

        task_runs = list(
            TaskRun.objects.filter(job_id=job_id_str, task_name="transcribe_job").order_by("-started_at")
        )
        task_ids = [tr.task_id for tr in task_runs if tr.task_id]
        active_task_ids = self._active_celery_task_ids(task_ids)

        # If no workers are handling the job, finalize immediately regardless of current status.
        if not active_task_ids:
            now = timezone.now()
            job.status = Job.Status.CANCELLED
            job.finished_at = now
            job.error_message = "Cancelled by user"
            job.upload_progress = None
            job.save(update_fields=["status", "finished_at", "error_message", "upload_progress"])
            for tr in task_runs:
                if tr.status != "CANCELLED":
                    tr.status = "CANCELLED"
                    tr.finished_at = now
                    tr.save(update_fields=["status", "finished_at"])
            try:
                self._cancel_azure_transcription(job)
            except Exception:
                pass
            append_job_log(case_id, org_id, job_id_str, "Cancellation completed (no active worker)")
            update_job_meta(case_id, org_id, job_id_str, {"cancelled_at": now.isoformat()})
            audit_emit(
                request,
                case_id=case_id,
                event="job.cancelled",
                data={"job_id": job_id_str, "immediate": True},
            )
            send_job_update(
                job_id_str,
                event="job.cancelled",
                status=Job.Status.CANCELLED,
                case_id=case_id,
                progress_percent=None,
                upload_progress=None,
            )
            return Response({"status": Job.Status.CANCELLED, "upload_progress": None})

        # Attempt to revoke active Celery tasks and mark the job as cancelling.
        for task_id in active_task_ids:
            try:
                celery_app.control.revoke(task_id, terminate=True)
            except Exception as exc:
                log.warning(
                    "unable to revoke celery task",
                    extra={"task_id": task_id, "job_id": job_id_str, "error": str(exc)},
                )

        job.status = Job.Status.CANCELLING
        job.error_message = "Cancellation requested"
        job.save(update_fields=["status", "error_message"])
        try:
            self._cancel_azure_transcription(job)
        except Exception:
            pass
        append_job_log(case_id, org_id, job_id_str, "Cancellation requested; awaiting worker shutdown")
        audit_emit(
            request,
            case_id=case_id,
            event="job.cancelling",
            data={"job_id": job_id_str, "tasks": list(active_task_ids)},
        )
        send_job_update(
            job_id_str,
            event="job.cancelling",
            status=Job.Status.CANCELLING,
            case_id=case_id,
            progress_percent=job.upload_progress,
            upload_progress=job.upload_progress,
        )
        return Response({"status": Job.Status.CANCELLING, "upload_progress": job.upload_progress})

    @action(detail=True, methods=["post"], url_path="restart")
    def restart(self, request, pk=None):
        job = self.get_object()
        if job.status == Job.Status.RUNNING:
            return Response({"detail": "Job is currently running."}, status=status.HTTP_400_BAD_REQUEST)
        if not job.audio_input:
            return Response({"detail": "Original audio input is missing."}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            new_job = Job.objects.create(
                case=job.case,
                organization=job.organization,
                audio_input=job.audio_input,
                mode=job.mode,
                diarization=job.diarization,
                language=job.language,
            )

        transcribe_job.delay(
            case_id=str(new_job.case_id),
            job_id=str(new_job.id),
            audio_input=new_job.audio_input,
            mode=new_job.mode,
            diarization=new_job.diarization,
            language=new_job.language,
            force_wav_conversion=(request.query_params.get("convert") in ("1", "true", "True")),
        )
        audit_emit(
            request,
            case_id=str(job.case_id),
            event="job.restarted",
            data={"job_id": str(job.id), "replacement_job_id": str(new_job.id)},
        )
        send_job_update(str(new_job.id), event="job.created", status=Job.Status.PENDING, case_id=str(new_job.case_id))
        return Response({"status": Job.Status.PENDING, "job_id": str(new_job.id)})

    @staticmethod
    def _active_celery_task_ids(task_ids: Iterable[str]) -> Set[str]:
        ids = [tid for tid in task_ids if tid]
        active: Set[str] = set()
        if not ids:
            return active
        inspect_obj = None
        try:
            inspect_obj = celery_app.control.inspect()
        except Exception as exc:
            log.debug("celery inspect init failed: %s", exc)
        if inspect_obj is not None:
            for attr in ("active", "reserved", "scheduled"):
                try:
                    data = getattr(inspect_obj, attr)()
                except Exception as exc:
                    log.debug("celery inspect %s failed: %s", attr, exc)
                    data = None
                if not data:
                    continue
                for tasks in data.values():
                    for entry in tasks:
                        entry_id = entry.get("id") or entry.get("request", {}).get("id")
                        entry_state = entry.get("state") or entry.get("request", {}).get("state")
                        if entry_id in ids and entry_state in {None, "STARTED", "RETRY"}:
                            active.add(entry_id)
        if active:
            return active
        for tid in ids:
            try:
                result = celery_app.AsyncResult(tid)
                if result.state in {"STARTED", "RETRY"}:
                    active.add(tid)
            except Exception as exc:
                log.debug("celery async result check failed for %s: %s", tid, exc)
        return active

    @action(detail=True, methods=["get"], url_path="logs")
    def logs(self, request, pk=None):
        job = self.get_object()
        case_id = str(job.case_id)
        ops = storage_ops_dir(case_id, job.case.organization_id) / f"{job.id}_transcription.log"
        if not ops.exists():
            raise Http404
        audit_emit(request, case_id=case_id, event="job.download_logs", data={"job_id": str(job.id)})
        return FileResponse(open(ops, "rb"), filename=f"{job.id}_transcription.log", content_type="text/plain", as_attachment=True)

    def _cancel_azure_transcription(self, job: Job) -> None:
        if job.mode != Job.Mode.BATCH:
            return
        key = getattr(settings, "AZURE_SPEECH_KEY", None)
        if not key:
            return
        ops_path = storage_ops_dir(str(job.case_id), job.case.organization_id) / f"{job.id}_transcription_log.json"
        if not ops_path.exists():
            return
        try:
            meta = json.loads(ops_path.read_text(encoding="utf-8"))
        except Exception:
            return
        loc = meta.get("azure_transcription_url")
        if not loc:
            return
        headers = {
            "Ocp-Apim-Subscription-Key": key,
            "Accept": "application/json",
        }
        try:
            resp = requests.delete(loc, headers=headers, timeout=10)
            status_text = f"{resp.status_code}"
            if resp.text:
                status_text += f" {resp.text[:120]}"
            log.info("azure batch cancel", extra={"job_id": str(job.id), "status": status_text})
            try:
                update_job_meta(
                    str(job.case_id),
                    job.organization_id,
                    str(job.id),
                    {
                        "azure_cancel_status": resp.status_code,
                        "azure_cancel_body": (resp.text or "")[:500],
                        "azure_transcription_url": loc,
                    },
                )
            except Exception:
                pass
        except Exception as exc:  # noqa: BLE001
            log.warning("azure batch cancel failed", extra={"job_id": str(job.id), "error": str(exc)})
            try:
                update_job_meta(
                    str(job.case_id),
                    job.organization_id,
                    str(job.id),
                    {"azure_cancel_error": str(exc)},
                )
            except Exception:
                pass

    @action(detail=True, methods=["post"], url_path="analyze/summary")
    def analyze_summary(self, request, pk=None):
        job = self.get_object()
        summarize_job.delay(case_id=str(job.case_id), job_id=str(job.id))
        audit_emit(request, case_id=str(job.case_id), event="analysis.summary.requested", data={"job_id": str(job.id)})
        return Response({"status": "queued"}, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["post"], url_path="analyze/timeline")
    def analyze_timeline(self, request, pk=None):
        job = self.get_object()
        timeline_job.delay(case_id=str(job.case_id), job_id=str(job.id))
        audit_emit(request, case_id=str(job.case_id), event="analysis.timeline.requested", data={"job_id": str(job.id)})
        return Response({"status": "queued"}, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["post"], url_path="analyze/graph")
    def analyze_graph(self, request, pk=None):
        job = self.get_object()
        graph_job.delay(case_id=str(job.case_id), job_id=str(job.id))
        audit_emit(request, case_id=str(job.case_id), event="analysis.graph.requested", data={"job_id": str(job.id)})
        return Response({"status": "queued"}, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["post"], url_path="title")
    def update_title(self, request, pk=None):
        job = self.get_object()
        artifact = (
            CaseArtifact.objects.filter(case_id=str(job.case_id), job_id=str(job.id), type="TRANSCRIPT")
            .order_by("-created_at")
            .first()
        )
        if not artifact:
            return Response({"detail": "Transcript not found for this job."}, status=status.HTTP_404_NOT_FOUND)
        new_title = (request.data.get("title") or "").strip()
        title_error = None
        if not new_title:
            title_error = "Title cannot be empty."
        else:
            clash = CaseArtifact.objects.filter(
                case_id=str(job.case_id), type="TRANSCRIPT", title=new_title
            ).exclude(pk=artifact.pk)
            if clash.exists():
                title_error = "A transcript with that title already exists in this case."
        if title_error:
            telemetry = JobTelemetrySerializer(job, context={"request": request, "ui_mode": True}).data
            context = {
                "case": job.case,
                "job": job,
                "telemetry": telemetry,
                "artifact": {"title": artifact.title, "path": artifact.path},
                "job_title": artifact.title or str(job.id),
                "metadata_items": [],
                "title_error": title_error,
                "title_edit": True,
                "user_can_review": True,
            }
            return render(request, "platform_ui/components/jobs/job_detail.html", context)

        artifact.title = new_title
        artifact.save(update_fields=["title"])
        append_job_log(str(job.case_id), job.organization_id, str(job.id), f"Transcript title set to '{new_title}'")
        headers = {"HX-Trigger": json.dumps({"job-title-updated": {"job_id": str(job.id), "title": new_title}})}
        telemetry = JobTelemetrySerializer(job, context={"request": request, "ui_mode": True}).data
        context = {
            "case": job.case,
            "job": job,
            "telemetry": telemetry,
            "artifact": {"title": new_title, "path": artifact.path},
            "job_title": new_title,
            "metadata_items": [],
            "user_can_review": True,
        }
        return render(request, "platform_ui/components/jobs/job_detail.html", context, headers=headers)

    @action(detail=False, methods=["post"], url_path="upload")
    def upload(self, request):
        """Upload an audio file and create a job.

        Accepts multipart/form-data with fields:
          - case: UUID (required)
          - audio: file (required unless audio_url provided)
          - audio_url: HTTPS URL (SAS) alternative to file upload
          - mode: "on-demand" or "batch"
          - diarization: boolean (batch only)
          - language: e.g., "en-CA"
        """
        from django.core.exceptions import ValidationError
        from django.utils.datastructures import MultiValueDictKeyError
        from django.shortcuts import get_object_or_404
        from apps.platform.cases.models import Case

        case_id = request.data.get("case")
        if not case_id:
            return Response({"detail": "Missing case"}, status=status.HTTP_400_BAD_REQUEST)
        case = get_object_or_404(Case.objects.select_related("organization"), pk=case_id)
        mode = request.data.get("mode", Job.Mode.ON_DEMAND)
        diarization = str(request.data.get("diarization", "false")).lower() in ("1", "true", "yes")
        language = request.data.get("language", "en-CA")
        if diarization and mode != Job.Mode.BATCH:
            return Response({"detail": "Diarization is only supported in batch mode."}, status=status.HTTP_400_BAD_REQUEST)

        file_obj = request.FILES.get("audio")
        audio_url = (request.data.get("audio_url") or "").strip()
        if not file_obj and not audio_url:
            return Response({"detail": "Provide 'audio' file or 'audio_url'"}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            job = Job.objects.create(case=case, audio_input="", mode=mode, diarization=diarization, language=language)
            # Determine audio_input
            if file_obj:
                case_dir = ensure_case_dirs(case_id, job.organization_id)
                audio_dir = case_dir / "audio"
                dest = audio_dir / f"{job.id}__{file_obj.name}"
                # Stream to disk
                with open(dest, "wb") as out:
                    for chunk in file_obj.chunks():
                        out.write(chunk)
                job.audio_input = str(dest)
            else:
                job.audio_input = audio_url
            job.save(update_fields=["audio_input"])

        force_wav_requested = str(request.data.get("force_wav") or "").lower() in {"1", "true", "yes", "on"}

        # Enqueue task
        transcribe_job.delay(
            case_id=str(job.case_id),
            job_id=str(job.id),
            audio_input=job.audio_input,
            mode=job.mode,
            diarization=job.diarization,
            language=job.language,
            force_wav_conversion=force_wav_requested,
        )
        out = JobSerializer(instance=job)
        headers = {"Location": f"/api/v1/jobs/{job.id}/"}
        audit_emit(
            request,
            case_id=str(case_id),
            event="job.uploaded",
            data={"job_id": str(job.id), "mode": mode, "file": bool(file_obj), "force_wav_conversion": force_wav_requested},
        )
        return Response(out.data, status=status.HTTP_201_CREATED, headers=headers)
