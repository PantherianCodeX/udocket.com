from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..common import as_dict


def _normalize_path(value: Any) -> Optional[str]:
    if isinstance(value, str) and value.strip():
        return value
    return None


def enrich_summary_artifacts(
    artifacts: List[Dict[str, Any]],
    jobs: List[Any],
    telemetry_map: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Merge summarize job metadata (outline/seeds/entities) into artifact payloads."""

    meta_by_job: Dict[str, Dict[str, Any]] = {}
    for job in jobs:
        job_id = getattr(job, "id", None)
        if job_id is None:
            continue
        telem = telemetry_map.get(str(job_id)) or {}
        meta_payload = as_dict(telem.get("metadata"))
        summary_path = _normalize_path(meta_payload.get("summary_file"))
        if not summary_path:
            continue
        outline_path = _normalize_path(meta_payload.get("summary_outline_file"))
        timeline_seed_path = _normalize_path(meta_payload.get("summary_timeline_file"))
        entity_hint_path = _normalize_path(meta_payload.get("summary_entity_file"))
        case_brief_path = _normalize_path(
            meta_payload.get("summary_case_brief_file") or meta_payload.get("case_brief_file")
        )
        provider_chain = meta_payload.get("summary_provider_chain") or meta_payload.get("provider_chain") or []
        if isinstance(provider_chain, str):
            provider_chain = [provider_chain]
        elif not isinstance(provider_chain, list):
            provider_chain = []
        details: Dict[str, Any] = {
            "summary_path": summary_path,
            "summary_name": Path(summary_path).name if summary_path else None,
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
        meta_by_job[str(job_id)] = details

    existing_ids = {str(item.get("job_id")) for item in artifacts}

    for artifact in artifacts:
        job_id = str(artifact.get("job_id") or "")
        details = meta_by_job.get(job_id)
        if not details:
            continue
        artifact.setdefault("details", {}).update(details)

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
                "filename": Path(details["summary_path"]).name if details.get("summary_path") else None,
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


def enrich_timeline_artifacts(artifacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for artifact in artifacts:
        meta = as_dict(artifact.get("metadata"))
        seed_path = meta.get("seed_source")
        if seed_path:
            artifact.setdefault("details", {})["seed_source"] = seed_path
    return artifacts


__all__ = ["enrich_summary_artifacts", "enrich_timeline_artifacts"]
