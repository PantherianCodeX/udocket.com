from __future__ import annotations

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from django.conf import settings
from rest_framework.response import Response
from django.http import FileResponse, Http404
from django.conf import settings
from pathlib import Path

from apps.platform.jobs.models import Job
from apps.platform.jobs.serializers import JobCreateSerializer, JobSerializer
from apps.platform.operations.tasks import transcribe_job


class JobViewSet(viewsets.ModelViewSet):
    queryset = Job.objects.all()
    serializer_class = JobSerializer
    permission_classes = [AllowAny]  # TODO: replace with proper auth/policy

    def get_serializer_class(self):  # type: ignore[override]
        if self.action in ("create", "transcribe"):
            return JobCreateSerializer
        return JobSerializer

    def get_queryset(self):  # type: ignore[override]
        qs = super().get_queryset().select_related("case")
        user = getattr(self.request, "user", None)
        if user and user.is_authenticated:
            return qs.filter(case__memberships__user=user).distinct()
        return qs if getattr(settings, "PLATFORM_DEV_OPEN", True) else qs.none()

    def create(self, request, *args, **kwargs):  # type: ignore[override]
        """Create a job and immediately enqueue transcription."""
        ser = JobCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        job = Job.objects.create(**ser.validated_data)
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
        return FileResponse(open(job.transcript_path, "rb"), filename=f"{job.id}__transcript.txt", content_type="text/plain")

    @action(detail=True, methods=["get"], url_path="logs")
    def logs(self, request, pk=None):
        job = self.get_object()
        case_id = str(job.case_id)
        ops = Path(settings.MEDIA_ROOT) / "cases" / case_id / "ops" / f"{job.id}_transcription.log"
        if not ops.exists():
            raise Http404
        return FileResponse(open(ops, "rb"), filename=f"{job.id}_transcription.log", content_type="text/plain")
