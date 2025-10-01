from __future__ import annotations

# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportAttributeAccessIssue=false

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from django.conf import settings
from django.http import HttpRequest
from django.urls import reverse

from apps.platform.accounts.models import OrganizationMembership
from apps.platform.artifacts.models import CaseArtifact
from apps.platform.cases.models import Case, CaseMembership
from apps.platform.jobs.models import Job, JobNote
from apps.platform.jobs.notes import serialize_notes

from ..constants import CASE_JOB_TABLE_COLUMNS, DEFAULT_TABLE_FILTERS, GLOBAL_JOB_TABLE_COLUMNS
from ..common import as_dict
from ..presenters.alerts import build_case_team_alerts
from ..presenters.utils import render_notes_panel_html, status_class, user_label
from .analysis import enrich_summary_artifacts, enrich_timeline_artifacts
from .analysis_modules import analysis_modules_context, artifact_payload, latest_successful_transcription_job
from .analysis_llm import build_analysis_llm_context
from .case_fields import prepare_case_fields
from ..presenters.jobs import (
    friendly_job_title,
    job_most_recent_timestamp,
    jobs_by_agent,
    latest_jobs_by_agent,
    map_job_status,
    select_agent,
)
def case_owner_memberships(memberships: List[CaseMembership]) -> List[CaseMembership]:
    return [m for m in memberships if m.role == CaseMembership.Role.OWNER and m.user]


def case_owner_labels(memberships: List[CaseMembership]) -> List[str]:
    return [user_label(m.user) for m in case_owner_memberships(memberships) if m.user]


def case_owner_details(memberships: List[CaseMembership]) -> List[Dict[str, str]]:
    details: List[Dict[str, str]] = []
    for membership in case_owner_memberships(memberships):
        user = membership.user
        if not user:
            continue
        details.append(
            {
                "label": user_label(user),
                "username": getattr(user, "username", ""),
            }
        )
    return details


def case_assignment_lists(case: Case, memberships: Optional[List[CaseMembership]] = None) -> Dict[str, List[Dict[str, str]]]:
    memberships = memberships or list(case.memberships.select_related("user"))
    reviewers: List[Dict[str, str]] = []
    clients: List[Dict[str, str]] = []
    owners: List[Dict[str, str]] = []
    for membership in memberships:
        user = membership.user
        if not user:
            continue
        entry = {"id": str(user.id), "label": user_label(user)}
        if membership.role == CaseMembership.Role.REVIEWER:
            reviewers.append(entry)
        elif membership.role == CaseMembership.Role.CLIENT:
            clients.append(entry)
        elif membership.role == CaseMembership.Role.OWNER:
            owners.append(entry)
    return {
        "reviewer_candidates": reviewers,
        "client_candidates": clients,
        "owner_candidates": owners,
    }


def build_case_progress(
    case: Case,
    jobs: List[Job],
    telemetry_map: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    latest = latest_jobs_by_agent(jobs, telemetry_map)
    items: List[Dict[str, Any]] = []

    setup_status = "Approved" if case.reviewer_id and case.client_user_id else "Created"
    setup_detail_parts: List[str] = []
    if case.reviewer:
        setup_detail_parts.append(f"Reviewer: {user_label(case.reviewer)}")
    if case.client_user:
        setup_detail_parts.append(f"Client: {user_label(case.client_user)}")
    if not setup_detail_parts:
        setup_detail_parts.append("Assign reviewer and client")
    items.append(
        {
            "key": "case_setup",
            "label": "Case Setup",
            "status": setup_status,
            "status_class": status_class(setup_status),
            "detail": " · ".join(setup_detail_parts),
            "updated": case.updated_at,
            "job": None,
            "telemetry": None,
        }
    )

    mappings = [
        ("transcription", "Transcribe", ("transcription", "speech", "audio", "transcribe")),
        ("summary", "Summarize", ("summary", "summarize")),
        ("timeline", "Timeline", ("timeline", "events")),
        ("relationships", "Relationships", ("relationship", "graph", "relationships")),
    ]

    for key, label, keywords in mappings:
        payload = select_agent(latest, keywords)
        if payload:
            job = payload.get("job")
            telem = payload.get("telemetry")
            status = map_job_status(job)
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
                    "status_class": status_class(status),
                    "job": job,
                    "telemetry": telem,
                    "updated": job_most_recent_timestamp(job),
                }
            )
        else:
            items.append(
                {
                    "key": key,
                    "label": label,
                    "status": "Created",
                    "status_class": status_class("Created"),
                    "job": None,
                    "telemetry": None,
                    "updated": None,
                }
            )

    return items




def case_progress_context(
    case: Case,
    jobs: List[Job],
    telemetry_map: Dict[str, Dict[str, Any]],
    memberships: Optional[List[CaseMembership]] = None,
) -> Dict[str, Any]:
    assignments = case_assignment_lists(case, memberships)
    progress_items = build_case_progress(case, jobs, telemetry_map)
    transcription_item = next((item for item in progress_items if item.get("key") == "transcription"), None)
    return {
        "progress_items": progress_items,
        "reviewer_candidates": assignments["reviewer_candidates"],
        "client_candidates": assignments["client_candidates"],
        "current_reviewer_label": user_label(case.reviewer) if case.reviewer else None,
        "current_client_label": user_label(case.client_user) if case.client_user else None,
        "transcription_review_status": transcription_item.get("status") if transcription_item else None,
    }


def _organization_member_options(case: Case) -> List[Dict[str, Any]]:
    memberships = (
        OrganizationMembership.objects.select_related("user")
        .filter(organization=case.organization)
        .order_by("user__display_name", "user__first_name", "user__email")
    )
    options: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for membership in memberships:
        user = membership.user
        key = str(user.pk)
        if key in seen:
            continue
        seen.add(key)
        options.append({"id": key, "label": user_label(user)})
    return options


def collect_case_artifacts(
    request: HttpRequest,
    case: Case,
    *,
    exclude_audio: bool = True,
) -> List[Dict[str, Any]]:
    user = getattr(request, "user", None)
    qs = CaseArtifact.objects.for_user(user).filter(case_id=str(case.id))
    if exclude_audio:
        qs = qs.exclude(type__iexact="AUDIO")
    artifacts: List[Dict[str, Any]] = []
    for artifact in qs.order_by("-created_at"):
        payload = artifact_payload(artifact)
        payload["type"] = artifact.type
        artifacts.append(payload)
    return artifacts


def table_config(
    *,
    panel_key: str,
    title: str,
    pill: Optional[str],
    rows: List[Dict[str, Any]],
    columns: Sequence[Dict[str, Any]],
    column_ids: Sequence[str],
    filters: Sequence[Dict[str, Any]],
    empty_message: str,
    show_identifiers: bool,
    case_id: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "id": f"{panel_key}-jobs",
        "key": panel_key,
        "title": title,
        "pill": pill,
        "rows": rows,
        "columns": list(columns),
        "column_ids": list(column_ids),
        "filters": list(filters),
        "row_template": "platform_ui/components/jobs/job_row.html",
        "empty_message": empty_message,
        "show_identifiers": show_identifiers,
        "body_id": "jobs-body",
        "case_id": case_id,
        "allow_column_toggle": True,
    }


def status_payload(progress_lookup: Dict[str, Dict[str, Any]], key: str, default_status: str = "Created") -> Dict[str, Any]:
    item = progress_lookup.get(key)
    if not item:
        return {
            "label": default_status,
            "class": status_class(default_status),
            "updated": None,
            "detail": None,
        }
    return {
        "label": item.get("status") or default_status,
        "class": item.get("status_class") or status_class(default_status),
        "updated": item.get("updated"),
        "detail": item.get("detail"),
    }


def build_case_developer_cards(panels: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    order = ["case-details", "transcribe", "summary", "timeline"]
    cards: List[Dict[str, Any]] = []
    for key in order:
        panel = panels.get(key)
        if not panel:
            continue
        cards.append(
            {
                "key": key,
                "label": panel.get("label"),
                "status_label": panel.get("status_label"),
                "status_class": panel.get("status_class"),
                "status_summary": panel.get("progress_detail") or panel.get("status_label"),
                "updated_at": panel.get("updated_at"),
            }
        )
    return cards


def build_case_header_context(
    case: Case,
    *,
    panels: Dict[str, Dict[str, Any]],
    case_fields: List[Dict[str, Any]],
    memberships: List[CaseMembership],
    job_summary_last_update: Optional[datetime],
) -> Dict[str, Any]:
    owner_details = case_owner_details(memberships)
    owners = [item["label"] for item in owner_details]
    reviewer_detail = (
        {
            "label": user_label(case.reviewer),
            "username": getattr(case.reviewer, "username", ""),
        }
        if case.reviewer
        else None
    )
    client_label = user_label(case.client_user) if case.client_user else None

    activity_candidates: List[Tuple[Optional[datetime], Optional[str]]] = []
    for panel in panels.values():
        updated = panel.get("updated_at")
        label = panel.get("label")
        if isinstance(updated, datetime):
            activity_candidates.append((updated, label))
    if job_summary_last_update:
        activity_candidates.append((job_summary_last_update, None))
    if case.updated_at:
        activity_candidates.append((case.updated_at, None))

    activity_candidates = [item for item in activity_candidates if item[0]]
    activity_candidates.sort(
        key=lambda item: (False if item[0] else True, item[0] or datetime.min),
        reverse=True,
    )
    last_activity_ts = activity_candidates[0][0] if activity_candidates else None
    last_activity_label = activity_candidates[0][1] if activity_candidates else None

    next_hearing_field = next((field for field in case_fields if field["name"] == "court_date"), None)
    filing_deadline_field = next((field for field in case_fields if field["name"] == "filing_deadline"), None)

    return {
        "title": case.title,
        "client_name": case.client_name or "—",
        "owner_labels": owners,
        "owner_details": owner_details,
        "reviewer_detail": reviewer_detail,
        "reviewer_label": reviewer_detail["label"] if reviewer_detail else None,
        "client_label": client_label,
        "next_hearing": next_hearing_field,
        "filing_deadline": filing_deadline_field,
        "last_activity_ts": last_activity_ts,
        "last_activity_label": last_activity_label,
        "fields": case_fields,
    }


def build_tool_panels(
    case: Case,
    *,
    jobs: Sequence[Job],
    progress_items: List[Dict[str, Any]],
    job_rows: List[Dict[str, Any]],
    telemetry_map: Dict[str, Dict[str, Any]],
    transcript_artifacts: Dict[str, CaseArtifact],
    analysis_modules: List[Dict[str, Any]],
    artifacts: List[Dict[str, Any]],
    memberships: List[CaseMembership],
    latest_job: Optional[Job],
    latest_job_telemetry: Optional[Dict[str, Any]],
    job_summary: Dict[str, Any],
    all_job_rows: Optional[List[Dict[str, Any]]] = None,
    job_summary_last_dt: Optional[datetime] = None,
    user_can_review: bool = False,
    return_url: str = "",
) -> Dict[str, Dict[str, Any]]:
    progress_lookup = {item["key"]: item for item in progress_items}
    analysis_lookup = {module["key"]: module for module in analysis_modules}
    team_alerts = build_case_team_alerts(case, jobs)
    empty_notes = {
        "job_id": None,
        "entries": [],
        "updated_at": None,
        "updated_by": None,
        "user_can_add": False,
        "count": 0,
    }

    def _notes_panel(notes: Dict[str, Any]) -> str:
        return render_notes_panel_html(
            job_id=notes.get("job_id"),
            entries=notes.get("entries"),
            updated_at=notes.get("updated_at"),
            updated_by=notes.get("updated_by"),
            user_can_add=notes.get("user_can_add", False),
        )
    owner_labels = case_owner_labels(memberships)
    owner_ids = [str(m.user_id) for m in case_owner_memberships(memberships)]
    reviewer_label = user_label(case.reviewer) if case.reviewer else None
    client_label = user_label(case.client_user) if case.client_user else None
    case_fields = prepare_case_fields(case)
    org_options = _organization_member_options(case)

    all_rows_iterable = all_job_rows or job_rows

    transcript_sources: List[Dict[str, Any]] = []
    for row in all_rows_iterable:
        job = row.get("job")
        telem = row.get("telemetry") or {}
        if not job:
            continue
        job_id = str(getattr(job, "id", ""))
        if not job_id:
            continue
        agent = (telem.get("agent") or {})
        agent_type = str(agent.get("type") or "").lower()
        meta = telem.get("metadata") or {}
        job_kind = str(meta.get("job_kind") or "").lower()
        if not any(word in agent_type for word in ("transcription", "speech", "audio")) and not job_kind.startswith("audio"):
            continue
        transcript_payload = telem.get("transcript") or {}
        path = transcript_payload.get("path")
        artifact = transcript_artifacts.get(job_id)
        if artifact and artifact.path:
            path = artifact.path
        transcript_sources.append(
            {
                "job_id": job_id,
                "label": row.get("title") or job_id,
                "status": getattr(job, "status", ""),
                "review_status": getattr(job, "review_status", ""),
                "approved": getattr(job, "review_status", "") == Job.ReviewStatus.APPROVED,
                "path": path,
                "language": getattr(job, "language", None),
                "created_at": getattr(job, "finished_at", None) or getattr(job, "created_at", None),
            }
        )

    artifacts_by_type: Dict[str, List[Dict[str, Any]]] = {}
    for artifact in artifacts:
        artifacts_by_type.setdefault(str(artifact.get("type", "")).upper(), []).append(artifact)

    for bucket in ("SUMMARY", "TIMELINE", "TRANSCRIPT"):
        artifacts_by_type.setdefault(bucket, [])

    panels: Dict[str, Dict[str, Any]] = {}

    case_status = status_payload(progress_lookup, "case_setup")
    field_map = {field["name"]: field for field in case_fields}
    field_groups: List[Dict[str, Any]] = []

    def _group(label: str, keys: List[str]) -> None:
        items = [field_map[key] for key in keys if key in field_map]
        if items:
            field_groups.append({"title": label, "fields": items})

    _group("Case Overview", ["title", "client_name", "client_position", "opposing_party"])
    _group("Scheduling & Court", ["court_location", "court_level", "court_division", "court_case_number", "court_date", "filing_deadline"])
    _group("Client Notes", ["notes"])

    representation_choices = list(Case.Representation.choices)
    current_representation = case.representation or ""
    engagement_options = [
        {"value": "standard", "label": "Standard"},
        {"value": "legal_aid", "label": "Legal aid"},
        {"value": "pro_bono", "label": "Pro bono"},
    ]
    if case.legal_aid:
        current_engagement = "legal_aid"
    elif case.pro_bono:
        current_engagement = "pro_bono"
    else:
        current_engagement = "standard"

    owner_id = owner_ids[0] if owner_ids else ""

    case_notes = empty_notes.copy()
    case_notes["user_can_add"] = user_can_review
    panels["case-details"] = {
        "key": "case-details",
        "label": "Intake Form",
        "description": "Update assignments, key dates, and intake metadata for this case.",
        "status_label": case_status["label"],
        "status_class": case_status["class"],
        "updated_at": case_status.get("updated") or case.updated_at,
        "progress_detail": case_status.get("detail"),
        "notes": case_notes,
        "notes_panel_html": _notes_panel(case_notes),
        "team_alerts": team_alerts,
        "meta": [
            {"label": "Owners", "value": ", ".join(owner_labels) or "Unassigned"},
            {"label": "Reviewer", "value": reviewer_label or "Unassigned"},
            {"label": "Client", "value": client_label or "Unassigned"},
            {"label": "Case ID", "value": case.id},
        ],
        "body_template": "platform_ui/tools/case_details.html",
        "body_context": {
            "case": case,
            "fields": case_fields,
            "field_groups": field_groups,
            "owner_labels": owner_labels,
            "owner_options": org_options,
            "current_owner_id": owner_id,
            "reviewer_id": str(case.reviewer_id) if case.reviewer_id else "",
            "client_user_id": str(case.client_user_id) if case.client_user_id else "",
            "reviewer_options": org_options,
            "client_options": org_options,
            "contributor_options": org_options,
            "contributor_ids": [
                str(m.user_id)
                for m in memberships
                if getattr(m, "role", "") == CaseMembership.Role.CONTRIBUTOR
            ],
            "update_url": reverse("ui-case-details-update", kwargs={"case_id": case.id}),
            "job_summary": job_summary,
            "job_summary_last_dt": job_summary_last_dt,
            "representation_choices": representation_choices,
            "current_representation": current_representation,
            "engagement_options": engagement_options,
            "current_engagement": current_engagement,
        },
        "jobs": job_rows,
        "jobs_title": "All Jobs",
        "jobs_pill": "Live updates",
        "jobs_empty_message": "No jobs recorded yet.",
        "case_id": str(case.id),
        "jobs_columns": list(CASE_JOB_TABLE_COLUMNS),
        "jobs_column_ids": [col["id"] for col in CASE_JOB_TABLE_COLUMNS],
        "jobs_filters": DEFAULT_TABLE_FILTERS,
        "jobs_show_identifiers": True,
        "jobs_table": table_config(
            panel_key="case-details",
            title="All Jobs",
            pill="Live updates",
            rows=job_rows,
            columns=CASE_JOB_TABLE_COLUMNS,
            column_ids=[col["id"] for col in CASE_JOB_TABLE_COLUMNS],
            filters=DEFAULT_TABLE_FILTERS,
            empty_message="No jobs recorded yet.",
            show_identifiers=True,
            case_id=str(case.id),
        ),
    }

    transcription_status = status_payload(progress_lookup, "transcription", "Not Started")
    transcription_jobs = jobs_by_agent(job_rows, keywords=("transcription", "speech", "audio"), include_conversion=True)

    latest_job_title = None
    if latest_job:
        latest_job_title = friendly_job_title(
            latest_job,
            latest_job_telemetry,
            transcript_artifacts.get(str(latest_job.id)),
        )

    latest_downloads: List[Dict[str, Any]] = []
    if latest_job:
        job_id_str = str(latest_job.id)
        latest_downloads.append(
            {
                "label": "Download transcript",
                "href": f"/api/v1/jobs/{job_id_str}/download/",
                "download": True,
            }
        )
        latest_downloads.append(
            {
                "label": "Download audio",
                "href": f"/api/v1/jobs/{job_id_str}/download-audio/",
                "download": True,
            }
        )

    transcribe_notes = empty_notes.copy()
    transcribe_notes["user_can_add"] = user_can_review
    if latest_job:
        latest_job_id = str(latest_job.id)
        notes_qs = (
            JobNote.objects.filter(job_id=latest_job_id)
            .select_related("created_by")
            .order_by("-created_at")
        )
        notes_entries = serialize_notes(notes_qs)
        notes_updated_at = notes_entries[0]["created_at"] if notes_entries else None
        notes_updated_by = (
            notes_entries[0].get("created_by_label")
            or notes_entries[0].get("created_by")
            if notes_entries
            else None
        )
        transcribe_notes.update(
            {
                "job_id": latest_job_id,
                "entries": notes_entries,
                "updated_at": notes_updated_at,
                "updated_by": notes_updated_by,
                "count": len(notes_entries),
            }
        )

    panels["transcribe"] = {
        "key": "transcribe",
        "label": "Transcribe",
        "description": "Upload audio or provide a SAS URL to run Azure Speech in Canada-only regions.",
        "status_label": transcription_status["label"],
        "status_class": transcription_status["class"],
        "updated_at": transcription_status["updated"],
        "progress_detail": transcription_status.get("detail"),
        "notes": transcribe_notes,
        "notes_panel_html": _notes_panel(transcribe_notes),
        "team_alerts": team_alerts,
        "meta": [
            {
                "label": "Approved",
                "value": sum(
                    1
                    for item in transcription_jobs
                    if getattr(item.get("job"), "review_status", "") == Job.ReviewStatus.APPROVED
                ),
            },
            {
                "label": "Total Jobs",
                "value": len(transcription_jobs),
            },
        ],
        "body_template": "platform_ui/tools/transcribe.html",
        "body_context": {
            "case": case,
            "form_action": reverse("ui-job-create", kwargs={"case_id": case.id}),
            "diarization_default": True,
            "force_wav_default": False,
            "language_default": getattr(latest_job, "language", "en-CA") if latest_job else "en-CA",
            "latest_job": latest_job,
            "latest_job_telemetry": latest_job_telemetry,
            "latest_job_title": latest_job_title,
            "downloads": latest_downloads,
            "transcript_sources": transcript_sources,
            "approved_transcripts": [item for item in transcript_sources if item.get("approved")],
            "can_review": user_can_review,
        },
        "jobs": transcription_jobs,
        "jobs_title": "Transcription Jobs",
        "jobs_pill": "Live updates",
        "jobs_empty_message": "No transcription jobs yet.",
        "case_id": str(case.id),
        "jobs_columns": list(CASE_JOB_TABLE_COLUMNS),
        "jobs_column_ids": [col["id"] for col in CASE_JOB_TABLE_COLUMNS],
        "jobs_filters": DEFAULT_TABLE_FILTERS,
        "jobs_show_identifiers": True,
        "jobs_table": table_config(
            panel_key="transcribe",
            title="Transcription Jobs",
            pill="Live updates",
            rows=transcription_jobs,
            columns=CASE_JOB_TABLE_COLUMNS,
            column_ids=[col["id"] for col in CASE_JOB_TABLE_COLUMNS],
            filters=DEFAULT_TABLE_FILTERS,
            empty_message="No transcription jobs yet.",
            show_identifiers=True,
            case_id=str(case.id),
        ),
    }

    if not return_url:
        return_url = reverse("ui-case-detail", kwargs={"case_id": case.id})

    analysis_llm = build_analysis_llm_context(case, return_url=return_url)
    summary_llm = analysis_llm["summary"]
    timeline_llm = analysis_llm["timeline"]
    summary_status = status_payload(progress_lookup, "summary", "Not Started")
    summary_module = analysis_lookup.get("summary") or {}
    summary_latest = summary_module.get("latest") or {}
    summary_history = summary_module.get("history") or []
    summary_jobs = jobs_by_agent(
        all_rows_iterable,
        keywords=("summary", "summarization", "summarize"),
        exclude_keywords=("transcription", "audio", "speech"),
    )
    panels["summary"] = {
        "key": "summary",
        "label": "Summarize",
        "description": "Generate layered summaries from approved transcripts.",
        "status_label": summary_status["label"],
        "status_class": summary_status["class"],
        "updated_at": summary_status["updated"] or summary_latest.get("created_at"),
        "progress_detail": summary_status.get("detail"),
        "notes": summary_module.get("notes") or empty_notes.copy(),
        "notes_panel_html": summary_module.get("notes_panel_html"),
        "team_alerts": summary_module.get("team_alerts", team_alerts),
        "meta": [
            {"label": "Summaries", "value": len(summary_history) + (1 if summary_latest else 0)},
            {
                "label": "Approved transcripts",
                "value": sum(1 for src in transcript_sources if src.get("approved")),
            },
        ],
        "body_template": "platform_ui/tools/summary.html",
        "body_context": {
            "case": case,
            "module": summary_module,
            "transcripts": transcript_sources,
            "job_endpoint_template": "/api/v1/jobs/{job_id}/analyze/summary/",
            "summary_llm": summary_llm,
        },
        "jobs": summary_jobs,
        "jobs_title": "Summarize Jobs",
        "jobs_pill": "Automations",
        "jobs_empty_message": "No summarize jobs yet. Queue one above.",
        "case_id": str(case.id),
        "jobs_columns": list(GLOBAL_JOB_TABLE_COLUMNS),
        "jobs_column_ids": [col["id"] for col in GLOBAL_JOB_TABLE_COLUMNS],
        "jobs_filters": DEFAULT_TABLE_FILTERS,
        "jobs_show_identifiers": False,
        "jobs_table": table_config(
            panel_key="summary",
            title="Summarize Jobs",
            pill="Automations",
            rows=summary_jobs,
            columns=GLOBAL_JOB_TABLE_COLUMNS,
            column_ids=[col["id"] for col in GLOBAL_JOB_TABLE_COLUMNS],
            filters=DEFAULT_TABLE_FILTERS,
            empty_message="No summarize jobs yet. Queue one above.",
            show_identifiers=False,
            case_id=str(case.id),
        ),
    }

    timeline_status = status_payload(progress_lookup, "timeline", "Not Started")
    timeline_module = analysis_lookup.get("timeline") or {}
    timeline_latest = timeline_module.get("latest") or {}
    timeline_history = timeline_module.get("history") or []
    timeline_jobs = jobs_by_agent(all_rows_iterable, keywords=("timeline", "event"))
    panels["timeline"] = {
        "key": "timeline",
        "label": "Timeline",
        "description": "Produce an event timeline anchored to transcript timestamps and summaries.",
        "status_label": timeline_status["label"],
        "status_class": timeline_status["class"],
        "updated_at": timeline_status["updated"] or timeline_latest.get("created_at"),
        "progress_detail": timeline_status.get("detail"),
        "notes": timeline_module.get("notes") or empty_notes.copy(),
        "notes_panel_html": timeline_module.get("notes_panel_html"),
        "team_alerts": timeline_module.get("team_alerts", team_alerts),
        "meta": [
            {"label": "Timelines", "value": len(timeline_history) + (1 if timeline_latest else 0)},
            {"label": "Artifacts", "value": len(artifacts)},
        ],
        "body_template": "platform_ui/tools/timeline.html",
        "body_context": {
            "case": case,
            "module": timeline_module,
            "transcripts": transcript_sources,
            "artifact_options": artifacts_by_type,
            "job_endpoint_template": "/api/v1/jobs/{job_id}/analyze/timeline/",
            "timeline_llm": timeline_llm,
        },
        "jobs": timeline_jobs,
        "jobs_title": "Timeline Jobs",
        "jobs_pill": "Automations",
        "jobs_empty_message": "No timeline jobs yet. Generate a timeline above.",
        "case_id": str(case.id),
        "jobs_columns": list(GLOBAL_JOB_TABLE_COLUMNS),
        "jobs_column_ids": [col["id"] for col in GLOBAL_JOB_TABLE_COLUMNS],
        "jobs_filters": DEFAULT_TABLE_FILTERS,
        "jobs_show_identifiers": False,
        "jobs_table": table_config(
            panel_key="timeline",
            title="Timeline Jobs",
            pill="Automations",
            rows=timeline_jobs,
            columns=GLOBAL_JOB_TABLE_COLUMNS,
            column_ids=[col["id"] for col in GLOBAL_JOB_TABLE_COLUMNS],
            filters=DEFAULT_TABLE_FILTERS,
            empty_message="No timeline jobs yet. Generate a timeline above.",
            show_identifiers=False,
            case_id=str(case.id),
        ),
    }

    return panels
