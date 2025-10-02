from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .common import AnalysisArtifact, ensure_dir, next_versioned, parse_transcript, sha256_file
from .common.docx import write_basic_docx
from .compose import COMPOSE_STAGE_PROFILES
from ..llm import LLMSettings, load_llm_settings
from ..llm.runtime import ChatClient, ChatClientError, build_chat_client, build_provider_runtime_config


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


def _normalize_stage_map(stage_map: Optional[Dict[str, Dict[str, Any]]]) -> Dict[str, Dict[str, Any]]:
    if not stage_map:
        return {}
    normalized: Dict[str, Dict[str, Any]] = {}
    for raw_key, payload in stage_map.items():
        canonical = _normalize_stage_identifier(raw_key)
        if not canonical:
            continue
        if not isinstance(payload, Mapping):
            continue
        normalized[canonical] = {str(k): v for k, v in payload.items()}
    return normalized


def _normalize_providers(values: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    ordered: List[str] = []
    for raw in values:
        name = (raw or "").strip().lower()
        if not name or name in seen:
            continue
        seen.add(name)
        ordered.append(name)
    return ordered


def _collect_requested_providers(
    default_chain: Sequence[str],
    override_chain: Sequence[str],
    stage_map: Mapping[str, Mapping[str, Any]],
) -> List[str]:
    providers = _normalize_providers(override_chain or default_chain)
    for payload in stage_map.values():
        if "provider" in payload:
            providers.extend(_normalize_providers([str(payload["provider"])]) )
        if "providers" in payload and isinstance(payload["providers"], Sequence):
            providers.extend(_normalize_providers(payload["providers"]))
    return _normalize_providers(providers)


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


def _markdown_paragraphs(markdown_text: str) -> List[str]:
    lines = markdown_text.splitlines()
    paragraphs: List[str] = []
    buffer: List[str] = []
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


@dataclass
class ComposeConfig:
    provider_chain: List[str] = field(default_factory=lambda: list(DEFAULT_PROVIDER_CHAIN))
    temperature: float = DEFAULT_TEMPERATURE
    lawyer_temperature: float = DEFAULT_LAWYER_TEMPERATURE
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS
    debug: bool = False

    @classmethod
    def from_env(cls) -> "ComposeConfig":
        providers_env = os.getenv("COMPOSE_PROVIDER_CHAIN", "")
        providers: List[str]
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


@dataclass
class ComposeResult:
    status: str
    artifacts: ComposeArtifacts
    meta_json: Path
    audit_jsonl: Path
    provider_chain: List[str]
    stage_usage: Dict[str, Dict[str, int]]


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
        intake: Optional[Dict[str, Any]] = None,
        provider_chain: Optional[List[str]] = None,
        stage_map: Optional[Dict[str, Dict[str, Any]]] = None,
        provider_credentials: Optional[Dict[str, Dict[str, Any]]] = None,
        targets: Optional[Sequence[str]] = None,
        attachments: Optional[Sequence[Dict[str, Any]]] = None,
        progress_callback: Optional[Callable[[str, str, Dict[str, Any]], None]] = None,
    ) -> ComposeResult:
        case_dir = Path(case_dir)
        analysis_dir = case_dir / "analysis"
        ops_dir = case_dir / "ops"
        ensure_dir(analysis_dir)
        ensure_dir(ops_dir)

        summary_data: Dict[str, Any] = {}
        summary_markdown = _load_text_file(summary_markdown_path)
        if summary_json_path and summary_json_path.exists():
            try:
                summary_data = json.loads(summary_json_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise ComposeStageError("compose.context_builder", f"Summary JSON invalid: {exc}") from exc

        timeline_seeds: List[Dict[str, Any]] = []
        if timeline_seed_path and timeline_seed_path.exists():
            try:
                payload = json.loads(timeline_seed_path.read_text(encoding="utf-8"))
                if isinstance(payload, dict) and "events" in payload:
                    events = payload.get("events")
                else:
                    events = payload
                if isinstance(events, list):
                    timeline_seeds = [item for item in events if isinstance(item, dict)]
            except json.JSONDecodeError:
                timeline_seeds = []

        entity_hints: Dict[str, Any] = {}
        if entity_hint_path and entity_hint_path.exists():
            try:
                payload = json.loads(entity_hint_path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    entity_hints = payload
            except json.JSONDecodeError:
                entity_hints = {}

        staff_report = _load_text_file(staff_report_path)
        transcript_text = _load_text_file(transcript_path)
        transcript_parse = parse_transcript(transcript_path) if transcript_path and transcript_path.exists() else None

        normalized_stage_map = _normalize_stage_map(stage_map)
        requested_targets = set(targets or [
            "timeline",
            "graph",
            "client",
            "lawyer",
            "qa",
        ])

        provider_chain = provider_chain or self.config.provider_chain
        provider_credentials = provider_credentials or {}
        collected_providers = _collect_requested_providers(provider_chain, provider_chain, normalized_stage_map)

        state_usage: Dict[str, Dict[str, int]] = {}
        stage_order: List[Tuple[str, str]] = [
            ("compose.context_builder", "context"),
            ("compose.timeline_builder", "timeline"),
            ("compose.graph_builder", "graph"),
            ("compose.client_brief", "client"),
            ("compose.lawyer_brief", "lawyer"),
            ("compose.qa_review", "qa"),
        ]

        context_payload: Dict[str, Any] = {}
        timeline_payload: Dict[str, Any] = {}
        graph_payload: Dict[str, Any] = {}
        client_markdown = ""
        lawyer_markdown = ""
        qa_payload: Dict[str, Any] = {}
        used_providers: List[str] = []

        def emit(stage: str, event: str, details: Optional[Dict[str, Any]] = None) -> None:
            if progress_callback is None:
                if self.config.debug:
                    self.logger.info("compose.stage", extra={"stage": stage, "event": event, "details": details})
                return
            try:
                progress_callback(stage, event, details or {})
            except Exception:  # pragma: no cover - defensive
                self.logger.debug("progress callback failed", exc_info=True)

        for stage_key, bucket in stage_order:
            if bucket != "context" and bucket not in requested_targets:
                continue

            emit(stage_key, "start")
            try:
                response, usage, provider = self._invoke_stage(
                    stage_key=stage_key,
                    normalized_stage_map=normalized_stage_map,
                    provider_chain=provider_chain,
                    provider_credentials=provider_credentials,
                    transcript_text=transcript_text,
                    transcript_parse=transcript_parse,
                    summary_markdown=summary_markdown,
                    summary_data=summary_data,
                    timeline_seeds=timeline_seeds,
                    entity_hints=entity_hints,
                    staff_report=staff_report,
                    case_brief=context_payload,
                    timeline_payload=timeline_payload,
                    graph_payload=graph_payload,
                    intake=intake or {},
                    attachments=attachments or [],
                )
            except ComposeStageError:
                emit(stage_key, "failed")
                raise
            used_providers.append(provider)
            if usage:
                state_usage[stage_key] = usage

            if stage_key == "compose.context_builder":
                context_payload = response  # type: ignore[assignment]
            elif stage_key == "compose.timeline_builder":
                timeline_payload = response  # type: ignore[assignment]
            elif stage_key == "compose.graph_builder":
                graph_payload = response  # type: ignore[assignment]
            elif stage_key == "compose.client_brief":
                client_markdown = str(response)
            elif stage_key == "compose.lawyer_brief":
                lawyer_markdown = str(response)
            elif stage_key == "compose.qa_review":
                qa_payload = response  # type: ignore[assignment]

            emit(stage_key, "complete", {"provider": provider})

        artifacts = ComposeArtifacts()

        if "timeline" in requested_targets and timeline_payload:
            timeline_file = next_versioned(analysis_dir / f"{job_id}__timeline_v2.json")
            timeline_file.write_text(json.dumps(timeline_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            artifacts.timeline_file = timeline_file

        if "graph" in requested_targets and graph_payload:
            entities = graph_payload.get("entities") if isinstance(graph_payload, Mapping) else None
            relationships = graph_payload.get("relationships") if isinstance(graph_payload, Mapping) else None
            graph_file = next_versioned(analysis_dir / f"{job_id}__graph_v2.json")
            graph_file.write_text(json.dumps(graph_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            artifacts.graph_file = graph_file
            if isinstance(entities, list):
                entities_file = next_versioned(analysis_dir / f"{job_id}__entities_v2.json")
                entities_file.write_text(json.dumps({"entities": entities}, ensure_ascii=False, indent=2), encoding="utf-8")
                artifacts.entities_file = entities_file

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

        meta_payload = {
            "case_id": case_id,
            "job_id": job_id,
            "summary_json": str(summary_json_path) if summary_json_path else None,
            "summary_markdown": str(summary_markdown_path) if summary_markdown_path else None,
            "transcript_path": str(transcript_path) if transcript_path else None,
            "timeline_file": str(artifacts.timeline_file) if artifacts.timeline_file else None,
            "graph_file": str(artifacts.graph_file) if artifacts.graph_file else None,
            "entities_file": str(artifacts.entities_file) if artifacts.entities_file else None,
            "client_markdown": str(artifacts.client_markdown) if artifacts.client_markdown else None,
            "lawyer_markdown": str(artifacts.lawyer_markdown) if artifacts.lawyer_markdown else None,
            "client_docx": str(artifacts.client_docx) if artifacts.client_docx else None,
            "lawyer_docx": str(artifacts.lawyer_docx) if artifacts.lawyer_docx else None,
            "context": context_payload,
            "timeline": timeline_payload,
            "graph": graph_payload,
            "qa": qa_payload,
            "provider_chain": used_providers,
            "stage_usage": state_usage,
            "status": "ok",
        }

        meta_json = ops_dir / f"{job_id}__compose_log.json"
        meta_json.write_text(json.dumps(meta_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        audit_jsonl = ops_dir / "ops_compose.jsonl"
        with audit_jsonl.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "case_id": case_id,
                "job_id": job_id,
                "status": "ok",
                "timeline_file": str(artifacts.timeline_file) if artifacts.timeline_file else None,
                "graph_file": str(artifacts.graph_file) if artifacts.graph_file else None,
                "client_markdown": str(artifacts.client_markdown) if artifacts.client_markdown else None,
                "lawyer_markdown": str(artifacts.lawyer_markdown) if artifacts.lawyer_markdown else None,
            }, ensure_ascii=False) + "\n")

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
        normalized_stage_map: Mapping[str, Mapping[str, Any]],
        provider_chain: Sequence[str],
        provider_credentials: Mapping[str, Dict[str, Any]],
        transcript_text: str,
        transcript_parse,
        summary_markdown: str,
        summary_data: Mapping[str, Any],
        timeline_seeds: Sequence[Mapping[str, Any]],
        entity_hints: Mapping[str, Any],
        staff_report: str,
        case_brief: Mapping[str, Any],
        timeline_payload: Mapping[str, Any],
        graph_payload: Mapping[str, Any],
        intake: Mapping[str, Any],
        attachments: Sequence[Mapping[str, Any]],
    ) -> Tuple[Any, Dict[str, int], str]:
        assignment = self.settings.stage(stage_key)
        override = normalized_stage_map.get(stage_key)
        providers = _normalize_providers(
            (
                override.get("providers")
                if override and isinstance(override.get("providers"), Sequence)
                else []
            )
            if override
            else []
        )
        if override and override.get("provider"):
            providers.insert(0, str(override["provider"]))
        if assignment and assignment.providers:
            providers.extend(assignment.providers)
        providers.extend(provider_chain or [])
        providers = _normalize_providers(providers or DEFAULT_PROVIDER_CHAIN)

        model_override = override.get("model") if override else None
        model = str(model_override) if model_override else (assignment.model if assignment else "")

        options: Dict[str, Any] = {}
        if assignment and assignment.options:
            options.update(assignment.options)
        if override and isinstance(override.get("options"), Mapping):
            options.update({str(k): v for k, v in override["options"].items()})

        last_error: Optional[Exception] = None
        for provider in providers:
            provider_obj = self.settings.provider(provider)
            if provider_obj is None:
                continue
            credential_payload = provider_credentials.get(provider)
            try:
                runtime_cfg = build_provider_runtime_config(
                    settings=self.settings,
                    provider=provider,
                    model=model,
                    credential_payload=credential_payload,
                    options=options or None,
                )
                client = build_chat_client(provider_runtime=runtime_cfg)
            except ChatClientError as exc:
                last_error = exc
                continue

            profile = COMPOSE_STAGE_PROFILES.get(stage_key)
            max_tokens = self.config.stage_max_tokens(stage_key, runtime_cfg.model.max_output_tokens if runtime_cfg.model else None)
            temperature = self.config.temperature
            if stage_key == "compose.lawyer_brief":
                temperature = self.config.lawyer_temperature
            if stage_key == "compose.client_brief" and options.get("temperature") is not None:
                try:
                    temperature = float(options["temperature"])
                except (TypeError, ValueError):
                    pass

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

            return parsed, {k: int(v) for k, v in usage.items() if isinstance(v, int)}, provider

        if last_error:
            raise ComposeStageError(stage_key, str(last_error))
        raise ComposeStageError(stage_key, "No provider available")

    def _build_prompts(
        self,
        *,
        stage_key: str,
        transcript_text: str,
        summary_markdown: str,
        summary_data: Mapping[str, Any],
        timeline_seeds: Sequence[Mapping[str, Any]],
        entity_hints: Mapping[str, Any],
        staff_report: str,
        case_brief: Mapping[str, Any],
        timeline_payload: Mapping[str, Any],
        graph_payload: Mapping[str, Any],
        intake: Mapping[str, Any],
        attachments: Sequence[Mapping[str, Any]],
        transcript_parse,
        profile,
        client_markdown: str,
        lawyer_markdown: str,
    ) -> Tuple[str, str, Optional[Dict[str, Any]]]:
        transcript_excerpt = _first_n_segments(transcript_text, limit=240)
        base_system = (
            "You are the uDocket Compose agent, a Canadian legal assistant who builds clear, "
            "auditable deliverables from transcripts, summaries, and prior analyses."
        )

        if stage_key == "compose.context_builder":
            response_schema = {
                "type": "json_schema",
                "json_schema": {
                    "name": "compose_context_response",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "parties": {
                                "type": "array",
                                "items": {"type": "object", "properties": {
                                    "name": {"type": "string"},
                                    "role": {"type": "string"},
                                    "description": {"type": "string"},
                                }, "required": ["name"]},
                            },
                            "issues": {
                                "type": "array",
                                "items": {"type": "object", "properties": {
                                    "label": {"type": "string"},
                                    "summary": {"type": "string"},
                                }, "required": ["label"]},
                            },
                            "posture": {"type": "string"},
                            "risks": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "next_steps": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "key_facts": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["parties", "issues"],
                    },
                },
            }
            user_payload = {
                "intake": intake,
                "summary": summary_data,
                "summary_markdown": summary_markdown,
                "staff_report": staff_report,
                "transcript_excerpt": transcript_excerpt,
            }
            user_prompt = (
                "Use the provided materials to build a concise case brief JSON with parties, "
                "legal posture, key issues, risks, and next steps."
            ) + "\n\n" + json.dumps(user_payload, ensure_ascii=False)
            return base_system, user_prompt, response_schema

        if stage_key == "compose.timeline_builder":
            response_schema = {
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
                                        "speakers": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                        "references": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                        "labels": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                    },
                                    "required": ["id", "title", "summary", "ts_start"],
                                },
                            },
                        },
                        "required": ["events"],
                    },
                },
            }
            payload = {
                "case_brief": case_brief,
                "timeline_seeds": timeline_seeds,
                "summary": summary_data,
                "transcript_excerpt": transcript_excerpt,
            }
            user_prompt = (
                "Produce timeline_v2 JSON describing the proceedings. Each event must reference "
                "timestamps and speakers when known. Keep the order chronological."
            ) + "\n\n" + json.dumps(payload, ensure_ascii=False)
            return base_system, user_prompt, response_schema

        if stage_key == "compose.graph_builder":
            response_schema = {
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
                                        "evidence": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                    },
                                    "required": ["id", "source", "target", "type"],
                                },
                            },
                        },
                        "required": ["entities"],
                    },
                },
            }
            payload = {
                "case_brief": case_brief,
                "entity_hints": entity_hints,
                "timeline": timeline_payload,
                "summary": summary_data,
                "transcript_excerpt": transcript_excerpt,
            }
            user_prompt = (
                "Generate entities and relationships JSON. Include evidence references to transcript timestamps or timeline IDs."
            ) + "\n\n" + json.dumps(payload, ensure_ascii=False)
            return base_system, user_prompt, response_schema

        if stage_key == "compose.client_brief":
            payload = {
                "case_brief": case_brief,
                "timeline": timeline_payload,
                "graph": graph_payload,
                "summary_text": summary_markdown,
                "staff_report": staff_report,
                "intake": intake,
            }
            user_prompt = (
                "Draft a Markdown brief for the client in grade-six reading level. Include sections: Overview, Timeline Highlights, Key Issues, Next Steps."
            ) + "\n\n" + json.dumps(payload, ensure_ascii=False)
            return base_system, user_prompt, None

        if stage_key == "compose.lawyer_brief":
            payload = {
                "case_brief": case_brief,
                "timeline": timeline_payload,
                "graph": graph_payload,
                "summary_text": summary_markdown,
            }
            user_prompt = (
                "Draft a professional Markdown brief for counsel. Organize by issue, reference timestamps, and list supporting evidence."
            ) + "\n\n" + json.dumps(payload, ensure_ascii=False)
            return base_system, user_prompt, None

        if stage_key == "compose.qa_review":
            response_schema = {
                "type": "json_schema",
                "json_schema": {
                    "name": "compose_qa_response",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "status": {"type": "string"},
                            "alerts": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "recommendations": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["status"],
                    },
                },
            }
            payload = {
                "case_brief": case_brief,
                "timeline": timeline_payload,
                "graph": graph_payload,
                "client_markdown": client_markdown,
                "lawyer_markdown": lawyer_markdown,
            }
            user_prompt = (
                "Review the compose outputs for completeness and compliance. Respond with JSON describing status, alerts, and recommendations."
            ) + "\n\n" + json.dumps(payload, ensure_ascii=False)
            return base_system, user_prompt, response_schema

        raise ComposeStageError(stage_key, "Unknown stage")

    def _parse_stage_output(self, stage_key: str, content: str) -> Any:
        if stage_key in {
            "compose.context_builder",
            "compose.timeline_builder",
            "compose.graph_builder",
            "compose.qa_review",
        }:
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError as exc:
                raise ComposeStageError(stage_key, f"Invalid JSON: {exc}")
            if stage_key == "compose.timeline_builder" and not isinstance(parsed, Mapping):
                raise ComposeStageError(stage_key, "Timeline response must be an object")
            if stage_key == "compose.graph_builder" and not isinstance(parsed, Mapping):
                raise ComposeStageError(stage_key, "Graph response must be an object")
            if stage_key == "compose.context_builder" and not isinstance(parsed, Mapping):
                raise ComposeStageError(stage_key, "Context response must be an object")
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
