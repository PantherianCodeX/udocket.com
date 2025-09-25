from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional


CANADIAN_REGIONS = {"canadacentral", "canadaeast"}


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
        # No divider; treat entire contents as body
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
    max_output_tokens: int = 4000
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

        summary_path = _next_versioned(summary_dir / f"{job_id}__summary_v1.md")
        outline_path = None
        timeline_path = None
        entity_path = None

        summary_text = self._offline_summary(job_id, transcript_path, parse)
        summary_path.write_text(summary_text, encoding="utf-8")
        summary_sha = _sha256(summary_path)
        words = len(summary_text.split())

        meta = {
            "case_id": case_id,
            "job_id": job_id,
            "source_transcript": str(transcript_path),
            "summary_file": summary_path.name,
            "summary_sha256": summary_sha,
            "outline_file": outline_path.name if outline_path else None,
            "timeline_seeds_file": timeline_path.name if timeline_path else None,
            "entity_hints_file": entity_path.name if entity_path else None,
            "language": self.config.language,
            "azure_enabled": self.config.azure_enabled,
            "timestamp_utc": _now_utc(),
            "status": "ok",
            "words": words,
            "diarized": parse.diarized,
        }
        if intake:
            meta["intake"] = intake
        if transcript_hint:
            meta["transcript_hint"] = transcript_hint

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

    def _resolve_transcript(self, input_path: Optional[Path], case_dir: Path) -> Path:
        if input_path:
            return Path(input_path)
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

    def _offline_summary(self, job_id: str, transcript_path: Path, parse: TranscriptParse) -> str:
        paragraphs = [seg.text for seg in parse.segments if seg.text]
        preview_lines: List[str] = []
        total_chars = 0
        for para in paragraphs:
            if not para.strip():
                continue
            preview_lines.append(para)
            total_chars += len(para)
            if len(preview_lines) >= 200 or total_chars >= 2000:
                break
        preview = "\n".join(preview_lines)
        if len(preview) > 2000:
            preview = preview[:2000].rstrip() + "\n…"
        header = [
            f"# Summarize output for {job_id}",
            "",
            f"Generated from transcript: {transcript_path.name}",
            "",
        ]
        if parse.diarized:
            header.append("Detected diarized transcript with speaker tags.")
            header.append("")
        if parse.header_lines:
            header.append("> Transcript header: ")
            for line in parse.header_lines:
                if line.strip():
                    header.append(f"> {line.strip()}")
            header.append("")
        header.append(preview)
        header.append("")
        header.append("_Offline fallback summary. Configure Azure OpenAI for richer outputs._")
        header.append("")
        return "\n".join(header)
