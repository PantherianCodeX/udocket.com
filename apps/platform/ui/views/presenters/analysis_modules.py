from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.http import HttpRequest
from django.urls import reverse

from apps.platform.authorization.capabilities import has_capability
from apps.platform.artifacts.models import CaseArtifact
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


def analysis_modules_context(
    request: HttpRequest,
    case: Case,
    jobs: List[Job],
    telemetry_map: Dict[str, Dict[str, Any]],
    transcript_artifacts: Optional[Dict[str, CaseArtifact]] = None,
) -> List[Dict[str, Any]]:
    return_url = request.get_full_path() if hasattr(request, "get_full_path") else ""
    user = getattr(request, "user", None)
    artifacts_qs = (
        CaseArtifact.objects.for_user(user)
        .filter(case_id=str(case.id), type__in=["SUMMARY", "TIMELINE"])
        .order_by("-created_at")
    )

    summary_artifacts: List[Dict[str, Any]] = []
    timeline_artifacts: List[Dict[str, Any]] = []
    for artifact in artifacts_qs:
        payload = artifact_payload(artifact)
        if artifact.type == "SUMMARY":
            summary_artifacts.append(payload)
        elif artifact.type == "TIMELINE":
            timeline_artifacts.append(payload)

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

        notes_context: Dict[str, Any] = {
            "job_id": None,
            "entries": [],
            "updated_at": None,
            "updated_by": None,
            "user_can_add": False,
            "count": 0,
        }
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
            notes_count = len(notes_entries)
            notes_context = {
                "job_id": str(latest_job_id),
                "entries": notes_entries,
                "updated_at": notes_updated_at,
                "updated_by": notes_updated_by,
                "user_can_add": _user_can_add_notes(user, case),
                "count": notes_count,
            }
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
    timeline_module = build_module(
        key="timeline",
        label="Timeline",
        description="Build an event timeline anchored to transcript timestamps.",
        artifacts=timeline_artifacts,
        empty_message="No timeline has been generated yet.",
        action_label="Generate timeline",
        success_label="Timeline queued",
    )

    return [summary_module, timeline_module]


__all__ = [
    "analysis_modules_context",
    "artifact_payload",
    "latest_successful_transcription_job",
]
