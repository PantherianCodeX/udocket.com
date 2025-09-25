from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, Optional

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

from .common import JobTelemetryPayload, _as_dict
from .presenters.job_actions import build_job_action_entries
from .presenters.cases import (
    _analysis_modules_context,
    _build_case_developer_cards,
    _build_case_header_context,
    _build_tool_panels,
    _case_progress_context,
    _collect_case_artifacts,
    _prepare_case_fields,
)
from .presenters.jobs import _build_job_rows, _friendly_job_title
from .selectors import _job_telemetry_map, _job_telemetry_payload


def _format_metadata(metadata: Dict[str, Any] | None) -> list[Dict[str, Any]]:
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


def _user_can_review_case(user: Optional[User], case: Case) -> bool:
    if getattr(settings, "PLATFORM_DEV_OPEN", False):
        return True
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if case.reviewer_id and str(user.id) == str(case.reviewer_id):
        return True
    return has_capability(user, str(case.id), "case.update")


def _compute_case_tool_state(request: HttpRequest, case: Case) -> Dict[str, Any]:
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

    telemetry_map: Dict[str, JobTelemetryPayload] = _job_telemetry_map(jobs_list, request)

    display_rows, flat_rows = _build_job_rows(jobs_list, telemetry_map, transcript_artifacts)

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
    user_can_review = _user_can_review_case(user, case)

    for row in flat_rows:
        row["actions"] = build_job_action_entries(
            row.get("job"),
            row.get("telemetry"),
            can_review=user_can_review,
            is_child=bool(row.get("is_child")),
        )

    progress_ctx = _case_progress_context(case, jobs_list, telemetry_map, memberships)
    analysis_modules = _analysis_modules_context(
        request, case, jobs_list, telemetry_map, transcript_artifacts
    )
    artifacts_all = _collect_case_artifacts(request, case)

    tool_panels = _build_tool_panels(
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
    case_fields = case_details_panel.get("body_context", {}).get("fields", _prepare_case_fields(case))
    case_header = _build_case_header_context(
        case,
        panels=tool_panels,
        case_fields=case_fields,
        memberships=memberships,
        job_summary_last_update=job_summary_last_dt,
    )
    developer_cards = _build_case_developer_cards(tool_panels)

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


def _job_detail_context(
    request: HttpRequest,
    job: Job,
    *,
    telemetry: Optional[Dict[str, Any]] = None,
    title_error: Optional[str] = None,
    title_edit: bool = False,
) -> Dict[str, Any]:
    telemetry_payload = telemetry if telemetry is not None else _job_telemetry_payload(job, request, ui_mode=True)
    telemetry = telemetry_payload
    artifacts = telemetry.get("artifacts") or []
    artifact = artifacts[0] if artifacts else None
    db_artifact = (
        CaseArtifact.objects.filter(case_id=str(job.case_id), job_id=str(job.id), type="TRANSCRIPT")
        .order_by("-created_at")
        .first()
    )
    job_title = _friendly_job_title(job, telemetry, db_artifact)
    metadata_map = _as_dict(telemetry.get("metadata"))
    metadata_items = _format_metadata(metadata_map)
    azure_cancel_status = metadata_map.get("azure_cancel_status")
    azure_cancel_body = metadata_map.get("azure_cancel_body")

    audio_meta = _as_dict(telemetry.get("audio"))
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
                source_telemetry = _job_telemetry_payload(source_job, request, ui_mode=True)
                source_audio_meta = _as_dict(source_telemetry.get("audio"))
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
    }


def _get_case_and_org(request: HttpRequest, case_id: str) -> tuple[Case, Any]:
    try:
        active_org = resolve_request_organization(request, required=True)
    except PermissionDenied:
        raise Http404
    cases_qs = Case.objects.select_related("organization")
    case = cases_qs.for_user(getattr(request, "user", None)).filter(pk=case_id).first()
    if not case or case.organization_id != getattr(active_org, "id", None):
        raise Http404
    return case, active_org
