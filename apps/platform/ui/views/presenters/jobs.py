from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from apps.platform.artifacts.models import CaseArtifact
from apps.platform.jobs.models import Job

from ..common import JobTelemetryPayload, _as_dict
from ..constants import STATUS_PILL_STYLES, STATUS_SORT_ORDER
from .utils import humanize_label, safe_lower, status_sort_value


def _friendly_job_title(
    job: Job,
    telemetry: Optional[JobTelemetryPayload] = None,
    artifact: Optional[CaseArtifact] = None,
) -> str:
    telem: JobTelemetryPayload = telemetry or {}
    meta = _as_dict(telem.get("metadata"))
    title_value = meta.get("job_title")
    if isinstance(title_value, str) and title_value.strip():
        return title_value
    artifacts = telem.get("artifacts") or []
    if isinstance(artifacts, list) and artifacts:
        candidate = artifacts[0]
        candidate_dict = _as_dict(candidate)
        candidate_title = candidate_dict.get("title")
        if isinstance(candidate_title, str) and candidate_title.strip():
            return candidate_title
    if artifact and getattr(artifact, "title", None):
        return artifact.title
    description = getattr(job, "description", None)
    return description or str(job.id)


def _job_agent_label(job: Optional[Job], telemetry: Optional[JobTelemetryPayload]) -> str:
    telem_agent = _as_dict((telemetry or {}).get("agent"))
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


def _job_type_label(job: Optional[Job], telemetry: Optional[JobTelemetryPayload]) -> str:
    meta = _as_dict((telemetry or {}).get("metadata"))
    kind = meta.get("job_kind")
    if kind:
        label = humanize_label(kind)
        if label:
            return label
    agent_label = _job_agent_label(job, telemetry)
    if agent_label:
        return agent_label
    mode = getattr(job, "mode", "")
    if mode:
        return humanize_label(mode)
    return "Job"


def _build_row_table_meta(row: Dict[str, Any]) -> None:
    """Populate a job row dict with deterministic sort/filter metadata for UI tables."""
    job = row.get("job")
    telemetry = row.get("telemetry") or {}
    title = str(row.get("title") or "")
    audio_meta = telemetry.get("audio") if isinstance(telemetry, dict) else {}
    meta = telemetry.get("metadata") if isinstance(telemetry, dict) else {}

    status_raw = str(telemetry.get("status") or getattr(job, "status", "") or "").strip().upper()
    review_status = str(getattr(job, "review_status", "") or "").strip().upper()
    agent_label = _job_agent_label(job, telemetry) or "Unknown"
    job_type_label = _job_type_label(job, telemetry)
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
    if isinstance(meta, dict):
        metadata_source = str(meta.get("source_name") or meta.get("source_label") or "")

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
        job_type_label,
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
        "type": safe_lower(job_type_label),
        "case": safe_lower(case_label),
        "created": created_sort,
    }
    row_table["filter"] = " ".join(safe_lower(value) for value in filter_parts if value)
    row_table["status"] = status_raw
    row_table["status_rank"] = STATUS_SORT_ORDER.get(status_raw, 900)
    row_table["status_display"] = status_display or "—"
    row_table["status_style"] = status_style
    row_table["agent_label"] = agent_label
    row_table["type_label"] = job_type_label
    row_table["case_label"] = getattr(getattr(job, "case", None), "title", "") or ""
    row_table["case_id"] = str(getattr(job, "case_id", "") or "")
    row_table["job_id"] = str(getattr(job, "id", "") or "")
    row_table["audio_name"] = audio_name
    row_table["metadata_source"] = metadata_source
    row_table["job_kind"] = job_kind_value
    row_table["review_status"] = review_status or "PENDING"
    row_table["created_iso"] = created_at.isoformat() if isinstance(created_at, datetime) else ""
    row_table["created_at"] = created_at if isinstance(created_at, datetime) else None


def _build_job_rows(
    jobs_list: List[Job],
    telemetry_map: Dict[str, JobTelemetryPayload],
    transcript_artifacts: Optional[Dict[str, CaseArtifact]] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Return hierarchical job rows ready for rendering with shared table components."""
    transcript_artifacts = transcript_artifacts or {}
    flat_rows: List[Dict[str, Any]] = []
    for job in jobs_list:
        key = str(job.id)
        data = telemetry_map.get(key)
        title = _friendly_job_title(job, data, transcript_artifacts.get(key))
        row: Dict[str, Any] = {
            "job": job,
            "telemetry": data,
            "title": title,
            "children": [],
            "is_child": False,
        }
        _build_row_table_meta(row)
        flat_rows.append(row)

    row_lookup: Dict[str, Dict[str, Any]] = {}
    for row in flat_rows:
        job_obj = row.get("job")
        if job_obj:
            row_lookup[str(job_obj.id)] = row

    display_rows: List[Dict[str, Any]] = []
    for row in flat_rows:
        telem = _as_dict(row.get("telemetry"))
        meta = _as_dict(telem.get("metadata"))
        kind = str(meta.get("job_kind", "") or "").lower()
        source_id = meta.get("source_job_id")
        parent = row_lookup.get(str(source_id)) if source_id else None
        if kind.startswith("audio_conversion") and parent:
            row["is_child"] = True
            if parent.get("job"):
                row["parent_id"] = str(parent["job"].id)

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
        display_rows.append(row)

    return display_rows, flat_rows


def _jobs_by_agent(
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
            _jobs_by_agent(children, keywords=keywords, include_conversion=include_conversion)
            if children
            else []
        )
        if _matches(row) or filtered_children:
            new_row = dict(row)
            new_row["children"] = filtered_children
            filtered.append(new_row)
    return filtered
