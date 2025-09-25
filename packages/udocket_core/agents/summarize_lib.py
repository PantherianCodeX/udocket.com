from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, MutableMapping, Optional, Tuple

try:  # pragma: no cover - optional dependency for online mode
    import requests
except Exception:  # pragma: no cover - fallback when requests missing
    requests = None  # type: ignore[assignment]


CANADIAN_REGIONS = {"canadacentral", "canadaeast"}
MAX_PROMPT_SEGMENTS = 120
MAX_PROMPT_CHARS = 8000


def _now_utc() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _next_versioned(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    match = re.match(r"^(?P<name>.+)_v(?P<ver>\d+)$", stem)
    if match:
        name = match.group("name")
        ver = int(match.group("ver"))
    else:
        name = stem
        ver = 1
    while True:
        ver += 1
        candidate = path.with_name(f"{name}_v{ver}{suffix}")
        if not candidate.exists():
            return candidate


def _append_jsonl(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(obj, ensure_ascii=False) + "\n")


@dataclass
class TranscriptSegment:
    ts: Optional[float]
    speaker: Optional[str]
    text: str


@dataclass
class TranscriptParse:
    header_lines: List[str]
    segments: List[TranscriptSegment]
    body_text: str
    diarized: bool


TIMESTAMP_RE = re.compile(
    r"^\s*\[(?P<minutes>\d{1,2}):(?P<seconds>\d{2})\]\s*(?:(?P<speaker>SPK_[\w-]+)\s*:\s*)?(?P<text>.*)$"
)
HEADER_DIVIDER_RE = re.compile(r"^-{20,}$")


def parse_transcript(path: Path) -> TranscriptParse:
    contents = path.read_text(encoding="utf-8", errors="ignore")
    lines = contents.splitlines()

    header: List[str] = []
    body_lines: List[str] = []
    in_body = False
    for line in lines:
        if not in_body and HEADER_DIVIDER_RE.match(line.strip()):
            in_body = True
            continue
        if in_body:
            body_lines.append(line)
        else:
            header.append(line)
    if not in_body:
        body_lines = lines
        header = []

    segments: List[TranscriptSegment] = []
    diarized = False
    for raw in body_lines:
        raw = raw.rstrip()
        if not raw:
            continue
        match = TIMESTAMP_RE.match(raw)
        if match:
            minutes = int(match.group("minutes"))
            seconds = int(match.group("seconds"))
            ts = minutes * 60 + seconds
            speaker = match.group("speaker")
            text = match.group("text").strip()
            segments.append(TranscriptSegment(ts=ts, speaker=speaker, text=text))
            if speaker:
                diarized = True
        else:
            segments.append(TranscriptSegment(ts=None, speaker=None, text=raw.strip()))
    body_text = "\n".join(seg.text for seg in segments if seg.text)
    return TranscriptParse(header_lines=header, segments=segments, body_text=body_text, diarized=diarized)


@dataclass
class SummarizeConfig:
    azure_openai_endpoint: str = ""
    azure_openai_key: str = ""
    azure_openai_deployment: str = ""
    azure_openai_api_version: str = "2024-08-01-preview"
    language: str = "en-CA"
    temperature: float = 0.2
    max_output_tokens: int = 24000
    debug: bool = False

    @classmethod
    def from_env(cls) -> "SummarizeConfig":
        endpoint = (os.getenv("AZURE_OPENAI_ENDPOINT") or "").strip()
        key = (os.getenv("AZURE_OPENAI_API_KEY") or "").strip()
        deployment = (os.getenv("AZURE_OPENAI_DEPLOYMENT") or "").strip()
        api_version = (os.getenv("AZURE_OPENAI_API_VERSION") or "2024-08-01-preview").strip()
        language = (os.getenv("LANGUAGE") or "en-CA").strip() or "en-CA"
        temperature = float(os.getenv("SUMMARY_TEMPERATURE", "0.2") or 0.2)
        max_tokens = int(os.getenv("SUMMARY_MAX_TOKENS", "24000") or 24000)
        debug = (os.getenv("DEBUG", "0").strip() == "1")

        if endpoint and not _endpoint_is_canadian(endpoint):
            raise ValueError("AZURE_OPENAI_ENDPOINT must target canadacentral or canadaeast")

        return cls(
            azure_openai_endpoint=endpoint,
            azure_openai_key=key,
            azure_openai_deployment=deployment,
            azure_openai_api_version=api_version,
            language=language,
            temperature=temperature,
            max_output_tokens=max_tokens,
            debug=debug,
        )

    @property
    def azure_enabled(self) -> bool:
        return bool(self.azure_openai_endpoint and self.azure_openai_key and self.azure_openai_deployment)

    @property
    def azure_region(self) -> Optional[str]:
        if not self.azure_openai_endpoint:
            return None
        match = re.search(r"https://([^.]+)", self.azure_openai_endpoint.lower())
        if match:
            region = match.group(1)
            if region in CANADIAN_REGIONS:
                return region
        for region in CANADIAN_REGIONS:
            if region in self.azure_openai_endpoint.lower():
                return region
        return None


def _endpoint_is_canadian(endpoint: str) -> bool:
    endpoint_lower = endpoint.lower()
    return any(region in endpoint_lower for region in CANADIAN_REGIONS)


@dataclass
class SummarizeResult:
    status: str
    summary_file: Path
    outline_file: Optional[Path]
    timeline_seeds_file: Optional[Path]
    entity_hints_file: Optional[Path]
    words: int
    source_transcript: Path
    meta_json: Path
    audit_jsonl: Path


OUTLINE_SCHEMA = {
    "type": "object",
    "properties": {
        "parties": {
            "type": "object",
            "properties": {
                "client": {
                    "type": "object",
                    "properties": {
                        "name": {"type": ["string", "null"]},
                        "role": {"type": ["string", "null"]},
                    },
                    "required": ["name", "role"],
                },
                "opposing": {
                    "type": "object",
                    "properties": {
                        "name": {"type": ["string", "null"]},
                        "role": {"type": ["string", "null"]},
                    },
                    "required": ["name", "role"],
                },
                "counsel": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "for": {"type": "string"},
                        },
                        "required": ["name", "for"],
                    },
                },
            },
            "required": ["client", "opposing", "counsel"],
        },
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "stance_client": {"type": ["string", "null"]},
                    "stance_opposing": {"type": ["string", "null"]},
                    "status": {"type": "string"},
                },
                "required": ["id", "title", "description", "status"],
            },
        },
        "claims_and_remedies": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "remedy_requested": {"type": ["string", "null"]},
                    "amounts": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "jurisdictional_notes": {"type": ["string", "null"]},
                },
                "required": ["claim", "amounts"],
            },
        },
        "facts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "ts": {"type": ["number", "null"]},
                    "speaker": {"type": ["string", "null"]},
                    "text": {"type": "string"},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["text", "tags"],
            },
        },
        "deadlines": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "date": {"type": ["string", "null"]},
                    "ts": {"type": ["number", "null"]},
                    "basis": {"type": ["string", "null"]},
                },
                "required": ["label"],
            },
        },
        "orders_and_directions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "date": {"type": ["string", "null"]},
                    "ts": {"type": ["number", "null"]},
                    "text": {"type": "string"},
                },
                "required": ["text"],
            },
        },
        "exhibits": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "description": {"type": "string"},
                    "cited_ts": {
                        "type": "array",
                        "items": {"type": "number"},
                    },
                },
                "required": ["id", "description", "cited_ts"],
            },
        },
        "legal_refs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "citation": {"type": "string"},
                    "context": {"type": "string"},
                },
                "required": ["citation", "context"],
            },
        },
    },
    "required": [
        "parties",
        "issues",
        "claims_and_remedies",
        "facts",
        "deadlines",
        "orders_and_directions",
        "exhibits",
        "legal_refs",
    ],
}

TIMELINE_SCHEMA = {
    "type": "object",
    "properties": {
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "ts_start": {"type": ["number", "null"]},
                    "ts_end": {"type": ["number", "null"]},
                    "speaker": {"type": ["string", "null"]},
                    "text": {"type": "string"},
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["ts_start", "text", "labels"],
            },
        }
    },
    "required": ["events"],
}

ENTITY_SCHEMA = {
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
                    "aliases": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["id", "name", "type", "aliases"],
            },
        },
        "relations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string"},
                    "source": {"type": "string"},
                    "target": {"type": "string"},
                    "evidence": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "ts": {"type": ["number", "null"]},
                                "text": {"type": "string"},
                            },
                            "required": ["text"],
                        },
                    },
                },
                "required": ["type", "source", "target", "evidence"],
            },
        },
    },
    "required": ["entities", "relations"],
}


class SummarizeAgent:
    def __init__(self, config: Optional[SummarizeConfig] = None) -> None:
        self.config = config or SummarizeConfig.from_env()

    def summarize(
        self,
        *,
        input: Optional[Path] = None,
        case_id: str,
        case_dir: Path,
        job_id: str,
        intake: Optional[dict] = None,
        transcript_hint: Optional[dict] = None,
    ) -> SummarizeResult:
        case_dir = Path(case_dir)
        transcript_path = self._resolve_transcript(input, case_dir)
        parse = parse_transcript(transcript_path)

        summary_dir = case_dir / "analysis"
        ops_dir = case_dir / "ops"
        _ensure_dir(summary_dir)
        _ensure_dir(ops_dir)

        context = self._build_context(parse, intake)
        token_usage: Dict[str, Dict[str, int]] = {}

        outline_data, usage_outline = self._generate_outline(parse, intake or {}, context)
        if usage_outline:
            token_usage["outline"] = usage_outline

        timeline_data, usage_timeline = self._generate_timeline(parse, outline_data, context)
        if usage_timeline:
            token_usage["timeline"] = usage_timeline

        entity_data, usage_entity = self._generate_entities(parse, outline_data, context)
        if usage_entity:
            token_usage["entities"] = usage_entity

        summary_text, usage_summary = self._generate_summary(parse, outline_data, timeline_data, entity_data, intake or {}, context)
        if usage_summary:
            token_usage["summary"] = usage_summary

        summary_path = _next_versioned(summary_dir / f"{job_id}__summary_v1.md")
        summary_path.write_text(summary_text, encoding="utf-8")

        outline_path = _next_versioned(summary_dir / f"{job_id}__outline_v1.json")
        outline_path.write_text(json.dumps(outline_data, ensure_ascii=False, indent=2), encoding="utf-8")

        timeline_path = _next_versioned(summary_dir / f"{job_id}__timeline_seeds_v1.json")
        timeline_path.write_text(json.dumps(timeline_data, ensure_ascii=False, indent=2), encoding="utf-8")

        entity_path = _next_versioned(summary_dir / f"{job_id}__entity_hints_v1.json")
        entity_path.write_text(json.dumps(entity_data, ensure_ascii=False, indent=2), encoding="utf-8")

        summary_sha = _sha256(summary_path)
        outline_sha = _sha256(outline_path)
        timeline_sha = _sha256(timeline_path)
        entity_sha = _sha256(entity_path)
        words = len(summary_text.split())

        meta: Dict[str, Any] = {
            "case_id": case_id,
            "job_id": job_id,
            "source_transcript": str(transcript_path),
            "summary_file": summary_path.name,
            "summary_sha256": summary_sha,
            "outline_file": outline_path.name,
            "outline_sha256": outline_sha,
            "timeline_seeds_file": timeline_path.name,
            "timeline_seeds_sha256": timeline_sha,
            "entity_hints_file": entity_path.name,
            "entity_hints_sha256": entity_sha,
            "language": self.config.language,
            "azure_enabled": self.config.azure_enabled,
            "azure_region": self.config.azure_region,
            "timestamp_utc": _now_utc(),
            "status": "ok",
            "words": words,
            "diarized": parse.diarized,
            "facts": len(outline_data.get("facts", [])),
            "timeline_events": len(timeline_data),
            "entity_count": len(entity_data.get("entities", [])),
        }
        if intake:
            meta["intake"] = intake
        if transcript_hint:
            meta["transcript_hint"] = transcript_hint
        if token_usage:
            meta["token_usage"] = token_usage

        meta_path = ops_dir / f"{job_id}__summary_log.json"
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        audit_path = ops_dir / "ops_summary.jsonl"
        _append_jsonl(
            audit_path,
            {
                "ts": _now_utc(),
                "case_id": case_id,
                "job_id": job_id,
                "event": "summary.created",
                "summary_file": str(summary_path),
                "outline_file": str(outline_path),
                "timeline_file": str(timeline_path),
                "entity_file": str(entity_path),
                "words": words,
            },
        )

        return SummarizeResult(
            status="ok",
            summary_file=summary_path,
            outline_file=outline_path,
            timeline_seeds_file=timeline_path,
            entity_hints_file=entity_path,
            words=words,
            source_transcript=transcript_path,
            meta_json=meta_path,
            audit_jsonl=audit_path,
        )

    # -------------------------
    # Generation stages
    # -------------------------

    def _generate_outline(
        self,
        parse: TranscriptParse,
        intake: Dict[str, Any],
        context: str,
    ) -> Tuple[Dict[str, Any], Dict[str, int]]:
        fallback = self._fallback_outline(parse, intake)
        if not self.config.azure_enabled:
            return fallback, {}

        try:
            system_prompt = (
                "You are a Canadian paralegal assistant. Extract structured outline data from the provided transcript"
                " context. Only return JSON that matches the provided schema."
            )
            user_prompt = (
                "Case intake info (may be empty):\n"
                f"{json.dumps(intake, ensure_ascii=False, indent=2)}\n\n"
                "Transcript excerpts:\n" + context + "\n"
            )
            content, usage = self._azure_chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": "outline_v1", "schema": OUTLINE_SCHEMA},
                },
                max_tokens=3000,
            )
            data = self._coerce_outline(json.loads(content), fallback)
            return data, _usage_dict(usage)
        except Exception:
            return fallback, {}

    def _generate_timeline(
        self,
        parse: TranscriptParse,
        outline: Dict[str, Any],
        context: str,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        fallback = self._fallback_timeline(parse)
        if not self.config.azure_enabled:
            return fallback, {}
        try:
            system_prompt = (
                "You are a legal timeline analyst. Produce normalized events with start/end offsets"
                " (seconds), optional speakers, and descriptive labels.")
            user_prompt = (
                "Use these transcript excerpts to generate events. Ensure every object includes labels array.\n"
                f"Outline issues (for context): {json.dumps(outline.get('issues', []), ensure_ascii=False)}\n\n"
                + context
            )
            content, usage = self._azure_chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": "timeline_v1", "schema": TIMELINE_SCHEMA},
                },
                max_tokens=2000,
            )
            payload = json.loads(content)
            events = payload.get("events", [])
            if not isinstance(events, list):
                events = fallback
            return self._coerce_timeline(events, fallback), _usage_dict(usage)
        except Exception:
            return fallback, {}

    def _generate_entities(
        self,
        parse: TranscriptParse,
        outline: Dict[str, Any],
        context: str,
    ) -> Tuple[Dict[str, Any], Dict[str, int]]:
        fallback = self._fallback_entities(parse, outline)
        if not self.config.azure_enabled:
            return fallback, {}
        try:
            system_prompt = (
                "You are an entity and relationship analyst for Canadian legal transcripts."
                " Extract people, organizations, locations, dockets, and relationships with evidence."
            )
            user_prompt = (
                "Use the outline and transcript snippets. Provide aliases where obvious."
                f"\nOutline parties: {json.dumps(outline.get('parties', {}), ensure_ascii=False)}\n"
                f"\nTranscript excerpts:\n{context}\n"
            )
            content, usage = self._azure_chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": "entity_v1", "schema": ENTITY_SCHEMA},
                },
                max_tokens=2000,
            )
            payload = json.loads(content)
            return self._coerce_entities(payload, fallback), _usage_dict(usage)
        except Exception:
            return fallback, {}

    def _generate_summary(
        self,
        parse: TranscriptParse,
        outline: Dict[str, Any],
        timeline: List[Dict[str, Any]],
        entities: Dict[str, Any],
        intake: Dict[str, Any],
        context: str,
    ) -> Tuple[str, Dict[str, int]]:
        fallback = self._offline_summary(parse, outline, timeline, entities, intake)
        if not self.config.azure_enabled:
            return fallback, {}
        try:
            system_prompt = (
                "You are a Canadian paralegal writing a layered legal summary for colleagues preparing court forms."
                " Include required sections: Case metadata, Executive summary (bullets), Detailed narrative,"
                " Claims and remedies, Procedural posture, Risks/gaps/questions, Next-step checklist."
                " Reference transcript timestamps in [mm:ss] format where relevant."
            )
            user_prompt = (
                "Case intake info:\n"
                f"{json.dumps(intake, ensure_ascii=False, indent=2)}\n\n"
                "Structured outline:\n"
                f"{json.dumps(outline, ensure_ascii=False, indent=2)}\n\n"
                "Timeline seeds:\n"
                f"{json.dumps(timeline, ensure_ascii=False, indent=2)}\n\n"
                "Entity hints:\n"
                f"{json.dumps(entities, ensure_ascii=False, indent=2)}\n\n"
                "Transcript excerpts:\n"
                f"{context}\n"
            )
            content, usage = self._azure_chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=4000,
            )
            return content.strip(), _usage_dict(usage)
        except Exception:
            return fallback, {}

    # -------------------------
    # Helpers
    # -------------------------

    def _resolve_transcript(self, input_path: Optional[Path], case_dir: Path) -> Path:
        if input_path:
            resolved = Path(input_path)
            if not resolved.exists():
                raise FileNotFoundError(f"Transcript not found at {resolved}")
            return resolved
        transcript_dir = case_dir / "transcript"
        if not transcript_dir.exists():
            raise FileNotFoundError(f"No transcript directory at {transcript_dir}")
        candidates = sorted(
            (p for p in transcript_dir.glob("*__transcript.txt") if p.is_file()),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            raise FileNotFoundError("No transcript files found for case")
        return candidates[0]

    def _build_context(self, parse: TranscriptParse, intake: Optional[Dict[str, Any]]) -> str:
        snippets: List[str] = []
        chars = 0
        for seg in parse.segments:
            text = seg.text.strip()
            if not text:
                continue
            prefix = ""
            if seg.ts is not None:
                minutes = int(seg.ts // 60)
                seconds = int(seg.ts % 60)
                speaker = seg.speaker or "SPK"
                prefix = f"[{minutes:02d}:{seconds:02d}] {speaker}: "
            line = prefix + text
            snippets.append(line)
            chars += len(line)
            if len(snippets) >= MAX_PROMPT_SEGMENTS or chars >= MAX_PROMPT_CHARS:
                break
        context = "\n".join(snippets)
        if intake and intake.get("court_case_number"):
            context = f"Case number: {intake['court_case_number']}\n" + context
        return context

    def _azure_chat(
        self,
        *,
        messages: List[Dict[str, str]],
        response_format: Optional[Dict[str, Any]] = None,
        max_tokens: Optional[int] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        if not self.config.azure_enabled:
            raise RuntimeError("Azure OpenAI not configured")
        if requests is None:  # pragma: no cover - dependency missing
            raise RuntimeError("requests library is required for Azure OpenAI calls")

        url = (
            self.config.azure_openai_endpoint.rstrip("/")
            + f"/openai/deployments/{self.config.azure_openai_deployment}/chat/completions"
        )
        params = {"api-version": self.config.azure_openai_api_version}
        payload: Dict[str, Any] = {
            "messages": messages,
            "temperature": self.config.temperature,
        }
        if max_tokens:
            payload["max_tokens"] = min(self.config.max_output_tokens, max_tokens)
        else:
            payload["max_tokens"] = min(self.config.max_output_tokens, 4000)
        if response_format:
            payload["response_format"] = response_format

        headers = {
            "api-key": self.config.azure_openai_key,
            "Content-Type": "application/json",
        }

        resp = requests.post(url, params=params, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("Azure OpenAI response missing choices")
        message = choices[0].get("message") or {}
        content = message.get("content") or ""
        usage = data.get("usage") or {}
        return content, usage

    # --- Fallbacks & coercion helpers ---

    def _fallback_outline(self, parse: TranscriptParse, intake: Dict[str, Any]) -> Dict[str, Any]:
        client_name = intake.get("client_name")
        opposing = intake.get("opposing_party")
        client_role = intake.get("client_position")
        issues = []
        for idx, seg in enumerate(parse.segments[:5], start=1):
            issues.append(
                {
                    "id": f"ISSUE-{idx}",
                    "title": seg.text[:80] or f"Issue {idx}",
                    "description": seg.text,
                    "stance_client": None,
                    "stance_opposing": None,
                    "status": "RAISED",
                }
            )
        facts = []
        for seg in parse.segments[:20]:
            facts.append(
                {
                    "ts": seg.ts,
                    "speaker": seg.speaker,
                    "text": seg.text,
                    "tags": ["transcript"],
                }
            )
        return {
            "parties": {
                "client": {"name": client_name, "role": client_role},
                "opposing": {"name": opposing, "role": None},
                "counsel": [],
            },
            "issues": issues,
            "claims_and_remedies": [],
            "facts": facts,
            "deadlines": [],
            "orders_and_directions": [],
            "exhibits": [],
            "legal_refs": [],
        }

    def _fallback_timeline(self, parse: TranscriptParse) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        for seg in parse.segments[:50]:
            events.append(
                {
                    "ts_start": seg.ts,
                    "ts_end": None,
                    "speaker": seg.speaker,
                    "text": seg.text,
                    "labels": ["transcript"],
                }
            )
        return events

    def _fallback_entities(self, parse: TranscriptParse, outline: Dict[str, Any]) -> Dict[str, Any]:
        speakers = {seg.speaker for seg in parse.segments if seg.speaker}
        entities = []
        for idx, speaker in enumerate(sorted(speakers or {"SPK"}), start=1):
            entities.append(
                {
                    "id": f"E{idx}",
                    "name": speaker,
                    "type": "PERSON",
                    "aliases": [],
                }
            )
        parties = outline.get("parties", {})
        client = parties.get("client", {}).get("name") if isinstance(parties, dict) else None
        opposing = parties.get("opposing", {}).get("name") if isinstance(parties, dict) else None
        if client:
            entities.insert(0, {"id": "CLIENT", "name": client, "type": "PERSON", "aliases": []})
        if opposing:
            entities.append({"id": "OPP", "name": opposing, "type": "PERSON", "aliases": []})
        return {"entities": entities, "relations": []}

    def _offline_summary(
        self,
        parse: TranscriptParse,
        outline: Dict[str, Any],
        timeline: List[Dict[str, Any]],
        entities: Dict[str, Any],
        intake: Dict[str, Any],
    ) -> str:
        header_lines = ["# Summarize output", ""]
        if intake:
            header_lines.append("## Case metadata")
            for key, value in intake.items():
                header_lines.append(f"- **{key.replace('_', ' ').title()}**: {value}")
            header_lines.append("")
        header_lines.append("## Executive summary")
        header_lines.append("- Offline fallback summary generated without Azure OpenAI.")
        header_lines.append("- Configure Azure credentials for richer analysis.")
        header_lines.append("")
        header_lines.append("## Detailed narrative")
        for seg in parse.segments[:10]:
            ts = ""
            if seg.ts is not None:
                minutes = int(seg.ts // 60)
                seconds = int(seg.ts % 60)
                ts = f"[{minutes:02d}:{seconds:02d}] "
            speaker = f"{seg.speaker}: " if seg.speaker else ""
            header_lines.append(f"- {ts}{speaker}{seg.text}")
        header_lines.append("")
        header_lines.append("## Claims and remedies")
        if outline.get("claims_and_remedies"):
            for claim in outline["claims_and_remedies"]:
                header_lines.append(f"- {claim.get('claim', 'Unknown claim')}")
        else:
            header_lines.append("- Not available in offline mode.")
        header_lines.append("")
        header_lines.append("## Procedural posture, orders, and deadlines")
        if outline.get("orders_and_directions"):
            for order in outline["orders_and_directions"]:
                header_lines.append(f"- {order.get('text', '')}")
        else:
            header_lines.append("- Not available in offline mode.")
        header_lines.append("")
        header_lines.append("## Risks, gaps, questions")
        header_lines.append("- Review transcript manually to confirm key issues.")
        header_lines.append("- Verify filing deadlines in court records.")
        header_lines.append("")
        header_lines.append("## Next-step checklist")
        header_lines.append("- Configure Azure OpenAI for full summarize pipeline.")
        header_lines.append("- Confirm transcript approval status before sharing.")
        header_lines.append("")
        header_lines.append("_Offline fallback summary. Configure Azure OpenAI for richer outputs._")
        header_lines.append("")
        return "\n".join(header_lines)

    def _coerce_outline(self, payload: Dict[str, Any], fallback: Dict[str, Any]) -> Dict[str, Any]:
        merged: Dict[str, Any] = {key: fallback.get(key) for key in fallback}
        for key in merged:
            value = payload.get(key) if isinstance(payload, dict) else None
            if value is not None:
                merged[key] = value
        return merged

    def _coerce_timeline(
        self,
        events: Iterable[Dict[str, Any]],
        fallback: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        coerced: List[Dict[str, Any]] = []
        for item in events:
            if not isinstance(item, dict):
                continue
            coerced.append(
                {
                    "ts_start": item.get("ts_start"),
                    "ts_end": item.get("ts_end"),
                    "speaker": item.get("speaker"),
                    "text": item.get("text", ""),
                    "labels": item.get("labels", []) or [],
                }
            )
        return coerced or fallback

    def _coerce_entities(self, payload: Dict[str, Any], fallback: Dict[str, Any]) -> Dict[str, Any]:
        entities = payload.get("entities") if isinstance(payload, dict) else None
        relations = payload.get("relations") if isinstance(payload, dict) else None
        return {
            "entities": entities if isinstance(entities, list) else fallback.get("entities", []),
            "relations": relations if isinstance(relations, list) else fallback.get("relations", []),
        }


def _usage_dict(usage: Dict[str, Any]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = usage.get(key)
        if isinstance(value, int):
            out[key] = value
    return out
