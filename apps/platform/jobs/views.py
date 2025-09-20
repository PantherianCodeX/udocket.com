from __future__ import annotations

import os
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from apps.platform.authorization.access_policies import JobAccessPolicy
from django.conf import settings
from rest_framework.response import Response
from django.http import FileResponse, Http404

from apps.platform.cases.models import Case
from apps.platform.jobs.models import Job
from apps.platform.jobs.serializers import JobCreateSerializer, JobSerializer
from apps.platform.operations.tasks import transcribe_job
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
        qs = super().get_queryset().select_related("case", "case__organization")
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
        }
        return Response(payload)

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        job = self.get_object()
        if not job.transcript_path:
            raise Http404
        audit_emit(request, case_id=str(job.case_id), event="job.download_transcript", data={"job_id": str(job.id)})
        return FileResponse(open(job.transcript_path, "rb"), filename=f"{job.id}__transcript.txt", content_type="text/plain")

    @action(detail=True, methods=["get"], url_path="logs")
    def logs(self, request, pk=None):
        job = self.get_object()
        case_id = str(job.case_id)
        ops = storage_ops_dir(case_id, job.case.organization_id) / f"{job.id}_transcription.log"
        if not ops.exists():
            raise Http404
        audit_emit(request, case_id=case_id, event="job.download_logs", data={"job_id": str(job.id)})
        return FileResponse(open(ops, "rb"), filename=f"{job.id}_transcription.log", content_type="text/plain")

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
