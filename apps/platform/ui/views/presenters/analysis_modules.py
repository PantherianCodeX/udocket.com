from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

from django.conf import settings
from django.http import HttpRequest
from django.urls import reverse

from apps.platform.authorization.capabilities import has_capability
from apps.platform.artifacts.models import CaseArtifact, CaseArtifactQuerySet
from apps.platform.cases.models import Case
from apps.platform.jobs.models import Job, JobNote
from apps.platform.jobs.notes import serialize_notes

from ..common import as_dict
from ..presenters.alerts import build_case_team_alerts
from ..presenters.jobs import friendly_job_title
from ..presenters.utils import render_notes_panel_html, status_class
from .analysis import enrich_summary_artifacts, enrich_timeline_artifacts


def _user_can_add_notes(user: Any, case: Case) -> bool:
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


def latest_successful_transcription_job(jobs: List[Job]) -> Optional[Job]:
    ordered = sorted(
        jobs,
        key=lambda j: (j.finished_at or j.started_at or j.created_at or datetime.min),
        reverse=True,
    )
    for job in ordered:
        if job.status == Job.Status.SUCCEEDED and job.transcript_path:
            return job
    return None


def artifact_payload(artifact: CaseArtifact) -> Dict[str, Any]:
    metadata = cast(Dict[str, Any], artifact.metadata or {})
    path_obj = Path(artifact.path) if artifact.path else None
    filename = path_obj.name if path_obj else str(artifact.path or "")
    source_val = metadata.get("source_transcript") or metadata.get("source")
    source: Optional[str]
    if source_val:
        source = str(source_val)
    else:
        source = None
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
        "artifact_type": artifact.type,
    }


def analysis_modules_context(
    request: HttpRequest,
    case: Case,
    jobs: List[Job],
    telemetry_map: Dict[str, Dict[str, Any]],
    transcript_artifacts: Optional[Dict[str, CaseArtifact]] = None,
) -> List[Dict[str, Any]]:
    return_url = request.get_full_path() if hasattr(request, "get_full_path") else ""
    user = getattr(request, "user", None)
    artifacts_manager = cast(CaseArtifactQuerySet, CaseArtifact.objects)
    artifacts_qs = (
        artifacts_manager.for_user(user)
        .filter(
            case_id=str(case.id),
            type__in=["SUMMARY", "TIMELINE", "ANALYSIS", "COMPOSE", "GRAPH", "ENTITIES"],
        )
        .order_by("-created_at")
    )

    artifact_payloads: List[Dict[str, Any]] = [artifact_payload(artifact) for artifact in artifacts_qs]

    summary_artifacts: List[Dict[str, Any]] = []
    timeline_artifacts: List[Dict[str, Any]] = []
    graph_artifacts: List[Dict[str, Any]] = []
    entity_artifacts: List[Dict[str, Any]] = []
    compose_candidates: Dict[str, Dict[str, Any]] = {}

    for payload in artifact_payloads:
        artifact_type = str(payload.get("artifact_type") or "").upper()
        if artifact_type == "SUMMARY":
            summary_artifacts.append(payload)
        elif artifact_type == "TIMELINE":
            timeline_artifacts.append(payload)
        elif artifact_type == "GRAPH":
            graph_artifacts.append(payload)
        elif artifact_type == "ENTITIES":
            entity_artifacts.append(payload)
        else:
            filename = payload.get("filename", "").lower()
            title = (payload.get("title") or "").lower()
            if "compose" in filename or "compose" in title:
                job_key = payload.get("job_id") or str(payload["id"]).replace(" ", "")
                candidate = compose_candidates.setdefault(
                    job_key,
                    {
                        "job_id": job_key,
                        "artifacts": [],
                        "created_at": payload.get("created_at"),
                        "source": payload.get("metadata", {}).get("source_summary"),
                        "title": payload.get("title") or "Compose Deliverables",
                    },
                )
                candidate["artifacts"].append(payload)
                created_at = payload.get("created_at")
                if created_at and (candidate.get("created_at") is None or created_at > candidate["created_at"]):
                    candidate["created_at"] = created_at
                if payload.get("title"):
                    candidate["title"] = payload["title"]

    summary_artifacts = enrich_summary_artifacts(summary_artifacts, jobs, telemetry_map)
    timeline_artifacts = enrich_timeline_artifacts(timeline_artifacts)

    latest_transcription = latest_successful_transcription_job(jobs)
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

    team_alerts = build_case_team_alerts(case, jobs)

    def _notes_context(job_identifier: Optional[str]) -> Dict[str, Any]:
        context: Dict[str, Any] = {
            "job_id": None,
            "entries": [],
            "updated_at": None,
            "updated_by": None,
            "user_can_add": False,
            "count": 0,
        }
        if not job_identifier:
            return context
        notes_qs = (
            JobNote.objects.filter(job_id=job_identifier)
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
        context.update(
            {
                "job_id": str(job_identifier),
                "entries": notes_entries,
                "updated_at": notes_updated_at,
                "updated_by": notes_updated_by,
                "user_can_add": _user_can_add_notes(user, case),
                "count": len(notes_entries),
            }
        )
        return context

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

        latest_job_id = None
        if latest:
            latest_job_id = latest.get("job_id") or latest.get("id")
        notes_context = _notes_context(latest_job_id)
        notes_panel_html = render_notes_panel_html(
            job_id=notes_context.get("job_id"),
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
            "notes_panel_html": notes_panel_html,
            "notes_panel": notes_panel_html,
            "return_url": return_url,
            "team_alerts": team_alerts,
        }

    summary_module = build_module(
        key="summary",
        label="Summarize",
        description="Generate layered summaries of transcripts with AI assistance.",
        artifacts=summary_artifacts,
        empty_message="No summarize jobs yet. Generate one from the latest transcript.",
        action_label="Queue summarize job",
        success_label="Summarize queued",
    )
    compose_entries = sorted(
        compose_candidates.values(),
        key=lambda entry: entry.get("created_at") or datetime.min,
        reverse=True,
    )

    def _format_compose_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
        items: List[Dict[str, Any]] = entry.get("artifacts", [])
        deliverables: List[Dict[str, Any]] = []
        for item in items:
            filename = item.get("filename", "")
            label = item.get("title") or filename
            lower_name = filename.lower()
            if "client" in lower_name:
                label = "Client deliverable"
            elif "lawyer" in lower_name:
                label = "Lawyer deliverable"
            deliverables.append(
                {
                    "label": label,
                    "download_url": item.get("download_url"),
                    "filename": filename,
                    "format": filename.split(".")[-1] if "." in filename else "",
                }
            )
        primary = items[0] if items else entry
        return {
            "id": primary.get("id"),
            "job_id": entry.get("job_id"),
            "title": entry.get("title") or "Compose Deliverables",
            "created_at": entry.get("created_at"),
            "source": entry.get("source"),
            "download_url": (deliverables[0]["download_url"] if deliverables and deliverables[0]["download_url"] else primary.get("download_url")),
            "details": {
                "deliverables": deliverables,
                "source_summary": entry.get("source"),
            },
            "deliverables": deliverables,
        }

    compose_latest_entry = _format_compose_entry(compose_entries[0]) if compose_entries else None
    compose_history_entries = [_format_compose_entry(entry) for entry in compose_entries[1:5]]
    compose_notes_context = _notes_context(compose_latest_entry.get("job_id") if compose_latest_entry else None)
    compose_notes_panel = render_notes_panel_html(
        job_id=compose_notes_context.get("job_id"),
        entries=compose_notes_context.get("entries"),
        updated_at=compose_notes_context.get("updated_at"),
        updated_by=compose_notes_context.get("updated_by"),
        user_can_add=compose_notes_context.get("user_can_add", False),
    )
    compose_downloads: List[Dict[str, Any]] = [
        {
            "label": item["label"],
            "href": item["download_url"],
            "download": True,
        }
        for item in (compose_latest_entry.get("deliverables", []) if compose_latest_entry else [])
        if item.get("download_url")
    ]

    timeline_latest = timeline_artifacts[0] if timeline_artifacts else None
    timeline_history = timeline_artifacts[1:5] if timeline_artifacts else []
    graph_latest: Optional[Dict[str, Any]]
    graph_history: List[Dict[str, Any]]
    if graph_artifacts:
        graph_latest = graph_artifacts[0]
        graph_history = graph_artifacts[1:5]
    elif entity_artifacts:
        graph_latest = entity_artifacts[0]
        graph_history = entity_artifacts[1:5]
    else:
        graph_latest = None
        graph_history = []

    if timeline_latest and timeline_latest.get("download_url"):
        compose_downloads.append(
            {
                "label": "Timeline JSON",
                "href": timeline_latest["download_url"],
                "download": True,
            }
        )
    if graph_latest and graph_latest.get("download_url"):
        compose_downloads.append(
            {
                "label": "Graph JSON" if (graph_latest.get("artifact_type", "").upper() == "GRAPH") else "Entities JSON",
                "href": graph_latest["download_url"],
                "download": True,
            }
        )
    compose_status = "Not Started"
    compose_header_hint = "No deliverables yet"
    compose_disabled = False
    compose_disabled_reason = None
    if not target_job:
        compose_status = "No Transcript"
        compose_header_hint = "Upload and run a transcription to enable Compose."
        compose_disabled = True
        compose_disabled_reason = "Requires a completed transcript."
    elif not summary_artifacts:
        compose_status = "Needs Summary"
        compose_header_hint = "Generate and approve a summary before composing deliverables."
        compose_disabled = True
        compose_disabled_reason = "Requires an approved summary."
    elif compose_latest_entry:
        compose_status = "Ready"
        compose_header_hint = "Latest deliverables"

    available_summaries = [
        {
            "job_id": item.get("job_id"),
            "title": item.get("title"),
            "created_at": item.get("created_at"),
        }
        for item in summary_artifacts[:5]
    ]

    compose_dependencies = {
        "has_transcript": bool(target_job),
        "has_summary": bool(summary_artifacts),
        "has_timeline": bool(timeline_artifacts),
        "has_graph": bool(graph_artifacts or entity_artifacts),
    }

    compose_module: Dict[str, Any] = {
        "key": "compose",
        "label": "Compose",
        "description": "Generate client and lawyer deliverables from approved summaries and transcripts.",
        "panel_id": "module-compose",
        "status": compose_status,
        "status_class": status_class(compose_status),
        "header_hint": compose_header_hint,
        "header_hint_time": compose_latest_entry["created_at"] if compose_latest_entry else None,
        "latest": compose_latest_entry,
        "history": compose_history_entries,
        "downloads": compose_downloads,
        "latest_details": {
            **(compose_latest_entry.get("details") if compose_latest_entry else {}),
            "timeline": timeline_latest,
            "graph": graph_latest,
        },
        "empty_message": "No compose jobs yet. Generate deliverables from the latest summary.",
        "target_job": target_job,
        "action": {
            "job_id": target_job["id"] if target_job else None,
            "label": "Queue compose job",
            "loading_label": "Queuing…",
            "success_label": "Compose queued",
            "disabled": compose_disabled,
            "disabled_reason": compose_disabled_reason,
        },
        "notes": compose_notes_context,
        "notes_panel_html": compose_notes_panel,
        "notes_panel": compose_notes_panel,
        "return_url": return_url,
        "team_alerts": team_alerts,
        "available_summaries": available_summaries,
        "dependencies": compose_dependencies,
        "timeline": {
            "latest": timeline_latest,
            "history": timeline_history,
        },
        "graph": {
            "latest": graph_latest,
            "history": graph_history,
            "entities": entity_artifacts,
        },
    }

    return [summary_module, compose_module]


__all__ = [
    "analysis_modules_context",
    "artifact_payload",
    "latest_successful_transcription_job",
]
