# pyright: strict

from __future__ import annotations

import uuid
from collections.abc import Mapping
from pathlib import Path

from django.utils import timezone

from apps.platform.jobs.models import Job
from apps.platform.operations.storage import ops_dir as storage_ops_dir
from packages.udocket_common.jobs.meta import JobRecordPatch, merge_job_meta
from packages.udocket_common.json_utils import (
    JSONObject,
    read_json_object,
    write_json_object,
)

LOG_FILE_TEMPLATE = "{job_id}_transcription.log"
META_FILE_TEMPLATE = "{job_id}_transcription_log.json"


def update_job_meta(
    case_id: str,
    organization_id: str | uuid.UUID | None,
    job_id: str,
    updates: Mapping[str, object],
) -> None:
    if not updates:
        return
    ops_path = storage_ops_dir(case_id, organization_id) / META_FILE_TEMPLATE.format(job_id=job_id)
    current = read_json_object(ops_path)
    merged_meta, changed = merge_job_meta(current, updates)
    if changed:
        try:
            write_json_object(ops_path, merged_meta)
        except Exception:
            pass

    patch = JobRecordPatch.from_meta(merged_meta)
    job_updates = patch.as_model_kwargs(include_source_job=False)

    source_job_id = patch.source_job_id
    if source_job_id is not None:
        # Guard against dangling references; only set when the source exists.
        try:
            if Job.objects.filter(pk=source_job_id).exists():
                job_updates["source_job_id"] = source_job_id
        except Exception:
            pass

    if not job_updates:
        return

    try:
        job_uuid = uuid.UUID(str(job_id))
    except (TypeError, ValueError):
        return

    try:
        Job.objects.filter(pk=job_uuid).update(**job_updates)
    except Exception:
        pass


def read_job_meta(
    case_id: str,
    organization_id: str | uuid.UUID | None,
    job_id: str,
) -> JSONObject:
    meta_path = storage_ops_dir(case_id, organization_id) / META_FILE_TEMPLATE.format(job_id=job_id)
    return read_json_object(meta_path)


def append_job_log(
    case_id: str,
    organization_id: str | uuid.UUID | None,
    job_id: str,
    message: str,
    level: str = "INFO",
) -> None:
    log_path = storage_ops_dir(case_id, organization_id) / LOG_FILE_TEMPLATE.format(job_id=job_id)
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = timezone.now().isoformat()
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{timestamp} {level.upper()} | {message}\n")
    except Exception:
        pass


def job_log_path(case_id: str, organization_id: str | uuid.UUID | None, job_id: str) -> Path:
    return storage_ops_dir(case_id, organization_id) / LOG_FILE_TEMPLATE.format(job_id=job_id)
