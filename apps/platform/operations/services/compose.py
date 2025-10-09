# pyright: strict

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from packages.udocket_core.agents import ComposeAgent, ComposeConfig
from packages.udocket_core.llm.config import LLMSettings, load_llm_settings
from apps.platform.jobs.models import Job
from apps.platform.artifacts.models import CaseArtifact
from apps.platform.accounts.models import Organization
from apps.platform.operations.llm import (
    LLMConfigurationPayload,
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
from packages.udocket_core.json_utils import (
    JSONValue,
    coerce_json_object,
    coerce_str,
    coerce_str_list,
    normalize_json_object,
    write_json_object,
)
from packages.udocket_core.logging.context import LogContext

log = logging.getLogger("apps.platform.operations.compose_service")


def _resolve_path(value: str | None, case_dir: Path) -> Path | None:
    if not value:
        return None
    path_obj = Path(value)
    if path_obj.is_absolute():
        return path_obj if path_obj.exists() else None
    candidate = case_dir / value
    return candidate if candidate.exists() else None


def _coerce_any_mapping(value: object) -> dict[str, Any] | None:
    if isinstance(value, Mapping):
        normalized = coerce_json_object(cast(Mapping[object, object], value))
        return {key: cast(Any, item) for key, item in normalized.items()}
    return None


def _summary_search_dirs(
    *,
    analysis_dir: Path,
    summary_job_case_dir: Path,
) -> list[Path]:
    dirs: list[Path] = []
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
) -> Path | None:
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
    llm_config_id: str | None,
) -> dict[str, Any]:
    job_case = getattr(job, "case", None)
    org_value = cast(UUID | None, getattr(job, "organization_id", None))
    if org_value is None and job_case is not None:
        org_value = cast(UUID | None, getattr(job_case, "organization_id", None))
    if org_value is None:
        raise ValueError("Compose job requires an organization id")
    org_id = str(org_value)
    case_dir, _, _ = case_paths(case_id, org_id)
    job_context = LogContext.from_defaults(
        component="compose.service",
        case_id=case_id,
        job_id=str(job.id),
        organization_id=org_id,
        summary_job_id=str(summary_job.id),
    )
    log.info(
        "Compose service starting",
        extra=job_context.extra(event="compose.service.start"),
    )

    summary_meta = read_job_meta(case_id, org_id, str(summary_job.id))

    def _meta_path(*keys: str) -> Path | None:
        for key in keys:
            raw_value = coerce_str(summary_meta.get(key))
            if raw_value:
                resolved = _resolve_path(raw_value, case_dir)
                if resolved:
                    return resolved
        return None

    summary_json_path = _meta_path("summary_file", "summary_json_file")
    summary_markdown_path = _meta_path("summary_markdown_file", "summary_markdown")
    timeline_seed_path = _meta_path("summary_timeline_file")
    entity_hint_path = _meta_path("summary_entity_file")
    staff_report_path = _meta_path("summary_case_brief_file", "summary_staff_report_file")

    transcript_raw = coerce_str(summary_meta.get("source_transcript_path"))
    transcript_raw = transcript_raw or coerce_str(getattr(summary_job, "transcript_path", None))
    transcript_path = _resolve_path(transcript_raw, case_dir)

    analysis_dir = case_dir / "analysis"
    summary_case = getattr(summary_job, "case", None)
    summary_org_value = cast(UUID | None, getattr(summary_job, "organization_id", None))
    if summary_org_value is None and summary_case is not None:
        summary_org_value = cast(UUID | None, getattr(summary_case, "organization_id", None))
    if summary_org_value is None:
        summary_org_str = org_id
    else:
        summary_org_str = str(summary_org_value)
    search_dirs = _summary_search_dirs(
        analysis_dir=analysis_dir,
        summary_job_case_dir=case_paths(case_id, summary_org_str)[0],
    )

    def _lookup_or_fallback(current: Path | None, stem: str, ext: str) -> Path | None:
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
            placeholder.parent.mkdir(parents=True, exist_ok=True)
            write_json_object(
                placeholder,
                {
                    "markdown": summary_markdown_path.read_text(encoding="utf-8"),
                },
            )
            summary_json_path = placeholder
        else:
            placeholder = analysis_dir / f"{summary_job.id}__summary_autogen_v1.json"
            placeholder.parent.mkdir(parents=True, exist_ok=True)
            write_json_object(placeholder, {"sections": []})
            summary_json_path = placeholder

    if summary_markdown_path is None or not summary_markdown_path.exists():
        fallback_md = analysis_dir / f"{summary_job.id}__summary_autogen_v1.md"
        fallback_md.write_text("# Summary\n\nNo summary available.\n", encoding="utf-8")
        summary_markdown_path = fallback_md

    compose_started_meta = normalize_json_object(
        {
            "compose_status": "running",
            "summary_job_id": str(summary_job.id),
            "summary_json": str(summary_json_path) if summary_json_path else None,
            "summary_markdown": str(summary_markdown_path) if summary_markdown_path else None,
        },
        drop_empty_keys=True,
        drop_nullish_values=True,
    )
    runtime.start(
        status=Job.Status.RUNNING,
        log_message="Worker started compose pipeline",
        event="job.started",
        meta_updates=compose_started_meta,
    )

    llm_settings: LLMSettings = load_llm_settings()
    organization_id_str = org_id or summary_org_str

    active_config: dict[str, Any] = {}

    def _assign_config(payload: LLMConfigurationPayload | None) -> bool:
        nonlocal active_config
        if payload is None:
            return False
        active_config = dict(payload)
        return True

    if llm_config_id:
        if _assign_config(
            get_llm_configuration(
                organization_id=organization_id_str,
                config_id=llm_config_id,
                target="compose",
            )
        ):
            pass
    if not active_config:
        _assign_config(
            get_llm_configuration(
                organization_id=organization_id_str,
                config_id=None,
                target="compose",
            )
        )
    if not active_config:
        _assign_config(
            ensure_default_llm_configuration(
                organization_id=organization_id_str,
                target="compose",
                llm_settings=llm_settings,
            )
        )

    stage_map: dict[str, dict[str, Any]] = {}
    raw_stage_map = _coerce_any_mapping(active_config.get("stage_map"))
    if raw_stage_map:
        for key, value in raw_stage_map.items():
            nested = _coerce_any_mapping(value)
            if nested is not None:
                stage_map[key] = nested

    provider_chain_values = coerce_str_list(active_config.get("provider_chain"), unique=False)
    if not provider_chain_values:
        provider_chain_values = list(compose_config.provider_chain)
    provider_chain = provider_chain_values
    log.debug(
        "Compose provider chain resolved",
        extra=job_context.extra(
            event="compose.service.providers",
            provider_chain=provider_chain,
            stage_map=list(stage_map.keys()),
        ),
    )

    provider_credentials: dict[str, dict[str, Any]] = {}
    if organization_id_str:
        requested_providers = collect_requested_providers(list(compose_config.provider_chain), provider_chain, stage_map)

        for provider in requested_providers:
            secret_payload = get_provider_secret_with_metadata(organization_id_str, provider)
            credential = _coerce_any_mapping(secret_payload)
            if credential:
                provider_credentials[provider] = credential
                log.debug(
                    "Loaded compose provider credentials",
                    extra=job_context.extra(
                        event="compose.service.credentials.loaded",
                        provider=provider,
                    ),
                )
            else:
                log.info(
                    "Compose provider credentials missing",
                    extra=job_context.extra(
                        event="compose.service.credentials.missing",
                        provider=provider,
                    ),
                )

    try:
        intake_payload = _coerce_any_mapping(summary_meta.get("intake"))
        if intake_payload is None:
            intake_payload = case_intake_payload(job_case)

        case_metadata: dict[str, Any] = {
            "case_id": case_id,
            "compose_job_id": str(job.id),
            "summary_job_id": str(summary_job.id),
            "job_display_title": str(getattr(job, "display_title", "") or ""),
        }
        case_title = coerce_str(getattr(job_case, "title", None))
        if case_title:
            case_metadata["case_title"] = case_title
        case_org_value = getattr(job_case, "organization_id", None)
        if case_org_value:
            case_metadata["organization_id"] = str(case_org_value)
        case_organization = getattr(job_case, "organization", None)
        if case_organization is not None:
            org_name = coerce_str(getattr(case_organization, "name", None))
            if org_name:
                case_metadata["organization_name"] = org_name
        if summary_markdown_path:
            case_metadata["summary_markdown_file"] = summary_markdown_path.name
        if summary_json_path:
            case_metadata["summary_json_file"] = summary_json_path.name

        compose_agent = ComposeAgent(compose_config)

        def _progress(stage: str, stage_event: str, details: Mapping[str, JSONValue]) -> None:
            runtime.emit(
                "compose.progress",
                stage=stage,
                stage_event=stage_event,
                summary_job_id=str(summary_job.id),
                details={key: cast(Any, value) for key, value in details.items()},
            )

        log.info(
            "Dispatching compose agent",
            extra=job_context.extra(
                event="compose.service.dispatch",
                provider_chain=provider_chain,
                summary_json=str(summary_json_path) if summary_json_path else None,
                summary_markdown=str(summary_markdown_path) if summary_markdown_path else None,
            ),
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
        log.error(
            "Compose agent raised an exception",
            extra=job_context.extra(
                event="compose.service.error",
                error=str(exc),
            ),
        )
        error_message = str(exc)
        runtime.fail(
            error=error_message,
            log_message=f"Compose failed: {error_message}",
            meta_updates={"compose_status": "failed", "compose_error": error_message},
            events=[("compose.failed", {"summary_job_id": str(summary_job.id)})],
        )
        raise

    artifacts = result.artifacts

    meta_updates: dict[str, Any] = {
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
    produced_artifact_count = sum(
        1
        for candidate in (
            artifacts.timeline_file,
            artifacts.graph_file,
            artifacts.entities_file,
            artifacts.timeline_summary,
            artifacts.entity_brief,
            artifacts.graph_visual,
            artifacts.client_markdown,
            artifacts.lawyer_markdown,
            artifacts.client_docx,
            artifacts.lawyer_docx,
        )
        if candidate
    )
    log.info(
        "Compose agent completed successfully",
        extra=job_context.extra(
            event="compose.service.completed",
            provider_chain=result.provider_chain,
            artifact_count=produced_artifact_count,
        ),
    )

    created_titles: dict[str, set[str]] = {
        kind: set(
            CaseArtifact.objects.filter(case_id=case_id, type=kind).values_list("title", flat=True)
        )
        for kind in ("COMPOSE", "TIMELINE", "GRAPH", "ENTITIES")
    }

    def _create_artifact(
        *,
        kind: str,
        path: Path | None,
        title_hint: str,
        metadata: dict[str, Any],
        schema_version: str = "v1",
    ) -> None:
        if path is None or not path.exists() or job_case is None:
            return
        checksum = sha256_file(path)
        titles = created_titles.setdefault(kind, set())
        title = unique_title(title_hint, titles)
        titles.add(title)
        organization_obj = getattr(job, "organization", None)
        if not isinstance(organization_obj, Organization):
            log.warning(
                "compose: organization missing on job; artifact creation skipped",
                extra={"job_id": str(job.id)},
            )
            return
        CaseArtifact.objects.create(
            case_id=case_id,
            case_fk=job_case,
            organization=organization_obj,
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
