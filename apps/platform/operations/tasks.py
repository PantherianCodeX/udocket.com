from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
import hashlib
import uuid
import json
import logging
import mimetypes
import shutil
import subprocess

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from packages.udocket_core.agents import (
    TranscriptionAgent,
    TranscriptionConfig,
    normalize_audio,
)
from packages.udocket_core.audio import probe_audio_metadata
from apps.platform.operations.channels import send_job_update, send_case_update
from apps.platform.jobs.models import Job
from apps.platform.artifacts.models import CaseArtifact
from apps.platform.operations.blob_upload import upload_with_sas, UploadCancelled
from apps.platform.operations.models import TaskRun
from apps.platform.cases.models import Case
from apps.platform.operations.audit import emit as audit_emit
from apps.platform.operations.storage import ensure_case_dirs, tenant_case_root, ops_dir as storage_ops_dir
from apps.platform.operations.utils import update_job_meta, append_job_log

# Backwards compatibility for tests importing _update_job_meta
def _update_job_meta(case_id: str, organization_id: Optional[str], job_id: str, updates: Dict[str, Any]) -> None:  # pragma: no cover - shim
    return update_job_meta(case_id, organization_id, job_id, updates)
import re
from apps.platform.jobs.utils import unique_title

log = logging.getLogger("apps.platform.operations.tasks")


def _sha256_file(path: Path) -> Optional[str]:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except Exception:
        return None



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
    force_wav_conversion: bool = False,
) -> Dict[str, Any]:
    """Run transcription using the importable agent.

    Arguments are explicit to decouple from legacy DB schema.
    """
    upload_required = (
        mode == "batch"
        and isinstance(audio_input, str)
        and not audio_input.lower().startswith(("http://", "https://"))
    )

    org_id: Optional[str] = None
    case_obj: Optional[Case] = None
    try:
        job_obj = Job.objects.select_related("case").get(pk=job_id)
        if job_obj.status == Job.Status.CANCELLED:
            log.info("job already cancelled before execution", extra={"job_id": job_id})
            return {"status": Job.Status.CANCELLED, "job_id": job_id, "case_id": case_id}
        job_obj.status = Job.Status.UPLOADING if upload_required else Job.Status.RUNNING
        job_obj.started_at = timezone.now()
        job_obj.upload_progress = 0.0 if upload_required else None
        job_obj.save(update_fields=["status", "started_at", "upload_progress"])
        org_id = job_obj.organization_id or getattr(job_obj.case, "organization_id", None)
        case_obj = getattr(job_obj, "case", None)
    except Exception:
        job_obj = None
    if org_id is None:
        org_id = (
            Case.objects.filter(pk=case_id)
            .values_list("organization_id", flat=True)
            .first()
        )
    if case_obj is None:
        case_obj = Case.objects.select_related("organization").filter(pk=case_id).first()
    case_dir = ensure_case_dirs(case_id, org_id)
    cfg = TranscriptionConfig.from_env()
    agent = TranscriptionAgent(cfg)

    audio_meta_updates: Dict[str, Any] = {}
    try:
        if isinstance(audio_input, str) and audio_input and not audio_input.startswith("http"):
            audio_path = Path(audio_input)
            if audio_path.exists():
                audio_meta_updates = {
                    "audio_sha256": _sha256_file(audio_path),
                    "audio_size_bytes": audio_path.stat().st_size,
                    "audio_mime": mimetypes.guess_type(audio_path.name)[0],
                }
                audio_meta_updates.update(probe_audio_metadata(audio_path))
                if job_obj is not None:
                    dirty_fields: list[str] = []
                    duration_val = audio_meta_updates.get("audio_duration_s")
                    if duration_val and not job_obj.duration_s:
                        try:
                            job_obj.duration_s = float(duration_val)
                            dirty_fields.append("duration_s")
                        except Exception:
                            pass
                    bitrate_val = audio_meta_updates.get("audio_bitrate_kbps")
                    if bitrate_val and job_obj.audio_bitrate_kbps != int(bitrate_val):
                        job_obj.audio_bitrate_kbps = int(bitrate_val)
                        dirty_fields.append("audio_bitrate_kbps")
                    channels_val = audio_meta_updates.get("audio_channels")
                    if channels_val and job_obj.audio_channels != int(channels_val):
                        job_obj.audio_channels = int(channels_val)
                        dirty_fields.append("audio_channels")
                    sr_val = audio_meta_updates.get("audio_sample_rate_hz")
                    if sr_val and job_obj.sample_rate_hz != int(sr_val):
                        job_obj.sample_rate_hz = int(sr_val)
                        dirty_fields.append("sample_rate_hz")
                    if dirty_fields:
                        try:
                            job_obj.save(update_fields=dirty_fields)
                        except Exception:
                            pass
    except Exception:
        audio_meta_updates = {}

    if audio_meta_updates:
        try:
            update_job_meta(case_id, org_id, job_id, audio_meta_updates)
        except Exception:
            pass

    # Update DB status and notify; record TaskRun
    log.info("job claimed", extra={"job_id": job_id, "case_id": case_id, "mode": mode, "diarization": diarization})
    try:
        append_job_log(
            case_id,
            org_id,
            job_id,
            f"Worker started transcription (mode={mode}, diarization={'on' if diarization else 'off'}, language={language or cfg.default_language if hasattr(cfg, 'default_language') else (language or 'auto')})",
        )
    except Exception:
        pass
    if upload_required:
        if bool(force_wav_conversion):
            send_job_update(
                job_id,
                event="job.converting",
                status=Job.Status.CONVERTING,
                case_id=case_id,
            )
    else:
        send_job_update(job_id, event="job.started", status=Job.Status.RUNNING, case_id=case_id)

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
    batch_upload_meta: Dict[str, Any] = {}
    try:
        # If batch mode and the input is a local file, upload to Azure Blob to obtain SAS URL
        ai = audio_input
        if upload_required:
            source_path = Path(audio_input)
            upload_path = source_path
            original_name = source_path.name
            cleanup_path: Optional[Path] = None
            normalization = normalize_audio(
                source_path,
                case_dir,
                case_id,
                metadata=audio_meta_updates or None,
                diarization=bool(diarization),
                force=bool(force_wav_conversion),
            )

            if normalization.converted:
                try:
                    try:
                        Job.objects.filter(pk=job_id).update(status=Job.Status.CONVERTING)
                    except Exception:
                        pass
                    try:
                        send_job_update(
                            job_id,
                            event="job.converting",
                            status=Job.Status.CONVERTING,
                            case_id=case_id,
                        )
                    except Exception:
                        pass
                    reasons_txt = ", ".join(normalization.reasons) or "format normalization"
                    append_job_log(
                        case_id,
                        org_id,
                        job_id,
                        f"Normalized source audio via ffmpeg ({reasons_txt})",
                    )
                except Exception:
                    pass

                try:
                    upload_path = normalization.path
                    if normalization.path != source_path:
                        cleanup_path = normalization.path
                    original_name = f"{source_path.stem}.wav"
                    batch_upload_meta.update(
                        {
                            "batch_upload_original_extension": source_path.suffix.lower(),
                            "batch_upload_converted": True,
                            "audio_conversion_reasons": normalization.reasons,
                        }
                    )
                    source_audio_meta = normalization.original_metadata or {}
                    target_audio_meta = normalization.metadata or {}
                    source_audio_applied = False
                    for key, value in source_audio_meta.items():
                        if key.startswith("audio_") and value is not None:
                            batch_upload_meta.setdefault(key, value)
                            source_audio_applied = True
                            batch_upload_meta.setdefault(f"source_{key}", value)
                    if not source_audio_applied:
                        for key, value in target_audio_meta.items():
                            if key.startswith("audio_") and value is not None:
                                batch_upload_meta.setdefault(key, value)
                    for key, value in target_audio_meta.items():
                        if key.startswith("audio_") and value is not None:
                            batch_upload_meta.setdefault(f"converted_{key}", value)

                    audio_dir = case_dir / "audio"
                    audio_dir.mkdir(parents=True, exist_ok=True)
                    original_display = source_path.name.split("__", 1)[-1] if "__" in source_path.name else source_path.name
                    requested_basename = Path(original_display).with_suffix(".wav").name

                    existing_meta = {}
                    src_meta_path = storage_ops_dir(case_id, org_id) / f"{job_id}_transcription_log.json"
                    if src_meta_path.exists():
                        try:
                            existing_meta = json.loads(src_meta_path.read_text(encoding="utf-8"))
                        except Exception:
                            existing_meta = {}

                    converted_job_obj: Optional[Job] = None
                    converted_job_id = existing_meta.get("converted_audio_job_id") or existing_meta.get("converted_wav_job_id")
                    if converted_job_id:
                        try:
                            converted_job_obj = Job.objects.select_related("case").get(pk=converted_job_id)
                            if str(converted_job_obj.case_id) != str(case_id):
                                converted_job_obj = None
                        except Job.DoesNotExist:
                            converted_job_obj = None

                    now_ts = timezone.now()
                    if converted_job_obj is None:
                        wav_job_uuid = uuid.uuid4()
                        try:
                            converted_job_obj = Job.objects.create(
                                id=wav_job_uuid,
                                case=case_obj,
                                organization=getattr(case_obj, "organization", None),
                                audio_input="",
                                mode=getattr(job_obj, "mode", Job.Mode.BATCH),
                                diarization=False,
                                language=getattr(job_obj, "language", language) or (language or cfg.default_language or "en-CA"),
                                status=Job.Status.SUCCEEDED,
                                started_at=now_ts,
                                finished_at=now_ts,
                            )
                        except Exception as exc:
                            log.warning("failed to create wav job", extra={"job_id": job_id, "error": str(exc)})
                            converted_job_obj = None
                    else:
                        wav_job_uuid = converted_job_obj.id

                    wav_job_id = str(wav_job_uuid) if converted_job_obj else None
                    if converted_job_obj and getattr(converted_job_obj, "audio_input", None):
                        converted_path = Path(str(converted_job_obj.audio_input))
                    else:
                        converted_path = audio_dir / requested_basename
                        if converted_path.exists():
                            base_path = Path(requested_basename)
                            stem = base_path.stem
                            suffix = base_path.suffix or ".wav"
                            counter = 2
                            while (audio_dir / f"{stem}_v{counter}{suffix}").exists():
                                counter += 1
                            converted_path = audio_dir / f"{stem}_v{counter}{suffix}"
                    converted_basename = converted_path.name
                    try:
                        if converted_path.exists():
                            converted_path.unlink()
                        shutil.copy2(upload_path, converted_path)
                    except Exception as exc:
                        log.warning(
                            "unable to persist converted wav",
                            extra={"job_id": job_id, "converted_job_id": wav_job_id, "error": str(exc)},
                        )
                        converted_path = Path(str(upload_path))

                    converted_stats = {}
                    try:
                        converted_stats = probe_audio_metadata(converted_path)
                    except Exception:
                        converted_stats = {}

                    converted_sha = _sha256_file(converted_path)
                    converted_size = None
                    try:
                        converted_size = converted_path.stat().st_size
                    except Exception:
                        converted_size = None

                    if converted_job_obj is not None:
                        converted_job_obj.audio_input = str(converted_path)
                        converted_job_obj.status = Job.Status.SUCCEEDED
                        converted_job_obj.finished_at = now_ts
                        converted_job_obj.started_at = converted_job_obj.started_at or now_ts
                        converted_job_obj.upload_progress = None
                        try:
                            converted_job_obj.duration_s = (
                                converted_stats.get("audio_duration_s")
                                or converted_job_obj.duration_s
                            )
                        except Exception:
                            pass
                        try:
                            converted_job_obj.save(
                                update_fields=[
                                    "audio_input",
                                    "status",
                                    "finished_at",
                                    "started_at",
                                    "upload_progress",
                                    "duration_s",
                                ]
                            )
                        except Exception:
                            converted_job_obj.save()
                        converted_job_id = str(converted_job_obj.id)

                        converted_meta_updates: Dict[str, Any] = {
                            "job_kind": "audio_conversion",
                            "job_title": converted_basename,
                            "agent_type": "Audio Conversion",
                            "audio_file": converted_basename,
                            "audio_path": str(converted_path),
                            "audio_sha256": converted_sha,
                            "audio_size_bytes": converted_size,
                            "audio_mime": "audio/wav",
                            "source_job_id": job_id,
                            "source_audio_path": str(source_path),
                            "source_audio_file": original_display,
                            "conversion_source_extension": source_path.suffix.lower(),
                            "conversion_completed_at": now_ts.isoformat(),
                        }
                        for key, value in (source_audio_meta or {}).items():
                            if key.startswith("audio_") and value is not None:
                                converted_meta_updates.setdefault(f"source_{key}", value)
                        if audio_meta_updates:
                            for key, value in audio_meta_updates.items():
                                if key.startswith("audio_") and value is not None:
                                    converted_meta_updates.setdefault(f"source_{key}", value)
                        for key, value in (target_audio_meta or {}).items():
                            if key.startswith("audio_") and value is not None:
                                converted_meta_updates.setdefault(f"converted_{key}", value)
                        if converted_sha:
                            converted_meta_updates.setdefault("converted_audio_sha256", converted_sha)
                        if converted_size is not None:
                            converted_meta_updates.setdefault("converted_audio_size_bytes", converted_size)
                        if converted_stats:
                            converted_meta_updates.update(converted_stats)
                        update_job_meta(case_id, org_id, converted_job_id, converted_meta_updates)
                        append_job_log(
                            case_id,
                            org_id,
                            converted_job_id,
                            f"Converted WAV created from job {job_id}",
                        )
                        try:
                            send_job_update(
                                converted_job_id,
                                event="job.created",
                                status=Job.Status.SUCCEEDED,
                                case_id=case_id,
                                job_title=converted_basename,
                                job_kind="audio_conversion",
                            )
                        except Exception:
                            log.exception(
                                "wav job emit failed",
                                extra={"job_id": job_id, "converted_job_id": converted_job_id},
                            )
                        try:
                            send_case_update(
                                case_id,
                                event="job.created",
                                job_id=converted_job_id,
                                job_kind="audio_conversion",
                            )
                        except Exception:
                            log.exception(
                                "case update emit failed",
                                extra={"case_id": case_id, "converted_job_id": converted_job_id},
                            )

                    batch_upload_meta["converted_temp_wav"] = True
                    if converted_job_id:
                        batch_upload_meta["converted_audio_job_id"] = converted_job_id
                    batch_upload_meta["converted_wav_path"] = str(converted_path)
                    batch_upload_meta["converted_audio_file"] = converted_basename
                    if converted_sha:
                        batch_upload_meta["converted_audio_sha256"] = converted_sha
                    if converted_size is not None:
                        batch_upload_meta["converted_audio_size_bytes"] = converted_size
                    update_job_meta(case_id, org_id, job_id, batch_upload_meta)
                    append_job_log(
                        case_id,
                        org_id,
                        job_id,
                        f"Conversion complete: {converted_basename}",
                    )
                    if converted_job_id:
                        try:
                            current_status = (
                                Job.objects.filter(pk=job_id).values_list("status", flat=True).first()
                                or (job_obj.status if job_obj else Job.Status.RUNNING)
                            )
                            send_job_update(
                                job_id,
                                event="job.updated",
                                status=current_status,
                                case_id=case_id,
                                converted_audio_job_id=converted_job_id,
                            )
                        except Exception:
                            log.exception(
                                "source job update emit failed",
                                extra={"job_id": job_id, "converted_job_id": converted_job_id},
                            )
                        try:
                            send_case_update(
                                case_id,
                                event="job.updated",
                                job_id=job_id,
                                converted_audio_job_id=converted_job_id,
                            )
                        except Exception:
                            log.exception(
                                "case job update emit failed",
                                extra={"case_id": case_id, "job_id": job_id},
                            )
                except Exception as exc:
                    raise RuntimeError(f"Batch upload conversion failed: {exc}") from exc
            else:
                batch_upload_meta["batch_upload_converted"] = False
                batch_upload_meta["converted_temp_wav"] = False
                append_job_log(
                    case_id,
                    org_id,
                    job_id,
                    "Using original audio format for batch upload",
                )
            log.info("uploading source to blob", extra={"job_id": job_id})
            append_job_log(case_id, org_id, job_id, f"Uploading audio to Azure Blob ({original_name})")
            last_progress = {"value": -1.0}

            def _progress_cb(ratio: float) -> None:
                pct = round(ratio * 100, 1)
                if pct == last_progress["value"]:
                    return
                last_progress["value"] = pct
                try:
                    Job.objects.filter(
                        pk=job_id,
                        status__in=[
                            Job.Status.PENDING,
                            getattr(Job.Status, "CONVERTING", "CONVERTING"),
                            Job.Status.UPLOADING,
                        ],
                    ).update(status=Job.Status.UPLOADING, upload_progress=pct)
                except Exception:
                    pass
                try:
                    send_job_update(
                        job_id,
                        event="job.uploading",
                        status=Job.Status.UPLOADING,
                        case_id=case_id,
                        progress_percent=pct,
                        upload_progress=pct,
                    )
                except Exception:
                    pass

            def _cancel_check() -> bool:
                return Job.objects.filter(
                    pk=job_id,
                    status__in=(Job.Status.CANCELLING, Job.Status.CANCELLED),
                ).exists()

            try:
                _progress_cb(0.0)
                ai = upload_with_sas(
                    upload_path,
                    case_id,
                    job_id,
                    organization_id=org_id,
                    original_name=original_name,
                    cancel_check=_cancel_check,
                    progress_cb=_progress_cb,
                )
                try:
                    # Record the URL prefix (no SAS) for diagnostics
                    url_prefix = ai.split('?', 1)[0] if isinstance(ai, str) else ''
                    update_job_meta(case_id, org_id, job_id, {"batch_upload_url_prefix": url_prefix})
                    append_job_log(case_id, org_id, job_id, f"Blob uploaded: {url_prefix}")
                except Exception:
                    pass
            except UploadCancelled:
                log.info("upload cancelled mid-transfer", extra={"job_id": job_id})
                append_job_log(case_id, org_id, job_id, "Upload cancelled mid-transfer", level="warning")
                raise
            except Exception as exc:
                log.exception("blob upload failed", extra={"job_id": job_id, "error": str(exc)})
                append_job_log(case_id, org_id, job_id, f"Blob upload failed: {exc}", level="error")
                raise
            # Cleanup if we converted to a temporary WAV
            if cleanup_path and cleanup_path.exists():
                try:
                    cleanup_path.unlink(missing_ok=True)
                except Exception:
                    pass

            current_status = Job.objects.filter(pk=job_id).values_list("status", flat=True).first()
            if current_status in (Job.Status.CANCELLING, Job.Status.CANCELLED):
                raise UploadCancelled("Cancelled before transcription start")
            Job.objects.filter(pk=job_id).update(status=Job.Status.RUNNING, upload_progress=None)
            if batch_upload_meta:
                batch_upload_meta.setdefault("batch_upload_blob_name", original_name)
                update_job_meta(case_id, org_id, job_id, batch_upload_meta)
            if job_obj is not None:
                job_obj.status = Job.Status.RUNNING
                job_obj.upload_progress = None
            send_job_update(
                job_id,
                event="job.started",
                status=Job.Status.RUNNING,
                case_id=case_id,
                upload_progress=None,
            )
            log.info("uploaded source to blob", extra={"job_id": job_id})
            append_job_log(case_id, org_id, job_id, f"Upload complete: {original_name}")

        append_job_log(
            case_id,
            org_id,
            job_id,
            "Submitting transcription request to Azure Speech",
        )
        log.info(
            "invoking transcription agent",
            extra={
                "job_id": job_id,
                "mode": mode,
                "diarization": diarization,
                "language": language,
                "upload_required": upload_required,
            },
        )

        result = agent.transcribe(
            input=ai,
            case_id=case_id,
            case_dir=case_dir,
            job_id=job_id,
            language=language,
            mode=mode,
            diarization=diarization,
        )
        append_job_log(
            case_id,
            org_id,
            job_id,
            "Transcription agent completed; persisting results",
        )
        try:
            if result.meta_json.exists():
                meta_payload = json.loads(result.meta_json.read_text(encoding="utf-8"))
                azure_url = meta_payload.get("azure_transcription_url")
                if azure_url:
                    append_job_log(case_id, org_id, job_id, f"Azure transcription created: {azure_url}")
                    update_job_meta(case_id, org_id, job_id, {"azure_transcription_url": azure_url})
        except Exception as exc:
            log.debug("unable to parse transcription meta", extra={"job_id": job_id, "error": str(exc)})
    except Exception as e:
        if isinstance(e, UploadCancelled):
            log.info("job cancelled during preparation", extra={"job_id": job_id})
            append_job_log(case_id, org_id, job_id, "Job cancelled during preparation", level="warning")
            try:
                now = timezone.now()
                Job.objects.filter(pk=job_id).update(
                    status=Job.Status.CANCELLED,
                    finished_at=now,
                    error_message="Cancelled by user",
                    upload_progress=None,
                )
                if job_obj is not None:
                    job_obj.status = Job.Status.CANCELLED
                    job_obj.finished_at = now
                    job_obj.error_message = "Cancelled by user"
            except Exception:
                pass
            try:
                if tr is not None:
                    tr.status = "CANCELLED"
                    tr.finished_at = timezone.now()
                    tr.save(update_fields=["status", "finished_at"])
            except Exception:
                pass
        try:
            send_job_update(
                job_id,
                event="job.cancelled",
                status=Job.Status.CANCELLED,
                case_id=case_id,
                progress_percent=None,
                upload_progress=None,
            )
        except Exception:
            log.exception(
                "job cancel update emit failed",
                extra={"job_id": job_id, "event": "job.cancelled"},
            )
        return {"status": Job.Status.CANCELLED, "job_id": job_id, "case_id": case_id}

        log.exception("job failed", extra={"job_id": job_id, "error": str(e)})
        append_job_log(case_id, org_id, job_id, f"Job failed: {e}", level="error")
        payload = {
            "status": "FAILED",
            "job_id": job_id,
            "case_id": case_id,
            "error": str(e)[:1000],
            "progress_percent": None,
            "upload_progress": None,
        }
        try:
            if job_obj is None:
                job_obj = Job.objects.get(pk=job_id)
            if job_obj.status != Job.Status.CANCELLED:
                job_obj.status = Job.Status.FAILED
                job_obj.finished_at = timezone.now()
                job_obj.error_message = payload["error"]
                job_obj.upload_progress = None
                job_obj.save(update_fields=["status", "finished_at", "error_message", "upload_progress"])
        except Exception:
            pass
        try:
            if tr is not None:
                tr.status = "FAILED"
                tr.finished_at = timezone.now()
                tr.save(update_fields=["status", "finished_at"])
        except Exception:
            pass
        emit_payload = {k: v for k, v in payload.items() if k != "job_id"}
        try:
            send_job_update(job_id, event="job.failed", **emit_payload)
        except Exception:
            log.exception(
                "job failure update emit failed",
                extra={"job_id": job_id, "event": "job.failed"},
            )
        meta_updates = dict(audio_meta_updates)
        if batch_upload_meta:
            meta_updates.update(batch_upload_meta)
        try:
            update_job_meta(case_id, org_id, job_id, meta_updates)
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
        "progress_percent": None,
        "upload_progress": None,
    }
    try:
        if job_obj is None:
            job_obj = Job.objects.get(pk=job_id)
        else:
            try:
                job_obj.refresh_from_db()
            except Exception:
                job_obj = Job.objects.get(pk=job_id)
        if job_obj.status == Job.Status.CANCELLED:
            log.info("job cancelled during execution; ignoring transcription output", extra={"job_id": job_id})
            try:
                if transcript_path_obj.exists():
                    transcript_path_obj.unlink()
            except Exception:
                pass
            try:
                if isinstance(ai, str) and ai.startswith("/"):
                    local_audio = Path(ai)
                    if local_audio.exists():
                        local_audio.unlink()
            except Exception:
                pass
            return {"status": Job.Status.CANCELLED, "job_id": job_id, "case_id": case_id}
        job_obj.status = Job.Status.SUCCEEDED
        job_obj.finished_at = timezone.now()
        job_obj.transcript_path = str(result.transcript_file)
        job_obj.duration_s = result.duration_s
        job_obj.upload_progress = None
        job_obj.save(update_fields=["status", "finished_at", "transcript_path", "duration_s", "upload_progress"])
        transcript_checksum: Optional[str] = None
        transcript_bytes: Optional[int] = None
        transcript_path_obj = Path(result.transcript_file)
        if transcript_path_obj.exists():
            try:
                transcript_bytes = transcript_path_obj.stat().st_size
            except Exception:
                transcript_bytes = None
            transcript_checksum = _sha256_file(transcript_path_obj)
        # Register artifact with checksum
        artifact_title = None
        try:
            existing_titles = CaseArtifact.objects.filter(
                case_id=str(case_id),
                type="TRANSCRIPT",
            ).values_list("title", flat=True)
            job_meta_title = None
            try:
                job_meta_path = storage_ops_dir(case_id, org_id) / f"{job_id}_transcription_log.json"
                if job_meta_path.exists():
                    job_meta_payload = json.loads(job_meta_path.read_text(encoding="utf-8"))
                    title_candidate = job_meta_payload.get("job_title")
                    if isinstance(title_candidate, str) and title_candidate.strip():
                        job_meta_title = title_candidate.strip()
            except Exception:
                job_meta_title = None
            artifact_title = job_meta_title or unique_title("Transcript", existing_titles)
            CaseArtifact.objects.create(
                case_id=str(case_id),
                case_fk=Job.objects.filter(pk=job_id).values_list('case', flat=True).first(),
                job_id=str(job_id),
                type="TRANSCRIPT",
                title=artifact_title,
                path=str(result.transcript_file),
                checksum=transcript_checksum or "",
                schema_version="v1",
                metadata={
                    "language": result.language,
                    "region": result.region,
                    "duration_s": result.duration_s,
                },
            )
        except Exception:
            pass
        meta_updates = dict(audio_meta_updates)
        meta_updates.update(
            {
                "transcript_sha256": transcript_checksum,
                "transcript_bytes": transcript_bytes,
                "transcript_title": artifact_title,
            }
        )
        if job_meta_title:
            meta_updates.setdefault("job_title", job_meta_title)
        if batch_upload_meta:
            meta_updates.update(batch_upload_meta)
        try:
            update_job_meta(case_id, org_id, job_id, meta_updates)
        except Exception:
            pass
    except Exception:
        pass
    log.info("job succeeded", extra={"job_id": job_id, "transcript": str(result.transcript_file)})
    append_job_log(
        case_id,
        org_id,
        job_id,
        f"Job succeeded: transcript={Path(result.transcript_file).name} duration={payload.get('duration_s')}s",
    )
    try:
        if tr is not None:
            tr.status = "SUCCEEDED"
            tr.finished_at = timezone.now()
            tr.save(update_fields=["status", "finished_at"])
    except Exception:
        pass
    emit_payload = {k: v for k, v in payload.items() if k != "job_id"}
    try:
        if artifact_title:
            payload["title"] = artifact_title
            emit_payload["title"] = artifact_title
        send_job_update(job_id, event="job.succeeded", **emit_payload)
    except Exception:
        log.exception(
            "job success update emit failed",
            extra={"job_id": job_id, "event": "job.succeeded"},
        )
    try:
        send_case_update(case_id, event="artifact.created", kind="transcript", job_id=job_id)
    except Exception:
        log.exception(
            "case artifact update emit failed",
            extra={"case_id": case_id, "job_id": job_id, "event": "artifact.created"},
        )
    return payload


# ----------------------
# Analysis task helpers
# ----------------------

def _case_paths(case_id: str, organization_id: str | None = None) -> tuple[Path, Path, Path]:
    base = ensure_case_dirs(case_id, organization_id)
    return base, base / "transcript", base / "analysis"


def _ops_dir(case_id: str, organization_id: str | None = None) -> Path:
    return storage_ops_dir(case_id, organization_id)


def _latest_transcript(case_id: str, organization_id: str | None = None) -> Path | None:
    _, tdir, _ = _case_paths(case_id, organization_id)
    if not tdir.exists():
        return None
    fx = sorted((p for p in tdir.glob("*__transcript.txt") if p.is_file()), key=lambda p: p.stat().st_mtime, reverse=True)
    return fx[0] if fx else None


def _write_json(p: Path, data: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_jsonl(p: Path, data: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


@shared_task(bind=True)
def summarize_job(*_args, case_id: str, job_id: str) -> Dict[str, Any]:
    job = Job.objects.select_related("case").get(pk=job_id)
    org_id = job.organization_id or job.case.organization_id
    case_dir, _, analysis_dir = _case_paths(case_id, org_id)
    src = Path(job.transcript_path) if job.transcript_path else _latest_transcript(case_id, org_id)
    if not src or not src.exists():
        raise RuntimeError("No transcript found to summarize")

    out = analysis_dir / f"{job_id}__summary_v1.md"
    text = Path(src).read_text(encoding="utf-8", errors="ignore")
    # Simple offline summary: first 200 lines or 2000 chars
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    head = "\n".join(lines[:200])
    if len(head) > 2000:
        head = head[:2000] + "\n…"
    content = f"# Summary for {job_id}\n\nGenerated from transcript: {src.name}\n\n{head}\n"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")

    # Register artifact
    try:
        import hashlib

        h = hashlib.sha256()
        with open(out, "rb") as f:
            for ch in iter(lambda: f.read(65536), b""):
                h.update(ch)
        CaseArtifact.objects.create(
            case_id=case_id,
            case_fk=job.case,
            job_id=str(job_id),
            type="SUMMARY",
            title=f"Summary {job_id}",
            path=str(out),
            checksum=h.hexdigest(),
            schema_version="v1",
            metadata={"source_transcript": str(src)},
        )
    except Exception:
        pass
    audit_emit(None, case_id=case_id, event="analysis.summary.created", data={"job_id": job_id, "file": str(out)})
    # Ops logs
    try:
        opsd = _ops_dir(case_id, org_id)
        meta = {
            "case_id": case_id,
            "job_id": job_id,
            "artifact": str(out),
            "checksum": h.hexdigest() if 'h' in locals() else None,
            "source_transcript": str(src),
            "ts": timezone.now().isoformat(),
            "schema_version": "v1",
            "status": "ok",
        }
        _write_json(opsd / f"{job_id}__summary_log.json", meta)
        _append_jsonl(opsd / "ops_summary.jsonl", meta)
    except Exception:
        pass
    try:
        send_case_update(case_id, event="artifact.created", kind="summary", job_id=job_id)
    except Exception:
        pass
    return {"status": "ok", "summary_file": str(out)}


@shared_task(bind=True)
def timeline_job(*_args, case_id: str, job_id: str) -> Dict[str, Any]:
    job = Job.objects.select_related("case").get(pk=job_id)
    org_id = job.organization_id or job.case.organization_id
    _, _, analysis_dir = _case_paths(case_id, org_id)
    src = Path(job.transcript_path) if job.transcript_path else _latest_transcript(case_id, org_id)
    if not src or not src.exists():
        raise RuntimeError("No transcript found to build timeline")
    rx = re.compile(r"^\[(\d{2}):(\d{2})\]\s+(?:SPK_(\d+):\s+)?(.*)$")
    events: list[dict[str, Any]] = []
    for ln in src.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = rx.match(ln.strip())
        if not m:
            continue
        mm, ss, spk, text = m.groups()
        ts = int(mm) * 60 + int(ss)
        events.append({
            "ts_start": ts,
            "ts_end": None,
            "speaker": f"SPK_{spk}" if spk else None,
            "text": text.strip(),
            "labels": [],
        })
    out = analysis_dir / f"{job_id}__timeline_v1.json"
    _write_json(out, events)
    try:
        import hashlib

        h = hashlib.sha256()
        with open(out, "rb") as f:
            for ch in iter(lambda: f.read(65536), b""):
                h.update(ch)
        CaseArtifact.objects.create(
            case_id=case_id,
            case_fk=job.case,
            job_id=str(job_id),
            type="TIMELINE",
            title=f"Timeline {job_id}",
            path=str(out),
            checksum=h.hexdigest(),
            schema_version="v1",
            metadata={"source_transcript": str(src), "events": len(events)},
        )
    except Exception:
        pass
    audit_emit(None, case_id=case_id, event="analysis.timeline.created", data={"job_id": job_id, "events": len(events)})
    try:
        opsd = _ops_dir(case_id, org_id)
        meta = {
            "case_id": case_id,
            "job_id": job_id,
            "artifact": str(out),
            "checksum": h.hexdigest() if 'h' in locals() else None,
            "source_transcript": str(src),
            "events": len(events),
            "ts": timezone.now().isoformat(),
            "schema_version": "v1",
            "status": "ok",
        }
        _write_json(opsd / f"{job_id}__timeline_log.json", meta)
        _append_jsonl(opsd / "ops_timeline.jsonl", meta)
    except Exception:
        pass
    try:
        send_case_update(case_id, event="artifact.created", kind="timeline", job_id=job_id)
    except Exception:
        pass
    return {"status": "ok", "timeline_file": str(out), "events": len(events)}


@shared_task(bind=True)
def graph_job(*_args, case_id: str, job_id: str) -> Dict[str, Any]:
    job = Job.objects.select_related("case").get(pk=job_id)
    org_id = job.organization_id or job.case.organization_id
    _, _, analysis_dir = _case_paths(case_id, org_id)
    src = Path(job.transcript_path) if job.transcript_path else _latest_transcript(case_id, org_id)
    if not src or not src.exists():
        raise RuntimeError("No transcript found to extract entities/graph")
    text = src.read_text(encoding="utf-8", errors="ignore")
    # Extremely lightweight: pick capitalized tokens as candidate entities (demo only)
    tokens = re.findall(r"\b([A-Z][a-zA-Z]{2,})\b", text)
    names = sorted(set(tokens))[:50]
    entities = [{
        "id": f"E{i+1}",
        "name": n,
        "type": "OTHER",
        "mentions": [],
    } for i, n in enumerate(names)]
    graph = {"nodes": [{"id": e["id"], "label": e["name"], "type": e["type"]} for e in entities], "edges": []}
    entities_file = analysis_dir / f"{job_id}__entities_v1.json"
    graph_file = analysis_dir / f"{job_id}__graph_v1.json"
    _write_json(entities_file, {"entities": entities})
    _write_json(graph_file, graph)
    try:
        import hashlib

        h1 = hashlib.sha256(entities_file.read_bytes()).hexdigest()
        h2 = hashlib.sha256(graph_file.read_bytes()).hexdigest()
        CaseArtifact.objects.create(
            case_id=case_id,
            case_fk=job.case,
            job_id=str(job_id),
            type="ENTITIES",
            title=f"Entities {job_id}",
            path=str(entities_file),
            checksum=h1,
            schema_version="v1",
            metadata={"source_transcript": str(src), "entities": len(entities)},
        )
        CaseArtifact.objects.create(
            case_id=case_id,
            case_fk=job.case,
            job_id=str(job_id),
            type="GRAPH",
            title=f"Graph {job_id}",
            path=str(graph_file),
            checksum=h2,
            schema_version="v1",
            metadata={"source_transcript": str(src), "nodes": len(graph["nodes"]), "edges": 0},
        )
    except Exception:
        pass
    audit_emit(None, case_id=case_id, event="analysis.graph.created", data={"job_id": job_id, "entities": len(entities)})
    try:
        opsd = _ops_dir(case_id, org_id)
        meta = {
            "case_id": case_id,
            "job_id": job_id,
            "entities_file": str(entities_file),
            "graph_file": str(graph_file),
            "entities_checksum": h1 if 'h1' in locals() else None,
            "graph_checksum": h2 if 'h2' in locals() else None,
            "source_transcript": str(src),
            "entities": len(entities),
            "edges": 0,
            "ts": timezone.now().isoformat(),
            "schema_version": "v1",
            "status": "ok",
        }
        _write_json(opsd / f"{job_id}__graph_log.json", meta)
        _append_jsonl(opsd / "ops_graph.jsonl", meta)
    except Exception:
        pass
    try:
        send_case_update(case_id, event="artifact.created", kind="graph", job_id=job_id)
    except Exception:
        pass
    return {"status": "ok", "entities_file": str(entities_file), "graph_file": str(graph_file), "entities": len(entities), "edges": 0}
