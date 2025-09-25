from __future__ import annotations

# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportAttributeAccessIssue=false

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
import json

from django.http import HttpRequest
from django.urls import reverse
from django.utils import timezone

from apps.platform.accounts.models import OrganizationMembership
from apps.platform.artifacts.models import CaseArtifact
from apps.platform.cases.models import Case, CaseMembership
from apps.platform.jobs.models import Job

from ..constants import CASE_JOB_TABLE_COLUMNS, DEFAULT_TABLE_FILTERS, GLOBAL_JOB_TABLE_COLUMNS
from ..presenters.utils import status_class, user_label
from .analysis import enrich_summary_artifacts, enrich_timeline_artifacts
from ..presenters.jobs import (
    friendly_job_title,
    job_most_recent_timestamp,
    jobs_by_agent,
    latest_jobs_by_agent,
    map_job_status,
    select_agent,
)
from packages.udocket_core.agents.summarize_lib import SummarizeConfig
from packages.udocket_core.llm import load_llm_settings
from apps.platform.operations.llm import (
    get_org_llm_overrides,
    get_org_provider_credentials,
    load_provider_catalog,
)


# Providers the current summarization pipeline can execute end-to-end.
# Keep this set in sync with packages.udocket_core.agents.summarize_lib.SUPPORTED_PROVIDERS.
SUMMARIZE_SUPPORTED_PROVIDERS = {"azure", "local"}


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


def _collect_provider_chain(overrides: Dict[str, Dict[str, Any]], default_chain: List[str]) -> List[str]:
    sequence: List[str] = []
    if overrides:
        for payload in overrides.values():
            if not isinstance(payload, dict):
                continue
            primary = payload.get("provider")
            fallbacks = payload.get("fallbacks") if isinstance(payload.get("fallbacks"), list) else []
            for name in [primary] + list(fallbacks):
                if isinstance(name, str):
                    lower = name.lower()
                    if lower and lower not in sequence:
                        sequence.append(lower)
    for name in default_chain:
        if name not in sequence:
            sequence.append(name)
    return sequence


def _build_provider_cache(
    *,
    llm_settings,
    provider_catalog: Dict[str, Dict[str, Any]],
    provider_credentials: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    cache: Dict[str, Dict[str, Any]] = {}
    for provider_name, provider in llm_settings.providers.items():
        catalog_entry = provider_catalog.get(provider_name, {})
        configured = provider_name in provider_credentials
        runtime_supported = provider_name in SUMMARIZE_SUPPORTED_PROVIDERS
        available = runtime_supported and (provider.is_available() or configured)
        reason = ""
        if not runtime_supported:
            reason = "Not supported yet"
        elif not available and not configured:
            reason = "Configure credentials"
        cache[provider_name] = {
            "value": provider_name,
            "label": provider.display_name,
            "available": available,
            "configured": configured,
            "default_endpoint": catalog_entry.get("default_endpoint"),
            "requires_api_key": bool(catalog_entry.get("requires_api_key", True)),
            "unavailable_reason": reason,
            "models": [
                {
                    "value": model_name,
                    "label": model_meta.label,
                    "cost_tier": model_meta.cost_tier,
                }
                for model_name, model_meta in provider.models.items()
            ],
        }
    return cache


def _build_llm_stage_configs(
    *,
    stage_defs: List[Dict[str, str]],
    llm_settings,
    overrides: Dict[str, Dict[str, Any]],
    provider_cache: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    stage_configs: List[Dict[str, Any]] = []

    for stage in stage_defs:
        stage_key = stage.get("key")
        stage_label = stage.get("label", stage_key)
        stage_description = stage.get("description", "")
        assignment = llm_settings.stage(stage_key)
        provider_configs = list(provider_cache.values())
        selected_provider = assignment.providers[0] if assignment and assignment.providers else "azure"
        selected_model = assignment.model or ""
        selected_fallbacks: List[str] = []
        allow_offline_default = False

        override_payload = overrides.get(stage_key)
        if override_payload:
            selected_provider = override_payload.get("provider", selected_provider)
            override_fallbacks = override_payload.get("fallbacks")
            if isinstance(override_fallbacks, list):
                selected_fallbacks = [str(name) for name in override_fallbacks if isinstance(name, str)]
            if override_payload.get("model"):
                selected_model = override_payload.get("model")
            allow_offline_default = bool(override_payload.get("allow_offline_fallback"))
        else:
            if assignment and assignment.providers:
                selected_fallbacks = [name for name in assignment.providers if name != selected_provider]
            allow_offline_default = "local" in selected_fallbacks or selected_provider == "local"

        stage_configs.append(
            {
                "key": stage_key,
                "label": stage_label,
                "description": stage_description,
                "providers": provider_configs,
                "selected_provider": selected_provider,
                "selected_model": selected_model,
                "selected_fallbacks": selected_fallbacks,
                "allow_offline_default": allow_offline_default,
            }
        )
    return stage_configs


def analysis_modules_context(
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

    summary_artifacts = enrich_summary_artifacts(summary_artifacts, jobs, telemetry_map)
    timeline_artifacts = enrich_timeline_artifacts(timeline_artifacts)

    latest_transcription = _latest_successful_transcription_job(jobs)
    target_job: Optional[Dict[str, Any]] = None
    if latest_transcription:
        target_job = {
            "id": str(latest_transcription.id),
            "title": friendly_job_title(
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
            "status_class": status_class(status),
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
            label="Summarize",
            description="Generate layered summaries of transcripts with AI assistance.",
            artifacts=summary_artifacts,
            empty_message="No summarize jobs yet. Generate one from the latest transcript.",
            action_label="Queue summarize job",
            success_label="Summarize queued",
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


def build_case_progress(case: Case, jobs: List[Job], telemetry_map: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
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
        ("transcription", "Transcription", ("transcription", "speech", "audio")),
        ("summary", "Summarize", ("summary",)),
        ("timeline", "Timeline", ("timeline", "events")),
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


def case_field_specs() -> List[Dict[str, Any]]:
    return [
        {"name": "title", "label": "Title", "type": "text"},
        {"name": "client_name", "label": "Client", "type": "text"},
        {"name": "opposing_party", "label": "Opposing Party", "type": "text"},
        {
            "name": "client_position",
            "label": "Client Position",
            "type": "choice",
            "choices": Case.ClientPosition.choices,
        },
        {"name": "court_location", "label": "Court Location", "type": "text"},
        {
            "name": "court_level",
            "label": "Court Level",
            "type": "choice",
            "choices": Case.CourtLevel.choices,
        },
        {
            "name": "court_division",
            "label": "Court Division",
            "type": "choice",
            "choices": Case.CourtDivision.choices,
        },
        {"name": "court_case_number", "label": "Court Case Number", "type": "text"},
        {
            "name": "court_date",
            "label": "Next Hearing",
            "type": "datetime",
        },
        {"name": "filing_deadline", "label": "Filing Deadline", "type": "date"},
        {"name": "notes", "label": "Client Notes", "type": "textarea"},
    ]


def _format_case_field_value(case: Case, spec: Dict[str, Any]) -> Dict[str, Any]:
    name = spec["name"]
    raw_value = getattr(case, name, None)
    field_type = spec.get("type", "text")
    display: str
    form_value: Any = raw_value

    if field_type == "boolean":
        display = "Yes" if raw_value else "No"
        form_value = bool(raw_value)
    elif field_type == "datetime":
        if raw_value:
            local_dt = timezone.localtime(raw_value)
            display = local_dt.strftime("%b %d, %Y %I:%M %p")
            form_value = local_dt.strftime("%Y-%m-%dT%H:%M")
        else:
            display = "—"
            form_value = ""
    elif field_type == "date":
        if raw_value:
            display = raw_value.strftime("%b %d, %Y")
            form_value = raw_value.strftime("%Y-%m-%d")
        else:
            display = "—"
            form_value = ""
    elif field_type == "choice":
        getter = getattr(case, f"get_{name}_display", None)
        if callable(getter):
            try:
                display = str(getter())
            except Exception:
                display = "—"
        else:
            display = str(raw_value) if raw_value is not None else "—"
        form_value = raw_value or ""
    elif field_type == "textarea":
        display = str(raw_value) if raw_value is not None else "—"
        form_value = raw_value or ""
    else:
        display = str(raw_value) if raw_value is not None else "—"
        form_value = raw_value or ""

    return {
        "name": name,
        "label": spec.get("label", name.replace("_", " ").title()),
        "type": field_type,
        "choices": spec.get("choices"),
        "display": display,
        "value": form_value,
    }


def prepare_case_fields(case: Case) -> List[Dict[str, Any]]:
    return [_format_case_field_value(case, spec) for spec in case_field_specs()]


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
        payload = _artifact_payload(artifact)
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
) -> Dict[str, Dict[str, Any]]:
    progress_lookup = {item["key"]: item for item in progress_items}
    analysis_lookup = {module["key"]: module for module in analysis_modules}
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

    panels["case-details"] = {
        "key": "case-details",
        "label": "Intake Form",
        "description": "Update assignments, key dates, and intake metadata for this case.",
        "status_label": case_status["label"],
        "status_class": case_status["class"],
        "updated_at": case_status.get("updated") or case.updated_at,
        "progress_detail": case_status.get("detail"),
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

    panels["transcribe"] = {
        "key": "transcribe",
        "label": "Transcribe",
        "description": "Upload audio or provide a SAS URL to run Azure Speech in Canada-only regions.",
        "status_label": transcription_status["label"],
        "status_class": transcription_status["class"],
        "updated_at": transcription_status["updated"],
        "progress_detail": transcription_status.get("detail"),
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

    try:
        summarize_cfg = SummarizeConfig.from_env()
    except Exception:  # noqa: BLE001
        summarize_cfg = SummarizeConfig()

    llm_settings = load_llm_settings()
    org_overrides = get_org_llm_overrides(case.organization_id)
    provider_catalog = load_provider_catalog()
    provider_credentials = get_org_provider_credentials(case.organization_id)
    provider_cache = _build_provider_cache(
        llm_settings=llm_settings,
        provider_catalog=provider_catalog,
        provider_credentials=provider_credentials,
    )

    provider_chain = list(summarize_cfg.provider_chain or ["azure", "local"])
    if summarize_cfg.force_offline_mode:
        provider_chain = ["local"]
    primary_default = provider_chain[0] if provider_chain else "azure"
    if primary_default == "azure" and not summarize_cfg.azure_enabled:
        primary_default = "local"
    fallback_defaults = [value for value in provider_chain if value != primary_default]

    provider_options: List[Dict[str, Any]] = []
    seen_providers: set[str] = set()
    for name, provider in llm_settings.providers.items():
        catalog_entry = provider_catalog.get(name, {})
        credential_entry = provider_credentials.get(name, {})
        configured = bool(credential_entry)
        available = provider_cache[name]["available"]
        option = {
            "value": name,
            "label": provider.display_name,
            "description": catalog_entry.get("description"),
            "available": available,
            "configured": configured,
            "default_endpoint": catalog_entry.get("default_endpoint"),
            "requires_api_key": bool(catalog_entry.get("requires_api_key", True)),
            "endpoint": credential_entry.get("endpoint"),
            "models": credential_entry.get("models") or catalog_entry.get("models"),
            "reason": provider_cache[name].get("unavailable_reason"),
        }
        provider_options.append(option)
        seen_providers.add(name)

    for name, credential in provider_credentials.items():
        if name in seen_providers:
            continue
        provider_options.append(
            {
                "value": name,
                "label": credential.get("display_name") or name,
                "description": None,
                "available": True,
                "configured": True,
                "default_endpoint": credential.get("endpoint"),
                "requires_api_key": True,
                "endpoint": credential.get("endpoint"),
                "models": credential.get("models"),
                "reason": "",
            }
        )
        seen_providers.add(name)

    summary_stage_defs = [
        {
            "key": "summarize.context_builder",
            "label": "Context builder",
            "description": "Collects intake details and transcript metadata for downstream prompts.",
        },
        {
            "key": "summarize.extract_outline",
            "label": "Outline extraction",
            "description": "Structures issues, facts, remedies, and legal references as JSON schema.",
        },
        {
            "key": "summarize.build_timeline_seeds",
            "label": "Timeline seeds",
            "description": "Proposes timestamped events to seed the timeline automation.",
        },
        {
            "key": "summarize.build_entity_hints",
            "label": "Entity hints",
            "description": "Identifies people, organizations, and relationships for the graph agent.",
        },
        {
            "key": "summarize.draft_markdown",
            "label": "Draft summary",
            "description": "Drafts the layered legal summary referencing transcript timestamps.",
        },
        {
            "key": "summarize.qa_and_finalize",
            "label": "QA and finalize",
            "description": "Ensures required sections exist, computes checksums, and prepares ops logs.",
        },
    ]

    summary_stage_keys = [stage["key"] for stage in summary_stage_defs]
    summary_overrides = {k: org_overrides[k] for k in summary_stage_keys if k in org_overrides}
    summary_stage_configs = _build_llm_stage_configs(
        stage_defs=summary_stage_defs,
        llm_settings=llm_settings,
        overrides=summary_overrides,
        provider_cache=provider_cache,
    )
    summary_chain = _collect_provider_chain(summary_overrides, provider_chain)
    summary_primary = summary_chain[0] if summary_chain else primary_default
    if summary_primary == "azure" and not summarize_cfg.azure_enabled:
        summary_primary = "local"
    summary_fallbacks = [value for value in summary_chain if value != summary_primary]
    summary_overrides_json = json.dumps(summary_overrides)
    summary_chain_json = json.dumps(summary_chain)

    timeline_stage_defs = [
        {
            "key": "timeline.builder",
            "label": "Timeline builder",
            "description": "Generates a normalized timeline from transcripts and timeline seeds.",
        }
    ]
    timeline_stage_keys = [stage["key"] for stage in timeline_stage_defs]
    timeline_overrides = {k: org_overrides[k] for k in timeline_stage_keys if k in org_overrides}
    timeline_stage_configs = _build_llm_stage_configs(
        stage_defs=timeline_stage_defs,
        llm_settings=llm_settings,
        overrides=timeline_overrides,
        provider_cache=provider_cache,
    )
    timeline_chain = _collect_provider_chain(timeline_overrides, provider_chain)
    timeline_primary = timeline_chain[0] if timeline_chain else primary_default
    if timeline_primary == "azure" and not summarize_cfg.azure_enabled:
        timeline_primary = "local"
    timeline_fallbacks = [value for value in timeline_chain if value != timeline_primary]
    timeline_chain_json = json.dumps(timeline_chain)
    timeline_overrides_json = json.dumps(timeline_overrides)

    summary_status = status_payload(progress_lookup, "summary", "Not Started")
    summary_module = analysis_lookup.get("summary") or {}
    summary_latest = summary_module.get("latest") or {}
    summary_history = summary_module.get("history") or []
    summary_jobs = jobs_by_agent(all_rows_iterable, keywords=("summary", "summarization", "summarize"))
    panels["summary"] = {
        "key": "summary",
        "label": "Summarize",
        "description": "Generate layered summaries from approved transcripts.",
        "status_label": summary_status["label"],
        "status_class": summary_status["class"],
        "updated_at": summary_status["updated"] or summary_latest.get("created_at"),
        "progress_detail": summary_status.get("detail"),
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
            "summary_llm": {
                "target": "summary",
                "provider_options": provider_options,
                "defaults": {
                    "primary": summary_primary,
                    "fallbacks": summary_fallbacks,
                    "allow_offline": summarize_cfg.enable_offline_fallback,
                    "force_offline": summarize_cfg.force_offline_mode,
                    "azure_available": summarize_cfg.azure_enabled,
                },
                "stage_configs": summary_stage_configs,
                "overrides": summary_overrides,
                "overrides_json": summary_overrides_json,
                "provider_chain_json": summary_chain_json,
                "catalog": provider_catalog,
                "catalog_json": json.dumps(provider_catalog),
                "credentials": provider_credentials,
                "credentials_json": json.dumps(provider_credentials),
            },
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
            "timeline_llm": {
                "target": "timeline",
                "provider_options": provider_options,
                "defaults": {
                    "primary": timeline_primary,
                    "fallbacks": timeline_fallbacks,
                    "allow_offline": summarize_cfg.enable_offline_fallback,
                    "force_offline": summarize_cfg.force_offline_mode,
                    "azure_available": summarize_cfg.azure_enabled,
                },
                "stage_configs": timeline_stage_configs,
                "overrides": timeline_overrides,
                "overrides_json": timeline_overrides_json,
                "provider_chain_json": timeline_chain_json,
                "catalog": provider_catalog,
                "catalog_json": json.dumps(provider_catalog),
                "credentials": provider_credentials,
                "credentials_json": json.dumps(provider_credentials),
            },
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
