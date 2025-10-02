"""Case tool panel presenter helpers."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from django.urls import reverse

from apps.platform.artifacts.models import CaseArtifact
from apps.platform.cases.models import Case, CaseMembership
from apps.platform.jobs.models import Job, JobNote
from apps.platform.jobs.notes import serialize_notes

from ..constants import CASE_JOB_TABLE_COLUMNS, DEFAULT_TABLE_FILTERS, GLOBAL_JOB_TABLE_COLUMNS
from ..presenters.alerts import build_case_team_alerts
from ..presenters.utils import render_notes_panel_html, status_class, user_label
from ..presenters.jobs import friendly_job_title, jobs_by_agent
from .analysis_llm import build_analysis_llm_context
from .case_fields import prepare_case_fields
from .case_memberships import case_owner_labels, case_owner_memberships
from .tool_registry import get_tool_definition


def table_config(
    *,
    panel_key: str,
    title: str,
    pill: str,
    rows: Sequence[Dict[str, Any]],
    columns: Sequence[Dict[str, Any]],
    column_ids: Sequence[str],
    filters: Sequence[Dict[str, Any]],
    empty_message: str,
    show_identifiers: bool,
    case_id: str,
    limit_value: Optional[int] = None,
    limit_options: Sequence[int] | None = None,
    total_count: Optional[int] = None,
    pagination: Optional[Dict[str, Any]] = None,
    param_prefix: Optional[str] = None,
    filter_param_names: Optional[Sequence[str]] = None,
    filters_active: int = 0,
    has_advanced_filters: bool = False,
) -> Dict[str, Any]:
    filter_lookup = {item["key"]: item for item in filters}
    filters_list = list(filters)
    pagination_payload = dict(pagination or {})
    columns_payload: List[Dict[str, Any]] = []
    for column in columns:
        column_payload = dict(column)
        filter_id = column_payload.get("filter_id")
        if filter_id and filter_id in filter_lookup:
            column_payload["filter"] = filter_lookup[filter_id]
        columns_payload.append(column_payload)
    default_total = total_count if total_count is not None else len(rows)
    default_page = int(pagination_payload.get("page") or 1)
    default_pages = int(pagination_payload.get("pages") or 1)
    default_page_size = int(pagination_payload.get("page_size") or (limit_value or len(rows) or 1))
    default_pages = max(default_pages, 1)
    default_page = max(min(default_page, default_pages), 1)
    pagination_payload.setdefault("total", default_total)
    pagination_payload.setdefault("pages", default_pages)
    pagination_payload.setdefault("page", default_page)
    pagination_payload.setdefault("page_size", default_page_size)
    pagination_payload.setdefault("start", pagination_payload.get("start", 0))
    pagination_payload.setdefault("end", pagination_payload.get("end", 0))
    pagination_payload.setdefault("has_previous", pagination_payload.get("has_previous", default_page > 1))
    pagination_payload.setdefault("has_next", pagination_payload.get("has_next", default_page < default_pages))
    pagination_payload.setdefault("previous_page", pagination_payload.get("previous_page", max(default_page - 1, 1)))
    pagination_payload.setdefault("next_page", pagination_payload.get("next_page", min(default_page + 1, default_pages)))
    pagination_payload.setdefault("display_count", pagination_payload.get("display_count", len(rows)))
    pagination_payload.setdefault("first_page", pagination_payload.get("first_page", 1))
    pagination_payload.setdefault("last_page", pagination_payload.get("last_page", default_pages))

    return {
        "id": f"{panel_key}-jobs",
        "key": panel_key,
        "title": title,
        "pill": pill,
        "rows": rows,
        "columns": columns_payload,
        "column_ids": list(column_ids),
        "filters": filters_list,
        "row_template": "platform_ui/components/jobs/job_row.html",
        "empty_message": empty_message,
        "show_identifiers": show_identifiers,
        "body_id": "jobs-body",
        "case_id": case_id,
        "allow_column_toggle": True,
        "limit_value": limit_value,
        "limit_options": list(limit_options) if limit_options else [],
        "total_count": total_count,
        "pagination": pagination_payload,
        "param_prefix": param_prefix or panel_key,
        "filter_param_names": list(filter_param_names) if filter_param_names else [],
        "filters_active": filters_active,
        "has_advanced_filters": has_advanced_filters,
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
    job_row_limit: int = 25,
    job_row_total: int = 0,
    job_limit_choices: Sequence[int] = (),
    job_filters: Optional[Sequence[Dict[str, Any]]] = None,
    job_pagination: Optional[Dict[str, Any]] = None,
    job_param_prefix: Optional[str] = None,
    job_param_names: Optional[Sequence[str]] = None,
    job_has_advanced_filters: bool = False,
    job_filters_active: int = 0,
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

    def _panel_from_definition(definition_key: str) -> Dict[str, Any]:
        definition = get_tool_definition(definition_key)
        panel: Dict[str, Any] = {
            "key": definition.key,
            "label": definition.label,
            "description": definition.description,
            "body_template": definition.body_template,
            "data_attributes": dict(definition.data_attributes),
        }
        if definition.llm_target:
            panel["llm_target"] = definition.llm_target
        if definition.job_endpoint_template:
            panel["job_endpoint_template"] = definition.job_endpoint_template
        if definition.alerts_key:
            panel["alerts_key"] = definition.alerts_key
        panel["notes_enabled"] = definition.notes_enabled
        return panel

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

    for bucket in ("SUMMARY", "TIMELINE", "TRANSCRIPT", "QUESTIONNAIRE"):
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

    questionnaire_artifacts = artifacts_by_type.get("QUESTIONNAIRE", [])

    case_panel = _panel_from_definition("intake")
    case_notes = empty_notes.copy()
    case_notes["user_can_add"] = user_can_review
    case_panel.update(
        {
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
                    str(membership.user_id)
                    for membership in memberships
                    if getattr(membership, "role", "") == CaseMembership.Role.CONTRIBUTOR
                ],
                "update_url": reverse("ui-case-details-update", kwargs={"case_id": case.id}),
                "job_summary": job_summary,
                "job_summary_last_dt": job_summary_last_dt,
                "representation_choices": representation_choices,
                "current_representation": current_representation,
                "engagement_options": engagement_options,
                "current_engagement": current_engagement,
                "questionnaire": {
                    "latest": questionnaire_artifacts[0] if questionnaire_artifacts else None,
                    "history": questionnaire_artifacts[1:5] if questionnaire_artifacts else [],
                    "manual_edit_url": "#",
                    "agent_edit_available": False,
                },
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
            "jobs_limit": job_row_limit,
            "jobs_limit_options": list(job_limit_choices),
            "jobs_total_count": job_row_total,
            "jobs_table": table_config(
                panel_key=case_panel["key"],
                title="All Jobs",
                pill="Live updates",
                rows=job_rows,
                columns=CASE_JOB_TABLE_COLUMNS,
                column_ids=[col["id"] for col in CASE_JOB_TABLE_COLUMNS],
                filters=job_filters or DEFAULT_TABLE_FILTERS,
                empty_message="No jobs recorded yet.",
                show_identifiers=True,
                case_id=str(case.id),
                limit_value=job_row_limit,
                limit_options=job_limit_choices,
                total_count=job_row_total,
                pagination=job_pagination,
                param_prefix=job_param_prefix,
                filter_param_names=job_param_names,
                filters_active=job_filters_active,
                has_advanced_filters=job_has_advanced_filters,
            ),
        }
    )
    panels[case_panel["key"]] = case_panel

    transcription_status = status_payload(progress_lookup, "transcription", "Not Started")
    transcription_jobs = jobs_by_agent(job_rows, keywords=("transcription", "speech", "audio"), include_conversion=True)

    latest_job_title = None
    if latest_job:
        latest_job_title = friendly_job_title(
            latest_job,
            latest_job_telemetry,
            telemetry_map=telemetry_map,
        )

    latest_downloads = []
    if latest_job:
        latest_payload = telemetry_map.get(str(latest_job.id), {})
        downloads = (latest_payload or {}).get("downloads") or []
        latest_downloads = [download for download in downloads if download.get("url")]

    # notes
    notes_payload = next((row.get("notes") for row in job_rows if row.get("job") == latest_job), None)
    transcribe_notes = notes_payload or empty_notes.copy()
    if latest_job:
        serialized_notes = serialize_notes(JobNote.objects.filter(job=latest_job))
        transcribe_notes = {
            "job_id": str(latest_job.id),
            "entries": serialized_notes,
            "updated_at": latest_job.notes_updated_at,
            "updated_by": getattr(latest_job.notes_updated_by, "display_name", None),
            "user_can_add": user_can_review,
            "count": len(serialized_notes),
        }

    transcribe_panel = _panel_from_definition("transcribe")
    transcribe_panel.update(
        {
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
                panel_key=transcribe_panel["key"],
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
    )
    panels[transcribe_panel["key"]] = transcribe_panel

    if not return_url:
        return_url = reverse("ui-case-detail", kwargs={"case_id": case.id})

    analysis_llm = build_analysis_llm_context(case, return_url=return_url)
    summary_llm = analysis_llm["summary"]
    compose_llm = analysis_llm["compose"]
    summary_status = status_payload(progress_lookup, "summary", "Not Started")
    summary_module = analysis_lookup.get("summary") or {}
    summary_latest = summary_module.get("latest") or {}
    summary_history = summary_module.get("history") or []
    summary_jobs = jobs_by_agent(
        all_rows_iterable,
        keywords=("summary", "summarization", "summarize"),
        exclude_keywords=("transcription", "audio", "speech"),
    )
    summary_panel = _panel_from_definition("summary")
    summary_panel.update(
        {
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
            "body_context": {
                "case": case,
                "module": summary_module,
                "transcripts": transcript_sources,
                "job_endpoint_template": summary_panel.get("job_endpoint_template"),
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
                panel_key=summary_panel["key"],
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
    )
    panels[summary_panel["key"]] = summary_panel

    compose_status = status_payload(progress_lookup, "compose", "Not Started")
    compose_module = analysis_lookup.get("compose") or {}
    compose_latest = compose_module.get("latest") or {}
    compose_history = compose_module.get("history") or []
    compose_jobs = jobs_by_agent(all_rows_iterable, keywords=("compose",))
    compose_panel = _panel_from_definition("compose")
    compose_details = compose_module.get("latest_details") or {}
    compose_panel.update(
        {
            "status_label": compose_status["label"],
            "status_class": compose_status["class"],
            "updated_at": compose_status["updated"] or compose_latest.get("created_at"),
            "progress_detail": compose_status.get("detail"),
            "notes": compose_module.get("notes") or empty_notes.copy(),
            "notes_panel_html": compose_module.get("notes_panel_html"),
            "team_alerts": compose_module.get("team_alerts", team_alerts),
            "meta": [
                {
                    "label": "Deliverables",
                    "value": len(compose_details.get("deliverables", [])),
                },
                {
                    "label": "History",
                    "value": len(compose_history) + (1 if compose_latest else 0),
                },
            ],
            "body_context": {
                "case": case,
                "module": compose_module,
                "summary_module": summary_module,
                "transcripts": transcript_sources,
                "summaries": compose_module.get("available_summaries") or [],
                "compose_llm": compose_llm,
                "job_endpoint_template": compose_panel.get("job_endpoint_template"),
                "dependencies": compose_module.get("dependencies")
                or {"has_summary": False, "has_transcript": False},
            },
            "jobs": compose_jobs,
            "jobs_title": "Compose Jobs",
            "jobs_pill": "Automations",
            "jobs_empty_message": "No compose jobs yet. Generate deliverables above.",
            "case_id": str(case.id),
            "jobs_columns": list(GLOBAL_JOB_TABLE_COLUMNS),
            "jobs_column_ids": [col["id"] for col in GLOBAL_JOB_TABLE_COLUMNS],
            "jobs_filters": DEFAULT_TABLE_FILTERS,
            "jobs_show_identifiers": False,
            "jobs_table": table_config(
                panel_key=compose_panel["key"],
                title="Compose Jobs",
                pill="Automations",
                rows=compose_jobs,
                columns=GLOBAL_JOB_TABLE_COLUMNS,
                column_ids=[col["id"] for col in GLOBAL_JOB_TABLE_COLUMNS],
                filters=DEFAULT_TABLE_FILTERS,
                empty_message="No compose jobs yet. Generate deliverables above.",
                show_identifiers=False,
                case_id=str(case.id),
            ),
        }
    )
    panels[compose_panel["key"]] = compose_panel

    return panels


def _organization_member_options(case: Case) -> List[Dict[str, str]]:
    options: List[Dict[str, str]] = []
    for membership in case.organization.memberships.select_related("user"):
        user = membership.user
        if not user:
            continue
        options.append({"value": str(user.id), "label": getattr(user, "display_name", user.username)})
    return options


__all__ = [
    "build_tool_panels",
    "status_payload",
    "table_config",
]
