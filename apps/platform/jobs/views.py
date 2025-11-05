from __future__ import annotations

import hashlib
import logging
import os
import uuid
from collections.abc import Iterable
from typing import Any

import requests
from django.conf import settings
from django.http import Http404
from django.http.response import FileResponse
from django.shortcuts import render
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.platform.authorization.access_policies import JobAccessPolicy
from config.paths import resolve_storage_root

log = logging.getLogger("apps.platform.jobs.views")
from pathlib import Path

ANALYSIS_KIND_TO_META_KEY: dict[str, str] = {
    "summary_json": "summary_file",
    "summary_markdown": "summary_markdown_file",
    "summary_outline": "summary_outline_file",
    "summary_timeline_seeds": "summary_timeline_file",
    "summary_entity_hints": "summary_entity_file",
    "summary_case_brief": "summary_case_brief_file",
    "timeline_v2": "timeline_v2_file",
    "graph_v2": "graph_v2_file",
    "graph_v2_html": "graph_v2_html_file",
    "graph_v2_png": "graph_v2_png_file",
    "entities_v2": "entities_v2_file",
    "compose_client_markdown": "compose_client_markdown",
    "compose_client_docx": "compose_client_docx",
    "compose_lawyer_markdown": "compose_lawyer_markdown",
    "compose_lawyer_docx": "compose_lawyer_docx",
    "compose_timeline_summary": "compose_timeline_summary",
    "compose_entity_brief": "compose_entity_brief",
    "compose_graph_visual_json": "compose_graph_visual_json",
}

from django.db import transaction

from apps.platform.artifacts.models import CaseArtifact
from apps.platform.authorization.capabilities import has_capability
from apps.platform.cases.models import Case
from apps.platform.config.celery import app as celery_app
from apps.platform.jobs.models import Job, JobNote
from apps.platform.jobs.notes import serialize_notes
from apps.platform.jobs.serializers import (
    JobCreateSerializer,
    JobSerializer,
    JobTelemetrySerializer,
)
from apps.platform.jobs.telemetry import job_telemetry
from apps.platform.operations.audit import emit as audit_emit
from apps.platform.operations.channels import send_job_update
from apps.platform.operations.llm import (
    ensure_default_llm_configuration,
    evaluate_provider_setup,
    get_llm_configuration,
    get_org_provider_credentials,
    get_provider_secret_with_metadata,
    load_llm_settings,
)
from apps.platform.operations.services import case_paths, resolve_case_relative
from apps.platform.operations.services.analysis import collect_requested_providers
from apps.platform.operations.services.files import sha256_file
from apps.platform.operations.storage import ensure_case_dirs
from apps.platform.operations.storage import ops_dir as storage_ops_dir
from apps.platform.operations.tasks import analyze_job, compose_job, transcribe_job
from apps.platform.operations.utils import append_job_log, read_job_meta, update_job_meta
from apps.platform.tenancy import scope_jobs
from packages.udocket_common.json_utils import read_json_object, stringify_json
from packages.udocket_common.operations import ComposeStageMap, optional_json_object
from packages.udocket_common.text import unique_title
from packages.udocket_core.agents.analyze_lib import AnalyzeConfig
from packages.udocket_core.audio import probe_audio_metadata


def _derive_audio_filename(path_obj: Path | None, meta: dict[str, Any], fallback: str) -> str:
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
            return Response(
                {"detail": "Diarization is only supported in batch mode."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        job = Job.objects.create(**v)
        force_wav_conversion = str(request.data.get("force_wav") or "").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
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
            data={
                "job_id": str(job.id),
                "mode": job.mode,
                "force_wav_conversion": force_wav_conversion,
            },
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

    @action(detail=True, methods=["post"], url_path="notes", url_name="notes")
    def notes(self, request, pk=None):
        job = self.get_object()
        if not self._can_review(request, job):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        incoming = request.data or {}
        notes_value = incoming.get("notes")
        if notes_value is None:
            return Response(
                {"detail": "Field 'notes' is required."}, status=status.HTTP_400_BAD_REQUEST
            )
        if not isinstance(notes_value, str):
            return Response(
                {"detail": "Field 'notes' must be a string."}, status=status.HTTP_400_BAD_REQUEST
            )

        # Normalise newlines but keep intentional spacing inside the message.
        text_value = notes_value.replace("\r\n", "\n")
        text_value = text_value.strip()
        if not text_value:
            return Response(
                {"detail": "Notes text must not be empty."}, status=status.HTTP_400_BAD_REQUEST
            )

        user = getattr(request, "user", None)
        user_obj = user if user and getattr(user, "is_authenticated", False) else None
        created_by_name = self._user_label(user_obj) if user_obj else ""
        JobNote.objects.create(
            job=job,
            text=text_value,
            created_by=user_obj,
            created_by_name=created_by_name or "",
        )

        notes_qs = JobNote.objects.filter(job=job).order_by("-created_at")
        note_entries = serialize_notes(notes_qs)
        latest_entry = note_entries[0] if note_entries else None
        notes_payload: dict[str, Any] = {
            "entries": note_entries,
            "count": len(note_entries),
        }
        if latest_entry:
            notes_payload["updated_at"] = latest_entry["created_at"]
            notes_payload["updated_by"] = latest_entry.get("created_by")
            notes_payload["updated_by_label"] = latest_entry.get("created_by_label")

        snippet = text_value.splitlines()[0]
        if len(snippet) > 80:
            snippet = f"{snippet[:77]}…"
        try:
            author_label = (
                latest_entry.get("created_by_label")
                if latest_entry
                else (created_by_name or "unknown")
            )
            append_job_log(
                str(job.case_id),
                job.organization_id,
                str(job.id),
                f"UI note added by {author_label}: {snippet}",
            )
        except Exception:
            pass

        send_job_update(
            str(job.id),
            event="job.notes",
            status=job.status,
            case_id=str(job.case_id),
            notes=notes_payload,
        )

        return Response({"status": "ok", "notes": notes_payload})

    @action(detail=False, methods=["get"], url_path="status/bulk")
    def bulk_status(self, request):
        """Return status payloads for multiple jobs in a single response.

        Expects a comma-delimited ``ids`` query parameter and respects tenancy
        constraints through ``scope_jobs``.
        """

        ids_param = request.query_params.get("ids")
        if not ids_param:
            return Response(
                {"detail": "Parameter 'ids' is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        job_ids: list[uuid.UUID] = []
        for raw_part in ids_param.split(","):
            part = (raw_part or "").strip()
            if not part:
                continue
            try:
                job_ids.append(uuid.UUID(part))
            except ValueError:
                continue

        if not job_ids:
            return Response([], status=status.HTTP_200_OK)

        qs = self.get_queryset().filter(pk__in=job_ids)
        case_id_param = request.query_params.get("case_id")
        if case_id_param:
            try:
                uuid.UUID(case_id_param)
            except ValueError:
                return Response(
                    {"detail": "Parameter 'case_id' must be a valid UUID."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
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
                    "review_activity_id": str(job.review_activity_id)
                    if job.review_activity_id
                    else None,
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
            CaseArtifact.objects.filter(
                case_id=str(job.case_id), job_id=str(job.id), type="TRANSCRIPT"
            )
            .order_by("-created_at")
            .first()
        )
        checksum = base_artifact.checksum if base_artifact else ""
        if not checksum and os.path.exists(job.transcript_path):
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
            return Response(
                {"detail": "Job must succeed before approval."}, status=status.HTTP_400_BAD_REQUEST
            )
        if not job.transcript_path:
            return Response(
                {"detail": "Transcript not available."}, status=status.HTTP_400_BAD_REQUEST
            )

        comment = (request.data.get("comment") or "").strip()
        activity_id = job.review_activity_id or uuid.uuid4()
        reviewer = getattr(request, "user", None)
        job.review_status = Job.ReviewStatus.APPROVED
        job.reviewed_at = timezone.now()
        job.reviewed_by = (
            reviewer if reviewer and getattr(reviewer, "is_authenticated", False) else None
        )
        job.review_comment = comment
        job.review_activity_id = activity_id
        job.save(
            update_fields=[
                "review_status",
                "reviewed_at",
                "reviewed_by",
                "review_comment",
                "review_activity_id",
            ]
        )

        try:
            self._ensure_approval_artifact(job, reviewer)
        except Exception:
            pass

        audit_emit(
            request,
            case_id=str(job.case_id),
            event="job.approved",
            data={"job_id": str(job.id), "activity_uuid": str(activity_id)},
        )
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
        job.reviewed_by = (
            reviewer if reviewer and getattr(reviewer, "is_authenticated", False) else None
        )
        job.review_comment = comment
        job.review_activity_id = activity_id
        job.save(
            update_fields=[
                "review_status",
                "reviewed_at",
                "reviewed_by",
                "review_comment",
                "review_activity_id",
            ]
        )

        CaseArtifact.objects.filter(
            case_id=str(job.case_id),
            job_id=str(job.id),
            type="TRANSCRIPT_APPROVED",
        ).delete()

        audit_emit(
            request,
            case_id=str(job.case_id),
            event="job.rejected",
            data={"job_id": str(job.id), "activity_uuid": str(activity_id)},
        )
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
        audit_emit(
            request,
            case_id=str(job.case_id),
            event="job.download_transcript",
            data={"job_id": str(job.id)},
        )
        return FileResponse(
            open(job.transcript_path, "rb"),
            filename=f"{job.id}__transcript.txt",
            content_type="text/plain",
            as_attachment=True,
        )

    @action(detail=True, methods=["get"], url_path="download-audio")
    def download_audio(self, request, pk=None):
        job = self.get_object()
        converted = str(request.query_params.get("converted", "")).lower() in {"1", "true", "yes"}
        org_id = getattr(getattr(job, "case", None), "organization_id", None) or getattr(
            job, "organization_id", None
        )
        job_meta: dict[str, Any] = {}
        if org_id is not None:
            job_meta_path = (
                storage_ops_dir(str(job.case_id), org_id) / f"{job.id}_transcription_log.json"
            )
            if job_meta_path.exists():
                job_meta = read_json_object(job_meta_path)
        path_obj: Path | None = None
        active_meta: dict[str, Any] = job_meta
        if converted:
            meta = job_meta
            converted_job_id = meta.get("converted_audio_job_id") or meta.get(
                "converted_wav_job_id"
            )
            converted_meta: dict[str, Any] = {}
            # Fast-path: if this job itself produced a converted audio file, prefer it
            if path_obj is None and getattr(job, "audio_input", None):
                try:
                    candidate = Path(job.audio_input)
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
                        converted_meta_path = (
                            storage_ops_dir(str(job.case_id), org_id)
                            / f"{converted_job_id}_transcription_log.json"
                        )
                        if converted_meta_path.exists():
                            converted_meta = read_json_object(converted_meta_path)
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
                audio_path = job_meta.get("source_audio_path") or job_meta.get("audio_path") or ""
                if not audio_path or not str(audio_path).startswith("/"):
                    raise Http404
            path_obj = Path(audio_path)
            active_meta = job_meta
        if not path_obj.exists():
            raise Http404
        storage_root = resolve_storage_root().resolve()
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
            return Response(
                {"detail": "Unsupported audio scope."}, status=status.HTTP_400_BAD_REQUEST
            )

        telemetry = job_telemetry(job)
        meta = telemetry.meta if isinstance(telemetry.meta, dict) else {}

        storage_root = resolve_storage_root().resolve()

        def _resolve_path(candidate: str | None) -> Path | None:
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

        expected_hash: str | None = None
        path_obj: Path | None = None

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
                path_obj = _resolve_path(
                    meta.get("converted_wav_path") or getattr(job, "audio_input", None)
                )
                expected_hash = meta.get("converted_audio_sha256") or meta.get("audio_sha256")
            else:
                path_obj = _resolve_path(getattr(job, "audio_input", None))
                expected_hash = meta.get("audio_sha256")
        else:  # transcript
            path_obj = _resolve_path(getattr(job, "transcript_path", None))
            expected_hash = meta.get("transcript_sha256")

        if path_obj is None or not path_obj.exists():
            return Response(
                {"detail": "File not found for verification."}, status=status.HTTP_404_NOT_FOUND
            )

        observed_hash = sha256_file(path_obj)
        size_bytes: int | None
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
            return Response(
                {"detail": "Job has no audio input."}, status=status.HTTP_400_BAD_REQUEST
            )

        path = Path(str(audio_input))
        if not path.exists():
            return Response(
                {"detail": "Audio file is unavailable."}, status=status.HTTP_404_NOT_FOUND
            )

        try:
            meta = probe_audio_metadata(path) or {}
        except Exception as exc:  # noqa: BLE001
            return Response(
                {"detail": f"Unable to probe audio: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        sha256_val = sha256_file(path)
        try:
            size_bytes = path.stat().st_size
        except Exception:  # noqa: BLE001
            size_bytes = None

        updates: dict[str, Any] = {}
        for key, value in meta.items():
            if value is not None:
                updates[key] = value
        if sha256_val:
            updates["audio_sha256"] = sha256_val
        if size_bytes is not None:
            updates["audio_size_bytes"] = size_bytes

        update_job_meta(
            str(job.case_id), getattr(job, "organization_id", None), str(job.id), updates
        )

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
        if job.status not in {
            Job.Status.PENDING,
            Job.Status.RUNNING,
            Job.Status.CANCELLING,
            Job.Status.UPLOADING,
        }:
            return Response(
                {"detail": "Job is not cancellable."}, status=status.HTTP_400_BAD_REQUEST
            )
        case_id = str(job.case_id)
        org_id = str(job.organization_id) if getattr(job, "organization_id", None) else None
        job_id_str = str(job.id)

        job_meta = read_job_meta(case_id, org_id, job_id_str)
        candidate_ids: list[str] = []
        task_meta_id = job_meta.get("celery_task_id")
        if isinstance(task_meta_id, str) and task_meta_id:
            candidate_ids.append(task_meta_id)
        history_ids = job_meta.get("celery_task_history")
        if isinstance(history_ids, list):
            for value in history_ids:
                if isinstance(value, str) and value:
                    candidate_ids.append(value)
        deduped_ids: list[str] = []
        seen: set[str] = set()
        for value in candidate_ids:
            if value not in seen:
                seen.add(value)
                deduped_ids.append(value)
        active_task_ids = self._active_celery_task_ids(deduped_ids)

        # If no workers are handling the job, finalize immediately regardless of current status.
        if not active_task_ids:
            now = timezone.now()
            job.status = Job.Status.CANCELLED
            job.finished_at = now
            job.error_message = "Cancelled by user"
            job.upload_progress = None
            job.save(update_fields=["status", "finished_at", "error_message", "upload_progress"])
            try:
                self._cancel_azure_transcription(job)
            except Exception:
                pass
            append_job_log(case_id, org_id, job_id_str, "Cancellation completed (no active worker)")
            update_job_meta(
                case_id,
                org_id,
                job_id_str,
                {
                    "cancelled_at": now.isoformat(),
                    "celery_task_status": "cancelled",
                    "celery_task_finished_at": now.isoformat(),
                },
            )
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
        append_job_log(
            case_id, org_id, job_id_str, "Cancellation requested; awaiting worker shutdown"
        )
        update_job_meta(
            case_id,
            org_id,
            job_id_str,
            {
                "celery_task_status": "cancelling",
                "cancellation_requested_at": timezone.now().isoformat(),
            },
        )
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
            return Response(
                {"detail": "Job is currently running."}, status=status.HTTP_400_BAD_REQUEST
            )
        if not job.audio_input:
            return Response(
                {"detail": "Original audio input is missing."}, status=status.HTTP_400_BAD_REQUEST
            )
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
        send_job_update(
            str(new_job.id),
            event="job.created",
            status=Job.Status.PENDING,
            case_id=str(new_job.case_id),
        )
        return Response({"status": Job.Status.PENDING, "job_id": str(new_job.id)})

    @staticmethod
    def _active_celery_task_ids(task_ids: Iterable[str]) -> set[str]:
        ids = [tid for tid in task_ids if tid]
        active: set[str] = set()
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
        audit_emit(
            request, case_id=case_id, event="job.download_logs", data={"job_id": str(job.id)}
        )
        return FileResponse(
            open(ops, "rb"),
            filename=f"{job.id}_transcription.log",
            content_type="text/plain",
            as_attachment=True,
        )

    def _cancel_azure_transcription(self, job: Job) -> None:
        if job.mode != Job.Mode.BATCH:
            return
        key = getattr(settings, "AZURE_SPEECH_KEY", None)
        if not key:
            return
        ops_path = (
            storage_ops_dir(str(job.case_id), job.case.organization_id)
            / f"{job.id}_transcription_log.json"
        )
        if not ops_path.exists():
            return
        meta = read_json_object(ops_path)
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
            log.warning(
                "azure batch cancel failed", extra={"job_id": str(job.id), "error": str(exc)}
            )
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
        source_job = self.get_object()
        payload = request.data if hasattr(request, "data") else {}
        llm_config_id = None
        if isinstance(payload, dict):
            config_value = payload.get("llm_config_id")
            if isinstance(config_value, str) and config_value.strip():
                llm_config_id = config_value.strip()

        transcript_path = source_job.transcript_path or ""
        source_artifact = (
            CaseArtifact.objects.filter(
                case_id=str(source_job.case_id),
                job_id=str(source_job.id),
                type="TRANSCRIPT",
            )
            .order_by("-created_at")
            .first()
        )
        source_label = source_artifact.title if source_artifact else str(source_job.id)
        existing_summary_titles = CaseArtifact.objects.filter(
            case_id=str(source_job.case_id),
            type="SUMMARY",
        ).values_list("title", flat=True)
        summary_title = unique_title("Summary", existing_summary_titles)

        organization_obj = source_job.organization or getattr(source_job.case, "organization", None)
        if organization_obj is None:
            try:
                organization_obj = source_job.case.organization
            except Exception:
                organization_obj = None
        if organization_obj is None:
            return Response(
                {"detail": "Organization context unavailable for summary job."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        org_id_str = str(organization_obj.id)
        try:
            analyze_config = AnalyzeConfig.from_env()
        except ValueError as exc:
            return Response(
                {"detail": f"Analyze configuration is invalid: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        llm_settings = load_llm_settings()
        config_payload: dict[str, Any] | None = None
        if llm_config_id:
            config_payload = get_llm_configuration(
                organization_id=org_id_str,
                config_id=llm_config_id,
                target="analyze",
            )
        if not config_payload:
            config_payload = ensure_default_llm_configuration(
                organization_id=org_id_str,
                target="analyze",
                llm_settings=llm_settings,
            )
        if not config_payload:
            return Response(
                {
                    "detail": "Configure an Analyze LLM provider before queueing this job.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        stage_map = ComposeStageMap.from_mapping(
            optional_json_object(config_payload.get("stage_map"))
        )
        requested_providers = collect_requested_providers(
            analyze_config.provider_chain or [],
            config_payload.get("provider_chain") or [],
            stage_map,
        )
        provider_credentials = get_org_provider_credentials(org_id_str)
        provider_issues: list[str] = []
        if not requested_providers:
            provider_issues.append("No providers defined for the active Analyze configuration.")
        else:
            for provider_name in requested_providers:
                provider_meta = llm_settings.provider(provider_name)
                if provider_meta is None:
                    provider_issues.append(f"Provider '{provider_name}' is not recognized.")
                    continue

                cred_entry = provider_credentials.get(provider_name, {})
                if not cred_entry:
                    provider_label = provider_meta.display_name or provider_name
                    provider_issues.append(
                        f"Provider '{provider_label}' is not configured."
                    )
                    continue

                secret_details = get_provider_secret_with_metadata(org_id_str, provider_name) or {}
                secret_metadata = secret_details.get("metadata")
                if not isinstance(secret_metadata, dict):
                    secret_metadata = {}
                credential_metadata = (
                    cred_entry.get("metadata")
                    if isinstance(cred_entry.get("metadata"), dict)
                    else {}
                )
                merged_metadata = {**secret_metadata, **credential_metadata}
                has_api_key = bool(secret_details.get("api_key") or cred_entry.get("has_api_key"))
                analysis = evaluate_provider_setup(
                    provider=provider_meta,
                    endpoint=cred_entry.get("endpoint"),
                    has_api_key=has_api_key,
                    metadata=merged_metadata,
                    models=cred_entry.get("models"),
                )
                if not analysis.get("ready"):
                    issues = analysis.get("issues") or ["Provider configuration is incomplete."]
                    for issue in issues:
                        provider_issues.append(
                            f"{provider_meta.display_name or provider_name}: {issue}"
                        )

        if provider_issues:
            return Response(
                {
                    "detail": "Analyze cannot start until required LLM providers are enabled.",
                    "issues": provider_issues,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            summary_job = Job.objects.create(
                case=source_job.case,
                organization=organization_obj,
                audio_input=source_job.audio_input,
                mode=source_job.mode,
                diarization=False,
                language=source_job.language,
                transcript_path=transcript_path,
                duration_s=source_job.duration_s,
            )

        ensure_case_dirs(str(source_job.case_id), source_job.organization_id)
        meta_seed: dict[str, Any] = {
            "job_kind": "analyze",
            "job_title": summary_title,
            "agent_type": "analyze",
            "agent_label": "Analyze",
            "source_job_id": str(source_job.id),
            "source_job_title": source_label,
            "source_transcript_path": transcript_path,
        }
        if llm_config_id:
            meta_seed["requested_llm_config_id"] = llm_config_id

        update_job_meta(
            str(source_job.case_id),
            source_job.organization_id,
            str(summary_job.id),
            meta_seed,
        )
        append_job_log(
            str(source_job.case_id),
            source_job.organization_id,
            str(summary_job.id),
            f"Queued analyze job from transcription {source_job.id}",
        )

        send_job_update(
            str(summary_job.id),
            event="job.created",
            status=Job.Status.PENDING,
            case_id=str(summary_job.case_id),
        )

        analyze_job.delay(
            case_id=str(summary_job.case_id),
            job_id=str(summary_job.id),
            llm_config_id=llm_config_id,
            source_job_id=str(source_job.id),
        )
        audit_emit(
            request,
            case_id=str(source_job.case_id),
            event="analysis.analyze.requested",
            data={
                "job_id": str(summary_job.id),
                "source_job_id": str(source_job.id),
                "llm_config_id": llm_config_id,
            },
        )
        return Response(
            {"status": "queued", "job_id": str(summary_job.id)},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["post"], url_path="analyze/compose")
    def analyze_compose(self, request, pk=None):
        summary_job = self.get_object()
        payload = request.data if hasattr(request, "data") else {}
        llm_config_id = None
        if isinstance(payload, dict):
            config_value = payload.get("llm_config_id")
            if isinstance(config_value, str) and config_value.strip():
                llm_config_id = config_value.strip()

        organization_obj = summary_job.organization or getattr(
            summary_job.case, "organization", None
        )
        if organization_obj is None:
            try:
                organization_obj = summary_job.case.organization
            except Exception:
                organization_obj = None
        if organization_obj is None:
            return Response(
                {"detail": "Organization context unavailable for compose job."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            new_job = Job.objects.create(
                case=summary_job.case,
                organization=organization_obj,
                audio_input=summary_job.audio_input,
                mode=summary_job.mode,
                diarization=summary_job.diarization,
                language=summary_job.language,
                transcript_path=summary_job.transcript_path,
                duration_s=summary_job.duration_s,
            )

        ensure_case_dirs(str(summary_job.case_id), summary_job.organization_id)
        meta_seed: dict[str, Any] = {
            "job_kind": "compose",
            "agent_type": "compose",
            "job_title": unique_title(
                "Compose",
                CaseArtifact.objects.filter(
                    case_id=str(summary_job.case_id), type="COMPOSE"
                ).values_list("title", flat=True),
            ),
            "summary_job_id": str(summary_job.id),
        }
        if llm_config_id:
            meta_seed["requested_llm_config_id"] = llm_config_id

        update_job_meta(
            str(summary_job.case_id),
            summary_job.organization_id,
            str(new_job.id),
            meta_seed,
        )
        append_job_log(
            str(summary_job.case_id),
            summary_job.organization_id,
            str(new_job.id),
            f"Queued compose job from summary {summary_job.id}",
        )

        send_job_update(
            str(new_job.id),
            event="job.created",
            status=Job.Status.PENDING,
            case_id=str(new_job.case_id),
        )

        compose_job.delay(
            case_id=str(new_job.case_id),
            job_id=str(new_job.id),
            summary_job_id=str(summary_job.id),
            llm_config_id=llm_config_id,
        )
        audit_emit(
            request,
            case_id=str(summary_job.case_id),
            event="analysis.compose.requested",
            data={
                "job_id": str(new_job.id),
                "summary_job_id": str(summary_job.id),
                "llm_config_id": llm_config_id,
            },
        )

        return Response(
            {"status": "queued", "job_id": str(new_job.id)}, status=status.HTTP_202_ACCEPTED
        )

    @action(detail=True, methods=["get"], url_path="download-analysis")
    def download_analysis(self, request, pk=None):
        job = self.get_object()
        kind = (request.query_params.get("kind") or "").strip()
        if not kind:
            return Response(
                {"detail": "Missing kind parameter."}, status=status.HTTP_400_BAD_REQUEST
            )

        meta_key = ANALYSIS_KIND_TO_META_KEY.get(kind)
        if meta_key is None:
            return Response(
                {"detail": "Unsupported analysis kind."}, status=status.HTTP_400_BAD_REQUEST
            )

        case_id = str(job.case_id)
        org_id = job.organization_id or job.case.organization_id
        meta = read_job_meta(case_id, org_id, str(job.id))
        path_hint = meta.get(meta_key)
        if not path_hint:
            return Response(
                {"detail": "Artifact not found for requested kind."},
                status=status.HTTP_404_NOT_FOUND,
            )

        case_dir, _, _ = case_paths(case_id, org_id)
        path_obj = resolve_case_relative(str(path_hint), case_dir)
        if path_obj is None or not path_obj.exists():
            return Response(
                {"detail": "Artifact file is missing."}, status=status.HTTP_404_NOT_FOUND
            )

        audit_emit(
            request,
            case_id=case_id,
            event="analysis.download",
            data={"job_id": str(job.id), "kind": kind},
        )

        return FileResponse(path_obj.open("rb"), as_attachment=True, filename=path_obj.name)

    @action(detail=True, methods=["post"], url_path="title")
    def update_title(self, request, pk=None):
        job = self.get_object()
        artifact = (
            CaseArtifact.objects.filter(
                case_id=str(job.case_id), job_id=str(job.id), type="TRANSCRIPT"
            )
            .order_by("-created_at")
            .first()
        )
        if not artifact:
            return Response(
                {"detail": "Transcript not found for this job."}, status=status.HTTP_404_NOT_FOUND
            )
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
            telemetry = JobTelemetrySerializer(
                job, context={"request": request, "ui_mode": True}
            ).data
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
        append_job_log(
            str(job.case_id),
            job.organization_id,
            str(job.id),
            f"Transcript title set to '{new_title}'",
        )
        headers = {
            "HX-Trigger": stringify_json(
                {"job-title-updated": {"job_id": str(job.id), "title": new_title}}
            )
        }
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
        return render(
            request, "platform_ui/components/jobs/job_detail.html", context, headers=headers
        )

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
        from django.shortcuts import get_object_or_404

        case_id = request.data.get("case")
        if not case_id:
            return Response({"detail": "Missing case"}, status=status.HTTP_400_BAD_REQUEST)
        case = get_object_or_404(Case.objects.select_related("organization"), pk=case_id)
        mode = request.data.get("mode", Job.Mode.ON_DEMAND)
        diarization = str(request.data.get("diarization", "false")).lower() in ("1", "true", "yes")
        language = request.data.get("language", "en-CA")
        if diarization and mode != Job.Mode.BATCH:
            return Response(
                {"detail": "Diarization is only supported in batch mode."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file_obj = request.FILES.get("audio")
        audio_url = (request.data.get("audio_url") or "").strip()
        if not file_obj and not audio_url:
            return Response(
                {"detail": "Provide 'audio' file or 'audio_url'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            job = Job.objects.create(
                case=case, audio_input="", mode=mode, diarization=diarization, language=language
            )
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

        force_wav_requested = str(request.data.get("force_wav") or "").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

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
            data={
                "job_id": str(job.id),
                "mode": mode,
                "file": bool(file_obj),
                "force_wav_conversion": force_wav_requested,
            },
        )
        return Response(out.data, status=status.HTTP_201_CREATED, headers=headers)
