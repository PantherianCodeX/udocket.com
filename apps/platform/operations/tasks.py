from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import hashlib
import uuid
import json
import logging
import mimetypes
import shutil
import subprocess
import os

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from packages.udocket_core.agents import (
    SummarizeAgent,
    SummarizeConfig,
    TranscriptionAgent,
    TranscriptionConfig,
    normalize_audio,
)
from packages.udocket_core.agents.guardian_lib import GuardianVerdict
from packages.udocket_core.llm.config import load_llm_settings
from packages.udocket_core.audio import probe_audio_metadata
from apps.platform.operations.channels import send_job_update, send_case_update
from apps.platform.jobs.models import Job
from apps.platform.artifacts.models import CaseArtifact
from apps.platform.operations.blob_upload import upload_with_sas, UploadCancelled
from apps.platform.cases.models import Case
from apps.platform.operations.audit import emit as audit_emit
from apps.platform.operations.storage import ensure_case_dirs, tenant_case_root, ops_dir as storage_ops_dir
from apps.platform.operations.llm import (
    ensure_default_llm_configuration,
    get_llm_configuration,
    get_provider_secret_with_metadata,
)
from apps.platform.operations.guardian import (
    build_guardian_context,
    build_guardian_review_record,
    snapshot_artifact_for_guardian,
    store_guardian_review,
)
from apps.platform.operations.utils import append_job_log, read_job_meta, update_job_meta
from apps.platform.operations.runtime import (
    JobRuntimeContext,
    _emit_job_update,
    _safe_job_log,
    _safe_job_meta,
)

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



def _unique_conversion_title(case_id: str, organization_id: Optional[str], source_job_id: str) -> str:
    existing: set[str] = set()
    ops_dir = storage_ops_dir(case_id, organization_id)
    if ops_dir.exists():
        for meta_path in ops_dir.glob("*_transcription_log.json"):
            try:
                payload = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if (
                isinstance(payload, dict)
                and payload.get("job_kind") == "audio_conversion"
                and str(payload.get("source_job_id")) == str(source_job_id)
            ):
                title_val = payload.get("job_title")
                if isinstance(title_val, str) and title_val.strip():
                    existing.add(title_val.strip())
    return unique_title("Conversion", existing)


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

    converting_status = getattr(Job.Status, "CONVERTING", "CONVERTING")

    org_id: Optional[str] = None
    case_obj: Optional[Case] = None
    try:
        job_obj = Job.objects.select_related("case").get(pk=job_id)
        if job_obj.status == Job.Status.CANCELLED:
            log.info("job already cancelled before execution", extra={"job_id": job_id})
            return {"status": Job.Status.CANCELLED, "job_id": job_id, "case_id": case_id}
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

    if job_obj is None:
        job_obj = Job.objects.select_related("case").get(pk=job_id)

    base_meta: Dict[str, Any] = {
        "job_kind": "transcription",
        "agent_type": "transcription",
        "agent_label": "Transcribe",
        "transcription_mode": mode,
        "requested_language": language or getattr(job_obj, "language", None),
        "transcription_status": str(getattr(job_obj, "status", "") or Job.Status.PENDING),
    }
    _safe_job_meta(case_id, org_id, job_id, base_meta)

    runtime = JobRuntimeContext(
        job=job_obj,
        case_id=case_id,
        org_id=org_id,
        task_name="transcribe_job",
        task_id=getattr(self.request, "id", None) or "",
        task_meta={
            "mode": mode,
            "diarization": diarization,
            "language": language,
        },
    )
    existing_job_meta = read_job_meta(case_id, org_id, job_id)

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

    # Update DB status and notify
    log.info(
        "job claimed",
        extra={"job_id": job_id, "case_id": case_id, "mode": mode, "diarization": diarization},
    )

    initial_status = Job.Status.RUNNING
    initial_event = "job.started"
    initial_meta_status = "running"
    initial_job_updates: Dict[str, Any] = {"upload_progress": None}
    initial_payload: Dict[str, Any] = {}

    if upload_required:
        if bool(force_wav_conversion):
            initial_status = converting_status
            initial_event = "job.converting"
            initial_meta_status = "converting"
            initial_job_updates["upload_progress"] = 0.0
        else:
            initial_status = Job.Status.UPLOADING
            initial_event = "job.uploading"
            initial_meta_status = "uploading"
            initial_job_updates["upload_progress"] = 0.0
            initial_payload = {"progress_percent": 0.0, "upload_progress": 0.0}

    start_log_message = (
        "Worker started transcription "
        f"(mode={mode}, diarization={'on' if diarization else 'off'}, "
        f"language={language or cfg.default_language if hasattr(cfg, 'default_language') else (language or 'auto')})"
    )

    start_meta_updates: Dict[str, Any] = {**base_meta, "transcription_status": initial_meta_status}
    celery_task_id = runtime.task_id or None
    if celery_task_id:
        history: List[str] = []
        history_payload = existing_job_meta.get("celery_task_history")
        if isinstance(history_payload, list):
            history = [value for value in history_payload if isinstance(value, str) and value]
        else:
            previous_id = existing_job_meta.get("celery_task_id")
            if isinstance(previous_id, str) and previous_id:
                history.append(previous_id)
        if celery_task_id not in history:
            history.append(celery_task_id)
        start_meta_updates["celery_task_id"] = celery_task_id
        if history:
            start_meta_updates["celery_task_history"] = history
        if runtime.task_name:
            start_meta_updates.setdefault("celery_task_name", runtime.task_name)

    started_at = runtime.start(
        status=initial_status,
        log_message=start_log_message,
        event=initial_event,
        meta_updates=start_meta_updates,
        job_updates=initial_job_updates,
        job_event_payload=initial_payload,
    )

    if celery_task_id and started_at:
        _safe_job_meta(
            case_id,
            org_id,
            job_id,
            {"celery_task_started_at": started_at.isoformat()},
        )

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
                    reasons_txt = ", ".join(normalization.reasons) or "format normalization"
                    runtime.transition(
                        status=converting_status,
                        log_message=f"Normalized source audio via ffmpeg ({reasons_txt})",
                        meta_updates={"transcription_status": "converting"},
                        job_updates={"upload_progress": 0.0},
                        event="job.converting",
                        job_event_payload={"upload_progress": 0.0},
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
                        try:
                            conversion_title = _unique_conversion_title(case_id, org_id, job_id)
                            converted_meta_updates["job_title"] = conversion_title
                        except Exception:
                            converted_meta_updates.setdefault("job_title", converted_basename)
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
                runtime.transition(
                    status=Job.Status.UPLOADING,
                    job_updates={"upload_progress": pct},
                    event="job.uploading",
                    job_event_payload={"progress_percent": pct, "upload_progress": pct},
                    task_meta_updates={"upload_progress": pct},
                )

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
            if batch_upload_meta:
                batch_upload_meta.setdefault("batch_upload_blob_name", original_name)
                update_job_meta(case_id, org_id, job_id, batch_upload_meta)
            runtime.transition(
                status=Job.Status.RUNNING,
                log_message=f"Upload complete: {original_name}",
                meta_updates={"transcription_status": "running"},
                job_updates={"upload_progress": None},
                event="job.started",
                job_event_payload={"upload_progress": None},
                task_meta_updates={"upload_progress": None},
            )
            log.info("uploaded source to blob", extra={"job_id": job_id})

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
    except UploadCancelled:
        cancel_meta = {**base_meta, "transcription_status": "cancelled"}
        cancel_meta.update(audio_meta_updates)
        cancel_meta.update(batch_upload_meta)
        if celery_task_id:
            cancel_meta.setdefault("celery_task_id", celery_task_id)
            cancel_meta["celery_task_status"] = "cancelled"
        cancel_payload = {
            "status": Job.Status.CANCELLED,
            "job_id": job_id,
            "case_id": case_id,
            "progress_percent": None,
            "upload_progress": None,
        }
        cancel_ts = runtime.cancel(
            reason="Cancelled by user",
            log_message="Job cancelled during preparation",
            meta_updates=cancel_meta,
            job_updates={"upload_progress": None, "error_message": "Cancelled by user"},
            job_event_payload={
                "progress_percent": None,
                "upload_progress": None,
                "error": "Cancelled by user",
            },
        )
        _safe_job_meta(
            case_id,
            org_id,
            job_id,
            {
                "transcription_completed_at": cancel_ts.isoformat() if cancel_ts else None,
                "celery_task_finished_at": cancel_ts.isoformat() if cancel_ts else None,
                "celery_task_status": "cancelled" if celery_task_id else None,
            },
        )
        try:
            if isinstance(ai, str) and ai.startswith("/"):
                local_audio = Path(ai)
                if local_audio.exists():
                    local_audio.unlink(missing_ok=True)
        except Exception:
            pass
        return cancel_payload

    except Exception as exc:
        error_message = str(exc)
        log.exception("job failed", extra={"job_id": job_id, "error": error_message})
        failure_payload = {
            "status": "FAILED",
            "job_id": job_id,
            "case_id": case_id,
            "error": error_message[:1000],
            "progress_percent": None,
            "upload_progress": None,
        }
        failure_meta = {**base_meta, "transcription_status": "failed"}
        failure_meta.update(audio_meta_updates)
        failure_meta.update(batch_upload_meta)
        if celery_task_id:
            failure_meta.setdefault("celery_task_id", celery_task_id)
            failure_meta["celery_task_status"] = "failed"
        fail_ts = runtime.fail(
            error=error_message,
            log_message=f"Job failed: {error_message}",
            meta_updates=failure_meta,
            job_updates={"upload_progress": None},
            job_event_payload={k: v for k, v in failure_payload.items() if k != "job_id"},
        )
        _safe_job_meta(
            case_id,
            org_id,
            job_id,
            {
                "transcription_completed_at": fail_ts.isoformat() if fail_ts else None,
                "celery_task_finished_at": fail_ts.isoformat() if fail_ts else None,
                "celery_task_status": "failed" if celery_task_id else None,
            },
        )
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
        job_obj.refresh_from_db()
    except Exception:
        job_obj = Job.objects.select_related("case").get(pk=job_id)
    if job_obj.status == Job.Status.CANCELLED:
        log.info("job cancelled during execution; ignoring transcription output", extra={"job_id": job_id})
        try:
            transcript_path_obj = Path(result.transcript_file)
            if transcript_path_obj.exists():
                transcript_path_obj.unlink(missing_ok=True)
        except Exception:
            pass
        try:
            if isinstance(ai, str) and ai.startswith("/"):
                local_audio = Path(ai)
                if local_audio.exists():
                    local_audio.unlink(missing_ok=True)
        except Exception:
            pass
        return {"status": Job.Status.CANCELLED, "job_id": job_id, "case_id": case_id}

    transcript_path_obj = Path(result.transcript_file)
    transcript_checksum: Optional[str] = None
    transcript_bytes: Optional[int] = None
    if transcript_path_obj.exists():
        try:
            transcript_bytes = transcript_path_obj.stat().st_size
        except Exception:
            transcript_bytes = None
        transcript_checksum = _sha256_file(transcript_path_obj)

    artifact_title: Optional[str] = None
    job_meta_title: Optional[str] = None
    try:
        existing_titles = CaseArtifact.objects.filter(
            case_id=str(case_id),
            type="TRANSCRIPT",
        ).values_list("title", flat=True)
        job_meta_path = storage_ops_dir(case_id, org_id) / f"{job_id}_transcription_log.json"
        if job_meta_path.exists():
            try:
                job_meta_payload = json.loads(job_meta_path.read_text(encoding="utf-8"))
                title_candidate = job_meta_payload.get("job_title")
                if isinstance(title_candidate, str) and title_candidate.strip():
                    job_meta_title = title_candidate.strip()
            except Exception:
                job_meta_title = None
        artifact_title = job_meta_title or unique_title("Transcript", existing_titles)
        CaseArtifact.objects.create(
            case_id=str(case_id),
            case_fk=case_obj or job_obj.case,
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

    meta_updates = {**base_meta, "transcription_status": "completed"}
    meta_updates.update(audio_meta_updates)
    meta_updates.update(batch_upload_meta)
    meta_updates.update(
        {
            "transcript_file": str(result.transcript_file),
            "transcript_sha256": transcript_checksum,
            "transcript_bytes": transcript_bytes,
            "transcript_title": artifact_title,
            "transcription_language": result.language,
            "transcription_region": result.region,
            "transcription_duration_s": result.duration_s,
        }
    )
    if celery_task_id:
        meta_updates.setdefault("celery_task_id", celery_task_id)
        meta_updates["celery_task_status"] = "succeeded"
    if job_meta_title:
        meta_updates.setdefault("job_title", job_meta_title)

    emit_payload = {k: v for k, v in payload.items() if k != "job_id"}
    if artifact_title:
        payload["title"] = artifact_title
        emit_payload["title"] = artifact_title

    job_updates = {
        "transcript_path": str(result.transcript_file),
        "duration_s": result.duration_s,
        "upload_progress": None,
    }

    log_message = f"Job succeeded: transcript={transcript_path_obj.name} duration={payload.get('duration_s')}s"
    finished_ts = runtime.succeed(
        log_message=log_message,
        meta_updates=meta_updates,
        job_updates=job_updates,
        job_event_payload=emit_payload,
    )
    _safe_job_meta(
        case_id,
        org_id,
        job_id,
        {
            "transcription_completed_at": finished_ts.isoformat() if finished_ts else None,
            "celery_task_finished_at": finished_ts.isoformat() if finished_ts else None,
            "celery_task_status": "succeeded" if celery_task_id else None,
        },
    )

    log.info("job succeeded", extra={"job_id": job_id, "transcript": str(result.transcript_file)})

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


def _resolve_case_relative(path_str: str, case_dir: Path) -> Optional[Path]:
    candidate = Path(path_str)
    if candidate.exists():
        return candidate
    candidate = case_dir / path_str
    if candidate.exists():
        return candidate
    return None


def _load_summary_timeline_events(
    meta: Dict[str, Any], case_dir: Path
) -> Tuple[List[Dict[str, Any]], Optional[Path]]:
    file_str = meta.get("summary_timeline_file") if isinstance(meta, dict) else None
    if not file_str:
        return [], None
    seeds_path = _resolve_case_relative(str(file_str), case_dir)
    if not seeds_path:
        return [], None
    try:
        payload = json.loads(seeds_path.read_text(encoding="utf-8"))
    except Exception:
        return [], None
    if isinstance(payload, dict) and "events" in payload:
        payload = payload.get("events")
    events: List[Dict[str, Any]] = []
    if isinstance(payload, list):
        for item in payload:
            if not isinstance(item, dict):
                continue
            events.append(
                {
                    "ts_start": item.get("ts_start"),
                    "ts_end": item.get("ts_end"),
                    "speaker": item.get("speaker"),
                    "text": item.get("text", ""),
                    "labels": list(item.get("labels") or []),
                }
            )
    if not events:
        return [], None
    return events, seeds_path


def _load_summary_entity_hints(
    meta: Dict[str, Any], case_dir: Path
) -> Tuple[Optional[Dict[str, Any]], Optional[Path]]:
    file_str = meta.get("summary_entity_file") if isinstance(meta, dict) else None
    if not file_str:
        return None, None
    hints_path = _resolve_case_relative(str(file_str), case_dir)
    if not hints_path:
        return None, None
    try:
        payload = json.loads(hints_path.read_text(encoding="utf-8"))
    except Exception:
        return None, None
    if not isinstance(payload, dict):
        return None, None
    return payload, hints_path


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


def _case_intake_payload(case: Case | None) -> Dict[str, Any]:
    if case is None:
        return {}
    fields = [
        "client_position",
        "court_level",
        "court_division",
        "court_location",
        "court_case_number",
        "court_date",
        "filing_deadline",
        "client_name",
        "opposing_party",
    ]
    payload: Dict[str, Any] = {}
    for field in fields:
        value = getattr(case, field, None)
        if value in (None, ""):
            continue
        if isinstance(value, datetime):
            payload[field] = value.isoformat()
        elif isinstance(value, date):
            payload[field] = value.isoformat()
        else:
            payload[field] = value
    return payload


def _collect_requested_providers(
    config_chain: List[str],
    provider_chain: Optional[List[str]],
    stage_map: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[str]:
    sequence: List[str] = []

    def _add(value: Any) -> None:
        if not value:
            return
        if not isinstance(value, str):
            return
        lowered = value.strip().lower()
        if lowered and lowered not in sequence:
            sequence.append(lowered)

    if stage_map:
        for payload in stage_map.values():
            if not isinstance(payload, dict):
                continue
            raw_providers = payload.get("providers")
            if isinstance(raw_providers, list):
                for item in raw_providers:
                    _add(item)
            _add(payload.get("provider"))

    if provider_chain:
        for item in provider_chain:
            _add(item)

    for item in config_chain:
        _add(item)

    return sequence


@shared_task(bind=True)
def summarize_job(
    self,
    *_args,
    case_id: str,
    job_id: str,
    llm_config_id: Optional[str] = None,
    source_job_id: Optional[str] = None,
) -> Dict[str, Any]:
    job = Job.objects.select_related("case", "case__organization").get(pk=job_id)
    source_job = job
    if source_job_id and str(source_job_id) != str(job_id):
        try:
            source_job = Job.objects.select_related("case", "case__organization").get(pk=source_job_id)
        except Job.DoesNotExist:
            source_job = job
    org_id = job.organization_id or job.case.organization_id
    case_dir, _, _ = _case_paths(case_id, org_id)
    existing_meta = read_job_meta(case_id, org_id, job_id)
    summary_title = str(existing_meta.get("job_title") or f"Summary {job_id}")
    transcript = (
        Path(source_job.transcript_path)
        if source_job.transcript_path
        else _latest_transcript(case_id, org_id)
    )
    transcript_path_str = str(transcript) if transcript else None

    base_meta: Dict[str, Any] = {
        "job_kind": "summary",
        "agent_type": "summary",
        "job_title": summary_title,
        "source_job_id": str(source_job.id),
        "source_transcript_path": transcript_path_str,
    }

    runtime = JobRuntimeContext(
        job=job,
        case_id=case_id,
        org_id=org_id,
        task_name="summarize_job",
        task_id=getattr(self.request, "id", None) or "",
        task_meta={
            "requested_llm_config_id": llm_config_id,
            "source_job_id": str(source_job.id),
        },
    )
    summary_start_meta = {**base_meta, "summary_status": "running"}
    summary_task_id = runtime.task_id or None
    if summary_task_id:
        history: List[str] = []
        history_payload = existing_meta.get("celery_task_history")
        if isinstance(history_payload, list):
            history = [value for value in history_payload if isinstance(value, str) and value]
        else:
            previous_id = existing_meta.get("celery_task_id")
            if isinstance(previous_id, str) and previous_id:
                history.append(previous_id)
        if summary_task_id not in history:
            history.append(summary_task_id)
        summary_start_meta["celery_task_id"] = summary_task_id
        summary_start_meta["celery_task_status"] = "running"
        if history:
            summary_start_meta["celery_task_history"] = history
        if runtime.task_name:
            summary_start_meta.setdefault("celery_task_name", runtime.task_name)

    summary_started_at = runtime.start(
        status=Job.Status.RUNNING,
        log_message="Worker started summarize pipeline",
        event="job.started",
        meta_updates=summary_start_meta,
    )

    if summary_task_id and summary_started_at:
        _safe_job_meta(
            case_id,
            org_id,
            job_id,
            {"celery_task_started_at": summary_started_at.isoformat()},
        )

    if not transcript or not transcript.exists():
        failure_meta = {**base_meta, "summary_status": "failed", "summary_error": "transcript_missing"}
        if summary_task_id:
            failure_meta.setdefault("celery_task_id", summary_task_id)
            failure_meta["celery_task_status"] = "failed"
        failure_ts = runtime.fail(
            error="No transcript found to summarize",
            log_message="Summarize failed: transcript missing",
            meta_updates=failure_meta,
            events=[("summary.failed", {})],
            task_meta_updates={"stage": "preflight", "reason": "missing_transcript"},
        )
        _safe_job_meta(
            case_id,
            org_id,
            job_id,
            {
                "summary_completed_at": failure_ts.isoformat(),
                "celery_task_finished_at": failure_ts.isoformat(),
                "celery_task_status": "failed" if summary_task_id else None,
            },
        )
        raise RuntimeError("No transcript found to summarize")

    try:
        summarize_config = SummarizeConfig.from_env()
    except ValueError as exc:
        log.error(
            "summarize config invalid",
            extra={"job_id": job_id, "case_id": case_id, "reason": str(exc)},
        )
        failure_meta = {**base_meta, "summary_status": "failed", "summary_error": str(exc)}
        if summary_task_id:
            failure_meta.setdefault("celery_task_id", summary_task_id)
            failure_meta["celery_task_status"] = "failed"
        failure_ts = runtime.fail(
            error=str(exc),
            log_message="Summarize configuration invalid",
            meta_updates=failure_meta,
            events=[("summary.failed", {"llm_config_id": llm_config_id})],
            task_meta_updates={"stage": "config", "reason": str(exc)},
        )
        _safe_job_meta(
            case_id,
            org_id,
            job_id,
            {
                "summary_completed_at": failure_ts.isoformat(),
                "celery_task_finished_at": failure_ts.isoformat(),
                "celery_task_status": "failed" if summary_task_id else None,
            },
        )
        raise

    org_id_str = str(org_id) if org_id else None
    llm_settings = load_llm_settings()
    config_payload = get_llm_configuration(
        organization_id=org_id_str,
        config_id=llm_config_id,
        target="summary",
    )
    if not config_payload:
        config_payload = ensure_default_llm_configuration(
            organization_id=org_id_str,
            target="summary",
            llm_settings=llm_settings,
        )
    if not config_payload:
        error_message = "No LLM configuration available for summarization"
        failure_meta = {**base_meta, "summary_status": "failed", "summary_error": error_message}
        if summary_task_id:
            failure_meta.setdefault("celery_task_id", summary_task_id)
            failure_meta["celery_task_status"] = "failed"
        failure_ts = runtime.fail(
            error=error_message,
            log_message=error_message,
            meta_updates=failure_meta,
            events=[("summary.failed", {"llm_config_id": llm_config_id})],
            task_meta_updates={"stage": "config", "reason": "missing_configuration"},
        )
        _safe_job_meta(
            case_id,
            org_id,
            job_id,
            {
                "summary_completed_at": failure_ts.isoformat(),
                "celery_task_finished_at": failure_ts.isoformat(),
                "celery_task_status": "failed" if summary_task_id else None,
            },
        )
        raise RuntimeError(error_message)

    config_stage_map = config_payload.get("stage_map") or {}
    config_provider_chain_raw = config_payload.get("provider_chain") or []
    normalized_chain: List[str] = []
    for entry in config_provider_chain_raw:
        if not isinstance(entry, str):
            continue
        value = entry.strip().lower()
        if value and value not in normalized_chain:
            normalized_chain.append(value)
    config_provider_chain = normalized_chain
    active_config_id = config_payload.get("id")
    active_config_name = config_payload.get("name")

    _safe_job_meta(
        case_id,
        org_id,
        job_id,
        {
            "summary_llm_config_id": active_config_id,
            "summary_llm_config_name": active_config_name,
        },
    )
    runtime.emit("summary.started", llm_config_id=active_config_id)
    runtime.transition(task_meta_updates={"active_llm_config_id": active_config_id})

    summarize_agent = SummarizeAgent(summarize_config)
    log.info(
        "summarize job started",
        extra={
            "job_id": job_id,
            "case_id": case_id,
            "org_id": org_id_str,
            "llm_config_id": active_config_id,
            "llm_config_name": active_config_name,
        },
    )
    intake_payload = _case_intake_payload(job.case)

    def _progress(stage: str, event: str, payload: Dict[str, Any]) -> None:
        progress_payload: Dict[str, Any] = {
            "case_id": case_id,
            "stage": stage,
            "state": event,
        }
        if active_config_id:
            progress_payload["llm_config_id"] = active_config_id
        if payload:
            progress_payload["details"] = payload
        runtime.emit("summary.progress", **progress_payload)
        if summarize_agent.config.debug:
            log.info(
                "summarize stage",
                extra={
                    "job_id": job_id,
                    "case_id": case_id,
                    "stage": stage,
                    "event": event,
                    "details": payload,
                },
            )

    requested_providers = _collect_requested_providers(
        summarize_config.provider_chain,
        config_provider_chain,
        config_stage_map,
    )
    provider_secrets: Dict[str, Dict[str, Any]] = {}
    if org_id_str:
        for provider_name in requested_providers:
            secret_payload = get_provider_secret_with_metadata(org_id_str, provider_name)
            if secret_payload:
                provider_secrets[provider_name] = secret_payload
            else:
                provider_meta = llm_settings.provider(provider_name)
                if provider_meta and provider_meta.requires_api_key:
                    log.info(
                        "Provider requires credentials but none stored",
                        extra={
                            "provider": provider_name,
                            "organization_id": org_id_str,
                            "job_id": job_id,
                        },
                    )

    try:
        result = summarize_agent.summarize(
            input=transcript,
            case_id=case_id,
            case_dir=case_dir,
            job_id=job_id,
            intake=intake_payload or None,
            provider_chain=config_provider_chain,
            stage_map=config_stage_map,
            provider_credentials=provider_secrets,
            progress_callback=_progress,
        )
    except Exception as exc:
        error_message = str(exc)
        log.error(
            "summarize job failed",
            extra={"job_id": job_id, "case_id": case_id, "error": error_message},
        )
        failure_meta = {**base_meta, "summary_status": "failed", "summary_error": error_message}
        if summary_task_id:
            failure_meta.setdefault("celery_task_id", summary_task_id)
            failure_meta["celery_task_status"] = "failed"
        failure_ts = runtime.fail(
            error=error_message,
            log_message=f"Summarize failed: {error_message}",
            meta_updates=failure_meta,
            events=[("summary.failed", {"llm_config_id": active_config_id, "details": {"stage": "runtime"}})],
            task_meta_updates={"error": error_message, "stage": "runtime"},
        )
        _safe_job_meta(
            case_id,
            org_id,
            job_id,
            {
                "summary_completed_at": failure_ts.isoformat(),
                "celery_task_finished_at": failure_ts.isoformat(),
                "celery_task_status": "failed" if summary_task_id else None,
            },
        )
        raise

    checksum = _sha256_file(result.summary_file)
    markdown_checksum = _sha256_file(result.summary_markdown_file)
    meta_updates: Dict[str, Any] = {
        **base_meta,
        "summary_status": "completed",
        "summary_file": str(result.summary_file),
        "summary_markdown_file": str(result.summary_markdown_file),
        "summary_outline_file": str(result.outline_file) if result.outline_file else None,
        "summary_timeline_file": str(result.timeline_seeds_file) if result.timeline_seeds_file else None,
        "summary_entity_file": str(result.entity_hints_file) if result.entity_hints_file else None,
        "summary_case_brief_file": str(result.case_brief_file) if result.case_brief_file else None,
        "summary_words": result.words,
        "summary_sha256": checksum,
        "summary_markdown_sha256": markdown_checksum,
        "summary_provider_chain": result.provider_chain,
        "summary_llm_config_id": active_config_id,
        "summary_llm_config_name": active_config_name,
    }
    if summary_task_id:
        meta_updates.setdefault("celery_task_id", summary_task_id)
        meta_updates["celery_task_status"] = "succeeded"

    finished_ts = runtime.succeed(
        log_message="Summarize pipeline completed",
        meta_updates=meta_updates,
        events=[
            (
                "summary.completed",
                {
                    "summary": str(result.summary_file),
                    "llm_config_id": active_config_id,
                },
            )
        ],
        job_updates={"transcript_path": str(result.summary_file)},
        task_meta_updates={
            "summary_file": str(result.summary_file),
            "outline_file": str(result.outline_file) if result.outline_file else None,
            "timeline_file": str(result.timeline_seeds_file) if result.timeline_seeds_file else None,
            "entity_file": str(result.entity_hints_file) if result.entity_hints_file else None,
            "words": result.words,
        },
    )
    _safe_job_meta(
        case_id,
        org_id,
        job_id,
        {
            "summary_completed_at": finished_ts.isoformat(),
            "celery_task_finished_at": finished_ts.isoformat(),
            "celery_task_status": "succeeded" if summary_task_id else None,
        },
    )

    summary_artifact_id: Optional[str] = None
    try:
        artifact = CaseArtifact.objects.create(
            case_id=case_id,
            case_fk=job.case,
            job_id=str(job_id),
            type="SUMMARY",
            title=summary_title,
            path=str(result.summary_file),
            checksum=checksum or "",
            schema_version="v1",
            metadata={
                "source_transcript": str(result.source_transcript),
                "source_job_id": str(source_job.id),
                "provider_chain": result.provider_chain,
                "summary_markdown_file": str(result.summary_markdown_file),
                "summary_outline_file": str(result.outline_file) if result.outline_file else None,
                "summary_timeline_file": str(result.timeline_seeds_file) if result.timeline_seeds_file else None,
                "summary_entity_file": str(result.entity_hints_file) if result.entity_hints_file else None,
                "summary_case_brief_file": str(result.case_brief_file) if result.case_brief_file else None,
            },
        )
        summary_artifact_id = str(artifact.id)
    except Exception:
        summary_artifact_id = None

    audit_emit(
        None,
        case_id=case_id,
        event="analysis.summary.created",
        data={
            "job_id": job_id,
            "source_job_id": str(source_job.id),
            "file": str(result.summary_file),
        },
    )

    try:
        send_case_update(case_id, event="artifact.created", kind="summary", job_id=job_id)
    except Exception:
        pass

    if summary_artifact_id:
        meta_updates["summary_artifact_id"] = summary_artifact_id

    payload: Dict[str, Any] = {
        "status": "ok",
        "job_id": job_id,
        "source_job_id": str(source_job.id),
        "summary_file": str(result.summary_file),
        "summary_markdown_file": str(result.summary_markdown_file),
        "outline_file": str(result.outline_file) if result.outline_file else None,
        "timeline_file": str(result.timeline_seeds_file) if result.timeline_seeds_file else None,
        "entity_file": str(result.entity_hints_file) if result.entity_hints_file else None,
        "words": result.words,
        "llm_config_id": active_config_id,
    }
    if summary_artifact_id:
        payload["artifact_id"] = summary_artifact_id

    return payload

@shared_task(bind=True)
def timeline_job(*_args, case_id: str, job_id: str) -> Dict[str, Any]:
    job = Job.objects.select_related("case").get(pk=job_id)
    org_id = job.organization_id or job.case.organization_id
    case_dir, _, analysis_dir = _case_paths(case_id, org_id)
    src = Path(job.transcript_path) if job.transcript_path else _latest_transcript(case_id, org_id)
    if not src or not src.exists():
        raise RuntimeError("No transcript found to build timeline")
    meta = read_job_meta(case_id, org_id, job_id)
    events, seeds_path = _load_summary_timeline_events(meta, case_dir)

    if not events:
        rx = re.compile(r"^\[(\d{2}):(\d{2})\]\s+(?:SPK_(\d+):\s+)?(.*)$")
        for ln in src.read_text(encoding="utf-8", errors="ignore").splitlines():
            m = rx.match(ln.strip())
            if not m:
                continue
            mm, ss, spk, text = m.groups()
            ts = int(mm) * 60 + int(ss)
            events.append(
                {
                    "ts_start": ts,
                    "ts_end": None,
                    "speaker": f"SPK_{spk}" if spk else None,
                    "text": text.strip(),
                    "labels": [],
                }
            )
    out = analysis_dir / f"{job_id}__timeline_v1.json"
    _write_json(out, events)
    try:
        import hashlib

        h = hashlib.sha256()
        with open(out, "rb") as f:
            for ch in iter(lambda: f.read(65536), b""):
                h.update(ch)
        artifact_meta = {"source_transcript": str(src), "events": len(events)}
        if seeds_path:
            artifact_meta["seed_source"] = str(seeds_path)
        CaseArtifact.objects.create(
            case_id=case_id,
            case_fk=job.case,
            job_id=str(job_id),
            type="TIMELINE",
            title=f"Timeline {job_id}",
            path=str(out),
            checksum=h.hexdigest(),
            schema_version="v1",
            metadata=artifact_meta,
        )
    except Exception:
        pass
    audit_payload = {"job_id": job_id, "events": len(events)}
    if seeds_path:
        audit_payload["seed_source"] = str(seeds_path)
    audit_emit(None, case_id=case_id, event="analysis.timeline.created", data=audit_payload)
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
        if seeds_path:
            meta["seed_source"] = str(seeds_path)
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
    case_dir, _, analysis_dir = _case_paths(case_id, org_id)
    src = Path(job.transcript_path) if job.transcript_path else _latest_transcript(case_id, org_id)
    if not src or not src.exists():
        raise RuntimeError("No transcript found to extract entities/graph")
    text = src.read_text(encoding="utf-8", errors="ignore")
    meta = read_job_meta(case_id, org_id, job_id)
    hints_data, hints_path = _load_summary_entity_hints(meta, case_dir)

    entities: List[Dict[str, Any]] = []
    graph: Dict[str, Any]

    if hints_data:
        entity_map: Dict[str, Dict[str, Any]] = {}
        for raw in hints_data.get("entities", []):
            if not isinstance(raw, dict):
                continue
            ent_id = str(raw.get("id") or f"E{len(entity_map) + 1}")
            name = raw.get("name") or ent_id
            ent_type = raw.get("type") or "OTHER"
            mentions_list: List[Dict[str, Any]] = []
            mentions_raw = raw.get("mentions")
            if isinstance(mentions_raw, list):
                for item in mentions_raw:
                    if isinstance(item, dict):
                        mentions_list.append(
                            {
                                "ts": item.get("ts"),
                                "text": item.get("text", ""),
                            }
                        )
            entity_map[ent_id] = {
                "id": ent_id,
                "name": name,
                "type": ent_type,
                "mentions": mentions_list,
            }

        edges: List[Dict[str, Any]] = []
        for raw_rel in hints_data.get("relations", []):
            if not isinstance(raw_rel, dict):
                continue
            source = raw_rel.get("source")
            target = raw_rel.get("target")
            if not source or not target:
                continue
            rel_type = raw_rel.get("type") or "relation"
            evidence_list: List[Dict[str, Any]] = []
            evidence_raw = raw_rel.get("evidence")
            if isinstance(evidence_raw, list):
                for item in evidence_raw:
                    if isinstance(item, dict):
                        evidence_list.append(
                            {
                                "ts": item.get("ts"),
                                "text": item.get("text", ""),
                            }
                        )
            if source not in entity_map:
                entity_map[source] = {
                    "id": source,
                    "name": source,
                    "type": "OTHER",
                    "mentions": [],
                }
            if target not in entity_map:
                entity_map[target] = {
                    "id": target,
                    "name": target,
                    "type": "OTHER",
                    "mentions": [],
                }
            edges.append(
                {
                    "id": f"REL-{len(edges) + 1}",
                    "source": source,
                    "target": target,
                    "type": rel_type,
                    "evidence": evidence_list,
                }
            )

        if not entity_map:
            hints_data = None
        else:
            entities = list(entity_map.values())
            graph = {
                "nodes": [
                    {"id": ent["id"], "label": ent["name"], "type": ent.get("type") or "OTHER"}
                    for ent in entities
                ],
                "edges": edges,
            }

    if not hints_data:
        tokens = re.findall(r"\b([A-Z][a-zA-Z]{2,})\b", text)
        names = sorted(set(tokens))[:50]
        entities = [
            {
                "id": f"E{i+1}",
                "name": n,
                "type": "OTHER",
                "mentions": [],
            }
            for i, n in enumerate(names)
        ]
        graph = {
            "nodes": [
                {"id": ent["id"], "label": ent["name"], "type": ent["type"]}
                for ent in entities
            ],
            "edges": [],
        }
    entities_file = analysis_dir / f"{job_id}__entities_v1.json"
    graph_file = analysis_dir / f"{job_id}__graph_v1.json"
    _write_json(entities_file, {"entities": entities})
    _write_json(graph_file, graph)
    try:
        import hashlib

        h1 = hashlib.sha256(entities_file.read_bytes()).hexdigest()
        h2 = hashlib.sha256(graph_file.read_bytes()).hexdigest()
        artifact_entities_meta = {"source_transcript": str(src), "entities": len(entities)}
        artifact_graph_meta = {"source_transcript": str(src), "nodes": len(graph["nodes"]), "edges": len(graph.get("edges", []))}
        if hints_path:
            artifact_entities_meta["hint_source"] = str(hints_path)
            artifact_graph_meta["hint_source"] = str(hints_path)
        CaseArtifact.objects.create(
            case_id=case_id,
            case_fk=job.case,
            job_id=str(job_id),
            type="ENTITIES",
            title=f"Entities {job_id}",
            path=str(entities_file),
            checksum=h1,
            schema_version="v1",
            metadata=artifact_entities_meta,
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
            metadata=artifact_graph_meta,
        )
    except Exception:
        pass
    audit_payload = {"job_id": job_id, "entities": len(entities), "edges": len(graph.get("edges", []))}
    if hints_path:
        audit_payload["hint_source"] = str(hints_path)
    audit_emit(None, case_id=case_id, event="analysis.graph.created", data=audit_payload)
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
            "edges": len(graph.get("edges", [])),
            "ts": timezone.now().isoformat(),
            "schema_version": "v1",
            "status": "ok",
        }
        if hints_path:
            meta["hint_source"] = str(hints_path)
        _write_json(opsd / f"{job_id}__graph_log.json", meta)
        _append_jsonl(opsd / "ops_graph.jsonl", meta)
    except Exception:
        pass
    try:
        send_case_update(case_id, event="artifact.created", kind="graph", job_id=job_id)
    except Exception:
        pass
    return {
        "status": "ok",
        "entities_file": str(entities_file),
        "graph_file": str(graph_file),
        "entities": len(entities),
        "edges": len(graph.get("edges", [])),
    }


@shared_task(bind=True)
def guardian_review_artifact(self, *, artifact_id: int) -> Dict[str, Any]:
    request_id = getattr(getattr(self, "request", None), "id", "") or ""
    try:
        artifact = CaseArtifact.objects.select_related("case_fk").get(pk=artifact_id)
    except CaseArtifact.DoesNotExist:
        return {"status": "missing", "artifact_id": artifact_id}

    job_id = str(artifact.job_id or "")
    job_obj: Optional[Job] = None
    if job_id:
        job_obj = Job.objects.select_related("case").filter(pk=job_id).first()

    org_id = artifact.organization_id
    if org_id is None and job_obj is not None:
        org_id = job_obj.organization_id
    if org_id is None and artifact.case_fk_id:
        org_id = artifact.case_fk.organization_id
    org_id_str = str(org_id) if org_id else None

    context = build_guardian_context(org_id_str)

    task_meta: Dict[str, Any] = {
        "artifact_id": artifact.id,
        "artifact_type": artifact.type,
        "job_id": job_id or None,
        "case_id": artifact.case_id,
    }

    runtime: Optional[JobRuntimeContext] = None
    if job_obj is not None:
        runtime = JobRuntimeContext(
            job=job_obj,
            case_id=case_id,
            org_id=org_id_str,
            task_name="guardian_review_artifact",
            task_id=request_id,
            task_meta=dict(task_meta),
        )
        runtime.transition(
            event="guardian.review.started",
            job_event_payload={
                "artifact_id": artifact.id,
                "guardian_status": "running",
            },
        )

    case_id = artifact.case_id

    if context is None:
        review_record = {
            "status": "skipped",
            "reason": "guardian_not_configured",
            "reviewed_at": timezone.now().isoformat(),
            "artifact_id": artifact.id,
            "artifact_type": artifact.type,
        }
        store_guardian_review(artifact, review_record)
        if runtime:
            runtime.transition(
                event="guardian.review.skipped",
                job_event_payload={
                    "artifact_id": artifact.id,
                    "guardian_status": "skipped",
                    "guardian_reason": "guardian_not_configured",
                },
            )
        return {"status": "skipped", "artifact_id": artifact.id, "reason": "guardian_not_configured"}

    artifact_payload = snapshot_artifact_for_guardian(artifact)
    if "content" not in artifact_payload and "parsed" not in artifact_payload:
        review_record = {
            "status": "skipped",
            "reason": "unreadable_artifact",
            "reviewed_at": timezone.now().isoformat(),
            "artifact_id": artifact.id,
            "artifact_type": artifact.type,
        }
        store_guardian_review(artifact, review_record)
        if runtime:
            runtime.transition(
                event="guardian.review.skipped",
                job_event_payload={
                    "artifact_id": artifact.id,
                    "guardian_status": "skipped",
                    "guardian_reason": "unreadable_artifact",
                },
            )
        return {"status": "skipped", "artifact_id": artifact.id, "reason": "unreadable_artifact"}

    verdict: Optional[GuardianVerdict] = None
    try:
        job_metadata: Dict[str, Any] = {}
        if job_id and org_id_str:
            try:
                job_metadata = read_job_meta(case_id, org_id_str, job_id)
            except Exception:
                job_metadata = {}

        artifact_type_upper = (artifact.type or "").upper()
        applicable_instructions: List[Dict[str, Any]] = []
        for instruction in context.instructions:
            applies_to = instruction.get("applies_to")
            if not applies_to:
                applicable_instructions.append(instruction)
                continue
            try:
                values = [str(item).upper() for item in applies_to]
            except Exception:
                values = []
            if artifact_type_upper in values:
                applicable_instructions.append(instruction)

        case_data: Dict[str, Any] = {}
        case_obj: Optional[Case] = artifact.case_fk
        if case_obj is None:
            case_obj = Case.objects.filter(pk=artifact.case_id).first()
        if case_obj is not None:
            case_data = {
                "id": str(case_obj.id),
                "title": case_obj.title,
                "client_name": case_obj.client_name,
                "representation": case_obj.representation,
            }

        guardian_context_payload = {
            "artifact_metadata": artifact.metadata or {},
            "job_metadata": job_metadata,
            "artifact_type": artifact.type,
            "artifact_title": artifact.title,
            "artifact_path": artifact.path,
            "instructions": applicable_instructions,
            "all_instructions": context.instructions,
            "case": case_data,
        }

        verdict = context.agent.review(
            case_id=case_id,
            job_id=job_id,
            artifact_kind=artifact.type or "artifact",
            payload=artifact_payload,
            providers=context.provider_chain,
            model=context.model,
            options={"temperature": context.temperature} if context.temperature is not None else None,
            provider_credentials=context.credentials,
            context=guardian_context_payload,
            max_tokens=context.max_tokens,
            temperature=context.temperature,
        )
    except Exception as exc:
        review_record = {
            "status": "error",
            "error": str(exc),
            "reviewed_at": timezone.now().isoformat(),
            "artifact_id": artifact.id,
            "artifact_type": artifact.type,
        }
        store_guardian_review(artifact, review_record)
        if job_id:
            _safe_job_log(case_id, org_id_str, job_id, f"Guardian review error: {exc}", level="ERROR")
        if runtime:
            runtime.transition(
                event="guardian.review.failed",
                job_event_payload={
                    "artifact_id": artifact.id,
                    "guardian_status": "error",
                    "guardian_error": str(exc),
                },
                meta_updates={"guardian_last_error": str(exc)},
            )
        raise

    status = "approved" if verdict.approved else "rejected"
    review_record = build_guardian_review_record(
        verdict=verdict,
        status=status,
        artifact=artifact,
        context=context,
        extra={
            "retry_attempts": context.agent.config.retry_attempts,
            "instructions_used": len(applicable_instructions),
        },
    )
    store_guardian_review(artifact, review_record)
    event_status = "SUCCEEDED" if verdict.approved else "FAILED"

    if job_id:
        reduced_record = dict(review_record)
        reduced_record.pop("artifact_id", None)
        reduced_record.pop("artifact_type", None)
        _safe_job_meta(case_id, org_id_str, job_id, {"guardian_last_review": reduced_record})
        _safe_job_log(
            case_id,
            org_id_str,
            job_id,
            "Guardian review completed" if verdict.approved else "Guardian review flagged violations",
        )
        _emit_job_update(
            job_id,
            case_id=case_id,
            event="guardian.review.completed",
            status=event_status,
            guardian_status=status,
            artifact_id=artifact.id,
        )

    if runtime:
        runtime.transition(
            event="guardian.review.completed",
            job_event_payload={
                "artifact_id": artifact.id,
                "guardian_status": status,
            },
            meta_updates={"guardian_last_review": review_record},
        )

    return {
        "status": status,
        "artifact_id": artifact.id,
        "provider": verdict.provider,
        "model": verdict.model,
        "violations": verdict.violations,
        "remediation": verdict.remediation,
    }
