from __future__ import annotations

# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportAttributeAccessIssue=false

import json
from datetime import datetime
from typing import Any, Dict, Iterable, Optional

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest

from apps.platform.accounts.models import User
from apps.platform.accounts.utils import resolve_request_organization
from apps.platform.artifacts.models import CaseArtifact
from apps.platform.authorization.capabilities import has_capability
from apps.platform.cases.models import Case
from apps.platform.jobs.models import Job
from apps.platform.jobs.telemetry import summarize_jobs
from apps.platform.tenancy import scope_jobs

from .common import JobTelemetryPayload, as_dict
from .presenters.job_actions import build_job_action_entries
from .presenters.cases import (
    analysis_modules_context,
    build_case_developer_cards,
    build_case_header_context,
    build_tool_panels,
    case_progress_context,
    collect_case_artifacts,
    prepare_case_fields,
)
from .presenters.jobs import build_job_rows, friendly_job_title
from .selectors import job_telemetry_map, job_telemetry_payload


SECTION_PREFIXES: list[tuple[str, str]] = [
    ("job_", "Job"),
    ("review_", "Review"),
    ("audio_", "Audio"),
    ("source_", "Source Audio"),
    ("transcript_", "Transcript"),
    ("converted_", "Converted Audio"),
    ("agent_", "Agent"),
    ("azure_", "Azure"),
    ("batch_", "Batch"),
]


def _format_metadata_value(value: Any) -> tuple[str, bool]:
    if isinstance(value, (dict, list)):
        display = json.dumps(value, ensure_ascii=False, indent=2)
        return display, True
    if value is None:
        return "", False
    if isinstance(value, float):
        return f"{value}", False
    return str(value), False


def _metadata_section_for_key(key: str) -> tuple[str, str, str]:
    lower_key = key.lower()
    for prefix, label in SECTION_PREFIXES:
        if lower_key.startswith(prefix):
            trimmed = key[len(prefix) :]
            return prefix, label, trimmed
    return "", "Additional Metadata", key


def _format_label(raw_key: str) -> str:
    key = raw_key.replace("__", "_")
    return key.replace("_", " ").strip().title() or raw_key


def format_metadata(metadata: Dict[str, Any] | None, *, exclude: Iterable[str] | None = None) -> list[Dict[str, Any]]:
    if not metadata:
        return []
    exclude_set = {key.lower() for key in (exclude or [])}
    grouped: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for key in sorted(metadata.keys()):
        if key.lower() in exclude_set:
            continue
        prefix, section_label, label_key = _metadata_section_for_key(key)
        section_id = section_label
        if section_id not in grouped:
            grouped[section_id] = {"title": section_label, "items": []}
            order.append(section_id)
        display, is_multiline = _format_metadata_value(metadata[key])
        grouped[section_id]["items"].append(
            {
                "key": key,
                "label": _format_label(label_key if prefix else key),
                "value": display,
                "is_multiline": is_multiline or "\n" in display,
                "copy_text": display,
            }
        )

    # Preserve declared prefix order first, then any additional sections alphabetically
    ordered_sections: list[Dict[str, Any]] = []
    seen = set()
    for _, label in SECTION_PREFIXES:
        if label in grouped:
            section = grouped[label]
            section["items"].sort(key=lambda item: item["label"])
            ordered_sections.append(section)
            seen.add(label)
    for section_id in sorted(order):
        if section_id in seen:
            continue
        section = grouped[section_id]
        section["items"].sort(key=lambda item: item["label"])
        ordered_sections.append(section)
    return ordered_sections


def user_can_review_case(user: Optional[User], case: Case) -> bool:
    if getattr(settings, "PLATFORM_DEV_OPEN", False):
        return True
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if case.reviewer_id and str(user.id) == str(case.reviewer_id):
        return True
    return has_capability(user, str(case.id), "case.update")


def compute_case_tool_state(request: HttpRequest, case: Case) -> Dict[str, Any]:
    jobs_qs = (
        Job.objects.select_related("case", "case__organization", "reviewed_by")
        .filter(case=case)
        .order_by("-created_at")
    )
    jobs_list = list(scope_jobs(jobs_qs, getattr(request, "user", None)))

    job_ids = [str(job.id) for job in jobs_list]
    transcript_artifacts: Dict[str, CaseArtifact] = {}
    if job_ids:
        for art in (
            CaseArtifact.objects.filter(case_id=str(case.id), job_id__in=job_ids, type="TRANSCRIPT")
            .order_by("-created_at")
        ):
            key = art.job_id or ""
            if key and key not in transcript_artifacts:
                transcript_artifacts[key] = art

    job_summary = summarize_jobs(jobs_list)
    job_summary_last_dt = job_summary.get("last_update")
    job_summary["last_update"] = job_summary_last_dt.isoformat() if job_summary_last_dt else None

    telemetry_map: Dict[str, JobTelemetryPayload] = job_telemetry_map(jobs_list, request)

    display_rows, flat_rows = build_job_rows(jobs_list, telemetry_map, transcript_artifacts)

    latest_job = None
    latest_job_telemetry = None
    latest_activity_ts = None
    if jobs_list:
        jobs_sorted = sorted(
            jobs_list,
            key=lambda j: (j.finished_at or j.started_at or j.created_at or datetime.min),
            reverse=True,
        )
        latest_job = jobs_sorted[0]
        latest_job_telemetry = telemetry_map.get(str(latest_job.id))
        latest_activity_ts = latest_job.finished_at or latest_job.started_at or latest_job.created_at

    memberships = list(case.memberships.select_related("user"))

    user = getattr(request, "user", None)
    user_can_review = user_can_review_case(user, case)

    for row in flat_rows:
        row["actions"] = build_job_action_entries(
            row.get("job"),
            row.get("telemetry"),
            can_review=user_can_review,
            is_child=bool(row.get("is_child")),
        )

    progress_ctx = case_progress_context(case, jobs_list, telemetry_map, memberships)
    analysis_modules = analysis_modules_context(
        request, case, jobs_list, telemetry_map, transcript_artifacts
    )
    artifacts_all = collect_case_artifacts(request, case)

    tool_panels = build_tool_panels(
        case,
        progress_items=progress_ctx["progress_items"],
        job_rows=display_rows,
        telemetry_map=telemetry_map,
        transcript_artifacts=transcript_artifacts,
        analysis_modules=analysis_modules,
        artifacts=artifacts_all,
        memberships=memberships,
        latest_job=latest_job,
        latest_job_telemetry=latest_job_telemetry,
        job_summary=job_summary,
        all_job_rows=flat_rows,
        job_summary_last_dt=job_summary_last_dt,
        user_can_review=user_can_review,
    )

    case_details_panel = tool_panels.get("case-details") or {}
    case_fields = case_details_panel.get("body_context", {}).get("fields", prepare_case_fields(case))
    case_header = build_case_header_context(
        case,
        panels=tool_panels,
        case_fields=case_fields,
        memberships=memberships,
        job_summary_last_update=job_summary_last_dt,
    )
    developer_cards = build_case_developer_cards(tool_panels)

    return {
        "jobs_list": jobs_list,
        "job_rows": display_rows,
        "job_rows_flat": flat_rows,
        "transcript_artifacts": transcript_artifacts,
        "tool_panels": tool_panels,
        "case_header": case_header,
        "developer_cards": developer_cards,
        "job_summary": job_summary,
        "latest_activity_ts": latest_activity_ts,
        "job_summary_last_dt": job_summary_last_dt,
        "user_can_review": user_can_review,
    }


def job_detail_context(
    request: HttpRequest,
    job: Job,
    *,
    telemetry: Optional[Dict[str, Any]] = None,
    title_error: Optional[str] = None,
    title_edit: bool = False,
) -> Dict[str, Any]:
    telemetry_payload = telemetry if telemetry is not None else job_telemetry_payload(job, request, ui_mode=True)
    telemetry = telemetry_payload
    artifacts = telemetry.get("artifacts") or []
    artifact = artifacts[0] if artifacts else None
    db_artifact = (
        CaseArtifact.objects.filter(case_id=str(job.case_id), job_id=str(job.id), type="TRANSCRIPT")
        .order_by("-created_at")
        .first()
    )
    job_title = friendly_job_title(job, telemetry, db_artifact)
    raw_metadata_map = as_dict(telemetry.get("metadata"))
    metadata_map: Dict[str, Any] = dict(raw_metadata_map)
    notes_info = as_dict(metadata_map.get("ui_notes")) if isinstance(metadata_map.get("ui_notes"), dict) else {}
    note_text = notes_info.get("text") if isinstance(notes_info.get("text"), str) else ""
    note_updated_at = notes_info.get("updated_at") if isinstance(notes_info.get("updated_at"), str) else None
    note_updated_by = notes_info.get("updated_by_label") or notes_info.get("updated_by")
    if note_updated_by and not isinstance(note_updated_by, str):
        note_updated_by = str(note_updated_by)
    if "ui_notes" in metadata_map:
        metadata_map.pop("ui_notes", None)
    azure_cancel_status = metadata_map.get("azure_cancel_status")
    azure_cancel_body = metadata_map.get("azure_cancel_body")

    audio_meta = as_dict(telemetry.get("audio"))
    audio_mime = str(audio_meta.get("mime") or "").lower()
    audio_names = [str(audio_meta.get("path") or ""), str(audio_meta.get("original_name") or "")]
    is_wav_input = audio_mime in {"audio/wav", "audio/x-wav"}
    if not is_wav_input:
        for name in audio_names:
            if name.lower().endswith(".wav"):
                is_wav_input = True
                break
    telemetry_meta = metadata_map
    converted_flag = bool(
        telemetry_meta.get("converted_wav_path")
        or telemetry_meta.get("batch_upload_converted")
        or telemetry_meta.get("converted_audio_job_id")
    )
    job_kind = str(telemetry_meta.get("job_kind", ""))
    show_convert_button = (
        job.status not in {Job.Status.SUCCEEDED, Job.Status.RUNNING, Job.Status.PENDING}
        and not converted_flag
        and not is_wav_input
        and job_kind != "audio_conversion"
    )

    source_audio_meta: Dict[str, Any] | None = None
    if job_kind == "audio_conversion":
        source_job_id = telemetry_meta.get("source_job_id")
        if source_job_id:
            try:
                source_job = Job.objects.select_related("case", "case__organization").get(pk=source_job_id, case_id=job.case_id)
                source_telemetry = job_telemetry_payload(source_job, request, ui_mode=True)
                source_audio_meta = as_dict(source_telemetry.get("audio"))
            except Job.DoesNotExist:
                source_audio_meta = None
            except Exception:
                source_audio_meta = None

    user_obj = getattr(request, "user", None)
    dev_open = getattr(settings, "PLATFORM_DEV_OPEN", False)
    can_review = False
    if dev_open:
        can_review = True
    elif user_obj and getattr(user_obj, "is_authenticated", False):
        if job.case.reviewer_id and str(user_obj.id) == str(job.case.reviewer_id):
            can_review = True
        elif has_capability(user_obj, str(job.case_id), "case.update"):
            can_review = True

    is_sub_job = bool(telemetry_meta.get("source_job_id"))
    allow_title_edit = not (job_kind == "audio_conversion" or is_sub_job)

    reviewer = getattr(job, "reviewed_by", None)
    reviewer_label = None
    if reviewer:
        reviewer_label = (
            getattr(reviewer, "display_name", None)
            or reviewer.get_full_name()
            or getattr(reviewer, "email", None)
            or getattr(reviewer, "username", None)
            or str(getattr(reviewer, "id", ""))
        )

    transcript_meta = as_dict(telemetry.get("transcript"))
    agent_meta = as_dict(telemetry.get("agent"))

    def iso_or_none(value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None

    # Enrich metadata for modal presentation without mutating persisted values
    metadata_enrichment: Dict[str, Any] = {
        "job_id": str(job.id),
        "job_case_id": str(job.case_id),
        "job_status": job.status,
        "job_mode": job.get_mode_display() if hasattr(job, "get_mode_display") else job.mode,
        "job_language": telemetry.get("language"),
        "job_diarization": "Enabled" if telemetry.get("diarization") else "Disabled",
        "job_created_at": iso_or_none(job.created_at),
        "job_started_at": iso_or_none(job.started_at),
        "job_finished_at": iso_or_none(job.finished_at),
        "review_status": job.review_status,
        "review_comment": job.review_comment,
        "reviewed_at": iso_or_none(job.reviewed_at),
        "reviewed_by": reviewer_label,
        "audio_original_name": audio_meta.get("original_name"),
        "audio_path": audio_meta.get("path"),
        "audio_duration_s": audio_meta.get("duration_s") or audio_meta.get("duration"),
        "audio_channels": audio_meta.get("channels"),
        "audio_sample_rate_hz": audio_meta.get("sample_rate_hz") or audio_meta.get("sample_rate"),
        "audio_bitrate_kbps": audio_meta.get("bitrate_kbps") or audio_meta.get("bitrate"),
        "audio_codec": audio_meta.get("codec"),
        "audio_layout": audio_meta.get("channel_layout"),
        "audio_mime": audio_meta.get("mime"),
        "audio_sha256": audio_meta.get("sha256") or raw_metadata_map.get("audio_sha256"),
        "audio_size_bytes": audio_meta.get("size_bytes_local")
        or audio_meta.get("size_bytes_remote")
        or raw_metadata_map.get("audio_size_bytes"),
        "transcript_words": transcript_meta.get("words"),
        "transcript_bytes": transcript_meta.get("bytes"),
        "transcript_avg_confidence_pct": transcript_meta.get("avg_confidence_pct"),
        "transcript_avg_confidence": transcript_meta.get("avg_confidence"),
        "transcript_segments": transcript_meta.get("segments"),
        "transcript_sha256": transcript_meta.get("sha256") or raw_metadata_map.get("transcript_sha256"),
        "transcript_path": transcript_meta.get("path"),
        "agent_region": agent_meta.get("region"),
        "agent_attempts_used": agent_meta.get("attempts_used"),
        "agent_diarization_speakers": agent_meta.get("diarization_speakers"),
        "agent_timestamp_utc": agent_meta.get("timestamp_utc"),
        "agent_azure_transcription_url": agent_meta.get("azure_transcription_url"),
    }
    for key, value in metadata_enrichment.items():
        if value is not None and key not in metadata_map:
            metadata_map[key] = value

    metadata_sections = format_metadata(metadata_map, exclude={"ui_notes"})
    if note_text or note_updated_at or note_updated_by:
        updated_display = note_updated_by or ""
        if note_updated_at:
            updated_display = f"{(note_updated_by or 'Unknown').strip()} · {note_updated_at}" if updated_display else note_updated_at
        elif note_updated_by:
            updated_display = note_updated_by
        metadata_sections.insert(
            0,
            {
                "title": "Team Notes",
                "items": [
                    {
                        "key": "ui_notes.text",
                        "label": "Notes",
                        "value": note_text,
                        "copy_text": note_text,
                        "is_multiline": True,
                    },
                    {
                        "key": "ui_notes.updated",
                        "label": "Updated",
                        "value": updated_display,
                        "copy_text": note_updated_at or updated_display,
                        "is_multiline": False,
                    },
                ],
            },
        )

    return {
        "case": job.case,
        "job": job,
        "telemetry": telemetry,
        "artifact": artifact,
        "job_title": job_title,
        "metadata_sections": metadata_sections,
        "metadata_items": metadata_sections,
        "azure_cancel_status": azure_cancel_status,
        "azure_cancel_body": azure_cancel_body,
        "user_can_review": can_review,
        "title_error": title_error,
        "title_edit": title_edit,
        "show_convert_button": show_convert_button,
        "job_kind": job_kind,
        "metadata_map": telemetry_meta,
        "audio_meta": audio_meta,
        "source_audio": source_audio_meta or {},
        "allow_title_edit": allow_title_edit,
        "notes_text": note_text,
        "notes_updated_at": note_updated_at,
        "notes_updated_by": note_updated_by,
    }


def get_case_and_org(request: HttpRequest, case_id: str) -> tuple[Case, Any]:
    try:
        active_org = resolve_request_organization(request, required=True)
    except PermissionDenied:
        raise Http404
    cases_qs = Case.objects.select_related("organization")
    case = cases_qs.for_user(getattr(request, "user", None)).filter(pk=case_id).first()
    if not case or case.organization_id != getattr(active_org, "id", None):
        raise Http404
    return case, active_org
