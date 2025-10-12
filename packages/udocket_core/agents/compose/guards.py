from __future__ import annotations

# pyright: strict

import re
from difflib import SequenceMatcher
from typing import Mapping, Optional, Sequence

from ...utils.json import JSONObject, coerce_str

from .state import GuardReport


def sentence_length_report(document: str, *, max_average_words: float) -> GuardReport:
    filtered_lines = [line for line in document.splitlines() if not line.strip().startswith(("- ", "* "))]
    body = "\n".join(filtered_lines)
    body = re.sub(r"^##.+$", "", body, flags=re.MULTILINE)
    candidates = [candidate.strip() for candidate in re.split(r"(?<=[.!?])\s+|\n", body) if candidate.strip()]
    lengths: list[int] = []
    for candidate in candidates:
        words = re.findall(r"\b\w+\b", candidate)
        if words:
            lengths.append(len(words))
    if not lengths:
        return GuardReport(ok=True, errors=[], warnings=[], checks={"average_words": 0.0})
    average = sum(lengths) / float(len(lengths))
    if average > max_average_words:
        return GuardReport(
            ok=False,
            errors=[f"Average sentence length {average:.1f} exceeds {max_average_words:.0f}"],
            warnings=[],
            checks={"average_words": average},
        )
    return GuardReport(ok=True, errors=[], warnings=[], checks={"average_words": average})


_ADVICE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\byou should\b", re.IGNORECASE),
    re.compile(r"\byou must\b", re.IGNORECASE),
    re.compile(r"\bi recommend\b", re.IGNORECASE),
    re.compile(r"\bi advise\b", re.IGNORECASE),
    re.compile(r"\bwe recommend\b", re.IGNORECASE),
    re.compile(r"\bwe advise\b", re.IGNORECASE),
    re.compile(r"\bseek legal (help|advice|counsel)\b", re.IGNORECASE),
    re.compile(r"\bfile (an?|the) (claim|complaint|motion)\b", re.IGNORECASE),
    re.compile(r"\byou (need|ought)\b", re.IGNORECASE),
)

_RISKY_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bshould consider\b", re.IGNORECASE), "Suggestive wording"),
    (re.compile(r"\blikely\b", re.IGNORECASE), "Speculative wording"),
    (re.compile(r"\bprobably\b", re.IGNORECASE), "Speculative wording"),
    (re.compile(r"\bstrong case\b", re.IGNORECASE), "Speculative wording"),
    (re.compile(r"\bgood chance\b", re.IGNORECASE), "Speculative wording"),
)

_HEADING_PATTERN = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def _split_markdown_sections(document: str) -> list[tuple[str, str]]:
    normalized = document.replace("\r\n", "\n")
    matches = list(_HEADING_PATTERN.finditer(normalized))
    sections: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        heading = "## " + match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
        sections.append((heading, normalized[start:end].strip()))
    return sections


def markdown_structure_report(
    document: str,
    required: Sequence[str],
    *,
    min_words: int,
    per_section_min: Optional[Mapping[str, int]] = None,
    per_section_max: Optional[Mapping[str, int]] = None,
) -> GuardReport:
    text = document.strip()
    if not text:
        return GuardReport(ok=False, errors=["Document is empty"], warnings=[], checks={})

    sections = _split_markdown_sections(text)
    heading_order = [heading for heading, _ in sections]
    errors: list[str] = []
    warnings: list[str] = []

    last_index = -1
    for heading in required:
        occurrences = [idx for idx, present in enumerate(heading_order) if present == heading]
        if not occurrences:
            errors.append(f"Missing heading '{heading}'")
            continue
        if len(occurrences) > 1:
            errors.append(f"Duplicate heading '{heading}'")
        current_index = occurrences[0]
        if current_index <= last_index:
            errors.append(f"Heading '{heading}' out of order")
        last_index = current_index

    allowed = set(required)
    for heading in heading_order:
        if heading not in allowed:
            warnings.append(f"Unexpected heading '{heading}'")

    section_map = {heading: content for heading, content in sections}
    for heading in required:
        content = section_map.get(heading, "")
        word_count = len(re.findall(r"\b\w+\b", content))
        floor = per_section_min.get(heading, min_words) if per_section_min else min_words
        if word_count < floor:
            errors.append(f"Section '{heading}' too short (has {word_count}, expected ≥ {floor})")
        if per_section_max and heading in per_section_max:
            cap = per_section_max[heading]
            if word_count > cap:
                errors.append(f"Section '{heading}' too long (has {word_count}, expected ≤ {cap})")

    return GuardReport(ok=not errors, errors=errors, warnings=warnings, checks={})


def compliance_report(document: str) -> GuardReport:
    errors: list[str] = []
    warnings: list[str] = []
    for line in document.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(">"):
            continue
        lowered = stripped.lower()
        if lowered.startswith(("order:", "court order:", "epo:", "directive:")):
            continue
        for pattern in _ADVICE_PATTERNS:
            if pattern.search(lowered):
                errors.append(f"Disallowed advice language: '{stripped}'")
        for pattern, label in _RISKY_PATTERNS:
            if pattern.search(lowered):
                warnings.append(f"{label}: '{stripped}'")
    return GuardReport(ok=not errors, errors=errors, warnings=warnings, checks={})


def factuality_report(
    document: str,
    *,
    claimable_atoms: Sequence[str],
    timeline_events: Sequence[JSONObject],
    min_timestamp_references: int,
) -> GuardReport:
    text = document.strip()
    if not text:
        return GuardReport(ok=False, errors=["Document is empty"], warnings=[], checks={})

    atom_set = {atom.lower() for atom in claimable_atoms if atom}
    event_ids = [coerce_str(e.get("id")) or "" for e in timeline_events]
    event_id_set = {eid for eid in event_ids if eid}

    ts_pattern = r"\[(?:\d{1,2}:\d{2}(?::\d{2})?)\]"
    ts_regex = re.compile(ts_pattern)

    total_ts = len(ts_regex.findall(document))
    required_refs = min(len(list(timeline_events)), min_timestamp_references)

    errors: list[str] = []
    warnings: list[str] = []

    if total_ts < required_refs:
        errors.append(f"Found {total_ts} timestamp references; expected at least {required_refs}")

    referenced_ids: set[str] = set()
    for eid in event_id_set:
        if re.search(rf"(?<!\w){re.escape(eid)}(?!\w)", document):
            referenced_ids.add(eid)

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n", document) if s.strip()]
    for sentence in sentences:
        lower = sentence.lower()

        if lower.startswith("## "):
            continue
        if lower == "information not provided.":
            continue
        if lower.startswith(("- ", "* ")):
            continue
        if ts_regex.search(sentence):
            continue

        atom_hit = (
            any(atom in lower or SequenceMatcher(None, atom, lower).ratio() >= 0.82 for atom in atom_set)
            if atom_set
            else False
        )
        event_hit = any(re.search(rf"(?<!\w){re.escape(eid)}(?!\w)", sentence) for eid in event_id_set)

        if not (atom_hit or event_hit) and len(lower) >= 24:
            errors.append(f"Unsupported assertion: '{sentence}'")

    missing_ids = sorted(eid for eid in event_id_set if eid and eid not in referenced_ids)
    if missing_ids:
        warnings.append(f"Timeline events not referenced: {', '.join(missing_ids)}")

    return GuardReport(ok=not errors, errors=errors, warnings=warnings, checks={})


__all__ = [
    "compliance_report",
    "factuality_report",
    "markdown_structure_report",
    "sentence_length_report",
]
