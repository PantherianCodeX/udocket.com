from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Protocol, cast

import re

from django.core.exceptions import PermissionDenied
import logging

from django.conf import settings
from django.db import models
from django.db.utils import IntegrityError
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import base64

from apps.platform.cases.models import Case, CaseMembership
from apps.platform.accounts.models import OrganizationMembership, User
from apps.platform.accounts.utils import (
    resolve_request_organization,
    set_active_admin_org_id,
    user_accessible_organizations,
)
from apps.platform.jobs.models import Job
from apps.platform.operations.tasks import transcribe_job
from apps.platform.operations.storage import ensure_case_dirs, ops_dir as storage_ops_dir
from apps.platform.operations.utils import append_job_log, update_job_meta, job_log_path
from apps.platform.authorization.models import PermissionPreset, Role
from apps.platform.authorization.capabilities import role_capabilities, has_capability
from apps.platform.artifacts.registry import ARTIFACT_FIELD_REGISTRY
from apps.platform.artifacts.models import CaseArtifact
from apps.platform.jobs.utils import unique_title
from django.contrib.auth import logout
from apps.platform.tenancy import accessible_organization_ids, scope_jobs
from apps.platform.jobs.telemetry import summarize_jobs

from .constants import (
    STATUS_CLASS_MAP,
    STATUS_PILL_STYLES,
    CANCELABLE_STATUSES,
    RESTARTABLE_STATUSES,
    STATUS_SORT_ORDER,
    DEFAULT_TABLE_FILTERS,
    CASE_JOB_TABLE_COLUMNS,
    GLOBAL_JOB_TABLE_COLUMNS,
)

from .presenters.utils import humanize_label, safe_lower, status_class, status_sort_value, user_label

from .common import JobTelemetryPayload, JobRow, _as_dict

from .selectors import _job_telemetry_map, _job_telemetry_payload

from .presenters.cases import (
    _analysis_modules_context,
    _artifact_payload,
    _build_case_developer_cards,
    _build_case_header_context,
    _build_case_progress,
    _build_tool_panels,
    _case_assignment_lists,
    _case_field_specs,
    _case_owner_details,
    _case_owner_labels,
    _case_owner_memberships,
    _case_progress_context,
    _collect_case_artifacts,
    _latest_successful_transcription_job,
    _organization_member_options,
    _prepare_case_fields,
    _table_config,
)

from .presenters.jobs import (
    _agent_key,
    _build_job_rows,
    _build_row_table_meta,
    _friendly_job_title,
    _job_agent_label,
    _job_most_recent_timestamp,
    _job_type_label,
    _jobs_by_agent,
    _latest_jobs_by_agent,
    _map_job_status,
    _select_agent,
)

log = logging.getLogger("apps.platform.ui")


class _TaskWithDelay(Protocol):
    def delay(self, *args: Any, **kwargs: Any) -> Any:
        ...


transcribe_job_task: _TaskWithDelay = cast(_TaskWithDelay, transcribe_job)




def _format_metadata(metadata: dict[str, Any] | None) -> list[dict[str, Any]]:
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


def user_label(user: User) -> str:
    return (
        user.display_name
        or user.get_full_name()
        or user.email
        or user.username
        or str(user.pk)
    )
def _map_job_status(job: Optional[Job]) -> str:
    if not job:
        return "Created"
    status = str(getattr(job, "status", "") or "").upper()
    if status == getattr(Job.Status, "CONVERTING", "CONVERTING"):
        return "Converting"
    if status == Job.Status.UPLOADING:
        return "Uploading"
    if status in {Job.Status.RUNNING, Job.Status.PENDING}:
        return "Running"
    if status == Job.Status.SUCCEEDED:
        return "Created"
    if status == getattr(Job.Status, "CANCELLING", "CANCELLING"):
        return "Cancelling"
    if status in {Job.Status.FAILED, getattr(Job.Status, "CANCELLED", "CANCELLED")}:
        return "Rejected"
    return "Created"
def _user_can_review_case(user: Optional[User], case: Case) -> bool:
    if getattr(settings, "PLATFORM_DEV_OPEN", False):
        return True
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if case.reviewer_id and str(user.id) == str(case.reviewer_id):
        return True
    return has_capability(user, str(case.id), "case.update")


def _job_action_entries(
    job: Optional[Job],
    telemetry: Optional[JobTelemetryPayload],
    *,
    can_review: bool,
    is_child: bool,
) -> List[Dict[str, Any]]:
    if not job:
        return []

    job_id = str(job.id)
    case_id = str(job.case_id)
    status = str(getattr(job, "status", "") or "").upper()
    telem = telemetry or {}
    meta = _as_dict(telem.get("metadata"))
    transcript_payload = _as_dict(telem.get("transcript"))
    audio_payload = _as_dict(telem.get("audio"))
    artifact_entry = None
    artifacts = telem.get("artifacts") or []
    if artifacts:
        candidate = artifacts[0]
        artifact_entry = _as_dict(candidate) if isinstance(candidate, Mapping) else candidate

    job_kind = str(meta.get("job_kind") or "").lower()
    converted_available = bool(meta.get("converted_wav_available"))
    source_job_id = meta.get("source_job_id")

    sections: List[Dict[str, Any]] = []

    def _add_section(label: str) -> List[Dict[str, Any]]:
        section: Dict[str, Any] = {"label": label, "items": []}
        sections.append(section)
        return section["items"]

    workflow_items: List[Dict[str, Any]] = []
    if status in CANCELABLE_STATUSES:
        workflow_items.append(
            {
                "label": "Cancel job",
                "action": "cancel",
                "confirm": "Cancel this job?",
                "visible_when": "cancel",
                "job_id": job_id,
                "kind": "api",
            }
        )

    if status in RESTARTABLE_STATUSES:
        workflow_items.append(
            {
                "label": "Restart transcription",
                "action": "restart",
                "confirm": "Restart this job?",
                "visible_when": "restart",
                "job_id": job_id,
                "kind": "api",
            }
        )

    if workflow_items:
        _items = _add_section("Workflow")
        _items.extend(workflow_items)

    review_items: List[Dict[str, Any]] = []
    if can_review and status == Job.Status.SUCCEEDED:
        review_items.append(
            {
                "label": "Approve transcript",
                "action": "approve",
                "confirm": "Approve this transcript?",
                "visible_when": "review",
                "job_id": job_id,
                "kind": "api",
            }
        )
        review_items.append(
            {
                "label": "Reject transcript",
                "action": "reject",
                "prompt": "Reason for rejection (optional):",
                "visible_when": "review",
                "job_id": job_id,
                "kind": "api",
            }
        )
    if review_items:
        _items = _add_section("Review")
        _items.extend(review_items)

    files_items: List[Dict[str, Any]] = []
    if artifact_entry and artifact_entry.get("download_url"):
        files_items.append(
            {
                "label": "Download transcript",
                "href": artifact_entry.get("download_url"),
                "kind": "link",
            }
        )
    if transcript_payload.get("path"):
        files_items.append(
            {
                "label": "View transcript",
                "action": "view-transcript",
                "job_id": job_id,
                "kind": "modal",
            }
        )
    audio_download_url = None
    if audio_payload.get("path"):
        audio_download_url = f"/api/v1/jobs/{job_id}/download-audio/"
    elif job_kind != "audio_conversion" and converted_available:
        audio_download_url = f"/api/v1/jobs/{job_id}/download-audio/?converted=1"
    if audio_download_url:
        files_items.append(
            {
                "label": "Download audio",
                "href": audio_download_url,
                "kind": "link",
            }
        )
    files_items.append(
        {
            "label": "View logs",
            "action": "view-log",
            "job_id": job_id,
            "case_id": case_id,
            "kind": "modal",
        }
    )
    if files_items:
        _items = _add_section("Files & Logs")
        _items.extend(files_items)

    navigation_items: List[Dict[str, Any]] = []
    if job_kind == "audio_conversion" and source_job_id:
        navigation_items.append(
            {
                "label": "View source job",
                "action": "view-job",
                "target": str(source_job_id),
                "kind": "navigate",
            }
        )
    if navigation_items:
        _items = _add_section("Navigation")
        _items.extend(navigation_items)

    if not is_child:
        danger_items: List[Dict[str, Any]] = [
            {
                "label": "Delete job",
                "action": "delete",
                "confirm": "Delete this job? This cannot be undone.",
                "job_id": job_id,
                "kind": "delete",
            }
        ]
        _items = _add_section("Danger zone")
        _items.extend(danger_items)

    return [section for section in sections if section.get("items")]


def _candidate_transcript_paths(job: Job, telemetry: Optional[JobTelemetryPayload]) -> List[str]:
    paths: List[str] = []
    if isinstance(job.transcript_path, str) and job.transcript_path:
        paths.append(job.transcript_path)
    transcript_payload = _as_dict((telemetry or {}).get("transcript"))
    path_from_telem = transcript_payload.get("path")
    if isinstance(path_from_telem, str) and path_from_telem and path_from_telem not in paths:
        paths.append(path_from_telem)
    return paths


def _default_transcript_title(job: Job, telemetry: Optional[JobTelemetryPayload]) -> str:
    transcript_payload = _as_dict((telemetry or {}).get("transcript"))
    title_value = transcript_payload.get("title")
    if isinstance(title_value, str) and title_value.strip():
        return title_value.strip()
    meta = _as_dict((telemetry or {}).get("metadata"))
    job_title = meta.get("job_title")
    if isinstance(job_title, str) and job_title.strip():
        return job_title.strip()
    return _friendly_job_title(job, telemetry)


def _unique_transcript_title(case_id: str, base_title: str, organization_id: Optional[str] = None) -> str:
    base = (base_title or "").strip() or "Transcript"
    base = base[:180]
    titles: set[str] = set(
        CaseArtifact.objects.filter(case_id=case_id, type="TRANSCRIPT").values_list("title", flat=True)
    )
    try:
        ops_dir = storage_ops_dir(case_id, organization_id)
        if ops_dir.exists():
            for meta_path in ops_dir.glob("*_transcription_log.json"):
                try:
                    payload = json.loads(meta_path.read_text(encoding="utf-8"))
                except Exception:
                    continue
                title_value = payload.get("job_title") or payload.get("transcript_title")
                if isinstance(title_value, str) and title_value.strip():
                    titles.add(title_value.strip())
    except Exception:
        pass

    candidate = unique_title(base, titles)
    if len(candidate) <= 200:
        return candidate

    if "-" in candidate:
        _stem, suffix = candidate.rsplit("-", 1)
        trimmed = base[: max(0, 200 - len(suffix) - 1)] or base[:200]
        return f"{trimmed}-{suffix}"[:200]

    return candidate[:200]


def _ensure_transcript_artifact(
    *,
    case: Case,
    job: Job,
    telemetry: Optional[JobTelemetryPayload] = None,
    title: Optional[str] = None,
    metadata_source: str = "ui.transcript_promote",
) -> Optional[CaseArtifact]:
    artifact = (
        CaseArtifact.objects.filter(case_id=str(case.id), job_id=str(job.id), type="TRANSCRIPT")
        .order_by("-created_at")
        .first()
    )
    if artifact:
        return artifact

    candidate_paths = _candidate_transcript_paths(job, telemetry)
    if not candidate_paths:
        return None

    for path in candidate_paths:
        existing = (
            CaseArtifact.objects.filter(case_id=str(case.id), type="TRANSCRIPT", path=path)
            .order_by("-created_at")
            .first()
        )
        if existing:
            return existing

    base_title = title or _default_transcript_title(job, telemetry)
    attempts = 0
    while attempts < 3:
        attempts += 1
        candidate_title = _unique_transcript_title(str(case.id), base_title, getattr(case, "organization_id", None))
        metadata = {"created_via": metadata_source}
        for path in candidate_paths:
            try:
                artifact = CaseArtifact.objects.create(
                    case_id=str(case.id),
                    case_fk=case,
                    job_id=str(job.id),
                    type="TRANSCRIPT",
                    title=candidate_title,
                    path=path,
                    metadata=metadata,
                )
                return artifact
            except IntegrityError:
                break
            except Exception:
                continue
    return None
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
        row["actions"] = _job_action_entries(
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
        request,
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


def _ensure_authenticated(request: HttpRequest) -> HttpResponse | None:
    """Gate UI views when dev-open mode is disabled."""

    user = getattr(request, "user", None)
    if user and getattr(user, "is_authenticated", False):
        return None
    if getattr(settings, "PLATFORM_DEV_OPEN", False):
        return None
    login_url = getattr(settings, "LOGIN_URL", "/admin/login/")
    if request.method == "GET":
        return redirect(login_url)
    return HttpResponse("Authentication required", status=401)


@require_http_methods(["GET", "POST"])
def index(request: HttpRequest) -> HttpResponse:
    auth_response = _ensure_authenticated(request)
    if auth_response:
        return auth_response

    organization = resolve_request_organization(request, required=False)
    cases_qs = Case.objects.select_related("organization")
    cases = cases_qs.for_user(getattr(request, "user", None)).order_by("-created_at")
    if organization is not None:
        cases = cases.filter(organization=organization)
    else:
        cases = cases.none()

    if request.method == "POST":
        if organization is None:
            context = {
                "cases": cases,
                "active_org": None,
                "error": "Select an organization before creating cases.",
                "client_position_choices": Case.ClientPosition.choices,
                "court_level_choices": Case.CourtLevel.choices,
                "court_division_choices": Case.CourtDivision.choices,
                "representation_choices": Case.Representation.choices,
            }
            return render(request, "platform_ui/dashboard/index.html", context)

        title = (request.POST.get("title") or "").strip()
        client_name = (request.POST.get("client_name") or "").strip()
        opposing_party = (request.POST.get("opposing_party") or "").strip()
        client_position = (request.POST.get("client_position") or "").strip()
        court_location = (request.POST.get("court_location") or "").strip()
        court_level = (request.POST.get("court_level") or "").strip()
        court_division = (request.POST.get("court_division") or "").strip()
        court_case_number = (request.POST.get("court_case_number") or "").strip()
        representation = (request.POST.get("representation") or "").strip()
        legal_aid = bool(request.POST.get("legal_aid"))
        pro_bono = bool(request.POST.get("pro_bono"))
        notes = (request.POST.get("notes") or "").strip()

        court_date_raw = request.POST.get("court_date") or ""
        filing_deadline_raw = request.POST.get("filing_deadline") or ""
        court_date_value = None
        filing_deadline_value = None
        if court_date_raw:
            try:
                dt = datetime.strptime(court_date_raw, "%Y-%m-%dT%H:%M")
                court_date_value = timezone.make_aware(dt, timezone.get_current_timezone())
            except Exception:
                court_date_value = None
        if filing_deadline_raw:
            try:
                filing_deadline_value = datetime.strptime(filing_deadline_raw, "%Y-%m-%d").date()
            except Exception:
                filing_deadline_value = None

        case = Case.objects.create(
            id=str(uuid.uuid4()),
            title=title or "Untitled case",
            organization=organization,
            client_name=client_name,
            opposing_party=opposing_party,
            client_position=client_position,
            court_location=court_location,
            court_level=court_level,
            court_division=court_division,
            court_case_number=court_case_number,
            representation=representation,
            legal_aid=legal_aid,
            pro_bono=pro_bono,
            court_date=court_date_value,
            filing_deadline=filing_deadline_value,
            notes=notes,
        )

        user = getattr(request, "user", None)
        if user and getattr(user, "is_authenticated", False):
            CaseMembership.objects.get_or_create(
                case=case,
                user=user,
                defaults={"role": CaseMembership.Role.OWNER},
            )
        return redirect("ui-case-detail", case_id=case.id)

    context = {
        "cases": cases,
        "active_org": organization,
        "client_position_choices": Case.ClientPosition.choices,
        "court_level_choices": Case.CourtLevel.choices,
        "court_division_choices": Case.CourtDivision.choices,
        "representation_choices": Case.Representation.choices,
    }
    return render(request, "platform_ui/dashboard/index.html", context)

@require_http_methods(["GET"])
def favicon(request: HttpRequest) -> HttpResponse:
    """Serve a tiny in-memory PNG favicon to avoid 404 noise."""
    # 1x1 transparent PNG
    data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
    )
    resp = HttpResponse(data, content_type="image/png")
    resp["Cache-Control"] = "public, max-age=86400"
    return resp

@require_http_methods(["GET"])
def permissions_overview(request: HttpRequest) -> HttpResponse:
    auth_response = _ensure_authenticated(request)
    if auth_response:
        return auth_response

    user = getattr(request, "user", None)
    dev_open = getattr(settings, "PLATFORM_DEV_OPEN", False)
    org_ids = accessible_organization_ids(user)

    registry = {
        artifact_type: {
            field: {
                "default_actions": list(meta.default_actions or ()),
                "description": meta.description,
            }
            for field, meta in fields.items()
        }
        for artifact_type, fields in ARTIFACT_FIELD_REGISTRY.items()
    }

    preset_qs = (
        PermissionPreset.objects.select_related("organization")
        .prefetch_related("capabilities")
        .order_by("name")
    )
    role_qs = Role.objects.select_related("organization").prefetch_related("presets").order_by("name")

    if not (dev_open and (not user or not getattr(user, "is_authenticated", False))):
        if org_ids:
            preset_qs = preset_qs.filter(
                models.Q(organization__isnull=True) | models.Q(organization_id__in=org_ids)
            )
            role_qs = role_qs.filter(
                models.Q(organization__isnull=True) | models.Q(organization_id__in=org_ids)
            )
        else:
            preset_qs = preset_qs.filter(organization__isnull=True)
            role_qs = role_qs.filter(organization__isnull=True)

    presets = []
    for preset in preset_qs:
        caps = sorted(pc.capability for pc in preset.capabilities.all())
        presets.append(
            {
                "uuid": str(preset.uuid) if preset.uuid else None,
                "name": preset.name,
                "description": preset.description,
                "system": preset.system,
                "organization": preset.organization_id,
                "organization_name": preset.organization.name if preset.organization else None,
                "capabilities": caps,
                "field_policies": [],
            }
        )

    roles = []
    for role in role_qs:
        caps = role_capabilities(role.name, organization_id=role.organization_id)
        roles.append(
            {
                "uuid": str(role.uuid) if role.uuid else None,
                "name": role.name,
                "system": role.system,
                "organization": role.organization_id,
                "organization_name": role.organization.name if role.organization else None,
                "presets": [p.name for p in role.presets.all()],
                "capabilities": sorted(caps),
            }
        )

    context = {"registry": registry, "presets": presets, "roles": roles}
    return render(request, "platform_ui/permissions/index.html", context)


def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("ui-index")


@require_http_methods(["POST"])
def select_organization(request: HttpRequest) -> HttpResponse:
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return redirect("ui-index")

    org_id = (request.POST.get("organization_id") or "").strip()
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or reverse("ui-index")

    if not org_id:
        set_active_admin_org_id(request, None)
        return HttpResponseRedirect(next_url)

    accessible = user_accessible_organizations(user).values_list("id", flat=True)
    if org_id in accessible or getattr(user, "is_superuser", False):
        set_active_admin_org_id(request, org_id)

    return HttpResponseRedirect(next_url)

@csrf_exempt
@require_http_methods(["POST"])
def ui_log(request: HttpRequest) -> HttpResponse:
    try:
        body = request.body.decode("utf-8") if request.body else "{}"
        payload = json.loads(body)
    except Exception:
        payload = {"raw": request.body.decode("utf-8", errors="ignore") if request.body else ""}

    log.error(
        "client_ui_error",
        extra={
            "user_id": str(getattr(getattr(request, "user", None), "id", "")) or None,
            "path": request.path,
            "payload": payload,
            "user_agent": request.META.get("HTTP_USER_AGENT"),
            "referer": request.META.get("HTTP_REFERER"),
        },
    )
    return HttpResponse(status=204)

from .jobs import (
    case_job_transcript,
    case_job_logs_modal,
    jobs,
    job_detail_panel,
    case_job_detail_panel,
    case_job_title_form,
    case_job_update_title,
    case_job_create_artifact,
    case_job_row,
    create_job,
)

from .cases import (
    case_detail,
    case_analysis_module,
    case_update_title,
    case_details_update,
    case_tool_panel,
    case_assign_reviewer,
    case_assign_client,
)
