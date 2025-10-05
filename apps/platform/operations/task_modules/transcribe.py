from __future__ import annotations

# pyright: strict

import logging
import mimetypes
import shutil
import uuid
from pathlib import Path

from collections.abc import Mapping
from typing import Any, Protocol, cast

from celery import shared_task


class TaskProtocol(Protocol):
    request: Any
from django.utils import timezone

from apps.platform.accounts.models import Organization
from apps.platform.artifacts.models import CaseArtifact
from apps.platform.cases.models import Case
from apps.platform.jobs.models import Job
from apps.platform.jobs.utils import unique_title
from apps.platform.operations.blob_upload import UploadCancelled, upload_with_sas
from apps.platform.operations.channels import send_case_update, send_job_update
from apps.platform.operations.runtime import JobRuntimeContext, safe_job_meta
from apps.platform.operations.services.files import sha256_file
from apps.platform.operations.storage import ensure_case_dirs, ops_dir as storage_ops_dir
from apps.platform.operations.utils import append_job_log, read_job_meta
from packages.udocket_core.agents import TranscriptionAgent, TranscriptionConfig, normalize_audio
from packages.udocket_core.audio import probe_audio_metadata
from packages.udocket_core.json_utils import (
    JSONObject,
    coerce_json_object,
    coerce_json_value,
    coerce_str,
    merge_json_objects,
    read_json_object,
)

log = logging.getLogger("apps.platform.operations.tasks.transcribe")


def _load_json_dict(path: Path) -> JSONObject:
    return coerce_json_object(read_json_object(path))


def _unique_conversion_title(
    case_id: str,
    organization_id: str | uuid.UUID | None,
    source_job_id: str,
) -> str:
    existing: set[str] = set()
    ops_dir = storage_ops_dir(case_id, organization_id)
    if ops_dir.exists():
        for meta_path in ops_dir.glob("*_transcription_log.json"):
            payload = _load_json_dict(meta_path)
            job_kind = payload.get("job_kind")
            if not isinstance(job_kind, str) or job_kind != "audio_conversion":
                continue
            source_payload = payload.get("source_job_id")
            if source_payload is None or str(source_payload) != str(source_job_id):
                continue
            title_val = payload.get("job_title")
            if isinstance(title_val, str):
                title_candidate = title_val.strip()
                if title_candidate:
                    existing.add(title_candidate)
    return unique_title("Conversion", existing)


@shared_task(bind=True)
def transcribe_job(
    self: TaskProtocol,
    *,
    case_id: str,
    job_id: str,
    audio_input: str,
    mode: str = "on-demand",
    diarization: bool = False,
    language: str | None = None,
    force_wav_conversion: bool = False,
) -> Mapping[str, object]:
    """Run transcription using the importable agent.

    Arguments are explicit to decouple from legacy DB schema.
    """
    case_id = str(case_id)
    job_id = str(job_id)

    upload_required = (
        mode == "batch"
        and audio_input
        and not audio_input.lower().startswith(("http://", "https://"))
    )

    converting_attr = getattr(Job.Status, "CONVERTING", Job.Status.RUNNING)
    if isinstance(converting_attr, str):
        try:
            converting_status = Job.Status(converting_attr)
        except ValueError:
            converting_status = Job.Status.RUNNING
    else:
        converting_status = converting_attr

    org_id: str | None = None
    case_obj: Case | None = None
    job_obj: Job | None = None
    try:
        job_obj = Job.typed_objects().select_related("case").get(pk=job_id)
        if job_obj.status == Job.Status.CANCELLED:
            log.info("job already cancelled before execution", extra={"job_id": job_id})
            return {"status": Job.Status.CANCELLED.value, "job_id": job_id, "case_id": case_id}
        org_value = getattr(job_obj, "organization_id", None)
        if org_value:
            org_id = str(org_value)
        case_obj = getattr(job_obj, "case", None)
    except Exception:
        job_obj = None
    if org_id is None:
        log.error(
            "transcribe: job missing organization", extra={"job_id": job_id, "case_id": case_id}
        )
        raise RuntimeError("Job organization is required for transcription")
    if case_obj is None:
        case_obj = Case.typed_objects().select_related("organization").filter(pk=case_id).first()
    case_dir = ensure_case_dirs(case_id, org_id)
    cfg = TranscriptionConfig.from_env()
    agent = TranscriptionAgent(cfg)
    default_language_raw = getattr(cfg, "default_language", None)
    default_language = default_language_raw if isinstance(default_language_raw, str) else None

    if job_obj is None:
        job_obj = Job.typed_objects().select_related("case").get(pk=job_id)

    base_meta: JSONObject = coerce_json_object(
        {
            "job_kind": "transcription",
            "agent_type": "transcription",
            "agent_label": "Transcribe",
            "transcription_mode": mode,
            "requested_language": language or getattr(job_obj, "language", None),
            "transcription_status": str(getattr(job_obj, "status", "") or Job.Status.PENDING),
        }
    )
    safe_job_meta(case_id, org_id, job_id, base_meta)

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
    existing_job_meta = coerce_json_object(read_job_meta(case_id, org_id, job_id))

    audio_meta_updates: JSONObject = {}
    ai: str = audio_input
    try:
        if audio_input and not audio_input.startswith("http"):
            audio_path = Path(audio_input)
            if audio_path.exists():
                audio_meta_updates = coerce_json_object(
                    {
                        "audio_sha256": sha256_file(audio_path),
                        "audio_size_bytes": audio_path.stat().st_size,
                        "audio_mime": mimetypes.guess_type(audio_path.name)[0],
                    }
                )
                audio_meta_updates = merge_json_objects(audio_meta_updates, probe_audio_metadata(audio_path))
                job_meta_target = job_obj
                duration_val = audio_meta_updates.get("audio_duration_s")
                if isinstance(duration_val, (int, float, str)):
                    try:
                        duration_float = float(duration_val)
                    except (TypeError, ValueError):
                        duration_float = None
                else:
                    duration_float = None
                if duration_float is not None and not job_meta_target.duration_s:
                    job_meta_target.duration_s = duration_float
                    try:
                        job_meta_target.save(update_fields=["duration_s"])
                    except Exception:
                        pass
    except Exception:
        audio_meta_updates = {}

    if audio_meta_updates:
        safe_job_meta(case_id, org_id, job_id, audio_meta_updates)

    # Update DB status and notify
    log.info(
        "job claimed",
        extra={"job_id": job_id, "case_id": case_id, "mode": mode, "diarization": diarization},
    )

    initial_status = Job.Status.RUNNING
    initial_event = "job.started"
    initial_meta_status = "running"
    initial_job_updates: dict[str, object] = {"upload_progress": None}
    initial_payload: dict[str, object] = {}

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

    log_language = language or default_language or "auto"
    start_log_message = (
        "Worker started transcription "
        f"(mode={mode}, diarization={'on' if diarization else 'off'}, language={log_language})"
    )

    start_meta_updates: JSONObject = merge_json_objects(
        base_meta,
        {"transcription_status": initial_meta_status},
    )
    celery_task_id = runtime.task_id or None
    if celery_task_id:
        history: list[str] = []
        history_payload = existing_job_meta.get("celery_task_history")
        if isinstance(history_payload, list):
            for raw_item in cast(list[object], history_payload):
                if isinstance(raw_item, str):
                    cleaned_item = raw_item.strip()
                    if cleaned_item:
                        history.append(cleaned_item)
        else:
            previous_id = existing_job_meta.get("celery_task_id")
            if isinstance(previous_id, str) and previous_id:
                history.append(previous_id)
        if celery_task_id not in history:
            history.append(celery_task_id)
        start_meta_updates["celery_task_id"] = celery_task_id
        if history:
            start_meta_updates["celery_task_history"] = coerce_json_value(history)
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
        safe_job_meta(
            case_id,
            org_id,
            job_id,
            {"celery_task_started_at": started_at.isoformat()},
        )

    # Run the agent; only this block determines success vs. failure
    batch_upload_meta: JSONObject = {}
    try:
        # If batch mode and the input is a local file, upload to Azure Blob to obtain SAS URL
        ai = audio_input
        if upload_required:
            source_path = Path(audio_input)
            upload_path = source_path
            original_name = source_path.name
            cleanup_path: Path | None = None
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
                    batch_upload_meta = merge_json_objects(
                        batch_upload_meta,
                        {
                            "batch_upload_original_extension": source_path.suffix.lower(),
                            "batch_upload_converted": True,
                            "audio_conversion_reasons": normalization.reasons,
                        },
                    )
                    source_audio_meta: JSONObject = normalization.original_metadata or {}
                    target_audio_meta: JSONObject = normalization.metadata or {}
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
                            existing_meta = _load_json_dict(src_meta_path)
                        except Exception:
                            existing_meta = {}

                    converted_job_obj: Job | None = None
                    converted_job_id = coerce_str(
                        existing_meta.get("converted_audio_job_id")
                        or existing_meta.get("converted_wav_job_id")
                    )
                    if converted_job_id:
                        try:
                            converted_job_obj = Job.typed_objects().select_related("case").get(pk=converted_job_id)
                            existing_case = getattr(converted_job_obj, "case", None)
                            existing_case_id = getattr(existing_case, "id", None)
                            if existing_case_id is None or str(existing_case_id) != case_id:
                                converted_job_obj = None
                        except Job.DoesNotExist:
                            converted_job_obj = None

                    now_ts = timezone.now()
                    if converted_job_obj is None:
                        if case_obj is None:
                            log.warning(
                                "transcribe: missing case when creating conversion job",
                                extra={"job_id": job_id, "case_id": case_id},
                            )
                            raise RuntimeError("Case not found for conversion job")
                        case_organization = getattr(case_obj, "organization", None)
                        if not isinstance(case_organization, Organization):
                            case_org_id = getattr(case_obj, "organization_id", None)
                            case_organization = (
                                Organization.objects.filter(id=case_org_id).first()
                                if case_org_id is not None
                                else None
                            )
                        if case_organization is None:
                            job_organization = getattr(job_obj, "organization", None)
                            if isinstance(job_organization, Organization):
                                case_organization = job_organization
                        if case_organization is None:
                            log.warning(
                                "transcribe: unable to resolve organization for conversion job",
                                extra={"job_id": job_id, "case_id": case_id},
                            )
                            raise RuntimeError("Organization not resolved for conversion job")
                        wav_job_uuid = uuid.uuid4()
                        try:
                            converted_job_obj = Job.typed_objects().create(
                                id=wav_job_uuid,
                                case=case_obj,
                                organization=case_organization,
                                audio_input="",
                                mode=getattr(job_obj, "mode", Job.Mode.BATCH),
                                diarization=False,
                                language=
                                getattr(job_obj, "language", language)
                                or language
                                or default_language
                                or "en-CA",
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

                    converted_stats: JSONObject = {}
                    try:
                        converted_stats = coerce_json_object(probe_audio_metadata(converted_path))
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
                            duration_candidate = converted_stats.get("audio_duration_s")
                            if isinstance(duration_candidate, (int, float, str)):
                                converted_job_obj.duration_s = float(duration_candidate)
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

                        converted_meta_updates: JSONObject = coerce_json_object(
                            {
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
                        )
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
                            converted_meta_updates = merge_json_objects(
                                converted_meta_updates,
                                converted_stats,
                            )
                        if converted_job_id:
                            safe_job_meta(case_id, org_id, converted_job_id, converted_meta_updates)
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
                    safe_job_meta(case_id, org_id, job_id, batch_upload_meta)
                    append_job_log(
                        case_id,
                        org_id,
                        job_id,
                        f"Conversion complete: {converted_basename}",
                    )
                    if converted_job_id:
                        try:
                            status_value = (
                                Job.typed_objects()
                                .filter(pk=job_id)
                                .values_list("status", flat=True)
                                .first()
                            )
                            status_str = coerce_str(status_value)
                            if status_str is None:
                                status_str = coerce_str(getattr(job_obj, "status", None))
                            current_status = (
                                Job.Status(status_str)
                                if status_str
                                else Job.Status.RUNNING
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
                return Job.typed_objects().filter(
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
                    url_prefix = ai.split("?", 1)[0]
                    safe_job_meta(
                        case_id,
                        org_id,
                        job_id,
                        {"batch_upload_url_prefix": url_prefix},
                    )
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

            status_value = (
                Job.typed_objects()
                .filter(pk=job_id)
                .values_list("status", flat=True)
                .first()
            )
            status_choice = (
                Job.Status(status_value)
                if isinstance(status_value, str)
                else None
            )
            if status_choice in (Job.Status.CANCELLING, Job.Status.CANCELLED):
                raise UploadCancelled("Cancelled before transcription start")
            if batch_upload_meta:
                batch_upload_meta.setdefault("batch_upload_blob_name", original_name)
                safe_job_meta(case_id, org_id, job_id, batch_upload_meta)
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
                meta_payload = _load_json_dict(result.meta_json)
                azure_url = meta_payload.get("azure_transcription_url")
                if isinstance(azure_url, str) and azure_url:
                    append_job_log(case_id, org_id, job_id, f"Azure transcription created: {azure_url}")
                    safe_job_meta(
                        case_id,
                        org_id,
                        job_id,
                        {"azure_transcription_url": azure_url},
                    )
        except Exception as exc:
            log.debug("unable to parse transcription meta", extra={"job_id": job_id, "error": str(exc)})
    except UploadCancelled:
        cancel_meta: JSONObject = merge_json_objects(
            base_meta,
            {"transcription_status": "cancelled"},
            audio_meta_updates,
            batch_upload_meta,
        )
        if celery_task_id:
            cancel_meta.setdefault("celery_task_id", celery_task_id)
            cancel_meta["celery_task_status"] = "cancelled"
        cancel_payload = {
            "status": Job.Status.CANCELLED.value,
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
        safe_job_meta(
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
            if ai.startswith("/"):
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
        failure_meta: JSONObject = merge_json_objects(
            base_meta,
            {"transcription_status": "failed"},
            audio_meta_updates,
            batch_upload_meta,
        )
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
        safe_job_meta(
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
    payload: dict[str, object] = {
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
        job_obj = Job.typed_objects().select_related("case").get(pk=job_id)
    if job_obj.status == Job.Status.CANCELLED:
        log.info("job cancelled during execution; ignoring transcription output", extra={"job_id": job_id})
        try:
            transcript_path_obj = Path(result.transcript_file)
            if transcript_path_obj.exists():
                transcript_path_obj.unlink(missing_ok=True)
        except Exception:
            pass
        try:
            if ai.startswith("/"):
                local_audio = Path(ai)
                if local_audio.exists():
                    local_audio.unlink(missing_ok=True)
        except Exception:
            pass
        return {"status": Job.Status.CANCELLED.value, "job_id": job_id, "case_id": case_id}

    transcript_path_obj = Path(result.transcript_file)
    transcript_checksum: str | None = None
    transcript_bytes: int | None = None
    if transcript_path_obj.exists():
        try:
            transcript_bytes = transcript_path_obj.stat().st_size
        except Exception:
            transcript_bytes = None
        transcript_checksum = sha256_file(transcript_path_obj)

    artifact_title: str | None = None
    job_meta_title: str | None = None
    try:
        existing_titles = CaseArtifact.typed_objects().filter(
            case_id=str(case_id),
            type="TRANSCRIPT",
        ).values_list("title", flat=True)
        job_meta_path = storage_ops_dir(case_id, org_id) / f"{job_id}_transcription_log.json"
        if job_meta_path.exists():
            job_meta_payload = _load_json_dict(job_meta_path)
            title_candidate = job_meta_payload.get("job_title")
            if isinstance(title_candidate, str) and title_candidate.strip():
                job_meta_title = title_candidate.strip()
        artifact_title = job_meta_title or unique_title("Transcript", existing_titles)
        CaseArtifact.typed_objects().create(
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

    meta_updates: JSONObject = merge_json_objects(
        base_meta,
        {"transcription_status": "completed"},
        audio_meta_updates,
        batch_upload_meta,
        {
            "transcript_file": str(result.transcript_file),
            "transcript_sha256": transcript_checksum,
            "transcript_bytes": transcript_bytes,
            "transcript_title": artifact_title,
            "transcription_language": result.language,
            "transcription_region": result.region,
            "transcription_duration_s": result.duration_s,
        },
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
    safe_job_meta(
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
