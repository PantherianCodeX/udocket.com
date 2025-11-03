from __future__ import annotations

# pyright: strict

import asyncio
import logging
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

from packages.udocket_core import __version__ as UDOCKET_CORE_VERSION
from packages.udocket_common.json_utils import (
    JSONArray,
    JSONObject,
    coerce_json_object,
    coerce_object_list,
    coerce_str,
    load_json_object,
    load_json_value,
    write_json_object,
)

from .common import append_jsonl, ensure_dir, sha256_file
from ..llm import LLMSettings, load_llm_settings
from .compose.errors import ComposeStageError
from .compose.guards import factuality_report
from .compose.io import ArtifactWriter
from .compose.llm_profiles import LANE_CONFIGS
from .compose.llm_runtime import invoke_llm
from .compose.logging_utils import ComposeLogContext
from .compose.orchestrator import ComposeOrchestrator, stable_doc_fingerprint
from .compose.prompt_config import ComposePromptConfig, load_prompt_config
from .compose.run import ComposeRun
from .compose.settings import ComposeConfig
from .compose.state import (
    ComposeArtifacts,
    ComposeInputs,
    ComposeResult,
    ComposeState,
    GuardReport,
    LaneActionDirective,
    LaneOutcome,
    LaneRuntimeState,
    lane_history_payload,
)


logger = logging.getLogger("udocket.compose.agent")


QA_REVIEWER_STATUS_OK = {"ok", "pass", "approved"}


def _stable_doc_fingerprint(document: str) -> str:
    return stable_doc_fingerprint(document)


def _factuality_report(
    document: str,
    *,
    claimable_atoms: Sequence[str],
    timeline_events: Sequence[JSONObject],
    min_timestamp_references: int,
) -> GuardReport:
    return factuality_report(
        document,
        claimable_atoms=claimable_atoms,
        timeline_events=timeline_events,
        min_timestamp_references=min_timestamp_references,
    )

class ComposeAgent:
    def __init__(self, config: Optional[ComposeConfig] = None) -> None:
        self.config = config or ComposeConfig.from_env()
        self.settings: LLMSettings = load_llm_settings()
        self.logger = logger
        self.prompts: ComposePromptConfig = load_prompt_config(self.config.prompt_config_path)

    def _new_orchestrator(
        self,
        *,
        compose_run: ComposeRun | None = None,
        log_context: ComposeLogContext | None = None,
    ) -> ComposeOrchestrator:
        return ComposeOrchestrator(
            config=self.config,
            settings=self.settings,
            logger=self.logger,
            qa_ok_status=QA_REVIEWER_STATUS_OK,
            prompts=self.prompts,
            compose_run=compose_run,
            log_context=log_context,
        )

    def _log_context_from_state(self, state: ComposeState) -> ComposeLogContext:
        metadata = state.inputs.case_metadata if state.inputs else {}
        case_id = coerce_str(metadata.get("case_id")) or "unknown"
        job_id = coerce_str(metadata.get("compose_job_id")) or coerce_str(metadata.get("job_id")) or "unknown"
        case_title = coerce_str(metadata.get("case_title")) or None
        job_display_title = coerce_str(metadata.get("job_display_title")) or None
        organization_name = coerce_str(metadata.get("organization_name")) or None
        return ComposeLogContext(
            case_id=case_id,
            job_id=job_id,
            case_title=case_title,
            job_display_title=job_display_title,
            organization_name=organization_name,
        )

    # ------------------------------------------------------------------
    # Backwards-compatible helpers for tests and maintenance scripts

    def _invoke_llm(
        self,
        *,
        stage: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        provider_credentials: Mapping[str, JSONObject],
    ) -> tuple[str, dict[str, int], str, str]:
        return invoke_llm(
            stage=stage,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            provider_credentials=provider_credentials,
            config=self.config,
            settings=self.settings,
        )

    def _qa_reviewer_step(
        self,
        *,
        state: ComposeState,
        provider_credentials: Mapping[str, JSONObject],
        progress: Optional[Callable[[str, str, JSONObject], None]],
    ) -> dict[str, object]:
        orchestrator = self._new_orchestrator(log_context=self._log_context_from_state(state))
        qa_step = getattr(orchestrator, "_qa_reviewer_step")
        return qa_step(
            state=state,
            provider_credentials=provider_credentials,
            progress=progress,
        )

    def _run_lane_editor(
        self,
        *,
        state: ComposeState,
        lane: str,
        directive: LaneActionDirective,
        provider_credentials: Mapping[str, JSONObject],
        progress: Optional[Callable[[str, str, JSONObject], None]],
    ) -> dict[str, object]:
        orchestrator = self._new_orchestrator(log_context=self._log_context_from_state(state))
        editor_step = getattr(orchestrator, "_run_lane_editor")
        return editor_step(
            state=state,
            lane=lane,
            directive=directive,
            provider_credentials=provider_credentials,
            progress=progress,
        )

    def compose(
        self,
        *,
        case_id: str,
        case_dir: Path,
        job_id: str,
        summary_json_path: Optional[Path],
        summary_markdown_path: Optional[Path],
        timeline_seed_path: Optional[Path] = None,
        entity_hint_path: Optional[Path] = None,
        intake: Optional[Mapping[str, Any]] = None,
        case_metadata: Optional[Mapping[str, Any]] = None,
        provider_credentials: Optional[Mapping[str, Mapping[str, Any]]] = None,
        progress_callback: Optional[Callable[[str, str, JSONObject], None]] = None,
        resume: bool = False,
    ) -> ComposeResult:
        case_dir = Path(case_dir)
        docs_dir = case_dir / "docs"
        ops_dir = case_dir / "ops"
        ensure_dir(docs_dir)
        ensure_dir(ops_dir)

        summary_markdown = _read_text(summary_markdown_path)
        summary_data = _read_json(summary_json_path)
        timeline_seeds = _load_sequence(timeline_seed_path)
        entity_hints = _read_json(entity_hint_path)
        inputs = ComposeInputs(
            summary_markdown=summary_markdown,
            summary_data=summary_data,
            timeline_seeds=timeline_seeds,
            entity_hints=entity_hints,
            intake=coerce_json_object(intake) if intake else {},
            case_metadata=coerce_json_object(case_metadata) if case_metadata else {},
        )

        provider_credentials_map: Mapping[str, JSONObject] = {
            name: coerce_json_object(payload)
            for name, payload in (provider_credentials or {}).items()
        }

        collected_events: list[JSONObject] = []

        metadata_payload = inputs.case_metadata
        case_title = coerce_str(metadata_payload.get("case_title"))
        if not case_title:
            case_title = coerce_str(metadata_payload.get("job_display_title"))
        log_context = ComposeLogContext(
            case_id=case_id,
            job_id=job_id,
            case_title=case_title or None,
            job_display_title=coerce_str(metadata_payload.get("job_display_title")) or None,
            organization_name=coerce_str(metadata_payload.get("organization_name")) or None,
        )

        run_tracker = ComposeRun(
            case_id=case_id,
            job_id=job_id,
            snapshot_dir=ops_dir / f"{job_id}__compose_run",
            logger=self.logger,
            log_context=log_context,
        )
        run_context: dict[str, object] = {
            "case_id": case_id,
            "job_id": job_id,
            "summary_json": str(summary_json_path) if summary_json_path else None,
            "summary_markdown": str(summary_markdown_path) if summary_markdown_path else None,
            "resume_requested": resume,
        }
        restored_snapshot = run_tracker.restore_latest() if resume else None
        if restored_snapshot is None:
            run_tracker.reset()
            state = ComposeState(
                inputs=inputs,
                client=LaneRuntimeState(
                    lane="client",
                    config=LANE_CONFIGS["client"],
                    max_attempts=self.config.max_client_attempts,
                ),
                lawyer=LaneRuntimeState(
                    lane="lawyer",
                    config=LANE_CONFIGS["lawyer"],
                    max_attempts=self.config.max_lawyer_attempts,
                ),
            )
        else:
            state = restored_snapshot.state
            state.inputs = inputs
            run_context["resume_stage"] = restored_snapshot.stage
            run_context["resume_sequence"] = restored_snapshot.sequence
            self.logger.info(
                f"{log_context.prefix}: Compose agent resuming at {restored_snapshot.stage} (snapshot #{restored_snapshot.sequence}).",
                extra={
                    "compose": {
                        "case_id": case_id,
                        "job_id": job_id,
                        "stage": restored_snapshot.stage,
                        "sequence": restored_snapshot.sequence,
                    },
                    "event": "compose.run.resumed",
                },
            )

        self.logger.info(
            f"{log_context.prefix}: Compose agent run starting.",
            extra={"compose": run_context, "event": "compose.run.start"},
        )
        if resume and restored_snapshot is None:
            self.logger.info(
                f"{log_context.prefix}: No compose snapshot available to resume.",
                extra={
                    "compose": {"case_id": case_id, "job_id": job_id},
                    "event": "compose.run.resume_unavailable",
                },
            )

        def progress_proxy(stage: str, event: str, payload: JSONObject) -> None:
            envelope = coerce_json_object({"stage": stage, "event": event, **payload})
            collected_events.append(envelope)
            if progress_callback:
                progress_callback(stage, event, envelope)

        if restored_snapshot is None:
            run_tracker.record("compose.init", state)
        else:
            run_tracker.record("compose.resume", state)

        orchestrator = self._new_orchestrator(compose_run=run_tracker, log_context=log_context)
        if self.config.enable_async:
            async def _invoke_async() -> ComposeState:
                return await orchestrator.run_async(
                    state=state,
                    provider_credentials=provider_credentials_map,
                    progress=progress_proxy,
                )

            try:
                state = asyncio.run(_invoke_async())
            except RuntimeError:
                self.logger.debug(
                    f"{log_context.prefix}: Async compose runner unavailable; falling back to sync execution.",
                    exc_info=True,
                    extra={
                        "compose": {"case_id": case_id, "job_id": job_id},
                        "event": "compose.run.async_unavailable",
                    },
                )
                state = orchestrator.run(
                    state=state,
                    provider_credentials=provider_credentials_map,
                    progress=progress_proxy,
                )
        else:
            state = orchestrator.run(
                state=state,
                provider_credentials=provider_credentials_map,
                progress=progress_proxy,
            )

        if state.qa is None:
            raise ComposeStageError("compose.qa_reviewer", "QA reviewer did not execute")

        if self.config.qa_enforced and state.qa.status.lower() not in QA_REVIEWER_STATUS_OK:
            self._log_qa_rejection_details(state=state, log_context=log_context)
            self.logger.warning(
                f"{log_context.prefix}: QA reviewer returned status '{state.qa.status}', proceeding with deliverable release.",
                extra={
                    "compose": {
                        "case_id": log_context.case_id,
                        "job_id": log_context.job_id,
                        "qa_status": state.qa.status,
                        "qa_alerts": len(state.qa.alerts),
                        "qa_recommendations": len(state.qa.recommendations),
                    },
                    "event": "compose.qa.released_with_issues",
                },
            )

        artifact_writer = ArtifactWriter(config=self.config, logger=self.logger)
        artifacts = artifact_writer.write(state=state, docs_dir=docs_dir, job_id=job_id)

        artifact_shas: dict[str, str] = {}

        def _record_sha(name: str, path: Path | None) -> None:
            if path is None:
                return
            try:
                artifact_shas[name] = sha256_file(path)
            except Exception:
                self.logger.debug("compose.sha.failed", extra={"artifact": name, "path": str(path)})

        _record_sha("client_markdown", artifacts.client_markdown)
        _record_sha("lawyer_markdown", artifacts.lawyer_markdown)
        _record_sha("bundle", artifacts.bundle_path)
        _record_sha("qa_report", artifacts.qa_report)
        _record_sha("staff_report", artifacts.staff_report)
        _record_sha("client_docx", artifacts.client_docx)
        _record_sha("lawyer_docx", artifacts.lawyer_docx)

        events_payload: JSONArray = [coerce_json_object(event) for event in collected_events]
        qa_lane_actions_payload: dict[str, JSONObject] = {
            lane: coerce_json_object(
                {
                    "action": directive.original_action,
                    "current_action": directive.action,
                    "revision_brief": directive.revision_brief,
                    "reason": directive.reason,
                }
            )
            for lane, directive in state.qa.lane_actions.items()
        }

        meta_payload = {
            "case_id": case_id,
            "job_id": job_id,
            "client_attempts": state.lanes["client"].attempts,
            "lawyer_attempts": state.lanes["lawyer"].attempts,
            "client_reports": lane_history_payload(state.lanes["client"].history),
            "lawyer_reports": lane_history_payload(state.lanes["lawyer"].history),
            "client_providers": state.lanes["client"].providers,
            "lawyer_providers": state.lanes["lawyer"].providers,
            "client_models": state.lanes["client"].models,
            "lawyer_models": state.lanes["lawyer"].models,
            "client_token_usage": state.lanes["client"].token_usage,
            "lawyer_token_usage": state.lanes["lawyer"].token_usage,
            "qa_status": state.qa.status,
            "qa_alerts": state.qa.alerts,
            "qa_recommendations": state.qa.recommendations,
            "qa_provider": state.qa.provider,
            "qa_global_notes": state.qa.global_notes,
            "qa_lane_actions": qa_lane_actions_payload,
            "qa_iterations": state.qa_iterations,
            "provider_chain": list(self.config.provider_chain),
            "stage_usage": {stage: dict(values) for stage, values in state.stage_usage.items()},
            "stage_durations": {stage: float(value) for stage, value in state.stage_durations.items()},
            "events": events_payload,
            "bundle_path": str(artifacts.bundle_path) if artifacts.bundle_path else None,
            "client_markdown": str(artifacts.client_markdown) if artifacts.client_markdown else None,
            "lawyer_markdown": str(artifacts.lawyer_markdown) if artifacts.lawyer_markdown else None,
            "client_docx": str(artifacts.client_docx) if artifacts.client_docx else None,
            "lawyer_docx": str(artifacts.lawyer_docx) if artifacts.lawyer_docx else None,
            "qa_report": str(artifacts.qa_report) if artifacts.qa_report else None,
            "staff_report": str(artifacts.staff_report) if artifacts.staff_report else None,
            "status": "ok",
            "artifact_sha256": artifact_shas,
            "udocket_core_version": UDOCKET_CORE_VERSION,
        }

        meta_json = ops_dir / f"{job_id}__compose_log.json"
        write_json_object(meta_json, meta_payload)

        audit_jsonl = ops_dir / "ops_compose.jsonl"
        for event_record in collected_events:
            qa_block = event_record.get("qa")
            guards_block = event_record.get("guards")
            status_summary: Optional[str] = None
            if isinstance(qa_block, Mapping):
                status_summary = coerce_str(qa_block.get("status"))
            if status_summary is None and isinstance(guards_block, Mapping):
                status_parts = [f"{key}:{value}" for key, value in guards_block.items()]
                if status_parts:
                    status_summary = ", ".join(status_parts)
            append_jsonl(
                audit_jsonl,
                {
                    "case_id": case_id,
                    "job_id": job_id,
                    "stage": event_record.get("stage"),
                    "event": event_record.get("event"),
                    "lane": event_record.get("lane"),
                    "attempt": event_record.get("attempt"),
                    "status": status_summary,
                    "details": coerce_json_object(event_record),
                },
            )
        append_jsonl(
            audit_jsonl,
                {
                    "case_id": case_id,
                    "job_id": job_id,
                    "status": "ok",
                    "qa_status": state.qa.status,
                    "qa_iterations": state.qa_iterations,
                    "qa_provider": state.qa.provider,
                    "bundle_path": str(artifacts.bundle_path) if artifacts.bundle_path else None,
                    "client_markdown": str(artifacts.client_markdown) if artifacts.client_markdown else None,
                    "lawyer_markdown": str(artifacts.lawyer_markdown) if artifacts.lawyer_markdown else None,
                    "staff_report": str(artifacts.staff_report) if artifacts.staff_report else None,
                    "artifact_sha256": artifact_shas,
                    "udocket_core_version": UDOCKET_CORE_VERSION,
                },
            )

        result = ComposeResult(
            status="ok",
            artifacts=artifacts,
            meta_json=meta_json,
            audit_jsonl=audit_jsonl,
            provider_chain=list(self.config.provider_chain),
            stage_usage={stage: dict(values) for stage, values in state.stage_usage.items()},
            stage_durations={stage: float(value) for stage, value in state.stage_durations.items()},
        )
        try:
            self.logger.info(
                "compose.run.complete",
                extra={
                    "compose": {
                        "case_id": case_id,
                        "job_id": job_id,
                        "client_attempts": state.lanes["client"].attempts,
                        "lawyer_attempts": state.lanes["lawyer"].attempts,
                        "qa_status": state.qa.status if state.qa else None,
                    }
                },
            )
        except Exception:  # pragma: no cover - defensive
            self.logger.debug("compose.logging_failed", exc_info=True)
        return result

    # ------------------------------------------------------------------
    # Logging helpers

    def _log_qa_rejection_details(
        self,
        *,
        state: ComposeState,
        log_context: ComposeLogContext,
    ) -> None:
        qa_result = state.qa
        if qa_result is None:
            return
        compose_payload: dict[str, object] = {
            "case_id": log_context.case_id,
            "job_id": log_context.job_id,
            "qa_status": qa_result.status,
            "qa_provider": qa_result.provider,
        }
        self.logger.debug(
            f"{log_context.prefix}: QA rejection recorded (status={qa_result.status}, alerts={len(qa_result.alerts)}, recommendations={len(qa_result.recommendations)}).",
            extra={
                "compose": compose_payload,
                "event": "compose.qa_rejection.summary",
            },
        )
        for alert in qa_result.alerts:
            alert_text = str(alert)
            if not alert_text:
                continue
            self.logger.debug(
                f"{log_context.prefix}: QA alert — {alert_text}",
                extra={
                    "compose": {
                        **compose_payload,
                        "qa_alert": alert_text,
                    },
                    "event": "compose.qa_rejection.alert",
                },
            )
        for recommendation in qa_result.recommendations:
            recommendation_text = str(recommendation)
            if not recommendation_text:
                continue
            self.logger.debug(
                f"{log_context.prefix}: QA recommendation — {recommendation_text}",
                extra={
                    "compose": {
                        **compose_payload,
                        "qa_recommendation": recommendation_text,
                    },
                    "event": "compose.qa_rejection.recommendation",
                },
            )
        lane_states = {
            "client": state.client,
            "lawyer": state.lawyer,
        }
        for lane, lane_state in lane_states.items():
            self._log_guard_report_details(
                log_context=log_context,
                lane=lane,
                guard="structure",
                report=lane_state.structure_report,
            )
            self._log_guard_report_details(
                log_context=log_context,
                lane=lane,
                guard="compliance",
                report=lane_state.compliance_report,
            )
            self._log_guard_report_details(
                log_context=log_context,
                lane=lane,
                guard="factuality",
                report=lane_state.factuality_report,
            )

    def _log_guard_report_details(
        self,
        *,
        log_context: ComposeLogContext,
        lane: str,
        guard: str,
        report: GuardReport | None,
    ) -> None:
        compose_base: dict[str, object] = {
            "case_id": log_context.case_id,
            "job_id": log_context.job_id,
            "lane": lane,
            "guard": guard,
        }
        if report is None:
            self.logger.debug(
                f"{log_context.prefix}: QA rejection lane={lane} guard={guard} missing report.",
                extra={
                    "compose": compose_base,
                    "event": "compose.qa_rejection.guard_missing",
                },
            )
            return
        for error_text in report.errors:
            message = str(error_text).strip()
            if not message:
                continue
            self.logger.debug(
                f"{log_context.prefix}: QA rejection lane={lane} guard={guard} ERROR: {message}",
                extra={
                    "compose": {
                        **compose_base,
                        "severity": "error",
                        "message": message,
                    },
                    "event": "compose.qa_rejection.guard_error",
                },
            )
        for warning_text in report.warnings:
            message = str(warning_text).strip()
            if not message:
                continue
            self.logger.debug(
                f"{log_context.prefix}: QA rejection lane={lane} guard={guard} WARNING: {message}",
                extra={
                    "compose": {
                        **compose_base,
                        "severity": "warning",
                        "message": message,
                    },
                    "event": "compose.qa_rejection.guard_warning",
                },
            )


def _load_sequence(path: Optional[Path]) -> list[JSONObject]:
    if path is None or not path.exists():
        return []
    try:
        payload = load_json_value(path, context=str(path))
    except ValueError:
        return []
    if isinstance(payload, Mapping):
        events = coerce_object_list(payload.get("events"))
        return [coerce_json_object(item) for item in events]
    if isinstance(payload, Sequence):
        return [coerce_json_object(item) for item in payload if isinstance(item, Mapping)]
    return []


def _read_text(path: Optional[Path]) -> str:
    if path is None:
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:  # pragma: no cover - defensive
        return ""


def _read_json(path: Optional[Path]) -> JSONObject:
    if path is None or not path.exists():
        return {}
    try:
        return load_json_object(path, context=str(path))
    except Exception:  # pragma: no cover - defensive
        return {}


__all__ = [
    "ComposeAgent",
    "ComposeConfig",
    "ComposeResult",
    "ComposeArtifacts",
    "ComposeStageError",
    "ComposeState",
    "ComposeInputs",
    "LaneRuntimeState",
    "LaneOutcome",
    "LaneActionDirective",
    "GuardReport",
    "LANE_CONFIGS",
    "_factuality_report",
    "_stable_doc_fingerprint",
]
