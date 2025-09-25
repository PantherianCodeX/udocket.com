from __future__ import annotations

from typing import Any, Dict, List, Optional

from apps.platform.jobs.models import Job

from ..common import JobTelemetryPayload, as_dict
from ..constants import CANCELABLE_STATUSES, RESTARTABLE_STATUSES


def build_job_action_entries(
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
    telem: JobTelemetryPayload = dict(telemetry or {})
    meta = as_dict(telem.get("metadata"))
    transcript_payload = as_dict(telem.get("transcript"))
    audio_payload = as_dict(telem.get("audio"))

    artifact_entry: Optional[Dict[str, Any]] = None
    artifacts_raw = telem.get("artifacts")
    if isinstance(artifacts_raw, list) and artifacts_raw:
        first_artifact: Any = artifacts_raw[0]
        if isinstance(first_artifact, dict):
            artifact_entry = as_dict(first_artifact)

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
        _add_section("Workflow").extend(workflow_items)

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
        _add_section("Review").extend(review_items)

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
        _add_section("Files & Logs").extend(files_items)

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
        _add_section("Navigation").extend(navigation_items)

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
        _add_section("Danger zone").extend(danger_items)

    return [section for section in sections if section.get("items")]
