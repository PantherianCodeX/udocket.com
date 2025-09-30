from __future__ import annotations

# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportAttributeAccessIssue=false

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
import json
from urllib.parse import quote

from django.conf import settings
from django.http import HttpRequest
from django.urls import reverse
from django.utils import timezone

from apps.platform.accounts.models import OrganizationMembership
from apps.platform.artifacts.models import CaseArtifact
from apps.platform.cases.models import Case, CaseMembership
from apps.platform.jobs.models import Job, JobNote

from ..constants import CASE_JOB_TABLE_COLUMNS, DEFAULT_TABLE_FILTERS, GLOBAL_JOB_TABLE_COLUMNS
from ..common import as_dict
from ..presenters.utils import render_notes_panel_html, status_class, user_label
from .analysis import enrich_summary_artifacts, enrich_timeline_artifacts
from ..presenters.jobs import (
    friendly_job_title,
    job_most_recent_timestamp,
    jobs_by_agent,
    latest_jobs_by_agent,
    map_job_status,
    select_agent,
)
from packages.udocket_core.agents.summarize_lib import SUMMARIZE_STAGE_PROFILES, SummarizeConfig
from packages.udocket_core.llm import load_llm_settings
from apps.platform.operations.llm import (
    build_provider_registry,
    ensure_default_llm_configuration,
    get_llm_configuration,
    get_org_llm_configurations,
    get_org_provider_credentials,
    load_provider_catalog,
)
from apps.platform.authorization.capabilities import has_capability
from apps.platform.jobs.notes import serialize_notes


def _user_can_add_notes(user, case: Case) -> bool:
    if getattr(settings, "PLATFORM_DEV_OPEN", False):
        return True
    if not user or not getattr(user, "is_authenticated", False):
        return False
    try:
        if case.reviewer_id and str(user.id) == str(case.reviewer_id):
            return True
    except Exception:
        pass
    try:
        return has_capability(user, str(case.id), "case.update")
    except Exception:
        return False


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


def _collect_provider_chain(
    provider_chain: Sequence[str],
    default_chain: List[str],
) -> List[str]:
    sequence: List[str] = []
    for name in provider_chain:
        value = str(name or "").strip().lower()
        if value and value not in sequence:
            sequence.append(value)
    for name in default_chain:
        if name not in sequence:
            sequence.append(name)
    return sequence


def _stage_profile_hint(stage_key: str) -> Optional[Dict[str, Any]]:
    profile = SUMMARIZE_STAGE_PROFILES.get(stage_key)
    if profile is None:
        return None
    return {
        "min_context_tokens": profile.min_context_tokens,
        "recommended_context_tokens": profile.recommended_context_tokens,
        "target_chunk_tokens": profile.target_chunk_tokens,
        "output_reserve_tokens": profile.output_reserve_tokens,
        "resource_notes": profile.resource_notes,
    }


def _stage_definitions_for_target(
    *,
    llm_settings,
    target: str,
    stage_map: Dict[str, Dict[str, Any]],
) -> List[Dict[str, str]]:
    stage_defs: List[Dict[str, str]] = []
    seen: set[str] = set()

    for assignment in llm_settings.assignments.values():
        if assignment.target != target:
            continue
        stage_defs.append(
            {
                "key": assignment.stage_key,
                "label": assignment.label or assignment.stage_key,
                "description": assignment.description,
            }
        )
        seen.add(assignment.stage_key)

    for raw_key in stage_map.keys():
        stage_key = str(raw_key)
        if stage_key in seen:
            continue
        stage_defs.append({"key": stage_key, "label": stage_key, "description": ""})
        seen.add(stage_key)

    return stage_defs


def _build_llm_stage_configs(
    *,
    target: str,
    llm_settings,
    stage_map: Dict[str, Dict[str, Any]],
    provider_registry: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    stage_map = stage_map or {}
    stage_defs = _stage_definitions_for_target(
        llm_settings=llm_settings,
        target=target,
        stage_map=stage_map,
    )
    stage_configs: List[Dict[str, Any]] = []

    for stage in stage_defs:
        stage_key = stage.get("key")
        stage_label = stage.get("label", stage_key)
        stage_description = stage.get("description", "")
        assignment = llm_settings.stage(stage_key)
        provider_configs = list(provider_registry.values())
        selected_provider = (
            assignment.providers[0]
            if assignment and assignment.providers
            else (provider_configs[0]["value"] if provider_configs else "azure")
        )
        selected_model = assignment.model or ""
        selected_options: Dict[str, Any] = dict(assignment.options) if assignment else {}
        selected_max_tokens: Optional[int] = None

        override_payload = stage_map.get(stage_key)
        if override_payload:
            provider_override = override_payload.get("provider")
            if isinstance(provider_override, str) and provider_override.strip():
                selected_provider = provider_override.strip().lower()
            providers_override = override_payload.get("providers")
            if isinstance(providers_override, list):
                for candidate in providers_override:
                    if isinstance(candidate, str) and candidate.strip():
                        selected_provider = candidate.strip().lower()
                        break
            model_override = override_payload.get("model")
            if isinstance(model_override, str) and model_override.strip():
                selected_model = model_override.strip()
            options_override = override_payload.get("options")
            if isinstance(options_override, dict):
                selected_options.update(options_override)
            max_override = override_payload.get("max_tokens")
            if isinstance(max_override, (int, float)):
                max_value = int(max_override)
                if max_value > 0:
                    selected_max_tokens = max_value

        stage_configs.append(
            {
                "key": stage_key,
                "label": stage_label,
                "description": stage_description,
                "providers": provider_configs,
                "selected_provider": selected_provider,
                "selected_model": selected_model,
                "selected_options": selected_options,
                "selected_max_tokens": selected_max_tokens,
                "profile": _stage_profile_hint(stage_key) if target == "summary" else None,
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
    return_url = request.get_full_path()
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

        notes_context: Dict[str, Any] = {}
        latest_job_id = None
        if latest:
            latest_job_id = latest.get("job_id") or latest.get("id")
        if latest_job_id:
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
            notes_context = {
                "job_id": str(latest_job_id),
                "entries": notes_entries,
                "updated_at": notes_updated_at,
                "updated_by": notes_updated_by,
                "user_can_add": _user_can_add_notes(user, case),
            }
        notes_panel_html = ""
        if notes_context.get("job_id"):
            notes_panel_html = render_notes_panel_html(
                job_id=notes_context["job_id"],
                entries=notes_context.get("entries"),
                updated_at=notes_context.get("updated_at"),
                updated_by=notes_context.get("updated_by"),
                user_can_add=notes_context.get("user_can_add", False),
            )

        latest_details = as_dict(latest.get("details")) if latest else {}
        downloads: List[Dict[str, Any]] = []
        job_identifier = latest.get("job_id") if latest else None
        if job_identifier:
            def _add_download(kind: str, label: str, meta: Optional[str] = None) -> None:
                downloads.append(
                    {
                        "label": label,
                        "href": f"/api/v1/jobs/{job_identifier}/download-analysis/?kind={kind}",
                        "download": True,
                        "meta": meta,
                    }
                )

            if latest_details.get("summary_path") or latest.get("download_url"):
                downloads.append(
                    {
                        "label": "Summary JSON",
                        "href": latest.get("download_url") or f"/api/v1/jobs/{job_identifier}/download-analysis/?kind=summary_json",
                        "download": True,
                    }
                )
            if latest_details.get("summary_markdown_path"):
                _add_download("summary_markdown", "Summary Markdown")
            if latest_details.get("outline_path"):
                _add_download("summary_outline", "Outline JSON")
            if latest_details.get("timeline_seed_path") or latest_details.get("timeline_seed_name"):
                _add_download("summary_timeline_seeds", "Timeline seeds")
            if latest_details.get("entity_hint_path"):
                _add_download("summary_entity_hints", "Entity hints")
            if latest_details.get("case_brief_path"):
                _add_download("summary_case_brief", "Case brief")

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
            "downloads": downloads,
            "latest_details": latest_details,
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
            "notes": notes_context,
            "notes_panel": notes_panel_html,
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
    return_url: str = "",
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
    encoded_return_url = quote(return_url, safe="")

    def _with_next(url: str) -> str:
        if not encoded_return_url:
            return url
        separator = "&" if "?" in url else "?"
        return f"{url}{separator}next={encoded_return_url}"

    try:
        summarize_cfg = SummarizeConfig.from_env()
    except Exception:  # noqa: BLE001
        summarize_cfg = SummarizeConfig()

    llm_settings = load_llm_settings()
    provider_catalog = load_provider_catalog()
    provider_credentials = get_org_provider_credentials(case.organization_id)
    provider_registry = build_provider_registry(
        organization_id=case.organization_id,
        llm_settings=llm_settings,
        provider_catalog=provider_catalog,
        provider_credentials=provider_credentials,
    )

    provider_chain = list(summarize_cfg.provider_chain or ["azure"])
    primary_default = provider_chain[0] if provider_chain else "azure"

    provider_options: List[Dict[str, Any]] = []
    for name, entry in provider_registry.items():
        catalog_entry = provider_catalog.get(name, {})
        credential_entry = provider_credentials.get(name, {})
        provider_options.append(
            {
                "value": name,
                "label": entry.get("label", name),
                "description": catalog_entry.get("description"),
                "available": entry.get("available", False),
                "configured": entry.get("configured", False),
                "default_endpoint": entry.get("default_endpoint"),
                "requires_api_key": entry.get("requires_api_key", True),
                "endpoint": entry.get("endpoint") or credential_entry.get("endpoint"),
                "models": entry.get("models"),
                "reason": entry.get("unavailable_reason", ""),
                "api_kind": entry.get("api_kind"),
            }
        )

    summary_config_list = get_org_llm_configurations(str(case.organization_id), target="summary")
    summary_active_config = get_llm_configuration(
        organization_id=str(case.organization_id),
        config_id=None,
        target="summary",
    )
    if not summary_active_config:
        summary_active_config = ensure_default_llm_configuration(
            organization_id=str(case.organization_id),
            target="summary",
            llm_settings=llm_settings,
        )
        if summary_active_config:
            summary_config_list = get_org_llm_configurations(str(case.organization_id), target="summary")

    summary_stage_map_raw = summary_active_config.get("stage_map", {}) if summary_active_config else {}
    summary_stage_map = dict(summary_stage_map_raw or {})
    summary_provider_chain = summary_active_config.get("provider_chain", []) if summary_active_config else []
    summary_stage_configs = _build_llm_stage_configs(
        target="summary",
        llm_settings=llm_settings,
        stage_map=summary_stage_map,
        provider_registry=provider_registry,
    )
    summary_chain = _collect_provider_chain(summary_provider_chain, provider_chain)
    summary_configured_stages: List[Dict[str, Any]] = []
    for stage in summary_stage_configs:
        override = summary_stage_map.get(stage["key"])
        if not override:
            continue
        summary_configured_stages.append(
            {
                "key": stage["key"],
                "label": stage["label"],
                "provider": override.get("provider") or stage.get("selected_provider"),
                "model": override.get("model") or stage.get("selected_model"),
                "max_tokens": override.get("max_tokens"),
                "options": override.get("options") or {},
            }
        )

    summary_stage_configs_json = json.dumps(summary_stage_configs)
    summary_configs_json = json.dumps(summary_config_list)
    summary_active_config_json = json.dumps(summary_active_config or {})
    summary_chain_json = json.dumps(summary_chain)
    summary_stage_map_json = json.dumps(summary_stage_map)
    summary_settings_base = reverse("ui-organization-settings-section", args=["summary"])
    summary_edit_base = (
        f"{summary_settings_base}?config={summary_active_config.get('id')}"
        if summary_active_config and summary_active_config.get("id")
        else summary_settings_base
    )
    summary_urls = {
        "base": summary_settings_base,
        "edit": _with_next(summary_edit_base),
        "new": _with_next(f"{summary_settings_base}?new=1"),
        "tuning": _with_next(reverse("ui-organization-settings-section", args=["providers"])),
    }

    timeline_config_list = get_org_llm_configurations(str(case.organization_id), target="timeline")
    timeline_active_config = get_llm_configuration(
        organization_id=str(case.organization_id),
        config_id=None,
        target="timeline",
    )
    if not timeline_active_config:
        timeline_active_config = ensure_default_llm_configuration(
            organization_id=str(case.organization_id),
            target="timeline",
            llm_settings=llm_settings,
        )
        if timeline_active_config:
            timeline_config_list = get_org_llm_configurations(str(case.organization_id), target="timeline")

    timeline_stage_map_raw = timeline_active_config.get("stage_map", {}) if timeline_active_config else {}
    timeline_stage_map = dict(timeline_stage_map_raw or {})
    timeline_provider_chain = timeline_active_config.get("provider_chain", []) if timeline_active_config else []
    timeline_stage_configs = _build_llm_stage_configs(
        target="timeline",
        llm_settings=llm_settings,
        stage_map=timeline_stage_map,
        provider_registry=provider_registry,
    )
    timeline_chain = _collect_provider_chain(timeline_provider_chain, provider_chain)
    timeline_configured_stages: List[Dict[str, Any]] = []
    for stage in timeline_stage_configs:
        override = timeline_stage_map.get(stage["key"])
        if not override:
            continue
        timeline_configured_stages.append(
            {
                "key": stage["key"],
                "label": stage["label"],
                "provider": override.get("provider") or stage.get("selected_provider"),
                "model": override.get("model") or stage.get("selected_model"),
                "max_tokens": override.get("max_tokens"),
                "options": override.get("options") or {},
            }
        )

    timeline_stage_configs_json = json.dumps(timeline_stage_configs)
    timeline_configs_json = json.dumps(timeline_config_list)
    timeline_active_config_json = json.dumps(timeline_active_config or {})
    timeline_chain_json = json.dumps(timeline_chain)
    timeline_stage_map_json = json.dumps(timeline_stage_map)
    timeline_settings_base = reverse("ui-organization-settings-section", args=["timeline"])
    timeline_edit_base = (
        f"{timeline_settings_base}?config={timeline_active_config.get('id')}"
        if timeline_active_config and timeline_active_config.get("id")
        else timeline_settings_base
    )
    timeline_urls = {
        "base": timeline_settings_base,
        "edit": _with_next(timeline_edit_base),
        "new": _with_next(f"{timeline_settings_base}?new=1"),
        "tuning": _with_next(reverse("ui-organization-settings-section", args=["providers"])),
    }
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
                    "configurations": summary_config_list,
                    "configurations_json": summary_configs_json,
                    "active_configuration": summary_active_config,
                    "active_configuration_json": summary_active_config_json,
                    "configured_stages": summary_configured_stages,
                    "stage_configs": summary_stage_configs,
                    "stage_configs_json": summary_stage_configs_json,
                    "stage_map_json": summary_stage_map_json,
                    "provider_chain": summary_chain,
                    "provider_chain_json": summary_chain_json,
                    "urls": summary_urls,
                    "return_url": return_url,
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
                    "configurations": timeline_config_list,
                    "configurations_json": timeline_configs_json,
                    "active_configuration": timeline_active_config,
                    "active_configuration_json": timeline_active_config_json,
                    "configured_stages": timeline_configured_stages,
                    "stage_configs": timeline_stage_configs,
                    "stage_configs_json": timeline_stage_configs_json,
                    "stage_map_json": timeline_stage_map_json,
                    "provider_chain": timeline_chain,
                    "provider_chain_json": timeline_chain_json,
                    "urls": timeline_urls,
                    "return_url": return_url,
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
