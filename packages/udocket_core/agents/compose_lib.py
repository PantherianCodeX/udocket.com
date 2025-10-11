from __future__ import annotations

# pyright: strict

import logging
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

from packages.udocket_core.json_utils import (
    JSONArray,
    JSONObject,
    coerce_json_object,
    coerce_object_list,
    coerce_str,
    load_json_object,
    load_json_value,
    write_json_object,
)

from .common import append_jsonl, ensure_dir
from ..llm import LLMSettings, load_llm_settings
from .compose.errors import ComposeStageError
from .compose.guards import factuality_report
from .compose.io import ArtifactWriter
from .compose.llm_profiles import LANE_CONFIGS
from .compose.llm_runtime import invoke_llm
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

    def _new_orchestrator(self, *, compose_run: ComposeRun | None = None) -> ComposeOrchestrator:
        return ComposeOrchestrator(
            config=self.config,
            settings=self.settings,
            logger=self.logger,
            qa_ok_status=QA_REVIEWER_STATUS_OK,
            prompts=self.prompts,
            compose_run=compose_run,
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
        orchestrator = self._new_orchestrator()
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
        orchestrator = self._new_orchestrator()
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

        provider_credentials_map: Mapping[str, JSONObject] = {
            name: coerce_json_object(payload)
            for name, payload in (provider_credentials or {}).items()
        }

        collected_events: list[JSONObject] = []

        run_tracker = ComposeRun(
            case_id=case_id,
            job_id=job_id,
            snapshot_dir=ops_dir / f"{job_id}__compose_run",
            logger=self.logger,
        )
        run_tracker.record("compose.init", state)

        def progress_proxy(stage: str, event: str, payload: JSONObject) -> None:
            envelope = coerce_json_object({"stage": stage, "event": event, **payload})
            collected_events.append(envelope)
            if progress_callback:
                progress_callback(stage, event, envelope)

        orchestrator = self._new_orchestrator(compose_run=run_tracker)
        state = orchestrator.run(
            state=state,
            provider_credentials=provider_credentials_map,
            progress=progress_proxy,
        )

        if state.qa is None:
            raise ComposeStageError("compose.qa_reviewer", "QA reviewer did not execute")

        if self.config.qa_required and state.qa.status.lower() not in QA_REVIEWER_STATUS_OK:
            raise ComposeStageError(
                "compose.qa_reviewer",
                f"QA reviewer returned status '{state.qa.status}'",
            )

        artifact_writer = ArtifactWriter(config=self.config, logger=self.logger)
        artifacts = artifact_writer.write(state=state, docs_dir=docs_dir, job_id=job_id)

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
