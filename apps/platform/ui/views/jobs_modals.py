from __future__ import annotations

# pyright: strict
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from apps.platform.jobs.models import Job
from apps.platform.operations.utils import job_log_path

from .auth import ensure_authenticated
from .common import JobTelemetryPayload
from .contexts import get_case_and_org, job_detail_context
from .presenters.jobs import friendly_job_title
from .selectors import job_telemetry_payload


def _dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    typed_items: list[dict[str, Any]] = []
    for element in cast(list[Any], value):
        if not isinstance(element, dict):
            continue
        typed_items.append(cast(dict[str, Any], element))
    return typed_items


_LEVEL_PRIORITY: dict[str, int] = {
    "CRITICAL": 0,
    "ERROR": 1,
    "WARNING": 2,
    "INFO": 3,
    "DEBUG": 4,
}

_LEVEL_STYLE_MAP: dict[str, str] = {
    "CRITICAL": "text-red-200 font-semibold",
    "ERROR": "text-red-300",
    "WARNING": "text-amber-300",
    "INFO": "text-sky-300",
    "DEBUG": "text-slate-400",
}


def _parse_log_entries(log_text: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for raw_line in log_text.splitlines():
        stripped_line = raw_line.rstrip("\n")
        if not stripped_line.strip():
            continue
        prefix, separator, remainder = stripped_line.partition("|")
        prefix_value = prefix.strip()
        message = remainder.strip() if separator else stripped_line.strip()
        timestamp = ""
        level = "INFO"
        if prefix_value:
            prefix_parts = prefix_value.split()
            if len(prefix_parts) >= 2:
                timestamp = " ".join(prefix_parts[:-1])
                level = prefix_parts[-1].upper()
            else:
                timestamp = prefix_parts[0]
        normalized_level = level.upper()
        entry: dict[str, str] = {
            "timestamp": timestamp,
            "level": normalized_level,
            "message": message,
            "level_class": _LEVEL_STYLE_MAP.get(normalized_level, "text-slate-300"),
        }
        entries.append(entry)
    return entries


def _resolve_job_or_404(case_id: str, job_id: UUID, request: HttpRequest) -> Job:
    case, _ = get_case_and_org(request, case_id)
    job = (
        Job.objects.select_related("case", "case__organization", "reviewed_by")
        .filter(case=case, pk=job_id)
        .first()
    )
    if not job:
        raise Http404
    return job


@require_http_methods(["GET"])
def case_job_transcript(request: HttpRequest, case_id: str, job_id: UUID) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    job = _resolve_job_or_404(case_id, job_id, request)

    transcript_path = job.transcript_path
    transcript_text = ""
    if transcript_path and Path(transcript_path).exists():
        try:
            with Path(transcript_path).open("r", encoding="utf-8", errors="replace") as handle:
                transcript_text = handle.read(20000)
                if handle.read(1):
                    transcript_text += "\n…"
        except Exception:
            transcript_text = ""

    telemetry_dict: JobTelemetryPayload = job_telemetry_payload(job, request, ui_mode=True)
    download_url: str | None = None
    raw_artifacts = telemetry_dict.get("artifacts")
    artifacts_list: list[dict[str, Any]] = _dict_list(raw_artifacts)
    for artifact in artifacts_list:
        artifact_type = str(artifact.get("type") or "").upper()
        download_candidate = artifact.get("download_url")
        if artifact_type != "TRANSCRIPT" or not isinstance(download_candidate, str):
            continue
        download_url = download_candidate
        break

    friendly_title = friendly_job_title(job, telemetry_dict, None)
    modal_created = job.finished_at or job.started_at or job.created_at
    context = {
        "title": friendly_title,
        "job_id": job.id,
        "created_at": modal_created,
        "modal_heading": "Transcript Preview",
        "modal_title_text": friendly_title,
        "modal_text": transcript_text,
        "modal_text_id": f"modal-text-{job.id}",
        "modal_download_url": download_url,
        "modal_download_label": "Download transcript",
        "modal_copy_label": "Copy transcript",
        "modal_close_label": "Close",
        "modal_empty_text": "Transcript not available for this job.",
    }
    return render(request, "platform_ui/components/modals/transcript_modal.html", context)


@require_http_methods(["GET"])
def case_job_logs_modal(request: HttpRequest, case_id: str, job_id: UUID) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    job = _resolve_job_or_404(case_id, job_id, request)

    log_path = job_log_path(str(job.case_id), getattr(job, "organization_id", None), str(job.id))
    log_entries: list[dict[str, str]] = []
    if not log_path.exists():
        log_text = "No log entries recorded for this job yet."
    else:
        try:
            text = log_path.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001
            text = "Unable to read log contents."
        if len(text) > 50000:
            text = text[-50000:]
            text = "…" + text
        log_text = text
        log_entries = _parse_log_entries(log_text)

    telemetry_dict = job_telemetry_payload(job, request, ui_mode=True)
    friendly_title = friendly_job_title(job, telemetry_dict, None)
    modal_created = job.finished_at or job.started_at or job.created_at
    meta_items: list[dict[str, Any]] = []
    if log_path.exists():
        meta_items.append(
            {"label": "Log path", "copy_text": str(log_path), "display": str(log_path)}
        )
    modal_log_levels: list[str] = []
    if log_entries:
        seen_levels: set[str] = set()
        for entry in log_entries:
            level_value = entry.get("level", "INFO").upper()
            entry["level"] = level_value
            entry["level_class"] = _LEVEL_STYLE_MAP.get(level_value, "text-slate-300")
            if level_value not in seen_levels:
                seen_levels.add(level_value)
                modal_log_levels.append(level_value)
        modal_log_levels.sort(key=lambda value: _LEVEL_PRIORITY.get(value, 99))
    context = {
        "title": friendly_title,
        "job_id": str(job.id),
        "created_at": modal_created,
        "modal_heading": "Job Logs",
        "modal_title_text": friendly_title,
        "modal_text": log_text,
        "modal_text_id": f"modal-log-{job.id}",
        "modal_download_url": f"/api/v1/jobs/{job.id}/logs/",
        "modal_download_label": "Download log",
        "modal_copy_label": "Copy log",
        "modal_close_label": "Close",
        "modal_empty_text": "No log entries recorded for this job.",
        "modal_meta_items": meta_items,
        "modal_log_entries": log_entries,
        "modal_log_levels": modal_log_levels,
    }
    return render(request, "platform_ui/components/modals/log_modal.html", context)


@require_http_methods(["GET"])
def case_job_metadata_modal(request: HttpRequest, case_id: str, job_id: UUID) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    job = _resolve_job_or_404(case_id, job_id, request)

    telemetry_dict = job_telemetry_payload(job, request, ui_mode=True)
    detail_context = job_detail_context(request, job, telemetry=telemetry_dict)
    raw_metadata_items = detail_context.get("metadata_items")
    metadata_items: list[dict[str, Any]] = _dict_list(raw_metadata_items)
    friendly_title = detail_context.get("job_title") or friendly_job_title(
        job, telemetry_dict, detail_context.get("artifact")
    )
    modal_created = job.finished_at or job.started_at or job.created_at
    meta_summary: list[dict[str, Any]] = []
    case_obj = getattr(job, "case", None)
    if case_obj:
        meta_summary.append(
            {
                "label": "Case",
                "display": getattr(case_obj, "title", "") or str(case_obj.id),
                "copy_text": str(case_obj.id),
            }
        )
    meta_summary.append({"label": "Job ID", "display": str(job.id), "copy_text": str(job.id)})
    metadata_sections: list[dict[str, Any]] = []
    if metadata_items:
        metadata_sections.append({"title": "Metadata", "items": metadata_items})

    notes_entries = detail_context.get("notes_entries") or []
    if notes_entries:
        note_items: list[dict[str, Any]] = []
        for idx, note in enumerate(notes_entries, start=1):
            if not isinstance(note, dict):
                continue
            raw_label = note.get("created_by_label") or note.get("created_by") or f"Note {idx}"
            timestamp = note.get("created_at")
            label = f"{raw_label} — {timestamp}" if timestamp else raw_label
            value = str(note.get("text") or "")
            note_items.append(
                {
                    "key": note.get("id") or f"note_{idx}",
                    "label": label,
                    "value": value,
                    "is_multiline": True,
                }
            )
        if note_items:
            metadata_sections.append({"title": "Team notes", "items": note_items})

    context = {
        "title": friendly_title,
        "job_id": str(job.id),
        "created_at": modal_created,
        "modal_title_text": friendly_title,
        "metadata_items": metadata_items,
        "metadata_sections": metadata_sections,
        "metadata_empty_text": "Metadata not recorded for this job.",
        "modal_meta_items": meta_summary,
    }
    return render(request, "platform_ui/components/modals/job_metadata_modal.html", context)
