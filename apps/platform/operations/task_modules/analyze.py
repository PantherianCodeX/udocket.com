from __future__ import annotations

# pyright: strict
import logging
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol, cast

from celery import shared_task


class TaskProtocol(Protocol):
    request: Any


from apps.platform.artifacts.models import CaseArtifact
from apps.platform.jobs.models import Job
from apps.platform.operations.audit import emit as _audit_emit
from apps.platform.operations.channels import send_case_update as _send_case_update
from apps.platform.operations.llm import (
    LLMConfigurationPayload,
)
from apps.platform.operations.llm import (
    ensure_default_llm_configuration as _ensure_default_llm_configuration,
)
from apps.platform.operations.llm import (
    get_llm_configuration as _get_llm_configuration,
)
from apps.platform.operations.llm import (
    get_provider_secret_with_metadata as _get_provider_secret_with_metadata,
)
from apps.platform.operations.runtime import JobRuntimeContext, safe_job_meta
from apps.platform.operations.services import (
    case_intake_payload,
    case_paths,
    latest_transcript,
)
from apps.platform.operations.services import (
    collect_requested_providers as _collect_requested_providers,
)
from apps.platform.operations.services.files import sha256_file
from apps.platform.operations.utils import read_job_meta
from packages.udocket_common.json_utils import JSONObject, coerce_json_object, read_json_object
from packages.udocket_common.operations import ComposeStageMap, optional_json_object
from packages.udocket_common.text import unique_title
from packages.udocket_core.agents import AnalyzeAgent as _AnalyzeAgent
from packages.udocket_core.agents import AnalyzeConfig
from packages.udocket_core.llm.config import load_llm_settings as _load_llm_settings

log = logging.getLogger("apps.platform.operations.tasks.analyze")


def _load_json_dict(path: Path) -> JSONObject:
    return coerce_json_object(read_json_object(path))


@shared_task(bind=True)
def analyze_job(
    self: TaskProtocol,
    *_args: object,
    case_id: str,
    job_id: str,
    llm_config_id: str | None = None,
    source_job_id: str | None = None,
) -> dict[str, object]:
    case_id = str(case_id)
    job_id = str(job_id)
    source_job_id = str(source_job_id) if source_job_id else None

    job = Job.typed_objects().select_related("case", "case__organization").get(pk=job_id)
    source_job = job
    if source_job_id and source_job_id != job_id:
        try:
            source_job = (
                Job.typed_objects()
                .select_related("case", "case__organization")
                .get(pk=source_job_id)
            )
        except Job.DoesNotExist:
            source_job = job
    org_value = job.organization_id or getattr(job.case, "organization_id", None)
    org_id = str(org_value) if org_value else None
    case_dir, _, _ = case_paths(case_id, org_id)
    existing_meta = read_job_meta(case_id, org_id, job_id)
    existing_summary_titles = [
        title
        for title in CaseArtifact.typed_objects()
        .filter(case_id=case_id, type="SUMMARY")
        .values_list("title", flat=True)
        if isinstance(title, str) and title
    ]
    summary_title = str(existing_meta.get("job_title") or "").strip()
    if not summary_title or summary_title in existing_summary_titles:
        summary_title = unique_title("Summary", existing_summary_titles)
    transcript = (
        Path(source_job.transcript_path)
        if source_job.transcript_path
        else latest_transcript(case_id, org_id)
    )
    transcript_path_str = str(transcript) if transcript else None

    base_meta: dict[str, object] = {
        "job_kind": "analyze",
        "agent_type": "analyze",
        "job_title": summary_title,
        "source_job_id": str(source_job.id),
        "source_transcript_path": transcript_path_str,
    }
    if llm_config_id:
        base_meta["requested_llm_config_id"] = llm_config_id

    runtime = JobRuntimeContext(
        job=job,
        case_id=case_id,
        org_id=org_id,
        task_name="analyze_job",
        task_id=getattr(self.request, "id", None) or "",
        task_meta={
            "requested_llm_config_id": llm_config_id,
            "source_job_id": str(source_job.id),
        },
    )
    summary_start_meta = {**base_meta, "summary_status": "running"}
    summary_task_id = runtime.task_id or None
    if summary_task_id:
        history: list[str] = []
        history_payload = existing_meta.get("celery_task_history")
        if isinstance(history_payload, list):
            for raw_item in cast(list[object], history_payload):
                if isinstance(raw_item, str):
                    cleaned_item = raw_item.strip()
                    if cleaned_item:
                        history.append(cleaned_item)
        else:
            previous_id = existing_meta.get("celery_task_id")
            if isinstance(previous_id, str) and previous_id:
                history.append(previous_id)
        if summary_task_id not in history:
            history.append(summary_task_id)
        summary_start_meta["celery_task_id"] = summary_task_id
        summary_start_meta["celery_task_status"] = "running"
        if history:
            summary_start_meta["celery_task_history"] = history
        if runtime.task_name:
            summary_start_meta.setdefault("celery_task_name", runtime.task_name)

    summary_started_at = runtime.start(
        status=Job.Status.RUNNING,
        log_message="Worker started analyze pipeline",
        event="job.started",
        meta_updates=summary_start_meta,
    )

    if summary_task_id and summary_started_at:
        safe_job_meta(
            case_id,
            org_id,
            job_id,
            {"celery_task_started_at": summary_started_at.isoformat()},
        )

    if not transcript or not transcript.exists():
        failure_meta = {
            **base_meta,
            "summary_status": "failed",
            "summary_error": "transcript_missing",
        }
        if summary_task_id:
            failure_meta.setdefault("celery_task_id", summary_task_id)
            failure_meta["celery_task_status"] = "failed"
        failure_ts = runtime.fail(
            error="No transcript found to analyze",
            log_message="Analyze failed: transcript missing",
            meta_updates=failure_meta,
            events=[("analyze.failed", {})],
            task_meta_updates={"stage": "preflight", "reason": "missing_transcript"},
        )
        safe_job_meta(
            case_id,
            org_id,
            job_id,
            {
                "summary_completed_at": failure_ts.isoformat(),
                "celery_task_finished_at": failure_ts.isoformat(),
                "celery_task_status": "failed" if summary_task_id else None,
            },
        )
        raise RuntimeError("No transcript found to analyze")

    try:
        analyze_config = AnalyzeConfig.from_env()
    except ValueError as exc:
        log.error(
            "analyze config invalid",
            extra={"job_id": job_id, "case_id": case_id, "reason": str(exc)},
        )
        failure_meta = {**base_meta, "summary_status": "failed", "summary_error": str(exc)}
        if summary_task_id:
            failure_meta.setdefault("celery_task_id", summary_task_id)
            failure_meta["celery_task_status"] = "failed"
        failure_ts = runtime.fail(
            error=str(exc),
            log_message="Analyze configuration invalid",
            meta_updates=failure_meta,
            events=[("analyze.failed", {"llm_config_id": llm_config_id})],
            task_meta_updates={"stage": "config", "reason": str(exc)},
        )
        safe_job_meta(
            case_id,
            org_id,
            job_id,
            {
                "summary_completed_at": failure_ts.isoformat(),
                "celery_task_finished_at": failure_ts.isoformat(),
                "celery_task_status": "failed" if summary_task_id else None,
            },
        )
        raise

    from apps.platform.operations import tasks as tasks_module

    load_llm_settings_fn = getattr(tasks_module, "load_llm_settings", _load_llm_settings)
    get_llm_configuration_fn = getattr(
        tasks_module, "get_llm_configuration", _get_llm_configuration
    )
    ensure_default_llm_configuration_fn = getattr(
        tasks_module,
        "ensure_default_llm_configuration",
        _ensure_default_llm_configuration,
    )
    get_provider_secret_with_metadata_fn = getattr(
        tasks_module,
        "get_provider_secret_with_metadata",
        _get_provider_secret_with_metadata,
    )
    collect_requested_providers_fn = cast(
        Callable[[Sequence[str], Sequence[str], ComposeStageMap | None], list[str]],
        getattr(
            tasks_module,
            "collect_requested_providers",
            _collect_requested_providers,
        ),
    )
    analyze_agent_cls = getattr(tasks_module, "AnalyzeAgent", _AnalyzeAgent)
    send_case_update_fn = getattr(tasks_module, "send_case_update", _send_case_update)
    audit_emit_fn = getattr(tasks_module, "audit_emit", _audit_emit)

    llm_settings = None
    try:
        llm_settings = load_llm_settings_fn()
    except Exception as exc:  # noqa: BLE001
        log.error(
            "load llm settings failed",
            extra={"job_id": job_id, "case_id": case_id, "error": str(exc)},
        )
        failure_meta = {
            **base_meta,
            "summary_status": "failed",
            "summary_error": "llm_settings_unavailable",
        }
        if summary_task_id:
            failure_meta.setdefault("celery_task_id", summary_task_id)
            failure_meta["celery_task_status"] = "failed"
        failure_ts = runtime.fail(
            error="LLM settings unavailable",
            log_message="Analyze failed: LLM settings unavailable",
            meta_updates=failure_meta,
            events=[("analyze.failed", {"llm_config_id": llm_config_id})],
            task_meta_updates={"stage": "config", "reason": "llm_settings_unavailable"},
        )
        safe_job_meta(
            case_id,
            org_id,
            job_id,
            {
                "summary_completed_at": failure_ts.isoformat(),
                "celery_task_finished_at": failure_ts.isoformat(),
                "celery_task_status": "failed" if summary_task_id else None,
            },
        )
        raise

    org_id_str = str(org_id) if org_id else None
    config_payload: LLMConfigurationPayload | None = None
    if org_id_str:
        if llm_config_id:
            config_payload = get_llm_configuration_fn(
                organization_id=org_id_str,
                config_id=llm_config_id,
                target="analyze",
            )
        if not config_payload:
            config_payload = ensure_default_llm_configuration_fn(
                organization_id=org_id_str,
                target="analyze",
                llm_settings=llm_settings,
            )

    if not config_payload:
        log.error(
            "analyze llm configuration missing",
            extra={"job_id": job_id, "case_id": case_id, "llm_config_id": llm_config_id},
        )
        failure_meta = {
            **base_meta,
            "summary_status": "failed",
            "summary_error": "llm_configuration_missing",
        }
        if summary_task_id:
            failure_meta.setdefault("celery_task_id", summary_task_id)
            failure_meta["celery_task_status"] = "failed"
        failure_ts = runtime.fail(
            error="LLM configuration missing",
            log_message="Analyze failed: LLM configuration missing",
            meta_updates=failure_meta,
            events=[("analyze.failed", {"llm_config_id": llm_config_id})],
            task_meta_updates={"stage": "config", "reason": "llm_configuration_missing"},
        )
        safe_job_meta(
            case_id,
            org_id,
            job_id,
            {
                "summary_completed_at": failure_ts.isoformat(),
                "celery_task_finished_at": failure_ts.isoformat(),
                "celery_task_status": "failed" if summary_task_id else None,
            },
        )
        raise RuntimeError("LLM configuration missing for analyze job")

    active_config_id = config_payload["id"] if config_payload and config_payload["id"] else None
    if active_config_id:
        base_meta["active_llm_config_id"] = active_config_id

    stage_map = ComposeStageMap.from_mapping(
        optional_json_object(config_payload.get("stage_map")) if config_payload else None
    )
    provider_chain_override: Sequence[str] = (
        tuple(config_payload["provider_chain"])
        if config_payload and config_payload["provider_chain"]
        else ()
    )
    config_chain = [provider for provider in provider_chain_override]

    requested_providers = collect_requested_providers_fn(
        tuple(analyze_config.provider_chain),
        config_chain,
        stage_map,
    )

    provider_credentials: dict[str, Mapping[str, object]] = {}
    if org_id_str:
        for provider_name in requested_providers:
            secret_payload = get_provider_secret_with_metadata_fn(org_id_str, provider_name)
            if secret_payload:
                provider_credentials[provider_name] = secret_payload

    intake_payload = case_intake_payload(job.case)
    transcript_hint_payload: Mapping[str, object] | None = None
    existing_hint = existing_meta.get("transcript_hint")
    if isinstance(existing_hint, Mapping):
        hint_payload: dict[str, object] = {}
        for key, value in cast(Mapping[object, object], existing_hint).items():
            hint_payload[str(key)] = value
        transcript_hint_payload = hint_payload

    agent = analyze_agent_cls(analyze_config)

    def _sanitize_details(details: Mapping[str, object]) -> dict[str, object]:
        sanitized: dict[str, object] = {}
        for key, value in details.items():
            if isinstance(value, Path):
                sanitized[str(key)] = str(value)
            elif isinstance(value, (str, int, float, bool)) or value is None:
                sanitized[str(key)] = value
            elif isinstance(value, Mapping):
                sanitized[str(key)] = _sanitize_details(cast(Mapping[str, object], value))
            elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
                sequence_items: list[object] = []
                for item in cast(Sequence[object], value):
                    normalized_item: object = str(item) if isinstance(item, Path) else item
                    sequence_items.append(normalized_item)
                sanitized[str(key)] = sequence_items
            else:
                sanitized[str(key)] = str(value)
        return sanitized

    def _progress(stage: str, stage_event: str, details: Mapping[str, object]) -> None:
        sanitized_details = _sanitize_details(details) if details else {}
        runtime.emit(
            "analyze.progress",
            stage=stage,
            stage_event=stage_event,
            details=sanitized_details,
        )

    try:
        result = agent.analyze(
            input=transcript,
            case_id=case_id,
            case_dir=case_dir,
            job_id=str(job.id),
            intake=intake_payload,
            transcript_hint=transcript_hint_payload,
            provider_chain=config_chain or analyze_config.provider_chain,
            stage_map=stage_map.to_dict(),
            provider_credentials=provider_credentials or None,
            progress_callback=_progress,
        )
    except Exception as exc:  # noqa: BLE001
        error_message = str(exc)
        log.exception(
            "analyze agent failed",
            extra={"job_id": job_id, "case_id": case_id, "error": error_message},
        )
        failure_meta = {**base_meta, "summary_status": "failed", "summary_error": error_message}
        if summary_task_id:
            failure_meta.setdefault("celery_task_id", summary_task_id)
            failure_meta["celery_task_status"] = "failed"
        failure_ts = runtime.fail(
            error=error_message,
            log_message=f"Analyze failed: {error_message}",
            meta_updates=failure_meta,
            events=[("analyze.failed", {"llm_config_id": active_config_id or llm_config_id})],
            task_meta_updates={"stage": "agent", "reason": error_message},
        )
        safe_job_meta(
            case_id,
            org_id,
            job_id,
            {
                "summary_completed_at": failure_ts.isoformat(),
                "celery_task_finished_at": failure_ts.isoformat(),
                "celery_task_status": "failed" if summary_task_id else None,
            },
        )
        raise

    summary_sha = sha256_file(result.summary_file)
    summary_markdown_sha = sha256_file(result.summary_markdown_file)
    outline_sha = sha256_file(result.outline_file) if result.outline_file else None
    timeline_sha = sha256_file(result.timeline_seeds_file) if result.timeline_seeds_file else None
    entity_sha = sha256_file(result.entity_hints_file) if result.entity_hints_file else None
    case_brief_sha = sha256_file(result.case_brief_file) if result.case_brief_file else None

    token_usage: dict[str, object] | None = None
    meta_payload = _load_json_dict(result.meta_json)
    usage_payload = meta_payload.get("token_usage")
    if isinstance(usage_payload, Mapping):
        token_usage = {str(key): value for key, value in usage_payload.items()}

    summary_meta_updates: dict[str, object] = {
        **base_meta,
        "summary_status": "completed",
        "summary_file": str(result.summary_file),
        "summary_markdown_file": str(result.summary_markdown_file),
        "summary_outline_file": str(result.outline_file) if result.outline_file else None,
        "summary_timeline_file": str(result.timeline_seeds_file)
        if result.timeline_seeds_file
        else None,
        "summary_entity_file": str(result.entity_hints_file) if result.entity_hints_file else None,
        "summary_case_brief_file": str(result.case_brief_file) if result.case_brief_file else None,
        "summary_meta_json": str(result.meta_json),
        "summary_audit_jsonl": str(result.audit_jsonl),
        "summary_words": result.words,
        "summary_provider_chain": list(result.provider_chain),
        "summary_sha256": summary_sha,
        "summary_markdown_sha256": summary_markdown_sha,
        "summary_outline_sha256": outline_sha,
        "summary_timeline_sha256": timeline_sha,
        "summary_entity_sha256": entity_sha,
        "summary_case_brief_sha256": case_brief_sha,
        "source_transcript_path": transcript_path_str,
    }
    if active_config_id:
        summary_meta_updates["summary_llm_config_id"] = active_config_id
    if token_usage:
        summary_meta_updates["token_usage"] = token_usage
    if summary_task_id:
        summary_meta_updates.setdefault("celery_task_id", summary_task_id)
        summary_meta_updates["celery_task_status"] = "succeeded"

    artifact_metadata: dict[str, object] = {
        "summary_file": str(result.summary_file),
        "summary_markdown_file": str(result.summary_markdown_file),
        "summary_outline_file": str(result.outline_file) if result.outline_file else None,
        "summary_timeline_file": str(result.timeline_seeds_file)
        if result.timeline_seeds_file
        else None,
        "summary_entity_file": str(result.entity_hints_file) if result.entity_hints_file else None,
        "summary_case_brief_file": str(result.case_brief_file) if result.case_brief_file else None,
        "summary_words": result.words,
        "summary_provider_chain": list(result.provider_chain),
        "summary_sha256": summary_sha,
        "summary_markdown_sha256": summary_markdown_sha,
        "summary_outline_sha256": outline_sha,
        "summary_timeline_sha256": timeline_sha,
        "summary_entity_sha256": entity_sha,
        "summary_case_brief_sha256": case_brief_sha,
        "source_transcript_path": transcript_path_str,
        "token_usage": token_usage,
        "summary_meta_json": str(result.meta_json),
    }
    filtered_artifact_metadata: dict[str, object] = {}
    for key, value in artifact_metadata.items():
        if value in (None, "", [], {}):
            continue
        filtered_artifact_metadata[key] = value
    artifact_metadata = filtered_artifact_metadata

    summary_checksum = summary_markdown_sha or ""

    try:
        CaseArtifact.typed_objects().create(
            case_id=str(case_id),
            case_fk=job.case,
            organization=job.organization,
            job_id=str(job.id),
            type="SUMMARY",
            title=summary_title,
            path=str(result.summary_markdown_file),
            checksum=summary_checksum,
            schema_version="v1",
            metadata=artifact_metadata,
        )
    except Exception:
        log.exception(
            "failed to register summary artifact",
            extra={"job_id": job_id, "case_id": case_id, "path": str(result.summary_markdown_file)},
        )

    log_message = f"Analyze succeeded: summary={result.summary_file.name} words={result.words}"
    job_event_payload = {
        "summary_file": str(result.summary_file),
        "summary_markdown_file": str(result.summary_markdown_file),
        "summary_words": result.words,
        "title": summary_title,
    }
    finished_ts = runtime.succeed(
        log_message=log_message,
        meta_updates=summary_meta_updates,
        job_event_payload=job_event_payload,
        events=[
            (
                "analyze.completed",
                {
                    "summary_file": str(result.summary_file),
                    "summary_markdown_file": str(result.summary_markdown_file),
                    "summary_words": result.words,
                },
            )
        ],
        task_meta_updates={"stage": "completed", "summary_words": result.words},
    )

    safe_job_meta(
        case_id,
        org_id,
        job_id,
        {
            "summary_completed_at": finished_ts.isoformat(),
            "celery_task_finished_at": finished_ts.isoformat(),
            "celery_task_status": "succeeded" if summary_task_id else None,
        },
    )

    audit_emit_fn(
        None,
        case_id=case_id,
        event="analysis.summary.completed",
        data={
            "job_id": str(job.id),
            "summary_file": str(result.summary_file),
            "summary_markdown_file": str(result.summary_markdown_file),
            "words": result.words,
            "provider_chain": list(result.provider_chain),
        },
    )

    try:
        send_case_update_fn(
            case_id,
            event="artifact.created",
            kind="summary",
            job_id=str(job.id),
        )
    except Exception:
        log.exception(
            "case artifact update emit failed",
            extra={"case_id": case_id, "job_id": job_id, "event": "artifact.created"},
        )

    return {
        "status": "ok",
        "job_id": str(job.id),
        "case_id": case_id,
        "summary_file": str(result.summary_file),
        "summary_markdown_file": str(result.summary_markdown_file),
        "outline_file": str(result.outline_file) if result.outline_file else None,
        "timeline_file": str(result.timeline_seeds_file) if result.timeline_seeds_file else None,
        "entity_file": str(result.entity_hints_file) if result.entity_hints_file else None,
        "case_brief_file": str(result.case_brief_file) if result.case_brief_file else None,
        "meta_json": str(result.meta_json),
        "audit_jsonl": str(result.audit_jsonl),
        "words": result.words,
        "provider_chain": list(result.provider_chain),
    }
