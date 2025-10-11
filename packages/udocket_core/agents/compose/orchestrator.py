from __future__ import annotations

# pyright: strict

import hashlib
import json
import logging
import re
from typing import Any, Callable, Mapping, Optional, cast

from langgraph.graph import END, START, StateGraph  # type: ignore[import]

from packages.udocket_core.json_utils import (
    JSONArray,
    JSONObject,
    JSONValue,
    coerce_json_object,
    coerce_json_value,
    coerce_str,
)

from .errors import ComposeStageError
from .context import assemble_context
from .guards import (
    compliance_report,
    factuality_report,
    markdown_structure_report,
    sentence_length_report,
)
from .llm_runtime import invoke_llm
from .prompt_config import ComposePromptConfig, LanePrompts
from .run import ComposeRun
from .settings import ComposeConfig
from .qa import run_qa_review
from .state import ComposeContext, ComposeState, GuardReport, LaneActionDirective, LaneAttempt, LaneOutcome, LaneRuntimeState, clone_guard_report
from ...llm import LLMSettings


class ComposeOrchestrator:
    def __init__(
        self,
        *,
        config: ComposeConfig,
        settings: LLMSettings,
        logger: logging.Logger,
        qa_ok_status: set[str],
        prompts: ComposePromptConfig,
        compose_run: ComposeRun | None = None,
    ) -> None:
        self.config: ComposeConfig = config
        self.settings: LLMSettings = settings
        self.logger = logger
        self._qa_ok_status = frozenset(status.lower() for status in qa_ok_status)
        self.prompts = prompts
        self._run_tracker = compose_run

    def run(
        self,
        *,
        state: ComposeState,
        provider_credentials: Mapping[str, JSONObject],
        progress: Optional[Callable[[str, str, JSONObject], None]],
    ) -> ComposeState:
        return self._run_graph(
            state=state,
            provider_credentials=provider_credentials,
            progress=progress,
        )

    # ------------------------------------------------------------------
    # Orchestration

    def _run_graph(
        self,
        *,
        state: ComposeState,
        provider_credentials: Mapping[str, JSONObject],
        progress: Optional[Callable[[str, str, JSONObject], None]],
    ) -> ComposeState:
        graph: Any = StateGraph(ComposeState)

        def context_node(current: ComposeState) -> dict[str, object]:
            return self._context_assembler(current, progress)

        def client_composer_node(current: ComposeState) -> dict[str, object]:
            return self._draft_lane(
                current,
                lane="client",
                provider_credentials=provider_credentials,
                progress=progress,
            )

        def client_structure_node(current: ComposeState) -> dict[str, object]:
            return self._structure_guard(current, lane="client", progress=progress)

        def client_compliance_node(current: ComposeState) -> dict[str, object]:
            return self._compliance_guard(current, lane="client", progress=progress)

        def client_factual_node(current: ComposeState) -> dict[str, object]:
            return self._factuality_gate(current, lane="client", progress=progress)

        def client_revision_node(current: ComposeState) -> dict[str, object]:
            return self._prepare_revision(current, lane="client", progress=progress)

        def lawyer_composer_node(current: ComposeState) -> dict[str, object]:
            return self._draft_lane(
                current,
                lane="lawyer",
                provider_credentials=provider_credentials,
                progress=progress,
            )

        def lawyer_structure_node(current: ComposeState) -> dict[str, object]:
            return self._structure_guard(current, lane="lawyer", progress=progress)

        def lawyer_compliance_node(current: ComposeState) -> dict[str, object]:
            return self._compliance_guard(current, lane="lawyer", progress=progress)

        def lawyer_factual_node(current: ComposeState) -> dict[str, object]:
            return self._factuality_gate(current, lane="lawyer", progress=progress)

        def lawyer_revision_node(current: ComposeState) -> dict[str, object]:
            return self._prepare_revision(current, lane="lawyer", progress=progress)

        def qa_reviewer_node(current: ComposeState) -> dict[str, object]:
            return self._qa_reviewer_step(
                current,
                provider_credentials=provider_credentials,
                progress=progress,
            )

        def client_qa_revision_node(current: ComposeState) -> dict[str, object]:
            return self._qa_lane_revision(
                current,
                lane="client",
                progress=progress,
            )

        def client_qa_editor_node(current: ComposeState) -> dict[str, object]:
            return self._qa_lane_editor(
                current,
                lane="client",
                provider_credentials=provider_credentials,
                progress=progress,
            )

        def lawyer_qa_revision_node(current: ComposeState) -> dict[str, object]:
            return self._qa_lane_revision(
                current,
                lane="lawyer",
                progress=progress,
            )

        def lawyer_qa_editor_node(current: ComposeState) -> dict[str, object]:
            return self._qa_lane_editor(
                current,
                lane="lawyer",
                provider_credentials=provider_credentials,
                progress=progress,
            )

        def compose_join_node(current: ComposeState) -> dict[str, object]:
            return {}

        def wait_for_client_node(current: ComposeState) -> dict[str, object]:
            return {}

        def wait_for_lawyer_node(current: ComposeState) -> dict[str, object]:
            return {}

        def release_node(current: ComposeState) -> dict[str, object]:
            return self._release_gate(
                current,
                progress=progress,
            )

        graph.add_node("ContextAssembler", context_node)
        graph.add_node("ClientComposer", client_composer_node)
        graph.add_node("ClientStructureValidator", client_structure_node)
        graph.add_node("ClientComplianceGuard", client_compliance_node)
        graph.add_node("ClientFactualityGate", client_factual_node)
        graph.add_node("ClientRevision", client_revision_node)
        graph.add_node("LawyerComposer", lawyer_composer_node)
        graph.add_node("LawyerStructureValidator", lawyer_structure_node)
        graph.add_node("LawyerComplianceGuard", lawyer_compliance_node)
        graph.add_node("LawyerFactualityGate", lawyer_factual_node)
        graph.add_node("LawyerRevision", lawyer_revision_node)
        graph.add_node("QAReviewer", qa_reviewer_node)
        graph.add_node("ClientQARevision", client_qa_revision_node)
        graph.add_node("ClientQAEditor", client_qa_editor_node)
        graph.add_node("LawyerQARevision", lawyer_qa_revision_node)
        graph.add_node("LawyerQAEditor", lawyer_qa_editor_node)
        graph.add_node("ComposeJoin", compose_join_node)
        graph.add_node("WaitForClientLane", wait_for_client_node)
        graph.add_node("WaitForLawyerLane", wait_for_lawyer_node)
        graph.add_node("ReleaseGate", release_node)

        graph.add_edge(START, "ContextAssembler")
        graph.add_edge("ContextAssembler", "ClientComposer")
        graph.add_edge("ContextAssembler", "LawyerComposer")
        graph.add_edge("ClientComposer", "ClientStructureValidator")
        graph.add_edge("ClientStructureValidator", "ClientComplianceGuard")
        graph.add_edge("ClientComplianceGuard", "ClientFactualityGate")
        graph.add_edge("ClientRevision", "ClientComposer")

        graph.add_edge("LawyerComposer", "LawyerStructureValidator")
        graph.add_edge("LawyerStructureValidator", "LawyerComplianceGuard")
        graph.add_edge("LawyerComplianceGuard", "LawyerFactualityGate")
        graph.add_edge("LawyerRevision", "LawyerComposer")

        graph.add_edge("ClientFactualityGate", "WaitForClientLane")
        graph.add_edge("LawyerFactualityGate", "WaitForLawyerLane")

        graph.add_edge("WaitForClientLane", "ComposeJoin")
        graph.add_edge("WaitForLawyerLane", "ComposeJoin")

        graph.add_edge("ComposeJoin", "QAReviewer")

        graph.add_conditional_edges(
            "QAReviewer",
            self._qa_decision,
            {
                "ReleaseGate": "ReleaseGate",
                "ClientQARevision": "ClientQARevision",
                "ClientQAEditor": "ClientQAEditor",
                "LawyerQARevision": "LawyerQARevision",
                "LawyerQAEditor": "LawyerQAEditor",
            },
        )
        graph.add_edge("ClientQARevision", "ClientComposer")
        graph.add_edge("LawyerQARevision", "LawyerComposer")
        graph.add_edge("ClientQAEditor", "WaitForClientLane")
        graph.add_edge("LawyerQAEditor", "WaitForLawyerLane")
        graph.add_edge("ReleaseGate", END)

        compiled = graph.compile()
        result_state = compiled.invoke(state)
        if isinstance(result_state, ComposeState):
            return result_state
        if isinstance(result_state, dict):
            result_mapping = cast(dict[str, object], result_state)
            for key, value in result_mapping.items():
                setattr(state, key, value)
            return state
        raise ComposeStageError("compose.graph", f"Unexpected graph result type: {type(result_state)!r}")

    @staticmethod
    def _lane_state(state: ComposeState, lane: str) -> LaneRuntimeState:
        if lane == "client":
            return state.client
        if lane == "lawyer":
            return state.lawyer
        raise ComposeStageError(f"compose.{lane}", "Unknown lane")

    def _lane_prompts(self, lane: str) -> LanePrompts:
        if lane == "client":
            return self.prompts.client
        if lane == "lawyer":
            return self.prompts.lawyer
        raise ComposeStageError(f"compose.{lane}", "Unknown lane")

    def _context_assembler(
        self,
        state: ComposeState,
        progress: Optional[Callable[[str, str, JSONObject], None]],
    ) -> dict[str, object]:
        stage_name = "compose.context"
        self._log(logging.INFO, stage_name, "start", {})
        emit(progress, stage_name, "start", {})
        context = assemble_context(state.inputs)
        state.context = context
        emit(progress, stage_name, "complete", {})
        self._log(logging.INFO, stage_name, "complete", {"has_context": True})
        self._snapshot(stage_name, state)
        return {"context": context}

    def _draft_lane(
        self,
        state: ComposeState,
        *,
        lane: str,
        provider_credentials: Mapping[str, JSONObject],
        progress: Optional[Callable[[str, str, JSONObject], None]],
    ) -> dict[str, object]:
        lane_state = self._lane_state(state, lane)
        context = state.context
        if context is None:
            raise ComposeStageError(f"compose.{lane}.draft", "Compose context missing")
        is_revision = lane_state.revision_brief is not None
        stage_name = f"compose.{lane}.{'revise' if is_revision else 'draft'}"
        next_attempt = lane_state.attempts + 1
        if next_attempt > lane_state.max_attempts:
            raise ComposeStageError(stage_name, "Maximum attempts exhausted", lane=lane, attempt=lane_state.attempts)
        lane_state.current_source = "revise" if is_revision else "draft"
        start_payload: JSONObject = {"attempt": next_attempt, "lane": lane, "source": lane_state.current_source}
        self._log(logging.INFO, stage_name, "start", dict(start_payload))
        emit(progress, stage_name, "start", start_payload)
        lane_state.attempts = next_attempt
        lane_prompts = self._lane_prompts(lane)
        temperature = self.config.temperature if lane == "client" else self.config.lawyer_temperature
        if is_revision:
            temperature = lane_state.config.revision_temperature
        system_prompt = (
            lane_prompts.revision_system_prompt if is_revision else lane_prompts.system_prompt
        )
        instruction = (
            lane_prompts.revision_instruction if is_revision else lane_prompts.draft_instruction
        )
        document, usage, provider, model = invoke_llm(
            stage=stage_name,
            system_prompt=system_prompt,
            user_prompt=lane_user_prompt(
                lane,
                context,
                lane_state.revision_brief,
                locale=self.config.locale,
                instruction=instruction,
            ),
            temperature=temperature,
            provider_credentials=provider_credentials,
            config=self.config,
            settings=self.settings,
        )
        lane_state.revision_brief = None
        lane_state.document = document
        doc_hash = stable_doc_fingerprint(document)
        if is_revision and lane_state.last_document_hash is not None and doc_hash == lane_state.last_document_hash:
            raise ComposeStageError(stage_name, "Revision produced no changes", lane=lane, attempt=lane_state.attempts)
        lane_state.last_document_hash = doc_hash
        lane_state.structure_report = None
        lane_state.compliance_report = None
        lane_state.factuality_report = None
        lane_state.providers.append(provider)
        lane_state.models.append(model)
        lane_state.record_usage(stage_name, usage)
        complete_payload: JSONObject = {
            "attempt": lane_state.attempts,
            "lane": lane,
            "provider": provider,
            "model": model,
            "usage": dict(usage),
            "source": lane_state.current_source,
        }
        emit(progress, stage_name, "complete", complete_payload)
        self._log(logging.INFO, stage_name, "complete", dict(complete_payload))
        result: dict[str, object] = {}
        result[lane] = lane_state
        result["stage_usage"] = {stage_name: dict(usage)}
        self._snapshot(stage_name, state)
        return result

    def _structure_guard(
        self,
        state: ComposeState,
        *,
        lane: str,
        progress: Optional[Callable[[str, str, JSONObject], None]],
    ) -> dict[str, object]:
        lane_state = self._lane_state(state, lane)
        document = lane_state.document
        if document is None:
            raise ComposeStageError(f"compose.{lane}.structure", "No draft available")
        stage_name = f"compose.{lane}.structure"
        self._log(logging.INFO, stage_name, "start", {"lane": lane, "attempt": lane_state.attempts})
        emit(
            progress,
            stage_name,
            "start",
            {"attempt": lane_state.attempts, "lane": lane, "source": lane_state.current_source},
        )
        per_section_min: Optional[Mapping[str, int]] = None
        per_section_max: Optional[Mapping[str, int]] = None
        if lane_state.config.lane == "client":
            from .llm_profiles import (
                CLIENT_MAX_WORDS_BY_SECTION as _CLIENT_MAX,
                CLIENT_MIN_WORDS_BY_SECTION as _CLIENT_MIN,
            )

            per_section_min = _CLIENT_MIN
            per_section_max = _CLIENT_MAX
        elif lane_state.config.lane == "lawyer":
            from .llm_profiles import (
                LAWYER_MAX_WORDS_BY_SECTION as _LAWYER_MAX,
                LAWYER_MIN_WORDS_BY_SECTION as _LAWYER_MIN,
            )

            per_section_min = _LAWYER_MIN
            per_section_max = _LAWYER_MAX
        report = markdown_structure_report(
            document,
            lane_state.config.headings,
            min_words=lane_state.config.min_words,
            per_section_min=per_section_min,
            per_section_max=per_section_max,
        )
        if lane_state.config.readability_limit is not None:
            readability = sentence_length_report(
                document,
                max_average_words=lane_state.config.readability_limit,
            )
            if not readability.ok:
                report.errors.extend(readability.errors)
                report.warnings.extend(readability.warnings)
        lane_state.structure_report = report
        emit(
            progress,
            stage_name,
            "complete",
            {
                "lane": lane,
                "attempt": lane_state.attempts,
                "guards": {"structure": "ok" if report.ok else "fail"},
                "errors": list(report.errors),
                "warnings": list(report.warnings),
            },
        )
        self._log(
            logging.INFO,
            stage_name,
            "complete",
            {
                "lane": lane,
                "ok": report.ok,
                "errors": len(report.errors),
                "warnings": len(report.warnings),
            },
        )
        result: dict[str, object] = {}
        result[lane] = lane_state
        self._snapshot(stage_name, state)
        return result

    def _compliance_guard(
        self,
        state: ComposeState,
        *,
        lane: str,
        progress: Optional[Callable[[str, str, JSONObject], None]],
    ) -> dict[str, object]:
        lane_state = self._lane_state(state, lane)
        document = lane_state.document
        if document is None:
            raise ComposeStageError(f"compose.{lane}.compliance", "No draft available")
        stage_name = f"compose.{lane}.compliance"
        self._log(logging.INFO, stage_name, "start", {"lane": lane, "attempt": lane_state.attempts})
        emit(
            progress,
            stage_name,
            "start",
            {"attempt": lane_state.attempts, "lane": lane, "source": lane_state.current_source},
        )
        report = compliance_report(document)
        lane_state.compliance_report = report
        emit(
            progress,
            stage_name,
            "complete",
            {
                "lane": lane,
                "attempt": lane_state.attempts,
                "guards": {"compliance": "ok" if report.ok else "fail"},
                "errors": list(report.errors),
                "warnings": list(report.warnings),
            },
        )
        self._log(
            logging.INFO,
            stage_name,
            "complete",
            {
                "lane": lane,
                "ok": report.ok,
                "errors": len(report.errors),
                "warnings": len(report.warnings),
            },
        )
        result: dict[str, object] = {}
        result[lane] = lane_state
        self._snapshot(stage_name, state)
        return result

    def _factuality_gate(
        self,
        state: ComposeState,
        *,
        lane: str,
        progress: Optional[Callable[[str, str, JSONObject], None]],
    ) -> dict[str, object]:
        lane_state = self._lane_state(state, lane)
        document = lane_state.document
        context = state.context
        if document is None or context is None:
            raise ComposeStageError(f"compose.{lane}.factuality", "Missing draft or context")
        stage_name = f"compose.{lane}.factuality"
        self._log(logging.INFO, stage_name, "start", {"lane": lane, "attempt": lane_state.attempts})
        emit(
            progress,
            stage_name,
            "start",
            {"attempt": lane_state.attempts, "lane": lane, "source": lane_state.current_source},
        )
        report = factuality_report(
            document,
            claimable_atoms=context.claimable_atoms,
            timeline_events=context.events,
            min_timestamp_references=lane_state.config.min_timestamp_references,
        )
        lane_state.factuality_report = report
        structure_snapshot = (
            clone_guard_report(lane_state.structure_report)
            if lane_state.structure_report
            else GuardReport(ok=False, errors=["Structure report missing"])
        )
        compliance_snapshot = (
            clone_guard_report(lane_state.compliance_report)
            if lane_state.compliance_report
            else GuardReport(ok=False, errors=["Compliance report missing"])
        )
        attempt_record = LaneAttempt(
            attempt_number=lane_state.attempts,
            source=lane_state.current_source,
            document=document,
            structure=structure_snapshot,
            compliance=compliance_snapshot,
            factuality=clone_guard_report(report),
        )
        lane_state.history.append(attempt_record)
        lane_state.current_source = "draft"
        payload: JSONObject = {
            "lane": lane,
            "attempt": lane_state.attempts,
            "guards": {"factuality": "ok" if report.ok else "fail"},
            "errors": list(report.errors),
            "warnings": list(report.warnings),
        }
        emit(progress, stage_name, "complete", payload)
        self._log(
            logging.INFO,
            stage_name,
            "complete",
            {
                "lane": lane,
                "ok": report.ok,
                "errors": len(report.errors),
                "warnings": len(report.warnings),
            },
        )
        lanes_update: Optional[dict[str, LaneOutcome]] = None
        if (
            lane_state.structure_report
            and lane_state.structure_report.ok
            and lane_state.compliance_report
            and lane_state.compliance_report.ok
            and report.ok
        ):
            lanes_update = {lane: lane_state.to_outcome()}
        updates: dict[str, object] = {lane: lane_state}
        if lanes_update:
            updates["lanes"] = lanes_update
        self._snapshot(stage_name, state)
        return updates

    def _prepare_revision(
        self,
        state: ComposeState,
        *,
        lane: str,
        progress: Optional[Callable[[str, str, JSONObject], None]],
    ) -> dict[str, object]:
        lane_state = self._lane_state(state, lane)
        stage_name = f"compose.{lane}.revision"
        emit(
            progress,
            stage_name,
            "start",
            {"attempt": lane_state.attempts, "lane": lane},
        )
        if lane_state.structure_report is None or lane_state.compliance_report is None or lane_state.factuality_report is None:
            raise ComposeStageError(stage_name, "Revision requested before guard reports computed")
        revision_brief = build_revision_brief(
            self.prompts.revision_header_template,
            lane,
            lane_state.structure_report,
            lane_state.compliance_report,
            lane_state.factuality_report,
        )
        lane_state.revision_brief = revision_brief
        emit(
            progress,
            stage_name,
            "complete",
            {"lane": lane, "attempt": lane_state.attempts},
        )
        result: dict[str, object] = {}
        result[lane] = lane_state
        self._snapshot(stage_name, state)
        return result

    def _qa_reviewer_step(
        self,
        state: ComposeState,
        *,
        provider_credentials: Mapping[str, JSONObject],
        progress: Optional[Callable[[str, str, JSONObject], None]],
    ) -> dict[str, object]:
        stage_name = "compose.qa_reviewer"
        self._log(logging.INFO, stage_name, "start", {"iteration": state.qa_iterations})
        if state.qa_iterations >= self.config.qa_iteration_limit:
            raise ComposeStageError(
                "compose.qa_reviewer",
                "QA iteration limit exceeded",
            )
        emit(
            progress,
            stage_name,
            "start",
            {"iteration": state.qa_iterations},
        )
        qa_result, usage, provider, model = run_qa_review(
            state=state,
            config=self.config,
            settings=self.settings,
            provider_credentials=provider_credentials,
            logger=self.logger,
            system_prompt=self.prompts.qa.system_prompt,
        )
        qa_emit_payload = coerce_json_object(
            {
                "status": qa_result.status,
                "lane_actions": {
                    lane: coerce_json_object(
                        {
                            "action": directive.original_action,
                            "current_action": directive.action,
                            "reason": directive.reason,
                        }
                    )
                    for lane, directive in qa_result.lane_actions.items()
                },
                "alerts": list(qa_result.alerts),
            }
        )
        emit(
            progress,
            stage_name,
            "complete",
            {
                "iteration": state.qa_iterations,
                "status": qa_result.status,
                "provider": provider,
                "model": model,
                "usage": dict(usage),
                "qa": qa_emit_payload,
            },
        )
        state.qa = qa_result
        self._snapshot(stage_name, state)
        state.qa_iterations += 1
        actions = {lane: (directive.action or "none") for lane, directive in qa_result.lane_actions.items()}
        level = logging.INFO if all(action == "none" for action in actions.values()) else logging.WARNING
        self._log(
            level,
            "compose.qa_reviewer",
            "complete",
            {"status": qa_result.status, "actions": actions, "iteration": state.qa_iterations},
        )
        return {
            "qa": qa_result,
            "qa_iterations": state.qa_iterations,
            "stage_usage": {"compose.qa_reviewer": dict(usage)},
        }

    def _qa_decision(self, state: ComposeState) -> str:
        qa = state.qa
        if qa is None:
            raise ComposeStageError("compose.qa_reviewer", "QA reviewer result missing")
        normalized_status = qa.status.lower().strip()
        if normalized_status in self._qa_ok_status:
            return "ReleaseGate"
        for lane in ("client", "lawyer"):
            directive = qa.lane_actions.get(lane)
            if directive is None:
                continue
            action = (directive.action or "none").strip().lower()
            if action == "revise":
                return "ClientQARevision" if lane == "client" else "LawyerQARevision"
            if action == "editor":
                return "ClientQAEditor" if lane == "client" else "LawyerQAEditor"
        raise ComposeStageError(
            "compose.qa_reviewer",
            "QA reported failure without actionable lane directives",
        )

    def _qa_lane_revision(
        self,
        state: ComposeState,
        *,
        lane: str,
        progress: Optional[Callable[[str, str, JSONObject], None]],
    ) -> dict[str, object]:
        qa = state.qa
        if qa is None:
            raise ComposeStageError(f"compose.{lane}.qa_revision", "QA reviewer result missing", lane=lane)
        directive = qa.lane_actions.get(lane)
        stage_name = f"compose.{lane}.qa_revision"
        if directive is None or (directive.action or "none").strip().lower() != "revise":
            raise ComposeStageError(stage_name, "No revision directive available", lane=lane)
        revision_brief = (directive.revision_brief or "").strip()
        if not revision_brief:
            raise ComposeStageError(stage_name, "QA requested revision without brief", lane=lane)
        lane_state = self._lane_state(state, lane)
        self._log(
            logging.WARNING,
            stage_name,
            "start",
            {"lane": lane, "attempt": lane_state.attempts + 1, "reason": directive.reason},
        )
        emit(
            progress,
            stage_name,
            "start",
            {
                "lane": lane,
                "attempt": lane_state.attempts + 1,
                "revision_brief": revision_brief,
                "reason": directive.reason,
            },
        )
        lane_state.revision_brief = revision_brief
        lane_state.current_source = "revise"
        lane_state.structure_report = None
        lane_state.compliance_report = None
        lane_state.factuality_report = None
        lane_state.editor_attempted = False
        directive.action = "none"
        emit(
            progress,
            stage_name,
            "complete",
            {"lane": lane, "revision_brief": revision_brief, "reason": directive.reason},
        )
        self._log(
            logging.WARNING,
            stage_name,
            "complete",
            {"lane": lane, "reason": directive.reason},
        )
        result: dict[str, object] = {}
        result[lane] = lane_state
        result["lanes"] = {lane: None}
        result["qa"] = qa
        self._snapshot(stage_name, state)
        return result

    def _qa_lane_editor(
        self,
        state: ComposeState,
        *,
        lane: str,
        provider_credentials: Mapping[str, JSONObject],
        progress: Optional[Callable[[str, str, JSONObject], None]],
    ) -> dict[str, object]:
        qa = state.qa
        if qa is None:
            raise ComposeStageError(f"compose.{lane}.editor", "QA reviewer result missing", lane=lane)
        directive = qa.lane_actions.get(lane)
        if directive is None or (directive.action or "none").strip().lower() != "editor":
            raise ComposeStageError(f"compose.{lane}.editor", "No editor directive available", lane=lane)
        updates = self._run_lane_editor(
            state=state,
            lane=lane,
            directive=directive,
            provider_credentials=provider_credentials,
            progress=progress,
        )
        directive.action = "none"
        return updates

    def _run_lane_editor(
        self,
        *,
        state: ComposeState,
        lane: str,
        directive: LaneActionDirective,
        provider_credentials: Mapping[str, JSONObject],
        progress: Optional[Callable[[str, str, JSONObject], None]],
    ) -> dict[str, object]:
        lane_state = self._lane_state(state, lane)
        stage_name = f"compose.{lane}.editor"
        if lane_state.editor_attempted:
            raise ComposeStageError(stage_name, "Editor already attempted", lane=lane)
        document = lane_state.document
        if document is None:
            raise ComposeStageError(stage_name, "No draft available for editor", lane=lane)
        lane_state.current_source = "editor"
        revision_brief = (directive.revision_brief or "").strip()
        known_issues = known_issues_from_brief(revision_brief)
        lane_prompts = self._lane_prompts(lane)
        constraints_payload = coerce_json_object(
            {
                "headings": list(lane_state.config.headings),
                "min_words": lane_state.config.min_words,
                "min_timestamp_references": lane_state.config.min_timestamp_references,
                "tone": lane,
            }
        )
        allowed_edits: JSONArray = [
            coerce_json_value(item)
            for item in [
                "formatting",
                "punctuation",
                "grammar",
                "compliance wording",
                "timestamp placement",
            ]
        ]
        known_issues_json: JSONArray = [coerce_json_value(item) for item in known_issues]
        base_payload: dict[str, JSONValue] = {
            "document": document,
            "constraints": constraints_payload,
            "known_issues": known_issues_json,
            "allowed_edits": allowed_edits,
        }
        if revision_brief:
            base_payload["revision_brief"] = revision_brief
        base_payload["locale"] = self.config.locale
        system_prompt = lane_prompts.editor_system_prompt
        base_payload["instruction"] = lane_prompts.editor_instruction
        payload = coerce_json_object(base_payload)
        user_prompt = json.dumps(payload, ensure_ascii=False)
        self._log(
            logging.INFO,
            stage_name,
            "start",
            {"lane": lane, "attempt": lane_state.attempts, "reason": directive.reason},
        )
        emit(
            progress,
            stage_name,
            "start",
            {"lane": lane, "attempt": lane_state.attempts, "revision_brief": revision_brief, "reason": directive.reason},
        )
        response, usage, provider, model = invoke_llm(
            stage=stage_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.0,
            provider_credentials=provider_credentials,
            config=self.config,
            settings=self.settings,
        )
        try:
            parsed = json.loads(response)
        except json.JSONDecodeError as exc:
            raise ComposeStageError(stage_name, f"Invalid editor response: {exc}", lane=lane, provider=provider, model=model) from exc
        new_document = coerce_str(parsed.get("document")) or ""
        if not new_document.strip():
            raise ComposeStageError(stage_name, "Editor returned empty document", lane=lane, provider=provider, model=model)
        change_log_raw = parsed.get("change_log")
        change_log: list[str] = []
        if isinstance(change_log_raw, list):
            for item in cast(list[JSONValue], change_log_raw):
                entry = coerce_str(item) if isinstance(item, str) else None
                if entry:
                    change_log.append(entry)
        lane_state.document = new_document
        lane_state.record_usage(stage_name, usage)
        lane_state.providers.append(provider)
        lane_state.models.append(model)
        lane_state.editor_attempted = True
        change_log_payload: JSONArray = [coerce_json_value(entry) for entry in change_log]
        emit(
            progress,
            stage_name,
            "complete",
            {
                "lane": lane,
                "provider": provider,
                "model": model,
                "usage": dict(usage),
                "change_log": change_log_payload,
            },
        )
        self._log(
            logging.INFO,
            stage_name,
            "complete",
            {"lane": lane, "provider": provider, "changes": len(change_log)},
        )
        result: dict[str, object] = {}
        result[lane] = lane_state
        self._snapshot(stage_name, state)
        return result

    def _release_gate(
        self,
        state: ComposeState,
        *,
        progress: Optional[Callable[[str, str, JSONObject], None]],
    ) -> dict[str, object]:
        stage_name = "compose.release_gate"
        emit(
            progress,
            stage_name,
            "start",
            {},
        )
        client_outcome = state.lanes.get("client")
        lawyer_outcome = state.lanes.get("lawyer")
        if client_outcome is None or lawyer_outcome is None:
            raise ComposeStageError(stage_name, "Missing lane outcomes")
        lane_status = lane_status_snapshot(client_outcome, lawyer_outcome)
        emit(
            progress,
            stage_name,
            "complete",
            lane_status,
        )
        self._snapshot(stage_name, state)
        return {}

    def _snapshot(self, stage: str, state: ComposeState) -> None:
        if self._run_tracker is None:
            return
        try:
            self._run_tracker.record(stage, state)
        except Exception:  # pragma: no cover - defensive
            self.logger.debug("compose.snapshot_failed", extra={"stage": stage}, exc_info=True)

    def _log(self, level: int, stage: str, event: str, details: Mapping[str, object]) -> None:
        try:
            payload = {**details, "stage": stage, "event": event}
            self.logger.log(level, "compose.stage", extra={"compose": payload})
        except Exception:  # pragma: no cover - defensive
            self.logger.debug("compose.logging_failed", extra={"stage": stage, "event": event}, exc_info=True)


def known_issues_from_brief(brief: str) -> list[str]:
    cleaned: list[str] = []
    for raw_line in brief.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.endswith(":"):
            continue
        cleaned_value = stripped.lstrip("-* ").strip()
        if cleaned_value:
            cleaned.append(cleaned_value)
    return cleaned[:20]


def lane_user_prompt(
    lane: str,
    context: ComposeContext,
    revision_brief: Optional[str],
    *,
    locale: str,
    instruction: str,
) -> str:
    payload: dict[str, JSONValue] = {
        "context": coerce_json_object(
            {
                "claimable_atoms": context.claimable_atoms,
                "events": context.events,
                "facts": context.facts,
                "issues": context.issues,
                "parties": context.parties,
                "procedural": context.procedural,
            }
        ),
        "lane": lane,
        "locale": locale,
    }
    if revision_brief:
        payload["revision_brief"] = revision_brief
    payload["instruction"] = instruction
    return json.dumps(payload, ensure_ascii=False)


def stable_doc_fingerprint(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def build_revision_brief(
    template: str,
    lane: str,
    structure: GuardReport,
    compliance: GuardReport,
    factuality: GuardReport,
) -> str:
    sections: list[str] = []
    if structure.errors or structure.warnings:
        sections.append("Structure:")
        for item in structure.errors:
            sections.append(f"- {item}")
        for item in structure.warnings:
            sections.append(f"- (warning) {item}")
    if compliance.errors or compliance.warnings:
        sections.append("Compliance:")
        for item in compliance.errors:
            sections.append(f"- {item}")
        for item in compliance.warnings:
            sections.append(f"- (warning) {item}")
    if factuality.errors or factuality.warnings:
        sections.append("Factuality:")
        for item in factuality.errors:
            sections.append(f"- {item}")
        for item in factuality.warnings:
            sections.append(f"- (warning) {item}")
    if not sections:
        sections.append("No issues detected; maintain required style and references.")
    header = template.format(lane=lane)
    return "\n".join([header, *sections])


def lane_status_snapshot(client: LaneOutcome, lawyer: LaneOutcome) -> JSONObject:
    return coerce_json_object(
        {
            "client": {
                "attempts": client.attempts,
                "structure": "ok" if client.structure_report.ok else "fail",
                "compliance": "ok" if client.compliance_report.ok else "fail",
                "factuality": "ok" if client.factuality_report.ok else "fail",
            },
            "lawyer": {
                "attempts": lawyer.attempts,
                "structure": "ok" if lawyer.structure_report.ok else "fail",
                "compliance": "ok" if lawyer.compliance_report.ok else "fail",
                "factuality": "ok" if lawyer.factuality_report.ok else "fail",
            },
        }
    )

def emit(
    progress: Optional[Callable[[str, str, JSONObject], None]],
    stage: str,
    event: str,
    payload: JSONObject,
) -> None:
    envelope: JSONObject = {"stage": stage, "event": event}
    for key, value in payload.items():
        envelope[key] = value
    if progress is None:
        logging.getLogger("udocket.compose.agent").debug(
            "compose.stage",
            extra={"stage": stage, "event": event, "payload": envelope},
        )
        return
    try:
        progress(stage, event, envelope)
    except Exception:
        logging.getLogger("udocket.compose.agent").debug("compose.progress_callback_failed", exc_info=True)


__all__ = [
    "ComposeOrchestrator",
    "emit",
    "known_issues_from_brief",
    "lane_status_snapshot",
    "lane_user_prompt",
    "stable_doc_fingerprint",
    "build_revision_brief",
]
