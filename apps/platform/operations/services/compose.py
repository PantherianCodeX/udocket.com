from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
import json
import logging

from packages.udocket_core.agents import ComposeAgent, ComposeConfig
from packages.udocket_core.llm.config import LLMSettings, load_llm_settings
from apps.platform.jobs.models import Job
from apps.platform.artifacts.models import CaseArtifact
from apps.platform.operations.llm import (
    ensure_default_llm_configuration,
    get_llm_configuration,
    get_provider_secret_with_metadata,
)
from apps.platform.operations.runtime import JobRuntimeContext
from apps.platform.operations.utils import read_job_meta, update_job_meta
from apps.platform.jobs.utils import unique_title

from .analysis import (
    case_intake_payload,
    case_paths,
    collect_requested_providers,
)
from .files import sha256_file

log = logging.getLogger("apps.platform.operations.compose_service")


def _resolve_path(value: Optional[str], case_dir: Path) -> Optional[Path]:
    if not value:
        return None
    path_obj = Path(value)
    if path_obj.is_absolute():
        return path_obj if path_obj.exists() else None
    candidate = case_dir / value
    return candidate if candidate.exists() else None


def _summary_search_dirs(
    *,
    analysis_dir: Path,
    summary_job_case_dir: Path,
) -> List[Path]:
    dirs: List[Path] = []
    for directory in (analysis_dir, summary_job_case_dir / "analysis"):
        if directory.exists() and directory not in dirs:
            dirs.append(directory)
    return dirs


def _find_fallback_file(
    *,
    stem: str,
    extension: str,
    search_dirs: Sequence[Path],
    summary_job_id: str,
) -> Optional[Path]:
    for directory in search_dirs:
        candidate = directory / f"{summary_job_id}__{stem}.{extension}"
        if candidate.exists():
            return candidate
    return None


def execute_compose_job(
    *,
    runtime: JobRuntimeContext,
    compose_config: ComposeConfig,
    job: Job,
    summary_job: Job,
    case_id: str,
    llm_config_id: Optional[str],
) -> Dict[str, Any]:
    org_value = job.organization_id or job.case.organization_id
    org_id: Optional[str] = str(org_value) if org_value else None
    case_dir, _, _ = case_paths(case_id, org_id)

    summary_meta = read_job_meta(case_id, org_id, str(summary_job.id))
    summary_json_path = summary_meta.get("summary_file") or summary_meta.get("summary_json_file")
    summary_markdown_path = summary_meta.get("summary_markdown_file") or summary_meta.get("summary_markdown")
    timeline_seed_path = summary_meta.get("summary_timeline_file")
    entity_hint_path = summary_meta.get("summary_entity_file")
    staff_report_path = summary_meta.get("summary_case_brief_file") or summary_meta.get("summary_staff_report_file")
    transcript_path = summary_meta.get("source_transcript_path") or summary_job.transcript_path

    summary_json_path = _resolve_path(summary_json_path, case_dir)
    summary_markdown_path = _resolve_path(summary_markdown_path, case_dir)
    timeline_seed_path = _resolve_path(timeline_seed_path, case_dir)
    entity_hint_path = _resolve_path(entity_hint_path, case_dir)
    staff_report_path = _resolve_path(staff_report_path, case_dir)
    transcript_path = _resolve_path(transcript_path, case_dir)

    analysis_dir = case_dir / "analysis"
    summary_org_value = summary_job.organization_id or summary_job.case.organization_id
    search_dirs = _summary_search_dirs(
        analysis_dir=analysis_dir,
        summary_job_case_dir=case_paths(case_id, str(summary_org_value) if summary_org_value else None)[0],
    )

    def _lookup_or_fallback(current: Optional[Path], stem: str, ext: str) -> Optional[Path]:
        if current and current.exists():
            return current
        return _find_fallback_file(stem=stem, extension=ext, search_dirs=search_dirs, summary_job_id=str(summary_job.id))

    summary_json_path = _lookup_or_fallback(summary_json_path, "summary_v1", "json")
    summary_markdown_path = _lookup_or_fallback(summary_markdown_path, "summary_v1", "md")
    timeline_seed_path = _lookup_or_fallback(timeline_seed_path, "timeline_seeds_v1", "json")
    entity_hint_path = _lookup_or_fallback(entity_hint_path, "entity_hints_v1", "json")
    staff_report_path = _lookup_or_fallback(staff_report_path, "case_brief_v1", "md")

    if summary_json_path is None or not summary_json_path.exists():
        if summary_markdown_path and summary_markdown_path.exists():
            placeholder = analysis_dir / f"{summary_job.id}__summary_fallback_v1.json"
            placeholder.write_text(
                json.dumps({"markdown": summary_markdown_path.read_text(encoding="utf-8")}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            summary_json_path = placeholder
        else:
            placeholder = analysis_dir / f"{summary_job.id}__summary_autogen_v1.json"
            placeholder.write_text(json.dumps({"sections": []}, ensure_ascii=False, indent=2), encoding="utf-8")
            summary_json_path = placeholder

    if summary_markdown_path is None or not summary_markdown_path.exists():
        fallback_md = analysis_dir / f"{summary_job.id}__summary_autogen_v1.md"
        fallback_md.write_text("# Summary\n\nNo summary available.\n", encoding="utf-8")
        summary_markdown_path = fallback_md

    compose_started_meta = {
        "compose_status": "running",
        "summary_job_id": str(summary_job.id),
        "summary_json": str(summary_json_path) if summary_json_path else None,
        "summary_markdown": str(summary_markdown_path) if summary_markdown_path else None,
    }
    runtime.start(
        status=Job.Status.RUNNING,
        log_message="Worker started compose pipeline",
        event="job.started",
        meta_updates=compose_started_meta,
    )

    llm_settings: LLMSettings = load_llm_settings()
    organization_id_str = str(job.organization_id or summary_job.organization_id or "")

    def _config_dict(payload: Any) -> Optional[Dict[str, Any]]:
        if isinstance(payload, dict):
            typed_dict: Dict[str, Any] = {str(key): value for key, value in payload.items()}
            return typed_dict
        return None

    active_config: Dict[str, Any] = {}
    if llm_config_id:
        candidate = _config_dict(
            get_llm_configuration(
                organization_id=organization_id_str,
                config_id=llm_config_id,
                target="compose",
            )
        )
        if candidate:
            active_config = candidate
    if not active_config:
        candidate = _config_dict(
            get_llm_configuration(
                organization_id=organization_id_str,
                config_id=None,
                target="compose",
            )
        )
        if candidate:
            active_config = candidate
    if not active_config:
        candidate = _config_dict(
            ensure_default_llm_configuration(
                organization_id=organization_id_str,
                target="compose",
                llm_settings=llm_settings,
            )
        )
        if candidate:
            active_config = candidate

    stage_map: Dict[str, Dict[str, Any]] = {}
    raw_stage_map = active_config.get("stage_map", {})
    if isinstance(raw_stage_map, dict):
        for key, value in raw_stage_map.items():
            if isinstance(key, str) and isinstance(value, dict):
                stage_map[key] = {str(inner_key): inner_value for inner_key, inner_value in value.items()}

    provider_chain_values: List[str] = []
    raw_chain = active_config.get("provider_chain")
    if isinstance(raw_chain, (list, tuple)):
        for entry in raw_chain:
            if isinstance(entry, str):
                provider_chain_values.append(entry)
    if not provider_chain_values:
        provider_chain_values = list(compose_config.provider_chain)
    provider_chain = provider_chain_values

    provider_credentials: Dict[str, Dict[str, Any]] = {}
    if organization_id_str:
        requested_providers = collect_requested_providers(list(compose_config.provider_chain), provider_chain, stage_map)

        for provider in requested_providers:
            secret_payload = get_provider_secret_with_metadata(organization_id_str, provider)
            if secret_payload:
                provider_credentials[provider] = secret_payload

    try:
        intake_raw = summary_meta.get("intake") if isinstance(summary_meta.get("intake"), dict) else None
        intake_payload = (
            {str(key): value for key, value in intake_raw.items()} if isinstance(intake_raw, dict) else None
        )
        if not intake_payload:
            intake_payload = case_intake_payload(job.case)

        case_metadata: Dict[str, Any] = {
            "case_id": case_id,
            "case_title": job.case.title,
            "compose_job_id": str(job.id),
            "summary_job_id": str(summary_job.id),
            "job_display_title": getattr(job, "display_title", "") or "",
        }
        case_organization = getattr(job.case, "organization", None)
        if case_organization is not None:
            case_metadata["organization_id"] = str(job.case.organization_id)
            org_name = getattr(case_organization, "name", None)
            if isinstance(org_name, str) and org_name:
                case_metadata["organization_name"] = org_name
        if summary_markdown_path:
            case_metadata["summary_markdown_file"] = summary_markdown_path.name
        if summary_json_path:
            case_metadata["summary_json_file"] = summary_json_path.name

        compose_agent = ComposeAgent(compose_config)

        def _progress(stage: str, stage_event: str, details: Dict[str, Any]) -> None:
            runtime.emit(
                "compose.progress",
                stage=stage,
                stage_event=stage_event,
                summary_job_id=str(summary_job.id),
                details=details,
            )

        result = compose_agent.compose(
            case_id=case_id,
            case_dir=case_dir,
            job_id=str(job.id),
            summary_json_path=summary_json_path,
            summary_markdown_path=summary_markdown_path,
            transcript_path=transcript_path,
            timeline_seed_path=timeline_seed_path,
            entity_hint_path=entity_hint_path,
            staff_report_path=staff_report_path,
            intake=intake_payload,
            case_metadata=case_metadata,
            provider_chain=provider_chain,
            stage_map=stage_map,
            provider_credentials=provider_credentials,
            progress_callback=_progress,
        )
    except Exception as exc:  # noqa: BLE001
        error_message = str(exc)
        runtime.fail(
            error=error_message,
            log_message=f"Compose failed: {error_message}",
            meta_updates={"compose_status": "failed", "compose_error": error_message},
            events=[("compose.failed", {"summary_job_id": str(summary_job.id)})],
        )
        raise

    artifacts = result.artifacts

    meta_updates: Dict[str, Any] = {
        "compose_status": "completed",
        "compose_meta_json": str(result.meta_json),
        "compose_provider_chain": result.provider_chain,
        "compose_stage_usage": result.stage_usage,
        "summary_job_id": str(summary_job.id),
    }
    if artifacts.timeline_file:
        meta_updates["timeline_v2_file"] = str(artifacts.timeline_file)
    if artifacts.graph_file:
        meta_updates["graph_v2_file"] = str(artifacts.graph_file)
    if artifacts.entities_file:
        meta_updates["entities_v2_file"] = str(artifacts.entities_file)
    if artifacts.timeline_summary:
        meta_updates["compose_timeline_summary"] = str(artifacts.timeline_summary)
    if artifacts.entity_brief:
        meta_updates["compose_entity_brief"] = str(artifacts.entity_brief)
    if artifacts.graph_visual:
        meta_updates["compose_graph_visual"] = str(artifacts.graph_visual)
    if artifacts.client_markdown:
        meta_updates["compose_client_markdown"] = str(artifacts.client_markdown)
    if artifacts.lawyer_markdown:
        meta_updates["compose_lawyer_markdown"] = str(artifacts.lawyer_markdown)
    if artifacts.client_docx:
        meta_updates["compose_client_docx"] = str(artifacts.client_docx)
    if artifacts.lawyer_docx:
        meta_updates["compose_lawyer_docx"] = str(artifacts.lawyer_docx)

    update_job_meta(case_id, org_id, str(job.id), meta_updates)

    created_titles = {
        kind: set(
            CaseArtifact.objects.filter(case_id=case_id, type=kind).values_list("title", flat=True)
        )
        for kind in ("COMPOSE", "TIMELINE", "GRAPH", "ENTITIES")
    }

    def _create_artifact(
        *,
        kind: str,
        path: Optional[Path],
        title_hint: str,
        metadata: Dict[str, Any],
        schema_version: str = "v1",
    ) -> None:
        if path is None or not path.exists():
            return
        checksum = sha256_file(path)
        titles = created_titles.setdefault(kind, set())
        title = unique_title(title_hint, titles)
        titles.add(title)
        CaseArtifact.objects.create(
            case_id=case_id,
            case_fk=job.case,
            organization=job.organization or summary_job.organization,
            job_id=str(job.id),
            type=kind,
            title=title,
            path=str(path),
            checksum=checksum or "",
            schema_version=schema_version,
            metadata=metadata,
        )

    summary_source = Path(summary_markdown_path) if summary_markdown_path else None
    summary_source_name = summary_source.name if summary_source else None

    _create_artifact(
        kind="COMPOSE",
        path=artifacts.client_markdown,
        title_hint="Client deliverable",
        metadata={"format": "markdown", "source_summary": summary_source_name},
    )
    _create_artifact(
        kind="COMPOSE",
        path=artifacts.client_docx,
        title_hint="Client deliverable (DOCX)",
        metadata={"format": "docx", "source_summary": summary_source_name},
    )
    _create_artifact(
        kind="COMPOSE",
        path=artifacts.lawyer_markdown,
        title_hint="Lawyer deliverable",
        metadata={"format": "markdown", "source_summary": summary_source_name},
    )
    _create_artifact(
        kind="COMPOSE",
        path=artifacts.lawyer_docx,
        title_hint="Lawyer deliverable (DOCX)",
        metadata={"format": "docx", "source_summary": summary_source_name},
    )
    _create_artifact(
        kind="COMPOSE",
        path=artifacts.timeline_summary,
        title_hint="Timeline narrative",
        metadata={"format": "markdown", "source_summary": summary_source_name},
    )
    _create_artifact(
        kind="COMPOSE",
        path=artifacts.entity_brief,
        title_hint="Entity briefing",
        metadata={"format": "markdown", "source_summary": summary_source_name},
    )
    _create_artifact(
        kind="COMPOSE",
        path=artifacts.graph_visual,
        title_hint="Graph visual embed",
        metadata={"format": "json", "source_summary": summary_source_name},
    )
    _create_artifact(
        kind="TIMELINE",
        path=artifacts.timeline_file,
        title_hint="Timeline",
        metadata={"source_summary": summary_source_name, "schema": "v2"},
        schema_version="v2",
    )
    _create_artifact(
        kind="GRAPH",
        path=artifacts.graph_file,
        title_hint="Relationship graph",
        metadata={"source_summary": summary_source_name, "schema": "v2"},
        schema_version="v2",
    )
    _create_artifact(
        kind="ENTITIES",
        path=artifacts.entities_file,
        title_hint="Entities",
        metadata={"source_summary": summary_source_name, "schema": "v2"},
        schema_version="v2",
    )

    finished_ts = runtime.succeed(
        log_message="Compose pipeline completed",
        meta_updates={"compose_status": "completed"},
        events=[("compose.completed", {"summary_job_id": str(summary_job.id)})],
        job_updates={"agent_type": "compose", "display_title": "Compose"},
    )
    update_job_meta(
        case_id,
        org_id,
        str(job.id),
        {
            "compose_completed_at": finished_ts.isoformat(),
            "celery_task_finished_at": finished_ts.isoformat(),
            "celery_task_status": "succeeded",
        },
    )

    return {
        "status": "ok",
        "timeline_file": str(artifacts.timeline_file) if artifacts.timeline_file else None,
        "graph_file": str(artifacts.graph_file) if artifacts.graph_file else None,
        "client_markdown": str(artifacts.client_markdown) if artifacts.client_markdown else None,
        "lawyer_markdown": str(artifacts.lawyer_markdown) if artifacts.lawyer_markdown else None,
    }
