from __future__ import annotations

# pyright: strict

import json
import logging
import os
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional, Tuple, cast
from uuid import NAMESPACE_URL, uuid5

from packages.udocket_core.json_utils import (
    JSONObject,
    JSONValue,
    coerce_float,
    coerce_int,
    coerce_json_object,
    coerce_json_value,
    coerce_object_list,
    coerce_str,
    coerce_str_list,
    load_json_object,
    load_json_value,
    merge_json_objects,
    parse_json_object,
    write_json_object,
)

from .common import append_jsonl, ensure_dir, next_versioned, parse_transcript, TranscriptParse
from .common.docx import write_basic_docx
from .compose import COMPOSE_STAGE_PROFILES, ComposeStageProfile
from ..llm import LLMSettings, load_llm_settings
from ..llm.runtime import (
    ChatClientError,
    ResponseFormat,
    build_chat_client,
    build_provider_runtime_config,
)


logger = logging.getLogger("udocket.compose.agent")


DEFAULT_PROVIDER_CHAIN = ["azure"]
DEFAULT_TEMPERATURE = 0.7
DEFAULT_LAWYER_TEMPERATURE = 0.4
DEFAULT_MAX_OUTPUT_TOKENS = 24000


class ComposeStageError(RuntimeError):
    def __init__(self, stage: str, message: str) -> None:
        super().__init__(f"{stage}: {message}")
        self.stage = stage


def _normalize_stage_identifier(value: str) -> Optional[str]:
    key = (value or "").strip().lower()
    if not key:
        return None
    if key in COMPOSE_STAGE_PROFILES:
        return key
    for profile_key in COMPOSE_STAGE_PROFILES:
        short = profile_key.split(".", 1)[-1]
        if key == short:
            return profile_key
    return None


def _normalize_stage_map(
    stage_map: Mapping[str, Mapping[str, object]] | None,
) -> dict[str, JSONObject]:
    if not stage_map:
        return {}
    normalized: dict[str, JSONObject] = {}
    for raw_key, payload in stage_map.items():
        canonical = _normalize_stage_identifier(coerce_str(raw_key) or "")
        if not canonical:
            continue
        normalized[canonical] = coerce_json_object(payload)
    return normalized


def _normalize_providers(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in values:
        name = (raw or "").strip().lower()
        if not name or name in seen:
            continue
        seen.add(name)
        ordered.append(name)
    return ordered


def _load_text_file(path: Optional[Path]) -> str:
    if not path:
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _first_n_segments(transcript_text: str, limit: int = 120) -> str:
    if not transcript_text:
        return ""
    lines = transcript_text.splitlines()
    return "\n".join(lines[:limit])


def _markdown_paragraphs(markdown_text: str) -> list[str]:
    lines = markdown_text.splitlines()
    paragraphs: list[str] = []
    buffer: list[str] = []
    for line in lines:
        striped = line.strip()
        if not striped:
            if buffer:
                paragraphs.append(" ".join(buffer).strip())
                buffer.clear()
            continue
        if striped.startswith("#"):
            if buffer:
                paragraphs.append(" ".join(buffer).strip())
                buffer.clear()
            paragraphs.append(striped.lstrip("#").strip())
        else:
            buffer.append(striped)
    if buffer:
        paragraphs.append(" ".join(buffer).strip())
    return paragraphs or [markdown_text.strip()]


def _normalize_timeline_payload(payload: Mapping[str, JSONValue]) -> JSONObject:
    payload_obj = coerce_json_object(payload)
    events = coerce_object_list(payload_obj.get("events"))
    normalized_events: list[JSONValue] = []
    for event in events:
        title = coerce_str(event.get("title")) or coerce_str(event.get("summary")) or coerce_str(event.get("text")) or ""
        summary = coerce_str(event.get("summary")) or coerce_str(event.get("text")) or ""
        ts_start_val = coerce_float(event.get("ts_start"))
        ts_end_val = coerce_float(event.get("ts_end"))
        speakers = coerce_str_list(event.get("speakers"))
        if not speakers:
            solo = coerce_str(event.get("speaker"))
            if solo:
                speakers = [solo]
        references = coerce_str_list(event.get("references"))
        labels = coerce_str_list(event.get("labels"), unique=True)
        signature = "|".join(
            [
                "compose.timeline",
                "" if ts_start_val is None else f"{ts_start_val:.3f}",
                "" if ts_end_val is None else f"{ts_end_val:.3f}",
                "::".join(speakers),
                summary or "",
            ]
        )
        derived_uuid = uuid5(NAMESPACE_URL, signature)
        existing_uuid = coerce_str(event.get("uuid"))
        event_uuid = existing_uuid or str(derived_uuid)
        existing_id = coerce_str(event.get("id"))
        event_id = existing_id or event_uuid
        normalized_events.append(
            _payload_dict(
                id=event_id,
                uuid=event_uuid,
                title=title or summary or "Timeline event",
                summary=summary,
                ts_start=ts_start_val,
                ts_end=ts_end_val,
                speakers=speakers,
                references=references,
                labels=labels,
            )
        )

    result: JSONObject = {
        key: coerce_json_value(value)
        for key, value in payload_obj.items()
        if key != "events"
    }
    result["events"] = normalized_events
    return result


def _normalize_graph_payload(payload: Mapping[str, JSONValue]) -> JSONObject:
    payload_obj = coerce_json_object(payload)
    entities_raw = coerce_object_list(payload_obj.get("entities"))
    relations_raw = coerce_object_list(payload_obj.get("relationships"))

    normalized_entities: list[JSONValue] = []
    for entity in entities_raw:
        name = coerce_str(entity.get("name")) or ""
        entity_type = coerce_str(entity.get("type")) or "UNKNOWN"
        signature = f"compose.entity|{entity_type}|{name.lower()}"
        derived_uuid = uuid5(NAMESPACE_URL, signature)
        existing_uuid = coerce_str(entity.get("uuid"))
        entity_uuid = existing_uuid or str(derived_uuid)
        entity_id = coerce_str(entity.get("id")) or entity_uuid
        aliases = coerce_str_list(entity.get("aliases"))
        mentions: list[JSONValue] = []
        for mention in coerce_object_list(entity.get("mentions")):
            text = coerce_str(mention.get("text")) or coerce_str(mention.get("excerpt"))
            if not text:
                continue
            ts_normalized = coerce_float(mention.get("ts"))
            if ts_normalized is None:
                ts_normalized = coerce_float(mention.get("timestamp"))
            mentions.append(_payload_dict(ts=ts_normalized, text=text))
        normalized_entities.append(
            _payload_dict(
                id=entity_id,
                uuid=entity_uuid,
                name=name,
                type=entity_type,
                aliases=aliases,
                mentions=mentions,
                description=coerce_str(entity.get("description")) or "",
            )
        )

    normalized_relations: list[JSONValue] = []
    for relation in relations_raw:
        relation_type = coerce_str(relation.get("type")) or "RELATED_TO"
        source = coerce_str(relation.get("source")) or ""
        target = coerce_str(relation.get("target")) or ""
        signature = f"compose.relation|{relation_type}|{source.lower()}|{target.lower()}"
        derived_uuid = uuid5(NAMESPACE_URL, signature)
        existing_uuid = coerce_str(relation.get("uuid"))
        relation_uuid = existing_uuid or str(derived_uuid)
        relation_id = coerce_str(relation.get("id")) or relation_uuid
        evidence_entries: list[JSONValue] = []
        for item in coerce_object_list(relation.get("evidence")):
            text = coerce_str(item.get("text")) or coerce_str(item.get("excerpt"))
            if not text:
                continue
            ts_value = coerce_float(item.get("ts"))
            if ts_value is None:
                ts_value = coerce_float(item.get("timestamp"))
            evidence_entries.append(_payload_dict(ts=ts_value, text=text))
        normalized_relations.append(
            _payload_dict(
                id=relation_id,
                uuid=relation_uuid,
                type=relation_type,
                source=source,
                target=target,
                summary=coerce_str(relation.get("summary")) or "",
                evidence=evidence_entries,
            )
        )

    result: JSONObject = {
        key: coerce_json_value(value)
        for key, value in payload_obj.items()
        if key not in {"entities", "relationships"}
    }
    result["entities"] = normalized_entities
    result["relationships"] = normalized_relations
    return result


def _payload_dict(**items: object) -> JSONObject:
    return {key: coerce_json_value(value) for key, value in items.items()}


@dataclass
class ComposeConfig:
    provider_chain: list[str] = field(default_factory=lambda: list(DEFAULT_PROVIDER_CHAIN))
    temperature: float = DEFAULT_TEMPERATURE
    lawyer_temperature: float = DEFAULT_LAWYER_TEMPERATURE
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS
    debug: bool = False

    @classmethod
    def from_env(cls) -> "ComposeConfig":
        providers_env = os.getenv("COMPOSE_PROVIDER_CHAIN", "")
        providers: list[str]
        if providers_env:
            providers = _normalize_providers(providers_env.split(","))
        else:
            providers = list(DEFAULT_PROVIDER_CHAIN)
        temp = os.getenv("COMPOSE_TEMPERATURE")
        lawyer_temp = os.getenv("COMPOSE_LAWYER_TEMPERATURE")
        max_tokens_env = os.getenv("COMPOSE_MAX_OUTPUT_TOKENS")
        debug = os.getenv("DEBUG", "0").strip().lower() in {"1", "true", "yes", "on"}
        try:
            temperature = float(temp) if temp else DEFAULT_TEMPERATURE
        except (TypeError, ValueError):
            temperature = DEFAULT_TEMPERATURE
        try:
            lawyer_temperature = float(lawyer_temp) if lawyer_temp else DEFAULT_LAWYER_TEMPERATURE
        except (TypeError, ValueError):
            lawyer_temperature = DEFAULT_LAWYER_TEMPERATURE
        try:
            max_tokens = int(max_tokens_env) if max_tokens_env else DEFAULT_MAX_OUTPUT_TOKENS
        except (TypeError, ValueError):
            max_tokens = DEFAULT_MAX_OUTPUT_TOKENS
        if not providers:
            providers = list(DEFAULT_PROVIDER_CHAIN)
        return cls(
            provider_chain=providers,
            temperature=temperature,
            lawyer_temperature=lawyer_temperature,
            max_output_tokens=max_tokens,
            debug=debug,
        )

    def stage_max_tokens(self, stage_key: str, model_max: Optional[int]) -> int:
        profile = COMPOSE_STAGE_PROFILES.get(stage_key)
        base = self.max_output_tokens
        if profile and profile.output_reserve_tokens > 0:
            base = max(base, profile.output_reserve_tokens)
        if model_max and model_max > 0:
            base = min(base, model_max)
        return max(base, 512)


@dataclass
class ComposeArtifacts:
    timeline_file: Optional[Path] = None
    graph_file: Optional[Path] = None
    entities_file: Optional[Path] = None
    client_markdown: Optional[Path] = None
    lawyer_markdown: Optional[Path] = None
    client_docx: Optional[Path] = None
    lawyer_docx: Optional[Path] = None
    timeline_summary: Optional[Path] = None
    entity_brief: Optional[Path] = None
    graph_visual: Optional[Path] = None


@dataclass
class ComposeResult:
    status: str
    artifacts: ComposeArtifacts
    meta_json: Path
    audit_jsonl: Path
    provider_chain: list[str]
    stage_usage: dict[str, dict[str, int]]


class ComposeAgent:
    def __init__(self, config: Optional[ComposeConfig] = None) -> None:
        self.config = config or ComposeConfig.from_env()
        self.settings: LLMSettings = load_llm_settings()
        self.logger = logger

    def compose(
        self,
        *,
        case_id: str,
        case_dir: Path,
        job_id: str,
        summary_json_path: Optional[Path],
        summary_markdown_path: Optional[Path],
        transcript_path: Optional[Path],
        timeline_seed_path: Optional[Path] = None,
        entity_hint_path: Optional[Path] = None,
        staff_report_path: Optional[Path] = None,
        intake: Optional[Mapping[str, Any]] = None,
        case_metadata: Optional[Mapping[str, Any]] = None,
        provider_chain: Optional[Sequence[str]] = None,
        stage_map: Optional[Mapping[str, Mapping[str, Any]]] = None,
        provider_credentials: Optional[Mapping[str, Mapping[str, Any]]] = None,
        targets: Optional[Sequence[str]] = None,
        attachments: Optional[Sequence[Mapping[str, Any]]] = None,
        progress_callback: Optional[Callable[[str, str, Mapping[str, JSONValue]], None]] = None,
    ) -> ComposeResult:
        case_dir = Path(case_dir)
        analysis_dir = case_dir / "analysis"
        ops_dir = case_dir / "ops"
        ensure_dir(analysis_dir)
        ensure_dir(ops_dir)

        summary_markdown = _load_text_file(summary_markdown_path)
        summary_data: JSONObject = {}
        if summary_json_path and summary_json_path.exists():
            try:
                summary_data = load_json_object(summary_json_path, context="summary data")
            except ValueError as exc:
                raise ComposeStageError("compose.context_builder", str(exc)) from exc

        timeline_seeds: list[JSONObject] = []
        if timeline_seed_path and timeline_seed_path.exists():
            try:
                payload = load_json_value(timeline_seed_path, context="timeline seeds")
            except ValueError as exc:
                raise ComposeStageError("compose.timeline_builder", str(exc)) from exc

            if isinstance(payload, Mapping):
                events = coerce_object_list(payload.get("events"))
            elif isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
                events = [item for item in payload if isinstance(item, Mapping)]
                events = [coerce_json_object(event) for event in events]
            else:
                events = []
            timeline_seeds = events

        entity_hints: JSONObject = {}
        if entity_hint_path and entity_hint_path.exists():
            try:
                entity_hints = load_json_object(entity_hint_path, context="entity hints")
            except ValueError as exc:
                raise ComposeStageError("compose.entity_brief", str(exc)) from exc

        staff_report = _load_text_file(staff_report_path)
        transcript_text = _load_text_file(transcript_path)
        transcript_parse = (
            parse_transcript(transcript_path)
            if transcript_path and transcript_path.exists()
            else None
        )

        normalized_stage_map = _normalize_stage_map(stage_map)
        requested_targets = set(targets or [
            "timeline",
            "graph",
            "client",
            "lawyer",
            "qa",
        ])

        provider_chain = list(provider_chain or self.config.provider_chain)
        provider_credentials_map: dict[str, JSONObject] = {
            provider_name: coerce_json_object(payload)
            for provider_name, payload in (provider_credentials or {}).items()
        }

        state_usage: dict[str, dict[str, int]] = {}
        stage_order: list[tuple[str, str]] = [
            ("compose.context_builder", "context"),
            ("compose.timeline_builder", "timeline"),
            ("compose.timeline_summary", "timeline_summary"),
            ("compose.graph_builder", "graph"),
            ("compose.entity_brief", "entity_brief"),
            ("compose.graph_visual", "graph_visual"),
            ("compose.client_brief", "client"),
            ("compose.lawyer_brief", "lawyer"),
            ("compose.qa_review", "qa"),
        ]

        context_payload: JSONObject = {}
        timeline_payload: JSONObject = {}
        graph_payload: JSONObject = {}
        client_markdown = ""
        lawyer_markdown = ""
        qa_payload: JSONObject = {}
        used_providers: list[str] = []
        case_metadata_obj = coerce_json_object(case_metadata) if case_metadata else {}
        timeline_summary_markdown = ""
        entity_brief_markdown = ""
        graph_visual_payload: JSONObject = {}
        intake_obj = coerce_json_object(intake) if intake else {}
        attachments_list: list[JSONObject] = [
            coerce_json_object(item) for item in (attachments or [])
        ]

        def emit(stage: str, event: str, details: Mapping[str, JSONValue] | None = None) -> None:
            if progress_callback is None:
                if self.config.debug:
                    self.logger.info(
                        "compose.stage",
                        extra={"stage": stage, "event": event, "details": dict(details or {})},
                    )
                return
            try:
                progress_callback(stage, event, details or {})
            except Exception:  # pragma: no cover - defensive
                self.logger.debug("progress callback failed", exc_info=True)

        def _bucket_enabled(bucket: str) -> bool:
            if bucket == "context":
                return True
            if bucket == "timeline":
                return any(target in requested_targets for target in {"timeline", "client", "lawyer", "qa"})
            if bucket == "timeline_summary":
                return any(target in requested_targets for target in {"timeline", "client", "lawyer", "qa"})
            if bucket == "graph":
                return any(target in requested_targets for target in {"graph", "client", "lawyer", "qa"})
            if bucket in {"entity_brief", "graph_visual"}:
                return any(target in requested_targets for target in {"graph", "client", "lawyer", "qa"})
            return bucket in requested_targets

        for stage_key, bucket in stage_order:
            if not _bucket_enabled(bucket):
                continue

            emit(stage_key, "start")
            try:
                response, usage, provider = self._invoke_stage(
                    stage_key=stage_key,
                    normalized_stage_map=normalized_stage_map,
                    provider_chain=provider_chain,
                    provider_credentials=provider_credentials_map,
                    transcript_text=transcript_text,
                    transcript_parse=transcript_parse,
                    summary_markdown=summary_markdown,
                    summary_data=summary_data,
                    timeline_seeds=tuple(timeline_seeds),
                    entity_hints=entity_hints,
                    staff_report=staff_report,
                    case_brief=context_payload,
                    timeline_payload=timeline_payload,
                    graph_payload=graph_payload,
                    intake=intake_obj,
                    case_metadata=case_metadata_obj,
                    timeline_summary=timeline_summary_markdown,
                    entity_brief=entity_brief_markdown,
                    graph_visual=graph_visual_payload,
                    attachments=tuple(attachments_list),
                    client_markdown=client_markdown,
                    lawyer_markdown=lawyer_markdown,
                )
            except ComposeStageError:
                emit(stage_key, "failed")
                raise
            used_providers.append(provider)
            if usage:
                state_usage[stage_key] = usage

            if stage_key == "compose.context_builder":
                context_payload = (
                    coerce_json_object(response)
                    if isinstance(response, Mapping)
                    else {}
                )
            elif stage_key == "compose.timeline_builder":
                if isinstance(response, Mapping):
                    timeline_payload = _normalize_timeline_payload(response)
            elif stage_key == "compose.timeline_summary":
                timeline_summary_markdown = str(response)
            elif stage_key == "compose.graph_builder":
                if isinstance(response, Mapping):
                    graph_payload = _normalize_graph_payload(response)
            elif stage_key == "compose.entity_brief":
                entity_brief_markdown = str(response)
            elif stage_key == "compose.graph_visual":
                graph_visual_payload = (
                    coerce_json_object(response)
                    if isinstance(response, Mapping)
                    else {}
                )
            elif stage_key == "compose.client_brief":
                client_markdown = str(response)
            elif stage_key == "compose.lawyer_brief":
                lawyer_markdown = str(response)
            elif stage_key == "compose.qa_review":
                qa_payload = (
                    coerce_json_object(response)
                    if isinstance(response, Mapping)
                    else {}
                )

            emit(stage_key, "complete", {"provider": provider})

        artifacts = ComposeArtifacts()

        if "timeline" in requested_targets and timeline_payload:
            timeline_file = next_versioned(analysis_dir / f"{job_id}__timeline_v2.json")
            write_json_object(timeline_file, timeline_payload)
            artifacts.timeline_file = timeline_file

        if timeline_summary_markdown:
            timeline_summary_file = next_versioned(analysis_dir / f"{job_id}__compose_timeline_v1.md")
            timeline_summary_file.write_text(timeline_summary_markdown, encoding="utf-8")
            artifacts.timeline_summary = timeline_summary_file

        if "graph" in requested_targets and graph_payload:
            graph_file = next_versioned(analysis_dir / f"{job_id}__graph_v2.json")
            write_json_object(graph_file, graph_payload)
            artifacts.graph_file = graph_file
            entities_value = graph_payload.get("entities")
            if isinstance(entities_value, list):
                entities_file = next_versioned(analysis_dir / f"{job_id}__entities_v2.json")
                write_json_object(entities_file, {"entities": entities_value})
                artifacts.entities_file = entities_file

        if entity_brief_markdown:
            entity_brief_file = next_versioned(analysis_dir / f"{job_id}__compose_entities_v1.md")
            entity_brief_file.write_text(entity_brief_markdown, encoding="utf-8")
            artifacts.entity_brief = entity_brief_file

        if graph_visual_payload:
            graph_visual_file = next_versioned(analysis_dir / f"{job_id}__compose_graph_visual_v1.json")
            write_json_object(graph_visual_file, graph_visual_payload)
            artifacts.graph_visual = graph_visual_file

        if "client" in requested_targets and client_markdown:
            client_md = next_versioned(analysis_dir / f"{job_id}__compose_client_v1.md")
            client_md.write_text(client_markdown, encoding="utf-8")
            artifacts.client_markdown = client_md
            docx_path = next_versioned(analysis_dir / f"{job_id}__compose_client_v1.docx")
            write_basic_docx(paragraphs=_markdown_paragraphs(client_markdown), output_path=docx_path, title="Client Deliverable")
            artifacts.client_docx = docx_path

        if "lawyer" in requested_targets and lawyer_markdown:
            lawyer_md = next_versioned(analysis_dir / f"{job_id}__compose_lawyer_v1.md")
            lawyer_md.write_text(lawyer_markdown, encoding="utf-8")
            artifacts.lawyer_markdown = lawyer_md
            docx_path = next_versioned(analysis_dir / f"{job_id}__compose_lawyer_v1.docx")
            write_basic_docx(paragraphs=_markdown_paragraphs(lawyer_markdown), output_path=docx_path, title="Lawyer Deliverable")
            artifacts.lawyer_docx = docx_path

        meta_payload = _payload_dict(
            case_id=case_id,
            job_id=job_id,
            summary_json=str(summary_json_path) if summary_json_path else None,
            summary_markdown=str(summary_markdown_path) if summary_markdown_path else None,
            transcript_path=str(transcript_path) if transcript_path else None,
            timeline_file=str(artifacts.timeline_file) if artifacts.timeline_file else None,
            graph_file=str(artifacts.graph_file) if artifacts.graph_file else None,
            entities_file=str(artifacts.entities_file) if artifacts.entities_file else None,
            client_markdown=str(artifacts.client_markdown) if artifacts.client_markdown else None,
            lawyer_markdown=str(artifacts.lawyer_markdown) if artifacts.lawyer_markdown else None,
            client_docx=str(artifacts.client_docx) if artifacts.client_docx else None,
            lawyer_docx=str(artifacts.lawyer_docx) if artifacts.lawyer_docx else None,
            context=context_payload,
            timeline=timeline_payload,
            graph=graph_payload,
            qa=qa_payload,
            case_metadata=case_metadata_obj,
            timeline_summary=timeline_summary_markdown,
            entity_brief=entity_brief_markdown,
            graph_visual=graph_visual_payload,
            provider_chain=used_providers,
            stage_usage=state_usage,
            status="ok",
        )

        meta_json = ops_dir / f"{job_id}__compose_log.json"
        write_json_object(meta_json, meta_payload)

        audit_jsonl = ops_dir / "ops_compose.jsonl"
        append_jsonl(
            audit_jsonl,
            {
                "case_id": case_id,
                "job_id": job_id,
                "status": "ok",
                "timeline_file": str(artifacts.timeline_file) if artifacts.timeline_file else None,
                "graph_file": str(artifacts.graph_file) if artifacts.graph_file else None,
                "client_markdown": str(artifacts.client_markdown) if artifacts.client_markdown else None,
                "lawyer_markdown": str(artifacts.lawyer_markdown) if artifacts.lawyer_markdown else None,
            },
        )

        return ComposeResult(
            status="ok",
            artifacts=artifacts,
            meta_json=meta_json,
            audit_jsonl=audit_jsonl,
            provider_chain=used_providers,
            stage_usage=state_usage,
        )

    def _invoke_stage(
        self,
        *,
        stage_key: str,
        normalized_stage_map: Mapping[str, JSONObject],
        provider_chain: Sequence[str],
        provider_credentials: Mapping[str, JSONObject],
        transcript_text: str,
        transcript_parse: TranscriptParse | None,
        summary_markdown: str,
        summary_data: JSONObject,
        timeline_seeds: Sequence[JSONObject],
        entity_hints: JSONObject,
        staff_report: str,
        case_brief: JSONObject,
        timeline_payload: JSONObject,
        graph_payload: JSONObject,
        intake: JSONObject,
        case_metadata: JSONObject,
        timeline_summary: str,
        entity_brief: str,
        graph_visual: JSONObject,
        attachments: Sequence[JSONObject],
        client_markdown: str,
        lawyer_markdown: str,
    ) -> tuple[JSONValue, dict[str, int], str]:
        assignment = self.settings.stage(stage_key)
        override = normalized_stage_map.get(stage_key)
        providers_list: list[str] = []
        if override:
            providers_list.extend(_normalize_providers(coerce_str_list(override.get("providers"))))
            provider_value = coerce_str(override.get("provider"))
            if provider_value:
                providers_list.insert(0, provider_value)
        if assignment and assignment.providers:
            providers_list.extend(assignment.providers)
        providers_list.extend(provider_chain)
        providers = _normalize_providers(providers_list or DEFAULT_PROVIDER_CHAIN)

        model_override = coerce_str(override.get("model")) if override else None
        model_name = model_override or (assignment.model if assignment and assignment.model else "")

        options_obj: JSONObject = {}
        if assignment and assignment.options:
            options_obj = merge_json_objects(options_obj, assignment.options)
        if override:
            override_options = override.get("options")
            if isinstance(override_options, Mapping):
                options_obj = merge_json_objects(options_obj, override_options)

        max_tokens_override = coerce_int(
            override.get("max_tokens") if override else None
        )
        if max_tokens_override is None and override:
            max_tokens_override = coerce_int(override.get("max_output_tokens"))

        last_error: Exception | None = None
        for provider_name in providers:
            provider_meta = self.settings.provider(provider_name)
            if provider_meta is None:
                continue

            credential_payload = provider_credentials.get(provider_name)
            resolved_model_name = model_name or (assignment.model if assignment and assignment.model else "")
            if not resolved_model_name:
                last_error = ComposeStageError(stage_key, "No model configured")
                continue

            try:
                runtime_cfg = build_provider_runtime_config(
                    provider=provider_meta,
                    model_name=resolved_model_name,
                    credential_payload=credential_payload,
                    options=options_obj if options_obj else None,
                )
            except ChatClientError as exc:
                last_error = exc
                continue

            try:
                client = build_chat_client(provider_runtime=runtime_cfg)
            except ChatClientError as exc:
                last_error = exc
                continue

            profile = COMPOSE_STAGE_PROFILES.get(stage_key)
            max_tokens = self.config.stage_max_tokens(
                stage_key,
                runtime_cfg.model.max_output_tokens if runtime_cfg.model and runtime_cfg.model.max_output_tokens else None,
            )
            if max_tokens_override and max_tokens_override > 0:
                max_tokens = min(max_tokens, max_tokens_override)

            temperature = (
                self.config.lawyer_temperature if stage_key == "compose.lawyer_brief" else self.config.temperature
            )
            override_temperature = coerce_float(options_obj.get("temperature"))
            if override_temperature is not None:
                temperature = override_temperature

            system_prompt, user_prompt, response_format = self._build_prompts(
                stage_key=stage_key,
                transcript_text=transcript_text,
                summary_markdown=summary_markdown,
                summary_data=summary_data,
                timeline_seeds=timeline_seeds,
                entity_hints=entity_hints,
                staff_report=staff_report,
                case_brief=case_brief,
                timeline_payload=timeline_payload,
                graph_payload=graph_payload,
                intake=intake,
                case_metadata=case_metadata,
                timeline_summary=timeline_summary,
                entity_brief=entity_brief,
                graph_visual=graph_visual,
                attachments=attachments,
                transcript_parse=transcript_parse,
                profile=profile,
                client_markdown=client_markdown,
                lawyer_markdown=lawyer_markdown,
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            try:
                content, usage = client.chat(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                )
            except ChatClientError as exc:
                last_error = exc
                continue

            try:
                parsed = self._parse_stage_output(stage_key, content)
            except ComposeStageError as exc:
                last_error = exc
                continue

            usage_int: dict[str, int] = {
                key: value for key, value in usage.items() if isinstance(value, int)
            }
            return parsed, usage_int, provider_name

        if last_error:
            raise ComposeStageError(stage_key, str(last_error))
        raise ComposeStageError(stage_key, "No provider available")

    def _build_prompts(
        self,
        *,
        stage_key: str,
        transcript_text: str,
        summary_markdown: str,
        summary_data: JSONObject,
        timeline_seeds: Sequence[JSONObject],
        entity_hints: JSONObject,
        staff_report: str,
        case_brief: JSONObject,
        timeline_payload: JSONObject,
        graph_payload: JSONObject,
        intake: JSONObject,
        case_metadata: JSONObject,
        timeline_summary: str,
        entity_brief: str,
        graph_visual: JSONObject,
        attachments: Sequence[JSONObject],
        transcript_parse: TranscriptParse | None,
        profile: ComposeStageProfile | None,
        client_markdown: str,
        lawyer_markdown: str,
    ) -> Tuple[str, str, ResponseFormat | None]:
        transcript_excerpt = _first_n_segments(transcript_text, limit=240)
        base_system = (
            "You are the uDocket Compose agent, a Canadian legal assistant who builds clear, "
            "auditable deliverables from transcripts, summaries, and prior analyses."
        )
        _ = profile
        _ = transcript_parse

        if stage_key == "compose.context_builder":
            response_schema = cast(
                ResponseFormat,
                {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "compose_context_response",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "parties": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string"},
                                            "role": {"type": "string"},
                                            "description": {"type": "string"},
                                        },
                                        "required": ["name"],
                                    },
                                },
                                "issues": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "label": {"type": "string"},
                                            "summary": {"type": "string"},
                                        },
                                        "required": ["label"],
                                    },
                                },
                                "posture": {"type": "string"},
                                "risks": {"type": "array", "items": {"type": "string"}},
                                "next_steps": {"type": "array", "items": {"type": "string"}},
                                "key_facts": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["parties", "issues"],
                        },
                    },
                },
            )
            user_payload = _payload_dict(
                intake=intake,
                case_metadata=case_metadata,
                summary=summary_data,
                summary_markdown=summary_markdown,
                staff_report=staff_report,
                transcript_excerpt=transcript_excerpt,
            )
            user_prompt = (
                "Use the provided summary outputs, staff report, and transcript excerpt to build a concise "
                "case brief JSON with parties, legal posture, key issues, risks, and next steps."
            ) + "\n\n" + json.dumps(user_payload, ensure_ascii=False)
            return base_system, user_prompt, response_schema

        if stage_key == "compose.timeline_builder":
            response_schema = cast(
                ResponseFormat,
                {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "compose_timeline_response",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "revision": {"type": "string"},
                                "events": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "id": {"type": "string"},
                                            "title": {"type": "string"},
                                            "summary": {"type": "string"},
                                            "ts_start": {"type": "number"},
                                            "ts_end": {"type": "number"},
                                            "speakers": {"type": "array", "items": {"type": "string"}},
                                            "references": {"type": "array", "items": {"type": "string"}},
                                            "labels": {"type": "array", "items": {"type": "string"}},
                                        },
                                        "required": ["id", "title", "summary", "ts_start"],
                                    },
                                },
                            },
                            "required": ["events"],
                        },
                    },
                },
            )
            payload = _payload_dict(
                case_brief=case_brief,
                timeline_seeds=list(timeline_seeds),
                summary=summary_data,
                transcript_excerpt=transcript_excerpt,
                case_metadata=case_metadata,
            )
            user_prompt = (
                "Produce timeline_v2 JSON describing the proceedings. Each event must reference "
                "timestamps and speakers when known, include a deterministic `id`, and mirror the "
                "existing `uuid` from seeds when available. Generate stable `uuid` values (use the "
                "provided one or derive via UUID5 over the event signature) so downstream tools can "
                "cross-link results. Keep the order chronological."
            ) + "\n\n" + json.dumps(payload, ensure_ascii=False)
            return base_system, user_prompt, response_schema

        if stage_key == "compose.timeline_summary":
            payload = _payload_dict(
                case_metadata=case_metadata,
                timeline=timeline_payload,
                summary=summary_data,
            )
            user_prompt = (
                "Create a Markdown narrative capturing the timeline."
                " Include sections for 'Key Milestones' and 'Upcoming Deadlines' when applicable,"
                " with bullet lists referencing timestamps in [mm:ss] format."
                " Highlight speakers or parties for each item."
            ) + "\n\n" + json.dumps(payload, ensure_ascii=False)
            return base_system, user_prompt, None

        if stage_key == "compose.graph_builder":
            response_schema = cast(
                ResponseFormat,
                {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "compose_graph_response",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "entities": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "id": {"type": "string"},
                                            "name": {"type": "string"},
                                            "type": {"type": "string"},
                                            "description": {"type": "string"},
                                            "mentions": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "timestamp": {"type": "number"},
                                                        "excerpt": {"type": "string"},
                                                    },
                                                    "required": ["excerpt"],
                                                },
                                            },
                                        },
                                        "required": ["id", "name", "type"],
                                    },
                                },
                                "relationships": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "id": {"type": "string"},
                                            "source": {"type": "string"},
                                            "target": {"type": "string"},
                                            "type": {"type": "string"},
                                            "summary": {"type": "string"},
                                            "evidence": {"type": "array", "items": {"type": "string"}},
                                        },
                                        "required": ["id", "source", "target", "type"],
                                    },
                                },
                            },
                            "required": ["entities"],
                        },
                    },
                },
            )
            payload = _payload_dict(
                case_brief=case_brief,
                entity_hints=entity_hints,
                timeline=timeline_payload,
                summary=summary_data,
                transcript_excerpt=transcript_excerpt,
                case_metadata=case_metadata,
            )
            user_prompt = (
                "Generate entities and relationships JSON. Include evidence references to transcript timestamps or timeline IDs."
                " Preserve provided entity/relationship IDs when present and emit stable UUID values"
                " (existing `uuid` or new UUID5 signatures). Every entity and relationship must have"
                " both `id` and `uuid` fields."
            ) + "\n\n" + json.dumps(payload, ensure_ascii=False)
            return base_system, user_prompt, response_schema

        if stage_key == "compose.entity_brief":
            payload = _payload_dict(
                case_metadata=case_metadata,
                entity_hints=entity_hints,
                graph=graph_payload,
                timeline=timeline_payload,
            )
            user_prompt = (
                "Draft a Markdown briefing summarizing principal entities, their roles, and notable relationships."
                " Organize content into 'Primary Parties', 'Supporting Participants', and 'Key Relationships'."
                " Reference timestamps or timeline event IDs when available."
            ) + "\n\n" + json.dumps(payload, ensure_ascii=False)
            return base_system, user_prompt, None

        if stage_key == "compose.graph_visual":
            response_schema = cast(
                ResponseFormat,
                {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "compose_graph_visual_response",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "embed_html": {"type": "string"},
                                "alt_text": {"type": "string"},
                                "size_hint": {
                                    "type": "object",
                                    "properties": {
                                        "width": {"type": "string"},
                                        "height": {"type": "string"},
                                    },
                                },
                                "notes": {"type": "string"},
                            },
                            "required": ["embed_html", "alt_text"],
                        },
                    },
                },
            )
            payload = _payload_dict(
                case_metadata=case_metadata,
                graph=graph_payload,
                existing_visual=graph_visual,
            )
            user_prompt = (
                "Plan an embeddable relationship graph snippet."
                " Return responsive HTML (max-width 100%), clear alt text summarizing the network,"
                " and optional notes with styling guidance or next actions (PNG export, etc.)."
            ) + "\n\n" + json.dumps(payload, ensure_ascii=False)
            return base_system, user_prompt, response_schema

        if stage_key == "compose.client_brief":
            payload = _payload_dict(
                case_brief=case_brief,
                timeline=timeline_payload,
                graph=graph_payload,
                summary_text=summary_markdown,
                staff_report=staff_report,
                intake=intake,
                case_metadata=case_metadata,
                timeline_summary=timeline_summary,
                entity_brief=entity_brief,
                graph_visual=graph_visual,
            )
            user_prompt = (
                "Draft a Markdown brief for the client in grade-six reading level. Include sections: Overview, Timeline Highlights, Key Issues, Next Steps."
            ) + "\n\n" + json.dumps(payload, ensure_ascii=False)
            return base_system, user_prompt, None

        if stage_key == "compose.lawyer_brief":
            payload = _payload_dict(
                case_brief=case_brief,
                timeline=timeline_payload,
                graph=graph_payload,
                summary_text=summary_markdown,
                case_metadata=case_metadata,
                timeline_summary=timeline_summary,
                entity_brief=entity_brief,
                graph_visual=graph_visual,
            )
            user_prompt = (
                "Draft a professional Markdown brief for counsel. Organize by issue, reference timestamps, and list supporting evidence."
            ) + "\n\n" + json.dumps(payload, ensure_ascii=False)
            return base_system, user_prompt, None

        if stage_key == "compose.qa_review":
            response_schema = cast(
                ResponseFormat,
                {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "compose_qa_response",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "status": {"type": "string"},
                                "alerts": {"type": "array", "items": {"type": "string"}},
                                "recommendations": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["status"],
                        },
                    },
                },
            )
            payload = _payload_dict(
                case_brief=case_brief,
                timeline=timeline_payload,
                graph=graph_payload,
                client_markdown=client_markdown,
                lawyer_markdown=lawyer_markdown,
                case_metadata=case_metadata,
                timeline_summary=timeline_summary,
                entity_brief=entity_brief,
                graph_visual=graph_visual,
                attachments=list(attachments),
            )
            user_prompt = (
                "Review the compose outputs for completeness and compliance. Respond with JSON describing status, alerts, and recommendations."
            ) + "\n\n" + json.dumps(payload, ensure_ascii=False)
            return base_system, user_prompt, response_schema

        raise ComposeStageError(stage_key, "Unknown stage")

    def _parse_stage_output(self, stage_key: str, content: str) -> JSONValue:
        if stage_key in {
            "compose.context_builder",
            "compose.timeline_builder",
            "compose.graph_builder",
            "compose.graph_visual",
            "compose.qa_review",
        }:
            try:
                parsed = parse_json_object(content, context=f"{stage_key} response")
            except ValueError as exc:
                raise ComposeStageError(stage_key, str(exc))
            return parsed

        if stage_key in {"compose.client_brief", "compose.lawyer_brief"}:
            return content.strip()

        return content


__all__ = [
    "ComposeAgent",
    "ComposeConfig",
    "ComposeResult",
    "ComposeStageError",
    "ComposeArtifacts",
]
