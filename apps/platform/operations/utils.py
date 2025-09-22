from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
import json

from django.utils import timezone

from apps.platform.operations.storage import ops_dir as storage_ops_dir

LOG_FILE_TEMPLATE = "{job_id}_transcription.log"
META_FILE_TEMPLATE = "{job_id}_transcription_log.json"


def update_job_meta(case_id: str, organization_id: Optional[str], job_id: str, updates: Dict[str, Any]) -> None:
    if not updates:
        return
    ops_path = storage_ops_dir(case_id, organization_id) / META_FILE_TEMPLATE.format(job_id=job_id)
    try:
        if ops_path.exists():
            current = json.loads(ops_path.read_text(encoding="utf-8"))
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


def append_job_log(case_id: str, organization_id: Optional[str], job_id: str, message: str, level: str = "INFO") -> None:
    log_path = storage_ops_dir(case_id, organization_id) / LOG_FILE_TEMPLATE.format(job_id=job_id)
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = timezone.now().isoformat()
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{timestamp} {level.upper()} | {message}\n")
    except Exception:
        pass


def job_log_path(case_id: str, organization_id: Optional[str], job_id: str) -> Path:
    return storage_ops_dir(case_id, organization_id) / LOG_FILE_TEMPLATE.format(job_id=job_id)
