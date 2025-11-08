from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from ..common import as_dict


def _normalize_path(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None


def enrich_summary_artifacts(
    artifacts: list[dict[str, Any]],
    jobs: list[Any],
    telemetry_map: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge analyze job metadata (outline/seeds/entities) into artifact payloads."""

    meta_by_job: dict[str, dict[str, Any]] = {}
    for job in jobs:
        job_id = getattr(job, "id", None)
        if job_id is None:
            continue
        telem = telemetry_map.get(str(job_id)) or {}
        meta_payload = as_dict(telem.get("metadata"))
        summary_path = _normalize_path(meta_payload.get("summary_file"))
        summary_markdown_path = _normalize_path(meta_payload.get("summary_markdown_file"))
        if not summary_path:
            continue
        outline_path = _normalize_path(meta_payload.get("summary_outline_file"))
        timeline_seed_path = _normalize_path(meta_payload.get("summary_timeline_file"))
        entity_hint_path = _normalize_path(meta_payload.get("summary_entity_file"))
        case_brief_path = _normalize_path(
            meta_payload.get("summary_case_brief_file") or meta_payload.get("case_brief_file")
        )
        provider_chain = (
            meta_payload.get("summary_provider_chain") or meta_payload.get("provider_chain") or []
        )
        if isinstance(provider_chain, str):
            provider_chain = [provider_chain]
        elif not isinstance(provider_chain, list):
            provider_chain = []
        details: dict[str, Any] = {
            "summary_path": summary_path,
            "summary_name": Path(summary_path).name if summary_path else None,
            "summary_markdown_path": summary_markdown_path,
            "summary_markdown_name": Path(summary_markdown_path).name
            if summary_markdown_path
            else None,
            "outline_path": outline_path,
            "outline_name": Path(outline_path).name if outline_path else None,
            "timeline_seed_path": timeline_seed_path,
            "timeline_seed_name": Path(timeline_seed_path).name if timeline_seed_path else None,
            "entity_hint_path": entity_hint_path,
            "entity_hint_name": Path(entity_hint_path).name if entity_hint_path else None,
            "words": meta_payload.get("summary_words"),
            "token_usage": as_dict(meta_payload.get("token_usage")) or None,
            "sha256": meta_payload.get("summary_sha256"),
            "case_brief_path": case_brief_path,
            "case_brief_name": Path(case_brief_path).name if case_brief_path else None,
            "provider_chain": provider_chain,
        }
        guardian_meta = (
            meta_payload.get("guardian_last_review") if isinstance(meta_payload, dict) else None
        )
        if isinstance(guardian_meta, dict):
            details["guardian"] = guardian_meta
            details["guardian_status"] = guardian_meta.get("status")
            details["guardian_reviewed_at"] = guardian_meta.get("reviewed_at")
            details["guardian_notes"] = guardian_meta.get("notes")
            details["guardian_violations"] = guardian_meta.get("violations")
        meta_by_job[str(job_id)] = details

    existing_ids = {str(item.get("job_id")) for item in artifacts}

    for artifact in artifacts:
        job_id = str(artifact.get("job_id") or "")
        details = meta_by_job.get(job_id)
        if not details:
            continue
        artifact.setdefault("details", {}).update(details)
        artifact_meta = as_dict(artifact.get("metadata"))
        if isinstance(artifact_meta, dict) and "guardian" in artifact_meta:
            guardian_payload = artifact_meta.get("guardian_last_review") or artifact_meta.get(
                "guardian"
            )
            if isinstance(guardian_payload, dict):
                artifact_details = artifact.setdefault("details", {})
                artifact_details.setdefault("guardian", guardian_payload)
                artifact_details.setdefault("guardian_status", guardian_payload.get("status"))
                artifact_details.setdefault(
                    "guardian_reviewed_at", guardian_payload.get("reviewed_at")
                )
                artifact_details.setdefault("guardian_notes", guardian_payload.get("notes"))
                artifact_details.setdefault(
                    "guardian_violations", guardian_payload.get("violations")
                )

    for job_id, details in meta_by_job.items():
        if job_id in existing_ids:
            continue
        job = next((j for j in jobs if str(getattr(j, "id", "")) == job_id), None)
        created_at = getattr(job, "finished_at", None) or getattr(job, "created_at", None)
        artifacts.append(
            {
                "id": None,
                "job_id": job_id,
                "title": f"Summary {job_id}",
                "created_at": created_at,
                "download_url": None,
                "filename": Path(details["summary_path"]).name
                if details.get("summary_path")
                else None,
                "metadata": {},
                "source": None,
                "details": details,
                "synthetic": True,
            }
        )

    artifacts.sort(
        key=lambda item: item.get("created_at") or datetime.min,
        reverse=True,
    )
    return artifacts


def enrich_timeline_artifacts(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for artifact in artifacts:
        meta = as_dict(artifact.get("metadata"))
        seed_path = meta.get("seed_source")
        if seed_path:
            artifact.setdefault("details", {})["seed_source"] = seed_path
        guardian_meta = meta.get("guardian_last_review") or meta.get("guardian")
        if isinstance(guardian_meta, dict):
            details = artifact.setdefault("details", {})
            details["guardian"] = guardian_meta
            details["guardian_status"] = guardian_meta.get("status")
            details["guardian_reviewed_at"] = guardian_meta.get("reviewed_at")
            details["guardian_notes"] = guardian_meta.get("notes")
            details["guardian_violations"] = guardian_meta.get("violations")
    return artifacts


__all__ = ["enrich_summary_artifacts", "enrich_timeline_artifacts"]
