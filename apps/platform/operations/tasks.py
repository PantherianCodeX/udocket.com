from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
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
    ComposeConfig,
    GraphAgent,
    GraphConfig,
    AnalyzeAgent,
    AnalyzeConfig,
    TimelineAgent,
    TimelineConfig,
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
from apps.platform.operations.services import (
    case_intake_payload,
    case_paths,
    collect_requested_providers,
    load_summary_entity_hints,
    load_summary_timeline_events,
    ops_dir,
    latest_transcript,
    execute_compose_job,
)
from apps.platform.operations.services.files import sha256_file

# Backwards compatibility for tests importing _update_job_meta
def _update_job_meta(case_id: str, organization_id: Optional[str], job_id: str, updates: Dict[str, Any]) -> None:  # pragma: no cover - shim
    return update_job_meta(case_id, organization_id, job_id, updates)
from apps.platform.jobs.utils import unique_title

log = logging.getLogger("apps.platform.operations.tasks")

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
                    "audio_sha256": sha256_file(audio_path),
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

                    converted_sha = sha256_file(converted_path)
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
            job_event_payload={k: v for k, v in failure_payload.items() if k not in {"job_id", "case_id", "event"}},
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
        transcript_checksum = sha256_file(transcript_path_obj)

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

    emit_payload = {k: v for k, v in payload.items() if k not in {"job_id", "case_id", "event"}}
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

@shared_task(bind=True)
def analyze_job(
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
    case_dir, _, _ = case_paths(case_id, org_id)
    existing_meta = read_job_meta(case_id, org_id, job_id)
    existing_summary_titles = list(
        CaseArtifact.objects.filter(case_id=str(case_id), type="SUMMARY").values_list("title", flat=True)
    )
    summary_title = str(existing_meta.get("job_title") or "").strip()
    if not summary_title or summary_title in existing_summary_titles:
        summary_title = unique_title("Summary", existing_summary_titles)
    transcript = (
        Path(source_job.transcript_path)
        if source_job.transcript_path
        else latest_transcript(case_id, org_id)
    )
    transcript_path_str = str(transcript) if transcript else None

    base_meta: Dict[str, Any] = {
        "job_kind": "analyze",
        "agent_type": "analyze",
        "job_title": summary_title,
        "source_job_id": str(source_job.id),
        "source_transcript_path": transcript_path_str,
    }

    runtime = JobRuntimeContext(
        job=job,
        case_id=case_id,
        org_id=org_id,
        task_name="analyze_job",
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
        log_message="Worker started analyze pipeline",
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
            error="No transcript found to analyze",
            log_message="Analyze failed: transcript missing",
            meta_updates=failure_meta,
            events=[("analyze.failed", {})],
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
        raise RuntimeError("No transcript found to analyze")

    try:
        analyze_config = AnalyzeConfig.from_env()
    except ValueError as exc:
        log.error(
            "analyze config invalid",
            extra={"job_id": job_id, "case_id": case_id, "reason": str(exc)},
        )
        failure_meta = {**base_meta, "summary_status": "failed", "summary_error": str(exc)}
        if summary_task_id:
            failure_meta.setdefault("celery_task_id", summary_task_id)
            failure_meta["celery_task_status"] = "failed"
        failure_ts = runtime.fail(
            error=str(exc),
            log_message="Analyze configuration invalid",
            meta_updates=failure_meta,
            events=[("analyze.failed", {"llm_config_id": llm_config_id})],
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


@shared_task(bind=True)
def compose_job(
    self,
    *_args,
    case_id: str,
    job_id: str,
    summary_job_id: str,
    llm_config_id: Optional[str] = None,
) -> Dict[str, Any]:
    job = Job.objects.select_related("case", "case__organization").get(pk=job_id)
    summary_job = Job.objects.select_related("case", "case__organization").get(pk=summary_job_id)
    if summary_job.case_id != job.case_id:
        raise RuntimeError("Summary job belongs to a different case")

    compose_config = ComposeConfig.from_env()
    runtime = JobRuntimeContext(
        job=job,
        case_id=case_id,
        org_id=job.organization_id or job.case.organization_id,
        task_name="compose_job",
        task_id=getattr(self.request, "id", None) or "",
        task_meta={"summary_job_id": summary_job_id, "requested_llm_config_id": llm_config_id},
    )

    result = execute_compose_job(
        runtime=runtime,
        compose_config=compose_config,
        job=job,
        summary_job=summary_job,
        case_id=case_id,
        llm_config_id=llm_config_id,
    )

    send_job_update(
        str(job.id),
        event="job.succeeded",
        status=Job.Status.SUCCEEDED,
        case_id=case_id,
    )
    send_case_update(
        case_id,
        event="artifact.created",
        kind="compose",
        job_id=str(job.id),
    )
    audit_emit(
        None,
        case_id=case_id,
        event="analysis.compose.completed",
        data={"job_id": str(job.id), "summary_job_id": summary_job_id},
    )

    return result

@shared_task(bind=True)
def analyze_job(
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
    case_dir, _, _ = case_paths(case_id, org_id)
    existing_meta = read_job_meta(case_id, org_id, job_id)
    existing_summary_titles = list(
        CaseArtifact.objects.filter(case_id=str(case_id), type="SUMMARY").values_list("title", flat=True)
    )
    summary_title = str(existing_meta.get("job_title") or "").strip()
    if not summary_title or summary_title in existing_summary_titles:
        summary_title = unique_title("Summary", existing_summary_titles)
    transcript = (
        Path(source_job.transcript_path)
        if source_job.transcript_path
        else latest_transcript(case_id, org_id)
    )
    transcript_path_str = str(transcript) if transcript else None

    base_meta: Dict[str, Any] = {
        "job_kind": "analyze",
        "agent_type": "analyze",
        "job_title": summary_title,
        "source_job_id": str(source_job.id),
        "source_transcript_path": transcript_path_str,
    }

    runtime = JobRuntimeContext(
        job=job,
        case_id=case_id,
        org_id=org_id,
        task_name="analyze_job",
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
        log_message="Worker started analyze pipeline",
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
            error="No transcript found to analyze",
            log_message="Analyze failed: transcript missing",
            meta_updates=failure_meta,
            events=[("analyze.failed", {})],
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
        raise RuntimeError("No transcript found to analyze")

    try:
        analyze_config = AnalyzeConfig.from_env()
    except ValueError as exc:
        log.error(
            "analyze config invalid",
            extra={"job_id": job_id, "case_id": case_id, "reason": str(exc)},
        )
        failure_meta = {**base_meta, "summary_status": "failed", "summary_error": str(exc)}
        if summary_task_id:
            failure_meta.setdefault("celery_task_id", summary_task_id)
            failure_meta["celery_task_status"] = "failed"
        failure_ts = runtime.fail(
            error=str(exc),
            log_message="Analyze configuration invalid",
            meta_updates=failure_meta,
            events=[("analyze.failed", {"llm_config_id": llm_config_id})],
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


@shared_task(bind=True)
def compose_job(
    self,
    *_args,
    case_id: str,
    job_id: str,
    summary_job_id: str,
    llm_config_id: Optional[str] = None,
) -> Dict[str, Any]:
    job = Job.objects.select_related("case", "case__organization").get(pk=job_id)
    summary_job = Job.objects.select_related("case", "case__organization").get(pk=summary_job_id)
    if summary_job.case_id != job.case_id:
        raise RuntimeError("Summary job belongs to a different case")

    org_id = job.organization_id or job.case.organization_id
    case_dir, _, _ = case_paths(case_id, org_id)

    compose_config = ComposeConfig.from_env()
    runtime = JobRuntimeContext(
        job=job,
        case_id=case_id,
        org_id=org_id,
        task_name="compose_job",
        task_id=getattr(self.request, "id", None) or "",
        task_meta={
            "summary_job_id": summary_job_id,
            "requested_llm_config_id": llm_config_id,
        },
    )

    summary_meta = read_job_meta(case_id, org_id, summary_job_id)
    summary_json_path = summary_meta.get("summary_file") or summary_meta.get("summary_json_file")
    summary_markdown_path = summary_meta.get("summary_markdown_file") or summary_meta.get("summary_markdown")
    timeline_seed_path = summary_meta.get("summary_timeline_file")
    entity_hint_path = summary_meta.get("summary_entity_file")
    staff_report_path = summary_meta.get("summary_case_brief_file") or summary_meta.get("summary_staff_report_file")
    transcript_path = summary_meta.get("source_transcript_path") or summary_job.transcript_path

    def _to_path(value: Optional[str]) -> Optional[Path]:
        if not value:
            return None
        try:
            path_obj = Path(value)
            if not path_obj.is_absolute():
                return case_dir / path_obj
            return path_obj
        except Exception:
            return None

    summary_json_path = _to_path(summary_json_path)
    summary_markdown_path = _to_path(summary_markdown_path)
    timeline_seed_path = _to_path(timeline_seed_path)
    entity_hint_path = _to_path(entity_hint_path)
    staff_report_path = _to_path(staff_report_path)
    transcript_path = _to_path(transcript_path)

    analysis_dir = case_dir / "analysis"
    summary_case_dir, _, _ = case_paths(case_id, summary_job.organization_id or summary_job.case.organization_id)
    summary_analysis_dir = summary_case_dir / "analysis"
    search_dirs = []
    for directory in (analysis_dir, summary_analysis_dir):
        if directory not in search_dirs and directory.exists():
            search_dirs.append(directory)

    if summary_json_path is None or not (summary_json_path.exists() if summary_json_path else False):
        for directory in search_dirs:
            candidate = directory / f"{summary_job_id}__summary_v1.json"
            if candidate.exists():
                summary_json_path = candidate
                break
    if summary_markdown_path is None or not (summary_markdown_path.exists() if summary_markdown_path else False):
        for directory in search_dirs:
            candidate = directory / f"{summary_job_id}__summary_v1.md"
            if candidate.exists():
                summary_markdown_path = candidate
                break
        if summary_markdown_path is None:
            for directory in search_dirs:
                try:
                    candidates = sorted(
                        directory.glob("*__summary_v1.md"),
                        key=lambda p: p.stat().st_mtime,
                        reverse=True,
                    )
                except Exception:
                    candidates = []
                if candidates:
                    summary_markdown_path = candidates[0]
                    break
    if timeline_seed_path is None or not (timeline_seed_path.exists() if timeline_seed_path else False):
        for directory in search_dirs:
            candidate = directory / f"{summary_job_id}__timeline_seeds_v1.json"
            if candidate.exists():
                timeline_seed_path = candidate
                break
    if entity_hint_path is None or not (entity_hint_path.exists() if entity_hint_path else False):
        for directory in search_dirs:
            candidate = directory / f"{summary_job_id}__entity_hints_v1.json"
            if candidate.exists():
                entity_hint_path = candidate
                break
    if staff_report_path is None or not (staff_report_path.exists() if staff_report_path else False):
        for directory in search_dirs:
            candidate = directory / f"{summary_job_id}__case_brief_v1.md"
            if candidate.exists():
                staff_report_path = candidate
                break

    if summary_json_path is None or not summary_json_path.exists():
        if summary_markdown_path and summary_markdown_path.exists():
            placeholder = analysis_dir / f"{summary_job_id}__summary_fallback_v1.json"
            placeholder.write_text(
                json.dumps({"markdown": summary_markdown_path.read_text(encoding="utf-8")}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            summary_json_path = placeholder
        else:
            for directory in search_dirs:
                try:
                    candidates = sorted(
                        directory.glob("*__summary_v1.json"),
                        key=lambda p: p.stat().st_mtime,
                        reverse=True,
                    )
                except Exception:
                    candidates = []
                if candidates:
                    summary_json_path = candidates[0]
                    break
        if summary_json_path is None or not summary_json_path.exists():
            fallback_json = analysis_dir / f"{summary_job_id}__summary_autogen_v1.json"
            fallback_json.write_text(json.dumps({"sections": [], "generated": True}, indent=2), encoding="utf-8")
            summary_json_path = fallback_json

    if summary_markdown_path is None or not summary_markdown_path.exists():
        fallback_md = analysis_dir / f"{summary_job_id}__summary_autogen_v1.md"
        fallback_md.write_text("# Summary\n\nNo summary available.", encoding="utf-8")
        summary_markdown_path = fallback_md

    compose_started_meta = {
        "compose_status": "running",
        "summary_job_id": summary_job_id,
        "summary_json": str(summary_json_path) if summary_json_path else None,
        "summary_markdown": str(summary_markdown_path) if summary_markdown_path else None,
    }
    runtime.start(
        status=Job.Status.RUNNING,
        log_message="Worker started compose pipeline",
        event="job.started",
        meta_updates=compose_started_meta,
    )

    llm_settings = load_llm_settings()
    active_config = None
    if llm_config_id:
        active_config = get_llm_configuration(
            organization_id=str(job.organization_id or summary_job.organization_id or ""),
            config_id=llm_config_id,
            target="compose",
        )
    if not active_config:
        active_config = get_llm_configuration(
            organization_id=str(job.organization_id or summary_job.organization_id or ""),
            config_id=None,
            target="compose",
        )
    if not active_config:
        active_config = ensure_default_llm_configuration(
            organization_id=str(job.organization_id or summary_job.organization_id or ""),
            target="compose",
            llm_settings=llm_settings,
        )

    stage_map = dict(active_config.get("stage_map") or {}) if active_config else {}
    provider_chain = active_config.get("provider_chain") if active_config else None
    provider_chain = provider_chain or compose_config.provider_chain
    provider_chain = [str(p) for p in provider_chain]

    provider_credentials: Dict[str, Dict[str, Any]] = {}
    org_id_str = str(org_id) if org_id else None
    if org_id_str:
        requested_providers: List[str] = []
        def _add_provider(name: Optional[str]) -> None:
            if not name:
                return
            candidate = str(name).strip().lower()
            if candidate and candidate not in requested_providers:
                requested_providers.append(candidate)

        for provider in compose_config.provider_chain:
            _add_provider(provider)
        for provider in provider_chain or []:
            _add_provider(provider)
        for cfg in (stage_map or {}).values():
            if isinstance(cfg, dict):
                _add_provider(cfg.get("provider"))
                prov_list = cfg.get("providers")
                if isinstance(prov_list, Sequence):
                    for entry in prov_list:
                        _add_provider(entry)

        for provider in requested_providers:
            secret_payload = get_provider_secret_with_metadata(org_id_str, provider)
            if secret_payload:
                provider_credentials[provider] = secret_payload

    compose_agent = ComposeAgent(compose_config)

    def _progress(stage: str, event: str, details: Dict[str, Any]) -> None:
        runtime.emit(
            "compose.progress",
            stage=stage,
            event=event,
            summary_job_id=summary_job_id,
            details=details,
        )

    intake_payload = summary_meta.get("intake") if isinstance(summary_meta.get("intake"), dict) else None
    if not intake_payload:
        intake_payload = case_intake_payload(job.case)

    case_metadata: Dict[str, Any] = {
        "case_id": case_id,
        "case_title": job.case.title,
        "compose_job_id": job_id,
        "summary_job_id": summary_job_id,
        "job_display_title": job.display_title or "",
    }
    if job.case.organization:
        case_metadata["organization_id"] = str(job.case.organization_id)
        case_metadata["organization_name"] = job.case.organization.name
    if summary_markdown_path:
        case_metadata["summary_markdown_file"] = summary_markdown_path.name
    if summary_json_path:
        case_metadata["summary_json_file"] = summary_json_path.name

    try:
        result = compose_agent.compose(
            case_id=case_id,
            case_dir=case_dir,
            job_id=job_id,
            summary_json_path=summary_json_path,
            summary_markdown_path=summary_markdown_path,
            transcript_path=transcript_path,
            timeline_seed_path=timeline_seed_path,
            entity_hint_path=entity_hint_path,
            staff_report_path=staff_report_path,
            intake=intake_payload,
            case_metadata=case_metadata,
            provider_chain=provider_chain,
            stage_map=stage_map,
            provider_credentials=provider_credentials,
            progress_callback=_progress,
        )
    except Exception as exc:
        error_message = str(exc)
        runtime.fail(
            error=error_message,
            log_message=f"Compose failed: {error_message}",
            meta_updates={"compose_status": "failed", "compose_error": error_message},
            events=[("compose.failed", {"summary_job_id": summary_job_id})],
        )
        raise

    artifacts = result.artifacts

    meta_updates: Dict[str, Any] = {
        "compose_status": "completed",
        "compose_meta_json": str(result.meta_json),
        "compose_provider_chain": result.provider_chain,
        "compose_stage_usage": result.stage_usage,
        "summary_job_id": summary_job_id,
    }
    if artifacts.timeline_file:
        meta_updates["timeline_v2_file"] = str(artifacts.timeline_file)
    if artifacts.graph_file:
        meta_updates["graph_v2_file"] = str(artifacts.graph_file)
    if artifacts.entities_file:
        meta_updates["entities_v2_file"] = str(artifacts.entities_file)
    if artifacts.timeline_summary:
        meta_updates["compose_timeline_summary"] = str(artifacts.timeline_summary)
    if artifacts.entity_brief:
        meta_updates["compose_entity_brief"] = str(artifacts.entity_brief)
    if artifacts.graph_visual:
        meta_updates["compose_graph_visual"] = str(artifacts.graph_visual)
    if artifacts.client_markdown:
        meta_updates["compose_client_markdown"] = str(artifacts.client_markdown)
    if artifacts.lawyer_markdown:
        meta_updates["compose_lawyer_markdown"] = str(artifacts.lawyer_markdown)
    if artifacts.client_docx:
        meta_updates["compose_client_docx"] = str(artifacts.client_docx)
    if artifacts.lawyer_docx:
        meta_updates["compose_lawyer_docx"] = str(artifacts.lawyer_docx)

    _safe_job_meta(case_id, org_id, job_id, meta_updates)

    # Register artifacts
    created_titles = {
        kind: set(
            CaseArtifact.objects.filter(case_id=case_id, type=kind).values_list("title", flat=True)
        )
        for kind in ("COMPOSE", "TIMELINE", "GRAPH", "ENTITIES")
    }

    def _create_artifact(*, kind: str, path: Optional[Path], title_hint: str, metadata: Dict[str, Any], schema_version: str = "v1") -> None:
        if path is None or not path.exists():
            return
        checksum = sha256_file(path)
        titles = created_titles.setdefault(kind, set())
        title = unique_title(title_hint, titles)
        titles.add(title)
        CaseArtifact.objects.create(
            case_id=case_id,
            case_fk=job.case,
            organization=job.organization or summary_job.organization,
            job_id=str(job.id),
            type=kind,
            title=title,
            path=str(path),
            checksum=checksum or "",
            schema_version=schema_version,
            metadata=metadata,
        )

    summary_source = Path(summary_markdown_path) if summary_markdown_path else None
    summary_source_name = summary_source.name if summary_source else None

    _create_artifact(
        kind="COMPOSE",
        path=artifacts.client_markdown,
        title_hint="Client deliverable",
        metadata={
            "format": "markdown",
            "source_summary": summary_source_name,
        },
    )
    _create_artifact(
        kind="COMPOSE",
        path=artifacts.client_docx,
        title_hint="Client deliverable (DOCX)",
        metadata={
            "format": "docx",
            "source_summary": summary_source_name,
        },
    )
    _create_artifact(
        kind="COMPOSE",
        path=artifacts.lawyer_markdown,
        title_hint="Lawyer deliverable",
        metadata={
            "format": "markdown",
            "source_summary": summary_source_name,
        },
    )
    _create_artifact(
        kind="COMPOSE",
        path=artifacts.lawyer_docx,
        title_hint="Lawyer deliverable (DOCX)",
        metadata={
            "format": "docx",
            "source_summary": summary_source_name,
        },
    )
    _create_artifact(
        kind="COMPOSE",
        path=artifacts.timeline_summary,
        title_hint="Timeline narrative",
        metadata={
            "format": "markdown",
            "source_summary": summary_source_name,
        },
    )
    _create_artifact(
        kind="COMPOSE",
        path=artifacts.entity_brief,
        title_hint="Entity briefing",
        metadata={
            "format": "markdown",
            "source_summary": summary_source_name,
        },
    )
    _create_artifact(
        kind="COMPOSE",
        path=artifacts.graph_visual,
        title_hint="Graph visual embed",
        metadata={
            "format": "json",
            "source_summary": summary_source_name,
        },
    )
    _create_artifact(
        kind="TIMELINE",
        path=artifacts.timeline_file,
        title_hint="Timeline",
        metadata={
            "source_summary": summary_source_name,
            "schema": "v2",
        },
        schema_version="v2",
    )
    _create_artifact(
        kind="GRAPH",
        path=artifacts.graph_file,
        title_hint="Relationship graph",
        metadata={
            "source_summary": summary_source_name,
            "schema": "v2",
        },
        schema_version="v2",
    )
    _create_artifact(
        kind="ENTITIES",
        path=artifacts.entities_file,
        title_hint="Entities",
        metadata={
            "source_summary": summary_source_name,
            "schema": "v2",
        },
        schema_version="v2",
    )

    finished_ts = runtime.succeed(
        log_message="Compose pipeline completed",
        meta_updates={"compose_status": "completed"},
        events=[("compose.completed", {"summary_job_id": summary_job_id})],
        job_updates={"agent_type": "compose", "display_title": meta_updates.get("job_title") or "Compose"},
        task_meta_updates={},
    )
    _safe_job_meta(
        case_id,
        org_id,
        job_id,
        {
            "compose_completed_at": finished_ts.isoformat(),
            "celery_task_finished_at": finished_ts.isoformat(),
            "celery_task_status": "succeeded",
        },
    )

    send_job_update(
        str(job.id),
        event="job.succeeded",
        status=Job.Status.SUCCEEDED,
        case_id=case_id,
    )
    send_case_update(
        case_id,
        event="artifact.created",
        kind="compose",
        job_id=str(job.id),
    )

    return {
        "status": "ok",
        "timeline_file": str(artifacts.timeline_file) if artifacts.timeline_file else None,
        "graph_file": str(artifacts.graph_file) if artifacts.graph_file else None,
        "client_markdown": str(artifacts.client_markdown) if artifacts.client_markdown else None,
        "lawyer_markdown": str(artifacts.lawyer_markdown) if artifacts.lawyer_markdown else None,
    }
    org_id_str = str(org_id) if org_id else None
    llm_settings = load_llm_settings()
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
        error_message = "No LLM configuration available for analyze stage"
        failure_meta = {**base_meta, "summary_status": "failed", "summary_error": error_message}
        if summary_task_id:
            failure_meta.setdefault("celery_task_id", summary_task_id)
            failure_meta["celery_task_status"] = "failed"
        failure_ts = runtime.fail(
            error=error_message,
            log_message=error_message,
            meta_updates=failure_meta,
            events=[("analyze.failed", {"llm_config_id": llm_config_id})],
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
            "analyze_llm_config_id": active_config_id,
            "analyze_llm_config_name": active_config_name,
        },
    )
    runtime.emit("analyze.started", llm_config_id=active_config_id)
    runtime.transition(task_meta_updates={"active_llm_config_id": active_config_id})

    analyze_agent = AnalyzeAgent(analyze_config)
    log.info(
        "analyze job started",
        extra={
            "job_id": job_id,
            "case_id": case_id,
            "org_id": org_id_str,
            "llm_config_id": active_config_id,
            "llm_config_name": active_config_name,
        },
    )
    intake_payload = case_intake_payload(job.case)

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
        runtime.emit("analyze.progress", **progress_payload)
        if analyze_agent.config.debug:
            log.info(
                "analyze stage",
                extra={
                    "job_id": job_id,
                    "case_id": case_id,
                    "stage": stage,
                    "event": event,
                    "details": payload,
                },
            )

    requested_providers = collect_requested_providers(
        analyze_config.provider_chain,
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
        result = analyze_agent.analyze(
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
            "analyze job failed",
            extra={"job_id": job_id, "case_id": case_id, "error": error_message},
        )
        failure_meta = {**base_meta, "summary_status": "failed", "summary_error": error_message}
        if summary_task_id:
            failure_meta.setdefault("celery_task_id", summary_task_id)
            failure_meta["celery_task_status"] = "failed"
        failure_ts = runtime.fail(
            error=error_message,
            log_message=f"Analyze failed: {error_message}",
            meta_updates=failure_meta,
            events=[("analyze.failed", {"llm_config_id": active_config_id, "details": {"stage": "runtime"}})],
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

    checksum = sha256_file(result.summary_file)
    markdown_checksum = sha256_file(result.summary_markdown_file)
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
        "analyze_llm_config_id": active_config_id,
        "analyze_llm_config_name": active_config_name,
    }
    if summary_task_id:
        meta_updates.setdefault("celery_task_id", summary_task_id)
        meta_updates["celery_task_status"] = "succeeded"

    finished_ts = runtime.succeed(
        log_message="Analyze pipeline completed",
        meta_updates=meta_updates,
        events=[
            (
                "analyze.completed",
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
        event="analysis.analyze.created",
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
    case_dir, _, _ = case_paths(case_id, org_id)
    transcript_path = Path(job.transcript_path) if job.transcript_path else latest_transcript(case_id, org_id)
    if not transcript_path or not transcript_path.exists():
        raise RuntimeError("No transcript found to build timeline")

    meta = read_job_meta(case_id, org_id, job_id)
    events_payload, seeds_path = load_summary_timeline_events(meta, case_dir)

    agent = TimelineAgent(TimelineConfig.from_env())
    result = agent.build(
        case_id=case_id,
        case_dir=case_dir,
        job_id=str(job_id),
        transcript_path=transcript_path,
        seed_path=seeds_path,
        seed_events=events_payload,
    )

    timeline_title: Optional[str] = None
    try:
        existing_titles = list(
            CaseArtifact.objects.filter(case_id=case_id, type="TIMELINE").values_list("title", flat=True)
        )
        timeline_title = unique_title("Timeline", existing_titles)
        artifact_meta = {
            "source_transcript": str(result.source_transcript),
            "events": len(result.events),
        }
        if result.seed_source is not None:
            artifact_meta["seed_source"] = str(result.seed_source)
        CaseArtifact.objects.create(
            case_id=case_id,
            case_fk=job.case,
            job_id=str(job_id),
            type="TIMELINE",
            title=timeline_title,
            path=str(result.timeline_file),
            checksum=result.checksum,
            schema_version=agent.config.schema_version,
            metadata=artifact_meta,
        )
    except Exception:
        pass

    audit_payload = {
        "job_id": job_id,
        "events": len(result.events),
        "timeline_file": str(result.timeline_file),
    }
    if result.seed_source is not None:
        audit_payload["seed_source"] = str(result.seed_source)
    audit_emit(None, case_id=case_id, event="analysis.timeline.created", data=audit_payload)

    try:
        send_case_update(case_id, event="artifact.created", kind="timeline", job_id=job_id)
    except Exception:
        pass

    return {
        "status": "ok",
        "timeline_file": str(result.timeline_file),
        "events": len(result.events),
    }


@shared_task(bind=True)
def graph_job(*_args, case_id: str, job_id: str) -> Dict[str, Any]:
    job = Job.objects.select_related("case").get(pk=job_id)
    org_id = job.organization_id or job.case.organization_id
    case_dir, _, _ = case_paths(case_id, org_id)
    transcript_path = Path(job.transcript_path) if job.transcript_path else latest_transcript(case_id, org_id)
    if not transcript_path or not transcript_path.exists():
        raise RuntimeError("No transcript found to extract entities/graph")

    meta = read_job_meta(case_id, org_id, job_id)
    hints_data, hints_path = load_summary_entity_hints(meta, case_dir)

    agent = GraphAgent(GraphConfig.from_env())
    result = agent.build(
        case_id=case_id,
        case_dir=case_dir,
        job_id=str(job_id),
        transcript_path=transcript_path,
        hint_path=hints_path,
        hint_payload=hints_data,
    )

    entities_title: Optional[str] = None
    relationships_title: Optional[str] = None
    try:
        existing_entity_titles = list(
            CaseArtifact.objects.filter(case_id=case_id, type="ENTITIES").values_list("title", flat=True)
        )
        entities_title = unique_title("Entities", existing_entity_titles)
        entity_meta = {
            "source_transcript": str(result.source_transcript),
            "entities": len(result.entities),
        }
        if result.hint_source is not None:
            entity_meta["hint_source"] = str(result.hint_source)

        existing_graph_titles = list(
            CaseArtifact.objects.filter(case_id=case_id, type="GRAPH").values_list("title", flat=True)
        )
        relationships_title = unique_title("Relationships", existing_graph_titles)
        graph_meta = {
            "source_transcript": str(result.source_transcript),
            "nodes": len(result.entities),
            "edges": len(result.edges),
        }
        if result.hint_source is not None:
            graph_meta["hint_source"] = str(result.hint_source)

        CaseArtifact.objects.create(
            case_id=case_id,
            case_fk=job.case,
            job_id=str(job_id),
            type="ENTITIES",
            title=entities_title,
            path=str(result.entities_file),
            checksum=result.entities_checksum,
            schema_version=agent.config.schema_version,
            metadata=entity_meta,
        )
        CaseArtifact.objects.create(
            case_id=case_id,
            case_fk=job.case,
            job_id=str(job_id),
            type="GRAPH",
            title=relationships_title,
            path=str(result.graph_file),
            checksum=result.graph_checksum,
            schema_version=agent.config.schema_version,
            metadata=graph_meta,
        )
    except Exception:
        pass

    audit_payload = {
        "job_id": job_id,
        "entities": len(result.entities),
        "edges": len(result.edges),
        "entities_file": str(result.entities_file),
        "graph_file": str(result.graph_file),
    }
    if result.hint_source is not None:
        audit_payload["hint_source"] = str(result.hint_source)
    audit_emit(None, case_id=case_id, event="analysis.graph.created", data=audit_payload)

    try:
        send_case_update(case_id, event="artifact.created", kind="graph", job_id=job_id)
    except Exception:
        pass

    return {
        "status": "ok",
        "entities_file": str(result.entities_file),
        "graph_file": str(result.graph_file),
        "entities": len(result.entities),
        "edges": len(result.edges),
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
