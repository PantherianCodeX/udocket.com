from __future__ import annotations

# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownParameterType=false

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from apps.platform.artifacts.models import CaseArtifact
from apps.platform.jobs.models import Job

from ..common import JobRow, JobTelemetryPayload, as_dict
from ..constants import STATUS_PILL_STYLES, STATUS_SORT_ORDER
from .utils import humanize_label, safe_lower, status_sort_value


def friendly_job_title(
    job: Job,
    telemetry: Optional[JobTelemetryPayload] = None,
    artifact: Optional[CaseArtifact] = None,
) -> str:
    telem: JobTelemetryPayload = telemetry or {}
    meta = as_dict(telem.get("metadata"))
    title_value = meta.get("job_title")
    if isinstance(title_value, str) and title_value.strip():
        return title_value
    artifacts = telem.get("artifacts") or []
    if isinstance(artifacts, list) and artifacts:
        candidate = artifacts[0]
        candidate_dict = as_dict(candidate)
        candidate_title = candidate_dict.get("title")
        if isinstance(candidate_title, str) and candidate_title.strip():
            return candidate_title
    if artifact and getattr(artifact, "title", None):
        return artifact.title
    description = getattr(job, "description", None)
    return description or str(job.id)


def job_agent_label(job: Optional[Job], telemetry: Optional[JobTelemetryPayload]) -> str:
    telem_agent = as_dict((telemetry or {}).get("agent"))
    for key in ("label", "name", "type"):
        value = telem_agent.get(key)
        if isinstance(value, str) and value.strip():
            return value
        if value:
            return str(value)
    if job:
        mode = getattr(job, "mode", None)
        if mode:
            return humanize_label(mode)
    return ""


def job_type_label(job: Optional[Job], telemetry: Optional[JobTelemetryPayload]) -> str:
    meta = as_dict((telemetry or {}).get("metadata"))
    kind = meta.get("job_kind")
    if kind:
        label = humanize_label(kind)
        if label:
            return label
    agent_label = job_agent_label(job, telemetry)
    if agent_label:
        return agent_label
    mode = getattr(job, "mode", "")
    if mode:
        return humanize_label(mode)
    return "Job"




def job_most_recent_timestamp(job: Optional[Job]) -> datetime:
    if not job:
        return datetime.min
    finished_at = getattr(job, "finished_at", None)
    if isinstance(finished_at, datetime):
        return finished_at
    started_at = getattr(job, "started_at", None)
    if isinstance(started_at, datetime):
        return started_at
    created_at = getattr(job, "created_at", None)
    return created_at if isinstance(created_at, datetime) else datetime.min


def agent_key(telem: Optional[JobTelemetryPayload], job: Optional[Job] = None) -> str:
    telem_payload: JobTelemetryPayload = telem or {}
    agent = as_dict(telem_payload.get("agent"))
    raw = agent.get("type") or agent.get("name") or telem_payload.get("agent_label") or ""
    if not raw and job is not None:
        raw = job.mode or ""
    normalized = str(raw).strip().lower()
    normalized = normalized.replace("agent", "").replace("analysis", "")
    normalized = normalized.replace(" ", "_")
    return normalized


def latest_jobs_by_agent(jobs: List[Job], telemetry_map: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    latest: Dict[str, Dict[str, Any]] = {}
    for job in jobs:
        job_id = getattr(job, "id", None)
        key = str(job_id) if job_id is not None else ""
        telem = telemetry_map.get(key) or {}
        key = agent_key(telem, job)
        if not key:
            mode = getattr(job, "mode", None)
            key = str(mode).lower() if mode else "unknown"
        existing = latest.get(key)
        if not existing:
            latest[key] = {"job": job, "telemetry": telem}
            continue
        current_ts = job_most_recent_timestamp(existing["job"])
        new_ts = job_most_recent_timestamp(job)
        if new_ts and new_ts > current_ts:
            latest[key] = {"job": job, "telemetry": telem}
    return latest


def select_agent(latest: Dict[str, JobRow], keywords: tuple[str, ...]) -> Optional[JobRow]:
    for key, payload in latest.items():
        if any(word in key for word in keywords):
            return payload
    return None


def map_job_status(job: Optional[Job]) -> str:
    if not job:
        return 'Created'
    status = str(getattr(job, 'status', '') or '').upper()
    if status == getattr(Job.Status, 'CONVERTING', 'CONVERTING'):
        return 'Converting'
    if status == Job.Status.UPLOADING:
        return 'Uploading'
    if status in {Job.Status.RUNNING, Job.Status.PENDING}:
        return 'Running'
    if status == Job.Status.SUCCEEDED:
        return 'Created'
    if status == getattr(Job.Status, 'CANCELLING', 'CANCELLING'):
        return 'Cancelling'
    if status in {Job.Status.FAILED, getattr(Job.Status, 'CANCELLED', 'CANCELLED')}:
        return 'Rejected'
    return 'Created'

def build_row_table_meta(row: Dict[str, Any]) -> None:
    """Populate a job row dict with deterministic sort/filter metadata for UI tables."""
    job = row.get("job")
    telemetry = row.get("telemetry") or {}
    title = str(row.get("title") or "")
    audio_meta = telemetry.get("audio") if isinstance(telemetry, dict) else {}
    meta = telemetry.get("metadata") if isinstance(telemetry, dict) else {}

    status_raw = str(telemetry.get("status") or getattr(job, "status", "") or "").strip().upper()
    review_status = str(getattr(job, "review_status", "") or "").strip().upper()
    agent_label = job_agent_label(job, telemetry) or "Unknown"
    job_type_label_text = job_type_label(job, telemetry)
    case_label = humanize_label(getattr(getattr(job, "case", None), "title", ""))
    created_at = getattr(job, "created_at", None)
    created_sort = (
        f"{int(created_at.timestamp() * 1000):020d}"
        if isinstance(created_at, datetime)
        else "00000000000000000000"
    )

    audio_name = ""
    if isinstance(audio_meta, dict):
        audio_name = str(
            audio_meta.get("original_name")
            or audio_meta.get("path")
            or audio_meta.get("audio_file")
            or ""
        )

    metadata_source = ""
    notes_count = 0
    if isinstance(meta, dict):
        metadata_source = str(meta.get("source_name") or meta.get("source_label") or "")
        ui_notes = meta.get("ui_notes")
        if isinstance(ui_notes, dict):
            raw_entries = ui_notes.get("entries")
            if isinstance(raw_entries, list):
                notes_count = sum(1 for entry in raw_entries if isinstance(entry, dict) and entry.get("text"))
            elif ui_notes.get("text"):
                notes_count = 1
        elif isinstance(ui_notes, list):
            notes_count = sum(1 for entry in ui_notes if isinstance(entry, dict) and entry.get("text"))

    job_kind_value = ""
    if isinstance(meta, dict):
        job_kind_value = str(meta.get("job_kind") or "")
    if not job_kind_value and job and getattr(job, "mode", None):
        job_kind_value = str(job.mode)

    status_display = status_raw.title() if status_raw else ""
    status_style = STATUS_PILL_STYLES.get(status_raw, "border-white/20 bg-white/5 text-slate-300")

    filter_parts = [
        title,
        status_raw,
        review_status,
        agent_label,
        job_type_label_text,
        case_label,
        audio_name,
        metadata_source,
    ]

    row.setdefault("table", {})
    row_table = row["table"]
    row_table["sort"] = {
        "title": safe_lower(title),
        "status": status_sort_value(status_raw),
        "review": review_status or "PENDING",
        "agent": safe_lower(agent_label),
        "type": safe_lower(job_type_label_text),
        "case": safe_lower(case_label),
        "created": created_sort,
    }
    row_table["filter"] = " ".join(safe_lower(value) for value in filter_parts if value)
    row_table["status"] = status_raw
    row_table["status_rank"] = STATUS_SORT_ORDER.get(status_raw, 900)
    row_table["status_display"] = status_display or "—"
    row_table["status_style"] = status_style
    row_table["agent_label"] = agent_label
    row_table["type_label"] = job_type_label_text
    row_table["case_label"] = getattr(getattr(job, "case", None), "title", "") or ""
    row_table["case_id"] = str(getattr(job, "case_id", "") or "")
    row_table["job_id"] = str(getattr(job, "id", "") or "")
    row_table["audio_name"] = audio_name
    row_table["metadata_source"] = metadata_source
    row_table["notes_count"] = notes_count
    row_table["job_kind"] = job_kind_value
    row_table["review_status"] = review_status or "PENDING"
    row_table["created_iso"] = created_at.isoformat() if isinstance(created_at, datetime) else ""
    row_table["created_at"] = created_at if isinstance(created_at, datetime) else None


def build_job_rows(
    jobs_list: List[Job],
    telemetry_map: Dict[str, JobTelemetryPayload],
    transcript_artifacts: Optional[Dict[str, CaseArtifact]] = None,
    *,
    note_counts: Optional[Dict[str, int]] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Return hierarchical job rows ready for rendering with shared table components."""
    transcript_artifacts = transcript_artifacts or {}
    flat_rows: List[Dict[str, Any]] = []
    for job in jobs_list:
        key = str(job.id)
        data = telemetry_map.get(key)
        title = friendly_job_title(job, data, transcript_artifacts.get(key))
        row: Dict[str, Any] = {
            "job": job,
            "telemetry": data,
            "title": title,
            "children": [],
            "is_child": False,
            "group_id": key,
            "root_id": key,
            "parent_id": "",
        }
        build_row_table_meta(row)
        if note_counts is not None:
            row.setdefault("table", {})["notes_count"] = note_counts.get(key, 0)
        flat_rows.append(row)

    row_lookup: Dict[str, Dict[str, Any]] = {}
    for row in flat_rows:
        job_obj = row.get("job")
        if job_obj:
            row_lookup[str(job_obj.id)] = row

    display_rows: List[Dict[str, Any]] = []
    for row in flat_rows:
        telem = as_dict(row.get("telemetry"))
        meta = as_dict(telem.get("metadata"))
        kind = str(meta.get("job_kind", "") or "").lower()
        source_id = meta.get("source_job_id")
        parent = row_lookup.get(str(source_id)) if source_id else None
        if kind.startswith("audio_conversion") and parent:
            row["is_child"] = True
            parent_group_id = parent.get("group_id") or str(getattr(parent.get("job"), "id", ""))
            row["parent_id"] = parent_group_id or ""
            row["root_id"] = parent.get("root_id") or parent_group_id or row.get("group_id")

            def child_sort_key(child_row: Dict[str, Any]) -> datetime:
                job_obj = child_row.get("job")
                if isinstance(job_obj, Job):
                    if job_obj.finished_at:
                        return job_obj.finished_at
                    if job_obj.started_at:
                        return job_obj.started_at
                    if job_obj.created_at:
                        return job_obj.created_at
                return datetime.min

            children_list = parent.setdefault("children", [])
            children_list.append(row)
            children_list.sort(key=child_sort_key)
            continue
        if note_counts is not None:
            row.setdefault("table", {})["notes_count"] = note_counts.get(str(getattr(row.get("job"), "id", "")), 0)
        display_rows.append(row)

    return display_rows, flat_rows


def jobs_by_agent(
    job_rows: List[Dict[str, Any]],
    *,
    keywords: Tuple[str, ...],
    include_conversion: bool = False,
) -> List[Dict[str, Any]]:
    keywords_lower = tuple(word.lower() for word in keywords)

    def _matches(row: Dict[str, Any]) -> bool:
        job = row.get("job")
        telem = row.get("telemetry") or {}
        meta = telem.get("metadata") or {}
        agent = telem.get("agent") or {}
        agent_type = str(agent.get("type") or "").lower()
        job_kind = str(meta.get("job_kind") or "").lower()
        job_mode = str(getattr(job, "mode", "") or "").lower()

        if any(word in agent_type for word in keywords_lower):
            return True
        if any(word in job_kind for word in keywords_lower):
            return True
        if any(word in job_mode for word in keywords_lower):
            return True
        if include_conversion and job_kind.startswith("audio_conversion"):
            return True
        return False

    filtered: List[Dict[str, Any]] = []
    for row in job_rows:
        children = row.get("children") or []
        filtered_children = (
            jobs_by_agent(children, keywords=keywords, include_conversion=include_conversion)
            if children
            else []
        )
        if _matches(row) or filtered_children:
            new_row = dict(row)
            new_row["children"] = filtered_children
            filtered.append(new_row)
    return filtered
