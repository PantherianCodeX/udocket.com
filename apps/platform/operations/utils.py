# pyright: strict

from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from django.utils import timezone

from apps.platform.operations.storage import ops_dir as storage_ops_dir
from apps.platform.jobs.models import Job

LOG_FILE_TEMPLATE = "{job_id}_transcription.log"
META_FILE_TEMPLATE = "{job_id}_transcription_log.json"


def _object_dict(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        mapping = cast(dict[object, object], value)
        return {str(key): val for key, val in mapping.items()}
    return {}


def update_job_meta(
    case_id: str,
    organization_id: str | uuid.UUID | None,
    job_id: str,
    updates: Mapping[str, object],
) -> None:
    if not updates:
        return
    ops_path = storage_ops_dir(case_id, organization_id) / META_FILE_TEMPLATE.format(job_id=job_id)
    try:
        if ops_path.exists():
            current = _object_dict(json.loads(ops_path.read_text(encoding="utf-8")))
        else:
            current = {}
    except Exception:
        current = {}
    changed = False
    for key, value in updates.items():
        if value is None:
            continue
        if current.get(key) != value:
            current[key] = value
            changed = True
    if changed:
        try:
            ops_path.write_text(json.dumps(current, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    # Persist select metadata fields onto the Job record for efficient querying.
    resolved_meta: dict[str, object] = (
        current if changed else {**current, **dict(updates)}
    )
    job_updates: dict[str, Any] = {}

    agent_type = resolved_meta.get("agent_type")
    if isinstance(agent_type, str) and agent_type.strip():
        job_updates["agent_type"] = agent_type.strip()[:64]

    agent_label = resolved_meta.get("agent_label")
    if isinstance(agent_label, str) and agent_label.strip():
        job_updates["agent_label"] = agent_label.strip()[:128]

    job_kind = resolved_meta.get("job_kind")
    if isinstance(job_kind, str) and job_kind.strip():
        job_updates["job_kind"] = job_kind.strip()[:64]

    job_title = (
        resolved_meta.get("job_title")
        or resolved_meta.get("title")
        or resolved_meta.get("display_title")
    )
    if isinstance(job_title, str) and job_title.strip():
        job_updates["display_title"] = job_title.strip()[:255]

    source_job_value = resolved_meta.get("source_job_id") or resolved_meta.get(
        "converted_audio_job_id"
    )
    if source_job_value:
        try:
            source_uuid = uuid.UUID(str(source_job_value))
        except (TypeError, ValueError):
            source_uuid = None
        if source_uuid:
            # Guard against dangling references; only set when the source exists
            try:
                if Job.objects.filter(pk=source_uuid).exists():
                    job_updates["source_job_id"] = source_uuid
            except Exception:
                pass

    if job_updates:
        try:
            job_uuid = uuid.UUID(str(job_id))
        except (TypeError, ValueError):
            job_uuid = None
        if job_uuid:
            try:
                Job.objects.filter(pk=job_uuid).update(**job_updates)
            except Exception:
                pass


def read_job_meta(
    case_id: str,
    organization_id: str | uuid.UUID | None,
    job_id: str,
) -> dict[str, Any]:
    meta_path = storage_ops_dir(case_id, organization_id) / META_FILE_TEMPLATE.format(job_id=job_id)
    if not meta_path.exists():
        return {}
    try:
        return _object_dict(json.loads(meta_path.read_text(encoding="utf-8")))
    except Exception:
        return {}


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
