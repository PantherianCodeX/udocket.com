from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from django.core.exceptions import PermissionDenied
import logging

from django.conf import settings
from django.db import models
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from apps.platform.cases.models import Case, CaseMembership
from apps.platform.accounts.models import OrganizationMembership, User
from apps.platform.accounts.utils import (
    resolve_request_organization,
    set_active_admin_org_id,
    user_accessible_organizations,
)
from apps.platform.jobs.models import Job
from apps.platform.operations.tasks import transcribe_job
from apps.platform.operations.storage import ensure_case_dirs
from apps.platform.operations.utils import append_job_log
from apps.platform.authorization.models import PermissionPreset, Role
from apps.platform.authorization.capabilities import role_capabilities, has_capability
from apps.platform.artifacts.registry import ARTIFACT_FIELD_REGISTRY
from apps.platform.artifacts.models import CaseArtifact
from django.contrib.auth import logout
from apps.platform.tenancy import accessible_organization_ids, scope_jobs
from apps.platform.jobs.serializers import JobTelemetrySerializer
from apps.platform.jobs.telemetry import summarize_jobs

log = logging.getLogger("apps.platform.ui")


STATUS_CLASS_MAP = {
    "Approved": "border-emerald-400/40 bg-emerald-500/10 text-emerald-200",
    "Created": "border-white/20 bg-white/5 text-slate-200",
    "Converting": "border-primary-400/40 bg-primary-500/10 text-primary-200",
    "Running": "border-primary-400/40 bg-primary-500/10 text-primary-200",
    "Uploading": "border-primary-400/40 bg-primary-500/10 text-primary-200",
    "Rejected": "border-rose-400/40 bg-rose-500/10 text-rose-200",
    "Cancelling": "border-slate-400/40 bg-slate-500/20 text-slate-200",
    "Ready": "border-emerald-400/40 bg-emerald-500/10 text-emerald-200",
    "Not Started": "border-white/20 bg-white/5 text-slate-200",
    "No Transcript": "border-amber-400/40 bg-amber-500/10 text-amber-100",
}


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


def _status_class(status: str) -> str:
    return STATUS_CLASS_MAP.get(status, "border-white/20 bg-white/5 text-slate-200")


def _user_label(user: User) -> str:
    return (
        user.display_name
        or user.get_full_name()
        or user.email
        or user.username
        or str(user.pk)
    )


def _job_most_recent_timestamp(job: Job) -> datetime:
    return job.finished_at or job.started_at or job.created_at


def _agent_key(telem: Optional[Dict[str, Any]], job: Optional[Job] = None) -> str:
    if not telem:
        telem = {}
    agent = telem.get("agent") or {}
    raw = agent.get("type") or agent.get("name") or telem.get("agent_label") or ""
    if not raw and job is not None:
        raw = job.mode or ""
    normalized = str(raw).strip().lower()
    normalized = normalized.replace("agent", "").replace("analysis", "")
    normalized = normalized.replace(" ", "_")
    return normalized


def _latest_jobs_by_agent(jobs: List[Job], telemetry_map: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    latest: Dict[str, Dict[str, Any]] = {}
    for job in jobs:
        key = str(job.id)
        telem = telemetry_map.get(key) or {}
        agent_key = _agent_key(telem, job)
        if not agent_key:
            agent_key = job.mode.lower() if job.mode else "unknown"
        existing = latest.get(agent_key)
        if not existing:
            latest[agent_key] = {"job": job, "telemetry": telem}
            continue
        current_ts = _job_most_recent_timestamp(existing["job"])
        new_ts = _job_most_recent_timestamp(job)
        if new_ts and new_ts > current_ts:
            latest[agent_key] = {"job": job, "telemetry": telem}
    return latest


def _select_agent(latest: Dict[str, Dict[str, Any]], keywords: tuple[str, ...]) -> Optional[Dict[str, Any]]:
    for key, payload in latest.items():
        if any(word in key for word in keywords):
            return payload
    return None


def _map_job_status(job: Job) -> str:
    status = str(job.status or "").upper()
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


def _friendly_job_title(
    job: Job,
    telemetry: Optional[Dict[str, Any]] = None,
    artifact: Optional[CaseArtifact] = None,
) -> str:
    telem = telemetry or {}
    meta = telem.get("metadata") or {}
    if isinstance(meta, dict):
        title = meta.get("job_title")
        if title:
            return str(title)
    artifacts = telem.get("artifacts") or []
    if artifacts:
        candidate = artifacts[0]
        if isinstance(candidate, dict):
            title = candidate.get("title")
            if title:
                return title
    if artifact and getattr(artifact, "title", None):
        return artifact.title
    description = getattr(job, "description", None)
    return description or str(job.id)


def _latest_successful_transcription_job(jobs: List[Job]) -> Optional[Job]:
    ordered = sorted(
        jobs,
        key=lambda j: (j.finished_at or j.started_at or j.created_at or datetime.min),
        reverse=True,
    )
    for job in ordered:
        if job.status == Job.Status.SUCCEEDED and job.transcript_path:
            return job
    return None


def _artifact_payload(artifact: CaseArtifact) -> Dict[str, Any]:
    metadata = artifact.metadata or {}
    path_obj = Path(artifact.path) if artifact.path else None
    filename = path_obj.name if path_obj else (artifact.path or "")
    source = metadata.get("source_transcript") or metadata.get("source")
    if source:
        try:
            source = Path(source).name
        except Exception:
            source = str(source)
    try:
        download_url = reverse("artifact-download", kwargs={"pk": artifact.pk})
    except Exception:
        download_url = ""
    return {
        "id": artifact.pk,
        "title": artifact.title or filename,
        "created_at": artifact.created_at,
        "download_url": download_url,
        "job_id": artifact.job_id,
        "filename": filename,
        "metadata": metadata,
        "source": source,
    }


def _analysis_modules_context(
    request: HttpRequest,
    case: Case,
    jobs: List[Job],
    telemetry_map: Dict[str, Dict[str, Any]],
    transcript_artifacts: Optional[Dict[str, CaseArtifact]] = None,
) -> List[Dict[str, Any]]:
    user = getattr(request, "user", None)
    artifacts_qs = (
        CaseArtifact.objects.for_user(user)
        .filter(case_id=str(case.id), type__in=["SUMMARY", "TIMELINE"])
        .order_by("-created_at")
    )

    summary_artifacts: List[Dict[str, Any]] = []
    timeline_artifacts: List[Dict[str, Any]] = []
    for artifact in artifacts_qs:
        payload = _artifact_payload(artifact)
        if artifact.type == "SUMMARY":
            summary_artifacts.append(payload)
        elif artifact.type == "TIMELINE":
            timeline_artifacts.append(payload)

    latest_transcription = _latest_successful_transcription_job(jobs)
    target_job: Optional[Dict[str, Any]] = None
    if latest_transcription:
        target_job = {
            "id": str(latest_transcription.id),
            "title": _friendly_job_title(
                latest_transcription,
                telemetry_map.get(str(latest_transcription.id)),
                (transcript_artifacts or {}).get(str(latest_transcription.id)),
            ),
            "status": latest_transcription.status,
            "finished_at": latest_transcription.finished_at,
        }

    def build_module(
        *,
        key: str,
        label: str,
        description: str,
        artifacts: List[Dict[str, Any]],
        empty_message: str,
        action_label: str,
        success_label: str,
    ) -> Dict[str, Any]:
        latest = artifacts[0] if artifacts else None
        history = artifacts[1:5]
        if not target_job:
            status = "No Transcript"
            header_hint = "Upload and run a transcription to enable this automation."
            action_disabled = True
            disabled_reason = "Requires a completed transcript."
        elif latest:
            status = "Ready"
            header_hint = "Latest run"
            action_disabled = False
            disabled_reason = None
        else:
            status = "Not Started"
            header_hint = "No runs yet"
            action_disabled = False
            disabled_reason = None

        return {
            "key": key,
            "label": label,
            "description": description,
            "panel_id": f"module-{key}",
            "status": status,
            "status_class": _status_class(status),
            "header_hint": header_hint,
            "header_hint_time": latest["created_at"] if latest else None,
            "latest": latest,
            "history": history,
            "empty_message": empty_message,
            "target_job": target_job,
            "action": {
                "job_id": target_job["id"] if target_job else None,
                "label": action_label,
                "loading_label": "Queuing…",
                "success_label": success_label,
                "disabled": action_disabled,
                "disabled_reason": disabled_reason,
            },
        }

    return [
        build_module(
            key="summary",
            label="Summarization",
            description="Generate layered summaries of transcripts with AI assistance.",
            artifacts=summary_artifacts,
            empty_message="No summaries yet. Generate one from the latest transcript.",
            action_label="Generate summary",
            success_label="Summary queued",
        ),
        build_module(
            key="timeline",
            label="Timeline",
            description="Build an event timeline anchored to transcript timestamps.",
            artifacts=timeline_artifacts,
            empty_message="No timeline has been generated yet.",
            action_label="Generate timeline",
            success_label="Timeline queued",
        ),
    ]


def _build_case_progress(case: Case, jobs: List[Job], telemetry_map: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    latest = _latest_jobs_by_agent(jobs, telemetry_map)
    items: List[Dict[str, Any]] = []

    setup_status = "Approved" if case.reviewer_id and case.client_user_id else "Created"
    setup_detail_parts: List[str] = []
    if case.reviewer:
        setup_detail_parts.append(f"Reviewer: {case.reviewer.get_full_name() or case.reviewer.display_name or case.reviewer.username}")
    if case.client_user:
        setup_detail_parts.append(f"Client: {case.client_user.get_full_name() or case.client_user.display_name or case.client_user.username}")
    if not setup_detail_parts:
        setup_detail_parts.append("Assign reviewer and client")
    items.append(
        {
            "key": "case_setup",
            "label": "Case Setup",
            "status": setup_status,
            "status_class": _status_class(setup_status),
            "detail": " · ".join(setup_detail_parts),
            "updated": case.updated_at,
            "job": None,
            "telemetry": None,
        }
    )

    mappings = [
        ("transcription", "Transcription", ("transcription", "speech", "audio")),
        ("summary", "Summary", ("summary",)),
        ("timeline", "Timeline", ("timeline", "events")),
    ]

    for key, label, keywords in mappings:
        payload = _select_agent(latest, keywords)
        if payload:
            job = payload.get("job")
            telem = payload.get("telemetry")
            status = _map_job_status(job)
            if key == "transcription":
                review_state = getattr(job, "review_status", None)
                if review_state == Job.ReviewStatus.APPROVED:
                    status = "Approved"
                elif review_state == Job.ReviewStatus.REJECTED:
                    status = "Rejected"
            items.append(
                {
                    "key": key,
                    "label": label,
                    "status": status,
                    "status_class": _status_class(status),
                    "job": job,
                    "telemetry": telem,
                    "updated": _job_most_recent_timestamp(job),
                }
            )
        else:
            items.append(
                {
                    "key": key,
                    "label": label,
                    "status": "Created",
                    "status_class": _status_class("Created"),
                    "job": None,
                    "telemetry": None,
                    "updated": None,
                }
            )

    return items


def _case_assignment_lists(case: Case) -> Dict[str, List[Dict[str, Any]]]:
    memberships = case.memberships.select_related("user").all()
    reviewers = [m.user for m in memberships if m.role == CaseMembership.Role.REVIEWER]
    clients = [m.user for m in memberships if m.role == CaseMembership.Role.CLIENT]

    def _package(users: List[User]) -> List[Dict[str, Any]]:
        output: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for u in users:
            if not u:
                continue
            key = str(u.pk)
            if key in seen:
                continue
            seen.add(key)
            output.append({"user": u, "id": key, "label": _user_label(u)})
        return output

    return {
        "reviewer_candidates": _package(reviewers),
        "client_candidates": _package(clients),
    }


def _case_progress_context(case: Case, jobs: List[Job], telemetry_map: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    assignments = _case_assignment_lists(case)
    progress_items = _build_case_progress(case, jobs, telemetry_map)
    transcription_item = next((item for item in progress_items if item.get("key") == "transcription"), None)
    return {
        "progress_items": progress_items,
        "reviewer_candidates": assignments["reviewer_candidates"],
        "client_candidates": assignments["client_candidates"],
        "current_reviewer_label": _user_label(case.reviewer) if case.reviewer else None,
        "current_client_label": _user_label(case.client_user) if case.client_user else None,
        "transcription_review_status": transcription_item.get("status") if transcription_item else None,
    }


def _job_detail_context(
    request: HttpRequest,
    job: Job,
    *,
    telemetry: Optional[Dict[str, Any]] = None,
    title_error: Optional[str] = None,
    title_edit: bool = False,
) -> Dict[str, Any]:
    telemetry = telemetry or JobTelemetrySerializer(job, context={"request": request, "ui_mode": True}).data
    artifacts = telemetry.get("artifacts") or []
    artifact = artifacts[0] if artifacts else None
    db_artifact = (
        CaseArtifact.objects.filter(case_id=str(job.case_id), job_id=str(job.id), type="TRANSCRIPT")
        .order_by("-created_at")
        .first()
    )
    job_title = _friendly_job_title(job, telemetry, db_artifact)
    metadata_items = _format_metadata(telemetry.get("metadata"))
    azure_cancel_status = telemetry.get("metadata", {}).get("azure_cancel_status") if isinstance(telemetry.get("metadata"), dict) else None
    azure_cancel_body = telemetry.get("metadata", {}).get("azure_cancel_body") if isinstance(telemetry.get("metadata"), dict) else None

    audio_meta = telemetry.get("audio") or {}
    audio_mime = str(audio_meta.get("mime") or "").lower()
    audio_names = [
        str(audio_meta.get("path") or ""),
        str(audio_meta.get("original_name") or ""),
    ]
    is_wav_input = audio_mime in {"audio/wav", "audio/x-wav"}
    if not is_wav_input:
        for name in audio_names:
            if name.lower().endswith(".wav"):
                is_wav_input = True
                break
    telemetry_meta = telemetry.get("metadata") or {}
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
            return render(request, "ui/index.html", context)

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
    return render(request, "ui/index.html", context)


@require_http_methods(["GET", "POST"])
def case_detail(request: HttpRequest, case_id: str) -> HttpResponse:
    auth_response = _ensure_authenticated(request)
    if auth_response:
        return auth_response

    try:
        active_org = resolve_request_organization(request, required=True)
    except PermissionDenied:
        return redirect("ui-index")

    cases_qs = Case.objects.select_related("organization")
    case = cases_qs.for_user(getattr(request, "user", None)).filter(pk=case_id).first()
    if not case or case.organization_id != getattr(active_org, "id", None):
        raise Http404

    if request.method == "POST":
        # Legacy non-HTMX POST fallback; delegate to create_job then redirect
        response = create_job(request, case_id)
        # If HTMX, the handler returned a row; for plain POST redirect back
        if request.headers.get("HX-Request"):
            return response
        return redirect("ui-case-detail", case_id=case_id)

    jobs_qs = (
        Job.objects.select_related("case", "case__organization", "reviewed_by")
        .filter(case=case)
        .order_by("-created_at")
    )
    jobs_scoped = scope_jobs(jobs_qs, getattr(request, "user", None))
    jobs_list = list(jobs_scoped)
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
    last_update = job_summary.get("last_update")
    job_summary["last_update"] = last_update.isoformat() if last_update else None
    telemetry = JobTelemetrySerializer(
        jobs_list,
        many=True,
        context={"request": request, "ui_mode": True},
    ).data
    telemetry_map = {item.get("id"): item for item in telemetry}
    job_insights = []
    job_rows = []
    for job in jobs_list:
        key = str(job.id)
        data = telemetry_map.get(key)
        if data:
            job_insights.append(data)
        display_title = _friendly_job_title(job, data, transcript_artifacts.get(key))
        job_rows.append({"job": job, "telemetry": data, "title": display_title})
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
    progress_ctx = _case_progress_context(case, jobs_list, telemetry_map)
    analysis_modules = _analysis_modules_context(
        request, case, jobs_list, telemetry_map, transcript_artifacts
    )

    user_can_review = False
    dev_open = getattr(settings, "PLATFORM_DEV_OPEN", False)
    if dev_open:
        user_can_review = True
    else:
        user_obj = getattr(request, "user", None)
        if user_obj and getattr(user_obj, "is_authenticated", False):
            if case.reviewer_id and str(user_obj.id) == str(case.reviewer_id):
                user_can_review = True
            elif has_capability(user_obj, str(case.id), "case.update"):
                user_can_review = True
    context = {
        "case": case,
        "jobs": jobs_list,
        "job_summary": job_summary,
        "job_telemetry": telemetry_map,
        "job_insights": job_insights,
        "job_rows": job_rows,
        "latest_job": latest_job,
        "latest_job_telemetry": latest_job_telemetry,
        "latest_activity_ts": latest_activity_ts,
        **progress_ctx,
        "user_can_review": user_can_review,
        "analysis_modules": analysis_modules,
    }
    return render(request, "ui/case_detail.html", context)


@require_http_methods(["GET"])
def case_analysis_module(request: HttpRequest, case_id: str, agent: str) -> HttpResponse:
    auth_response = _ensure_authenticated(request)
    if auth_response:
        return auth_response

    case, _ = _get_case_and_org(request, case_id)

    jobs_qs = (
        Job.objects.select_related("case", "case__organization", "reviewed_by")
        .filter(case=case)
        .order_by("-created_at")
    )
    jobs_scoped = scope_jobs(jobs_qs, getattr(request, "user", None))
    jobs_list = list(jobs_scoped)
    telemetry = JobTelemetrySerializer(
        jobs_list,
        many=True,
        context={"request": request, "ui_mode": True},
    ).data
    telemetry_map = {item.get("id"): item for item in telemetry}

    modules = _analysis_modules_context(request, case, jobs_list, telemetry_map)
    module = next((item for item in modules if item.get("key") == agent), None)
    if not module:
        raise Http404

    return render(request, "ui/_analysis_module.html", {"module": module, "case": case})


@require_http_methods(["POST"])
def case_update_title(request: HttpRequest, case_id: str) -> HttpResponse:
    auth_response = _ensure_authenticated(request)
    if auth_response:
        return auth_response

    case, _ = _get_case_and_org(request, case_id)
    new_title = (request.POST.get("title") or "").strip()
    if not new_title:
        new_title = case.title or case.id
    if new_title != case.title:
        case.title = new_title
        case.save(update_fields=["title"])
    return render(request, "ui/_case_title.html", {"case": case})


@require_http_methods(["POST"])
def case_assign_reviewer(request: HttpRequest, case_id: str) -> HttpResponse:
    auth_response = _ensure_authenticated(request)
    if auth_response:
        return auth_response

    case, _ = _get_case_and_org(request, case_id)

    dev_open = getattr(settings, "PLATFORM_DEV_OPEN", False)
    user = getattr(request, "user", None)
    if not dev_open:
        if not user or not getattr(user, "is_authenticated", False) or not has_capability(user, str(case.id), "case.update"):
            return HttpResponse("Forbidden", status=403)

    reviewer_id = (request.POST.get("reviewer_id") or "").strip()
    if reviewer_id:
        try:
            reviewer = User.objects.get(pk=reviewer_id)
        except User.DoesNotExist:
            return HttpResponse("Reviewer not found", status=404)
        OrganizationMembership.objects.get_or_create(
            organization=case.organization,
            user=reviewer,
            defaults={"role": OrganizationMembership.Role.MEMBER},
        )
        membership, created = CaseMembership.objects.get_or_create(
            case=case,
            user=reviewer,
            defaults={"role": CaseMembership.Role.REVIEWER},
        )
        if not created and membership.role != CaseMembership.Role.REVIEWER:
            membership.role = CaseMembership.Role.REVIEWER
            membership.save(update_fields=["role"])
        case.reviewer = reviewer
        case.save(update_fields=["reviewer", "updated_at"])
    else:
        if case.reviewer_id is not None:
            case.reviewer = None
            case.save(update_fields=["reviewer", "updated_at"])

    jobs_qs = (
        Job.objects.select_related("case", "case__organization", "reviewed_by")
        .filter(case=case)
        .order_by("-created_at")
    )
    jobs_list = list(scope_jobs(jobs_qs, getattr(request, "user", None)))
    telemetry = JobTelemetrySerializer(
        jobs_list,
        many=True,
        context={"request": request, "ui_mode": True},
    ).data
    telemetry_map = {item.get("id"): item for item in telemetry}
    context = {"case": case, **_case_progress_context(case, jobs_list, telemetry_map)}
    return render(request, "ui/_case_progress.html", context)


@require_http_methods(["POST"])
def case_assign_client(request: HttpRequest, case_id: str) -> HttpResponse:
    auth_response = _ensure_authenticated(request)
    if auth_response:
        return auth_response

    case, _ = _get_case_and_org(request, case_id)

    dev_open = getattr(settings, "PLATFORM_DEV_OPEN", False)
    user = getattr(request, "user", None)
    if not dev_open:
        if not user or not getattr(user, "is_authenticated", False) or not has_capability(user, str(case.id), "case.update"):
            return HttpResponse("Forbidden", status=403)

    client_id = (request.POST.get("client_id") or "").strip()
    email = (request.POST.get("client_email") or "").strip()
    name = (request.POST.get("client_name") or "").strip()

    client_user: Optional[User] = None
    if client_id:
        try:
            client_user = User.objects.get(pk=client_id)
        except User.DoesNotExist:
            return HttpResponse("Client not found", status=404)
    else:
        if not email:
            return HttpResponse("Client email is required", status=400)
        client_user = User.objects.filter(email__iexact=email).first()
        if client_user is None:
            username = email or f"client-{uuid.uuid4().hex[:10]}"
            base_username = username
            idx = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}-{idx}"[:150]
                idx += 1
            client_user = User.objects.create_user(username=username, email=email, password=None)
            if name:
                client_user.first_name = name.split(" ")[0]
                if " " in name.strip():
                    client_user.last_name = name.strip().split(" ", 1)[1]
                client_user.display_name = name
                client_user.save(update_fields=["first_name", "last_name", "display_name"])
        elif name:
            if not client_user.display_name:
                client_user.display_name = name
                client_user.save(update_fields=["display_name"])

    assert client_user is not None  # for mypy-like reasoning

    OrganizationMembership.objects.get_or_create(
        organization=case.organization,
        user=client_user,
        defaults={"role": OrganizationMembership.Role.MEMBER},
    )
    membership, created = CaseMembership.objects.get_or_create(
        case=case,
        user=client_user,
        defaults={"role": CaseMembership.Role.CLIENT},
    )
    if not created and membership.role != CaseMembership.Role.CLIENT:
        membership.role = CaseMembership.Role.CLIENT
        membership.save(update_fields=["role"])

    case.client_user = client_user
    if name and not case.client_name:
        case.client_name = name
        case.save(update_fields=["client_user", "client_name", "updated_at"])
    else:
        case.save(update_fields=["client_user", "updated_at"])

    jobs_qs = (
        Job.objects.select_related("case", "case__organization", "reviewed_by")
        .filter(case=case)
        .order_by("-created_at")
    )
    jobs_list = list(scope_jobs(jobs_qs, getattr(request, "user", None)))
    telemetry = JobTelemetrySerializer(
        jobs_list,
        many=True,
        context={"request": request, "ui_mode": True},
    ).data
    telemetry_map = {item.get("id"): item for item in telemetry}
    context = {"case": case, **_case_progress_context(case, jobs_list, telemetry_map)}
    return render(request, "ui/_case_progress.html", context)


def jobs(request: HttpRequest) -> HttpResponse:
    auth_response = _ensure_authenticated(request)
    if auth_response:
        return auth_response

    try:
        organization = resolve_request_organization(request, required=True)
    except PermissionDenied:
        raise Http404
    jobs_qs = Job.objects.select_related("case", "case__organization")
    scoped = scope_jobs(jobs_qs, getattr(request, "user", None))
    scoped = scoped.filter(organization=organization)
    all_jobs = list(scoped[:200])
    return render(request, "ui/jobs.html", {"jobs": all_jobs, "active_org": organization})


@require_http_methods(["GET"])
def job_detail_panel(request: HttpRequest, job_id: str) -> HttpResponse:
    try:
        auth_response = _ensure_authenticated(request)
        if auth_response:
            return auth_response

        jobs_qs = Job.objects.select_related("case", "case__organization", "reviewed_by").filter(pk=job_id)
        job = scope_jobs(jobs_qs, getattr(request, "user", None)).first()
        if not job:
            raise Http404

        # Support forcing the title editor open via query param for HTMX swaps
        title_edit = str(request.GET.get("title_edit") or "").lower() in {"1", "true", "yes", "on"}
        context = _job_detail_context(request, job, title_edit=title_edit)
        return render(request, "ui/_job_detail.html", context)
    except Http404:
        raise
    except Exception as exc:  # noqa: BLE001
        log.exception("job_detail_panel error", extra={"job_id": job_id})
        return HttpResponse(
            '<div class="space-y-2 text-xs text-rose-200">'
            "<p>Unable to load job detail.</p>"
            f"<p class=\"font-mono text-[10px] text-rose-300\">{exc}</p>"
            "</div>",
            status=500,
        )


@require_http_methods(["GET"])
def case_job_detail_panel(request: HttpRequest, case_id: str, job_id: str) -> HttpResponse:
    try:
        auth_response = _ensure_authenticated(request)
        if auth_response:
            return auth_response

        case, _ = _get_case_and_org(request, case_id)
        job = (
            Job.objects.select_related("case", "case__organization", "reviewed_by")
            .filter(case=case, pk=job_id)
            .first()
        )
        if not job:
            raise Http404

        # Support forcing the title editor open via query param for HTMX swaps
        title_edit = str(request.GET.get("title_edit") or "").lower() in {"1", "true", "yes", "on"}
        context = _job_detail_context(request, job, title_edit=title_edit)
        context["case"] = case
        return render(request, "ui/_job_detail.html", context)
    except Http404:
        raise
    except Exception as exc:  # noqa: BLE001
        log.exception(
            "case_job_detail_panel error", extra={"job_id": job_id, "case_id": case_id}
        )
        return HttpResponse(
            '<div class="space-y-2 text-xs text-rose-200">'
            "<p>Unable to load job detail.</p>"
            f"<p class=\"font-mono text-[10px] text-rose-300\">{exc}</p>"
            "</div>",
            status=500,
        )


@require_http_methods(["GET"])
def case_job_title_form(request: HttpRequest, case_id: str, job_id: str) -> HttpResponse:
    auth_response = _ensure_authenticated(request)
    if auth_response:
        return auth_response

    case, _ = _get_case_and_org(request, case_id)
    job = (
        Job.objects.select_related("case", "case__organization", "reviewed_by")
        .filter(case=case, pk=job_id)
        .first()
    )
    if not job:
        raise Http404

    edit_flag = str(request.GET.get("edit") or request.GET.get("title_edit") or "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    context = _job_detail_context(request, job, title_edit=edit_flag)
    context["case"] = case
    return render(request, "ui/_job_detail_title_form.html", context)


@require_http_methods(["POST"])
def case_job_update_title(request: HttpRequest, case_id: str, job_id: str) -> HttpResponse:
    auth_response = _ensure_authenticated(request)
    if auth_response:
        return auth_response

    case, _ = _get_case_and_org(request, case_id)
    job = (
        Job.objects.select_related("case", "case__organization", "reviewed_by")
        .filter(case=case, pk=job_id)
        .first()
    )
    if not job:
        raise Http404

    user = getattr(request, "user", None)
    dev_open = getattr(settings, "PLATFORM_DEV_OPEN", False)
    can_edit = False
    if dev_open:
        can_edit = True
    elif user and getattr(user, "is_authenticated", False):
        if case.reviewer_id and str(user.id) == str(case.reviewer_id):
            can_edit = True
        elif has_capability(user, str(case.id), "case.update"):
            can_edit = True
    if not can_edit:
        return HttpResponse("Forbidden", status=403)

    new_title = (request.POST.get("title") or "").strip()
    title_error: Optional[str] = None
    if not new_title:
        title_error = "Title cannot be empty."

    telemetry_payload = JobTelemetrySerializer(job, context={"request": request, "ui_mode": True}).data

    artifact = (
        CaseArtifact.objects.filter(case_id=str(case.id), job_id=str(job.id), type="TRANSCRIPT")
        .order_by("-created_at")
        .first()
    )

    def ensure_transcript_artifact() -> Optional[CaseArtifact]:
        nonlocal artifact
        if artifact:
            return artifact
        candidate_paths: list[str] = []
        transcript_payload = telemetry_payload.get("transcript") or {}
        path_from_telem = transcript_payload.get("path") if isinstance(transcript_payload, dict) else None
        if isinstance(job.transcript_path, str) and job.transcript_path:
            candidate_paths.append(job.transcript_path)
        if isinstance(path_from_telem, str) and path_from_telem:
            candidate_paths.append(path_from_telem)
        for path in candidate_paths:
            existing = (
                CaseArtifact.objects.filter(case_id=str(case.id), type="TRANSCRIPT", path=path)
                .order_by("-created_at")
                .first()
            )
            if existing:
                return existing
        for path in candidate_paths:
            if not path:
                continue
            try:
                created = CaseArtifact.objects.create(
                    case_id=str(case.id),
                    case_fk=case,
                    job_id=str(job.id),
                    type="TRANSCRIPT",
                    title=new_title,
                    path=path,
                    metadata={"created_via": "ui.job_title"},
                )
                return created
            except Exception:
                continue
        return None

    if not title_error:
        conflict_qs = CaseArtifact.objects.filter(case_id=str(case.id), type="TRANSCRIPT", title=new_title)
        if artifact:
            conflict_qs = conflict_qs.exclude(pk=artifact.pk)
        if conflict_qs.exists():
            title_error = "A transcript with that title already exists in this case."

    if not title_error:
        artifact = ensure_transcript_artifact()
        if not artifact:
            title_error = "Transcript not found for this job."

    if title_error:
        context = _job_detail_context(
            request,
            job,
            telemetry=telemetry_payload,
            title_error=title_error,
            title_edit=True,
        )
        context["case"] = case
        context["job_title"] = new_title or context.get("job_title")
        return render(request, "ui/_job_detail_title_form.html", context, status=400)

    artifact.title = new_title
    if isinstance(artifact.metadata, dict):
        metadata = dict(artifact.metadata)
    else:
        metadata = {}
    metadata.update({
        "transcript_title": new_title,
        "job_title": new_title,
        "title_updated_at": timezone.now().isoformat(),
    })
    if user and getattr(user, "is_authenticated", False):
        metadata["title_updated_by"] = str(getattr(user, "id", ""))
    artifact.metadata = metadata
    artifact.save(update_fields=["title", "metadata"])

    update_job_meta(
        str(case.id),
        case.organization_id,
        str(job.id),
        {"job_title": new_title, "transcript_title": new_title},
    )

    append_job_log(
        str(job.case_id),
        job.organization_id,
        str(job.id),
        f"Transcript title set to '{new_title}'",
    )

    context = _job_detail_context(request, job)
    context["case"] = case
    headers = {
        "HX-Trigger": json.dumps({"job-title-updated": {"job_id": str(job.id), "title": new_title}})
    }
    return render(request, "ui/_job_detail_title_form.html", context, headers=headers)


@require_http_methods(["GET"])
def case_job_row(request: HttpRequest, case_id: str, job_id: str) -> HttpResponse:
    auth_response = _ensure_authenticated(request)
    if auth_response:
        return auth_response

    case, _ = _get_case_and_org(request, case_id)
    job = (
        Job.objects.select_related("case", "case__organization")
        .filter(case=case, pk=job_id)
        .first()
    )
    if not job:
        raise Http404

    telemetry = JobTelemetrySerializer(job, context={"request": request, "ui_mode": True}).data
    title = _friendly_job_title(job, telemetry)
    return render(request, "ui/_job_row.html", {"j": job, "telem": telemetry, "title": title})


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
    return render(request, "ui/permissions.html", context)


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


@require_http_methods(["POST"])
def create_job(request: HttpRequest, case_id: str) -> HttpResponse:
    """Create a job and return a table row partial (HTMX) or JSON as needed."""
    auth_response = _ensure_authenticated(request)
    if auth_response:
        return auth_response

    try:
        active_org = resolve_request_organization(request, required=True)
    except PermissionDenied:
        return redirect("ui-index")

    cases_qs = Case.objects.select_related("organization")
    case = cases_qs.for_user(getattr(request, "user", None)).filter(pk=case_id).first()
    if not case or case.organization_id != getattr(active_org, "id", None):
        raise Http404

    mode = request.POST.get("mode") or Job.Mode.ON_DEMAND
    diarization = bool(request.POST.get("diarization"))
    language = request.POST.get("language") or "en-CA"
    up = request.FILES.get("audio")
    sas_url = (request.POST.get("audio_url") or "").strip()

    if diarization and mode != Job.Mode.BATCH:
        mode = Job.Mode.BATCH

    job_id = uuid.uuid4()
    case_dir = ensure_case_dirs(case_id, case.organization_id)
    audio_dir = case_dir / "audio"
    audio_input: str

    force_wav_conversion = str(request.POST.get("force_wav") or "").lower() in {"1", "true", "yes", "on"}

    if up:
        dest = audio_dir / f"{job_id}__{up.name}"
        with dest.open("wb") as f:
            for chunk in up.chunks():
                f.write(chunk)
        audio_input = str(dest)
    elif sas_url:
        audio_input = sas_url
        if mode != Job.Mode.BATCH:
            mode = Job.Mode.BATCH
    else:
        return HttpResponse("Upload a file or provide a SAS URL.", status=400)

    job = Job.objects.create(
        id=job_id,
        case=case,
        organization=case.organization,
        audio_input=audio_input,
        mode=mode,
        diarization=diarization,
        language=language,
    )

    log.info(
        "ui enqueue job",
        extra={
            "job_id": str(job.id),
            "case_id": case_id,
            "mode": mode,
            "force_wav_conversion": force_wav_conversion,
        },
    )
    transcribe_job.delay(
        case_id=str(case.id),
        job_id=str(job.id),
        audio_input=audio_input,
        mode=mode,
        diarization=diarization,
        language=language,
        force_wav_conversion=force_wav_conversion,
    )

    telemetry = JobTelemetrySerializer(job, context={"request": request, "ui_mode": True}).data
    response = render(request, "ui/_job_row.html", {"j": job, "telem": telemetry})
    if request.headers.get("HX-Request"):
        trigger = {
            "job-enqueued": {
                "job_id": str(job.id),
                "status": job.status,
                "force_wav": force_wav_conversion,
            }
        }
        response["HX-Trigger"] = json.dumps(trigger)
    return response


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
