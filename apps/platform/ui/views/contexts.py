from __future__ import annotations

# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportAttributeAccessIssue=false

import json
from datetime import datetime
from typing import Any, Dict, Optional

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest
from django.db.models import Count

from apps.platform.accounts.models import User
from apps.platform.accounts.utils import resolve_request_organization
from apps.platform.artifacts.models import CaseArtifact
from apps.platform.authorization.capabilities import has_capability
from apps.platform.cases.models import Case
from apps.platform.jobs.models import Job, JobNote
from apps.platform.jobs.telemetry import summarize_jobs
from apps.platform.tenancy import scope_jobs

from .common import JobTelemetryPayload, as_dict
from .presenters.job_actions import build_job_action_entries
from .presenters.cases import (
    build_case_developer_cards,
    build_case_header_context,
    build_tool_panels,
    case_progress_context,
    collect_case_artifacts,
)
from .presenters.case_fields import prepare_case_fields
from .presenters.analysis_modules import analysis_modules_context
from .presenters.guardian import (
    collect_guardian_reviews,
    guardian_stats_from_reviews,
    guardian_violation_entries,
)
from .presenters.jobs import build_job_rows, friendly_job_title
from .presenters.utils import render_audio_brief_panel_html, render_notes_panel_html
from apps.platform.jobs.notes import serialize_notes
from .selectors import job_telemetry_map, job_telemetry_payload


def format_metadata(metadata: Dict[str, Any] | None) -> list[Dict[str, Any]]:
    if not metadata:
        return []
    items: list[dict[str, Any]] = []
    for key in sorted(metadata.keys()):
        value = metadata[key]
        is_structured = isinstance(value, (dict, list))
        if is_structured:
            display = json.dumps(value, ensure_ascii=False, indent=2)
        else:
            display = "" if value is None else str(value)
        items.append(
            {
                "key": key,
                "label": key.replace("_", " ").title(),
                "value": display,
                "is_multiline": "\n" in display,
            }
        )
    return items


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

    note_counts: Dict[str, int] = {}
    if jobs_list:
        note_count_rows = (
            JobNote.objects.filter(job__in=jobs_list)
            .values("job_id")
            .annotate(count=Count("id"))
        )
        note_counts = {str(row["job_id"]): int(row["count"]) for row in note_count_rows}

    job_summary = summarize_jobs(jobs_list)
    job_summary_last_dt = job_summary.get("last_update")
    job_summary["last_update"] = job_summary_last_dt.isoformat() if job_summary_last_dt else None

    telemetry_map: Dict[str, JobTelemetryPayload] = job_telemetry_map(jobs_list, request)

    display_rows, flat_rows = build_job_rows(
        jobs_list,
        telemetry_map,
        transcript_artifacts,
        note_counts=note_counts,
    )

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

    analysis_modules = analysis_modules_context(
        request, case, jobs_list, telemetry_map, transcript_artifacts
    )
    artifacts_all = collect_case_artifacts(request, case)

    guardian_reviews = collect_guardian_reviews(artifacts_all)
    guardian_stats = guardian_stats_from_reviews(guardian_reviews)
    guardian_violations = guardian_violation_entries(guardian_reviews)

    progress_ctx = case_progress_context(
        case,
        jobs_list,
        telemetry_map,
        memberships,
        guardian_stats=guardian_stats,
    )

    return_url = request.get_full_path()

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
        return_url=return_url,
        guardian_stats=guardian_stats,
        guardian_reviews=guardian_reviews,
        guardian_violations=guardian_violations,
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
    metadata_map = as_dict(telemetry.get("metadata"))
    metadata_items = format_metadata(metadata_map)
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

    source_job_id_value = str(telemetry_meta.get("source_job_id") or "")
    conversion_mark_targets = ",".join(filter(None, [str(job.id), source_job_id_value]))

    job_notes = list(
        JobNote.objects.filter(job=job)
        .select_related("created_by")
        .order_by("-created_at")
    )
    notes_entries = serialize_notes(job_notes)
    notes_updated_at = notes_entries[0]["created_at"] if notes_entries else None
    notes_updated_by = (
        notes_entries[0].get("created_by_label")
        or notes_entries[0].get("created_by")
        if notes_entries
        else ""
    )
    notes_count = len(notes_entries)

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

    job_id_str = str(job.id)
    case_id_str = str(job.case_id)
    notes_panel_html = render_notes_panel_html(
        job_id=job_id_str,
        entries=notes_entries,
        updated_at=notes_updated_at,
        updated_by=notes_updated_by,
        user_can_add=can_review,
    )

    audio_verify_enabled = bool(
        audio_meta.get("path")
        or audio_meta.get("sha256")
        or telemetry_meta.get("converted_audio_sha256")
        or telemetry_meta.get("audio_sha256")
    )
    audio_panel_current_html = render_audio_brief_panel_html(
        panel_title="Audio",
        panel_key="current",
        job_id=job_id_str,
        audio=audio_meta,
        metadata=telemetry_meta,
        refresh_enabled=True,
        refresh_panel="current",
        refresh_job_id=job_id_str,
        refresh_display_job_id=job_id_str,
        refresh_case_id=case_id_str,
        verify_enabled=audio_verify_enabled,
        verify_target="audio",
        verify_scope=None,
        verify_mark_targets=job_id_str,
        case=job.case,
        job=job,
        case_id=case_id_str,
    )

    source_panel_html = ""
    converted_panel_html = ""
    if job_kind == "audio_conversion":
        source_verify_enabled = bool(
            (source_audio_meta or {}).get("path")
            or (source_audio_meta or {}).get("sha256")
            or telemetry_meta.get("source_audio_file")
            or telemetry_meta.get("source_audio_sha256")
        )
        source_panel_html = render_audio_brief_panel_html(
            panel_title="Source audio",
            panel_key="source",
            job_id=job_id_str,
            audio=source_audio_meta or {},
            metadata=telemetry_meta,
            refresh_enabled=bool(source_job_id_value),
            refresh_panel="source",
            refresh_job_id=source_job_id_value,
            refresh_display_job_id=job_id_str,
            refresh_case_id=case_id_str,
            verify_enabled=source_verify_enabled,
            verify_target="audio",
            verify_scope="source",
            verify_source_job=source_job_id_value,
            verify_mark_targets=conversion_mark_targets,
            case=job.case,
            job=job,
            case_id=case_id_str,
        )
        converted_verify_enabled = bool(
            audio_meta.get("path")
            or audio_meta.get("sha256")
            or telemetry_meta.get("converted_audio_sha256")
            or telemetry_meta.get("converted_audio_file")
        )
        converted_panel_html = render_audio_brief_panel_html(
            panel_title="Converted WAV",
            panel_key="converted",
            job_id=job_id_str,
            audio=audio_meta,
            metadata=telemetry_meta,
            refresh_enabled=True,
            refresh_panel="converted",
            refresh_job_id=job_id_str,
            refresh_display_job_id=job_id_str,
            refresh_case_id=case_id_str,
            verify_enabled=converted_verify_enabled,
            verify_target="audio",
            verify_scope="converted",
            verify_mark_targets=conversion_mark_targets,
            case=job.case,
            job=job,
            case_id=case_id_str,
        )

    return {
        "case": job.case,
        "job": job,
        "telemetry": telemetry,
        "artifact": artifact,
        "job_title": job_title,
        "metadata_items": metadata_items,
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
        "notes_updated_at": notes_updated_at,
        "notes_updated_by": notes_updated_by,
        "notes_entries": notes_entries,
        "notes_count": notes_count,
        "notes_panel_html": notes_panel_html,
        "source_job_id": source_job_id_value,
        "conversion_mark_targets": conversion_mark_targets,
        "audio_panel_current_html": audio_panel_current_html,
        "audio_panel_source_html": source_panel_html,
        "audio_panel_converted_html": converted_panel_html,
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
