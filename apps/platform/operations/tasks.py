from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from packages.udocket_core.agents import (
    TranscriptionAgent,
    TranscriptionConfig,
)
from apps.platform.operations.channels import send_job_update, send_case_update
from apps.platform.jobs.models import Job
from apps.platform.artifacts.models import CaseArtifact
from apps.platform.operations.blob_upload import upload_with_sas
from apps.platform.operations.models import TaskRun
from apps.platform.cases.models import Case
import logging

log = logging.getLogger("apps.platform.operations.tasks")


@shared_task(bind=True)
def transcribe_job(
    self,
    *,
    case_id: str,
    job_id: str,
    audio_input: str,
    mode: str = "on-demand",
    diarization: bool = False,
    language: Optional[str] = None,
) -> Dict[str, Any]:
    """Run transcription using the importable agent.

    Arguments are explicit to decouple from legacy DB schema.
    """
    case_dir = Path(settings.MEDIA_ROOT) / "cases" / case_id
    cfg = TranscriptionConfig.from_env()
    agent = TranscriptionAgent(cfg)

    # Update DB status and notify; record TaskRun
    try:
        job_obj = Job.objects.get(pk=job_id)
        job_obj.status = Job.Status.RUNNING
        job_obj.started_at = timezone.now()
        job_obj.save(update_fields=["status", "started_at"])
    except Exception:
        job_obj = None
    log.info("job claimed", extra={"job_id": job_id, "case_id": case_id, "mode": mode, "diarization": diarization})
    send_job_update(job_id, event="job.started", status="RUNNING", case_id=case_id)

    # Create a TaskRun row for reproducibility
    tr = TaskRun(
        task_name="transcribe_job",
        task_id=getattr(self.request, "id", None) or "",
        status="RUNNING",
        job_id=job_id,
        case_id=case_id,
        meta={"mode": mode, "diarization": diarization, "language": language},
    )
    try:
        tr.save()
    except Exception:
        tr = None

    # Run the agent; only this block determines success vs. failure
    try:
        # If batch mode and the input is a local file, upload to Azure Blob to obtain SAS URL
        ai = audio_input
        if mode == "batch" and not (str(audio_input).startswith("http://") or str(audio_input).startswith("https://")):
            try:
                log.info("uploading source to blob", extra={"job_id": job_id})
                ai = upload_with_sas(Path(audio_input), case_id, job_id)
                log.info("uploaded source to blob", extra={"job_id": job_id})
            except Exception:
                try:
                    # Legacy fallback (used in FastAPI worker)
                    from apps.worker.app.blob_upload import upload_with_sas as legacy_upload

                    log.warning("blob upload failed; trying legacy uploader", extra={"job_id": job_id})
                    ai = legacy_upload(Path(audio_input), case_id, job_id)
                except Exception as e:
                    log.error("blob upload failed (both paths)", extra={"job_id": job_id, "error": str(e)})
                    raise

        result = agent.transcribe(
            input=ai,
            case_id=case_id,
            case_dir=case_dir,
            job_id=job_id,
            language=language,
            mode=mode,
            diarization=diarization,
        )
    except Exception as e:
        log.error("job failed", extra={"job_id": job_id, "error": str(e)})
        payload = {
            "status": "FAILED",
            "job_id": job_id,
            "case_id": case_id,
            "error": str(e)[:1000],
        }
        try:
            if job_obj is None:
                job_obj = Job.objects.get(pk=job_id)
            job_obj.status = Job.Status.FAILED
            job_obj.finished_at = timezone.now()
            job_obj.error_message = payload["error"]
            job_obj.save(update_fields=["status", "finished_at", "error_message"])
        except Exception:
            pass
        try:
            if tr is not None:
                tr.status = "FAILED"
                tr.finished_at = timezone.now()
                tr.save(update_fields=["status", "finished_at"])
        except Exception:
            pass
        try:
            send_job_update(job_id, event="job.failed", **payload)
        except Exception:
            pass
        raise

    # If agent succeeded, persist results; notification errors won't flip status
    payload: Dict[str, Any] = {
            "status": "SUCCEEDED",
            "job_id": job_id,
            "case_id": case_id,
            "transcript_file": str(result.transcript_file),
            "duration_s": result.duration_s,
            "language": result.language,
            "region": result.region,
        }
    try:
        if job_obj is None:
            job_obj = Job.objects.get(pk=job_id)
        job_obj.status = Job.Status.SUCCEEDED
        job_obj.finished_at = timezone.now()
        job_obj.transcript_path = str(result.transcript_file)
        job_obj.duration_s = result.duration_s
        job_obj.save(update_fields=["status", "finished_at", "transcript_path", "duration_s"])
        # Register artifact with checksum
        try:
            import hashlib

            h = hashlib.sha256()
            with open(result.transcript_file, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            CaseArtifact.objects.create(
                case_id=str(case_id),
                job_id=str(job_id),
                type="TRANSCRIPT",
                title=f"Transcript {job_id}",
                path=str(result.transcript_file),
                checksum=h.hexdigest(),
                schema_version="v1",
                metadata={
                    "language": result.language,
                    "region": result.region,
                    "duration_s": result.duration_s,
                },
            )
        except Exception:
            pass
    except Exception:
        pass
    log.info("job succeeded", extra={"job_id": job_id, "transcript": str(result.transcript_file)})
    try:
        if tr is not None:
            tr.status = "SUCCEEDED"
            tr.finished_at = timezone.now()
            tr.save(update_fields=["status", "finished_at"])
    except Exception:
        pass
    try:
        send_job_update(job_id, event="job.succeeded", **payload)
    except Exception:
        pass
    try:
        send_case_update(case_id, event="artifact.created", kind="transcript", job_id=job_id)
    except Exception:
        pass
    return payload
