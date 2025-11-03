# pyright: strict

from __future__ import annotations
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from packages.udocket_common.json_utils import JSONObject, JSONValue, stringify_json


@dataclass
class TranscriptSegment:
    ts: float | None
    speaker: str | None
    text: str


@dataclass
class TranscriptParse:
    header_lines: list[str]
    segments: list[TranscriptSegment]
    body_text: str
    diarized: bool


@dataclass
class AnalysisArtifact:
    kind: str
    path: Path
    checksum: str
    metadata: JSONObject


TIMESTAMP_RE = re.compile(
    r"^\s*\[(?P<minutes>\d{1,2}):(?P<seconds>\d{2})\]\s*(?:(?P<speaker>SPK_[\w-]+)\s*:\s*)?(?P<text>.*)$"
)
HEADER_DIVIDER_RE = re.compile(r"^-{20,}$")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def next_versioned(path: Path) -> Path:
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


def append_jsonl(path: Path, obj: Mapping[str, JSONValue]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        payload: JSONObject = {key: value for key, value in obj.items()}
        handle.write(stringify_json(payload) + "\n")


def sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_transcript(path: Path) -> TranscriptParse:
    contents = path.read_text(encoding="utf-8", errors="ignore")
    lines = contents.splitlines()

    header: list[str] = []
    body_lines: list[str] = []
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

    segments: list[TranscriptSegment] = []
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


__all__ = [
    "JSONValue",
    "JSONObject",
    "TranscriptSegment",
    "TranscriptParse",
    "AnalysisArtifact",
    "ensure_dir",
    "next_versioned",
    "append_jsonl",
    "sha256_file",
    "parse_transcript",
]
