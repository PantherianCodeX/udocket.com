from __future__ import annotations

import json
import logging
import os
import uuid

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
from apps.platform.operations.tasks import transcribe_job, _update_job_meta
from apps.platform.operations.channels import send_job_update
from apps.platform.operations.audit import emit as audit_emit
from django.db import transaction
from apps.platform.operations.tasks import summarize_job, timeline_job, graph_job
from apps.platform.tenancy import scope_jobs
from apps.platform.operations.storage import ensure_case_dirs, ops_dir as storage_ops_dir


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
        # Enqueue task
        transcribe_job.delay(
            case_id=str(job.case_id),
            job_id=str(job.id),
            audio_input=job.audio_input,
            mode=job.mode,
            diarization=job.diarization,
            language=job.language,
        )
        out = JobSerializer(instance=job)
        headers = {"Location": f"/api/v1/jobs/{job.id}/"}
        audit_emit(request, case_id=str(job.case_id), event="job.created", data={"job_id": str(job.id), "mode": job.mode})
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
            "transcript_path": job.transcript_path,
            "finished_at": job.finished_at,
            "review_status": job.review_status,
            "review_comment": job.review_comment,
            "reviewed_at": job.reviewed_at,
            "reviewed_by": self._user_label(job.reviewed_by),
            "review_activity_id": str(job.review_activity_id) if job.review_activity_id else None,
        }
        return Response(payload)

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
        audio_path = getattr(job, "audio_input", None)
        if not audio_path or not str(audio_path).startswith("/"):
            raise Http404
        path_obj = Path(audio_path)
        if not path_obj.exists():
            raise Http404
        audit_emit(request, case_id=str(job.case_id), event="job.download_audio", data={"job_id": str(job.id)})
        filename = path_obj.name or f"{job.id}_audio"
        return FileResponse(path_obj.open("rb"), filename=filename, as_attachment=True)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        job = self.get_object()
        if job.status not in {Job.Status.PENDING, Job.Status.RUNNING}:
            return Response({"detail": "Job is not cancellable."}, status=status.HTTP_400_BAD_REQUEST)
        job.status = Job.Status.CANCELLED
        job.finished_at = timezone.now()
        job.error_message = "Cancelled by user"
        job.save(update_fields=["status", "finished_at", "error_message"])
        try:
            self._cancel_azure_transcription(job)
        except Exception:
            pass
        audit_emit(request, case_id=str(job.case_id), event="job.cancelled", data={"job_id": str(job.id)})
        send_job_update(str(job.id), event="job.cancelled", status=Job.Status.CANCELLED, case_id=str(job.case_id))
        return Response({"status": Job.Status.CANCELLED})

    @action(detail=True, methods=["post"], url_path="restart")
    def restart(self, request, pk=None):
        job = self.get_object()
        if job.status == Job.Status.RUNNING:
            return Response({"detail": "Job is currently running."}, status=status.HTTP_400_BAD_REQUEST)
        if not job.audio_input:
            return Response({"detail": "Original audio input is missing."}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            Job.objects.filter(pk=job.pk).update(
                status=Job.Status.CANCELLED,
                finished_at=timezone.now(),
                error_message="Superseded by restart",
            )
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
        )
        audit_emit(
            request,
            case_id=str(job.case_id),
            event="job.restarted",
            data={"job_id": str(job.id), "replacement_job_id": str(new_job.id)},
        )
        send_job_update(str(job.id), event="job.cancelled", status=Job.Status.CANCELLED, case_id=str(job.case_id))
        send_job_update(str(new_job.id), event="job.created", status=Job.Status.PENDING, case_id=str(new_job.case_id))
        return Response({"status": Job.Status.PENDING, "job_id": str(new_job.id)})

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
                _update_job_meta(
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
                _update_job_meta(
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

        # Enqueue task
        transcribe_job.delay(
            case_id=str(job.case_id),
            job_id=str(job.id),
            audio_input=job.audio_input,
            mode=job.mode,
            diarization=job.diarization,
            language=job.language,
        )
        out = JobSerializer(instance=job)
        headers = {"Location": f"/api/v1/jobs/{job.id}/"}
        audit_emit(request, case_id=str(case_id), event="job.uploaded", data={"job_id": str(job.id), "mode": mode, "file": bool(file_obj)})
        return Response(out.data, status=status.HTTP_201_CREATED, headers=headers)
