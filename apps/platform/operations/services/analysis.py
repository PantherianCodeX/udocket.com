# pyright: strict

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from pathlib import Path
from typing import Any, TypedDict, cast

from apps.platform.cases.models import Case
from apps.platform.operations.storage import ensure_case_dirs, ops_dir as storage_ops_dir


def case_paths(case_id: str, organization_id: str | None = None) -> tuple[Path, Path, Path]:
    base = ensure_case_dirs(case_id, organization_id)
    return base, base / "transcript", base / "analysis"


def ops_dir(case_id: str, organization_id: str | None = None) -> Path:
    return storage_ops_dir(case_id, organization_id)


def resolve_case_relative(path_str: str, case_dir: Path) -> Path | None:
    candidate = Path(path_str)
    if candidate.exists():
        return candidate
    candidate = case_dir / path_str
    if candidate.exists():
        return candidate
    return None


class SummaryTimelineEvent(TypedDict, total=False):
    ts_start: float | int | str | None
    ts_end: float | int | str | None
    speaker: str | None
    text: str
    labels: list[str]


def _coerce_event_mappings(payload: object) -> list[Mapping[str, object]]:
    events: list[Mapping[str, object]] = []
    if isinstance(payload, Mapping):
        payload_mapping = cast(Mapping[str, object], payload)
        events_value = payload_mapping.get("events")
        if isinstance(events_value, Sequence) and not isinstance(events_value, (str, bytes)):
            for candidate in cast(Sequence[object], events_value):
                if isinstance(candidate, Mapping):
                    events.append(cast(Mapping[str, object], candidate))
        return events
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes)):
        for candidate in cast(Sequence[object], payload):
            if isinstance(candidate, Mapping):
                events.append(cast(Mapping[str, object], candidate))
    return events


def _normalize_timestamp(value: object) -> float | int | str | None:
    if isinstance(value, (float, int, str)):
        return value
    return None


def _extract_labels(value: object) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    labels: list[str] = []
    for raw_label in cast(Sequence[object], value):
        labels.append(str(raw_label))
    return labels


def load_summary_timeline_events(
    meta: Mapping[str, object],
    case_dir: Path,
) -> tuple[list[SummaryTimelineEvent], Path | None]:
    file_value = meta.get("summary_timeline_file")
    if not isinstance(file_value, str) or not file_value:
        return [], None
    seeds_path = resolve_case_relative(file_value, case_dir)
    if not seeds_path:
        return [], None
    try:
        payload: object = json.loads(seeds_path.read_text(encoding="utf-8"))
    except Exception:  # pragma: no cover - malformed file
        return [], None
    raw_events = _coerce_event_mappings(payload)
    events: list[SummaryTimelineEvent] = []
    for event_map in raw_events:
        speaker_value = event_map.get("speaker")
        events.append(
            {
                "ts_start": _normalize_timestamp(event_map.get("ts_start")),
                "ts_end": _normalize_timestamp(event_map.get("ts_end")),
                "speaker": str(speaker_value) if speaker_value is not None else None,
                "text": str(event_map.get("text") or ""),
                "labels": _extract_labels(event_map.get("labels")),
            }
        )
    if not events:
        return [], None
    return events, seeds_path


def load_summary_entity_hints(
    meta: Mapping[str, object],
    case_dir: Path,
) -> tuple[dict[str, Any] | None, Path | None]:
    file_value = meta.get("summary_entity_file")
    if not isinstance(file_value, str) or not file_value:
        return None, None
    hints_path = resolve_case_relative(file_value, case_dir)
    if not hints_path:
        return None, None
    try:
        payload: object = json.loads(hints_path.read_text(encoding="utf-8"))
    except Exception:  # pragma: no cover - malformed file
        return None, None
    if not isinstance(payload, Mapping):
        return None, None
    payload_mapping = cast(Mapping[str, object], payload)
    payload_dict: dict[str, Any] = {}
    for key_obj, value in payload_mapping.items():
        payload_dict[key_obj] = value
    return payload_dict, hints_path


def latest_transcript(case_id: str, organization_id: str | None = None) -> Path | None:
    _, transcript_dir, _ = case_paths(case_id, organization_id)
    if not transcript_dir.exists():
        return None
    files = sorted(
        (p for p in transcript_dir.glob("*__transcript.txt") if p.is_file()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return files[0] if files else None


def case_intake_payload(case: Case | None) -> dict[str, Any]:
    if case is None:
        return {}
    fields = [
        "client_position",
        "court_level",
        "court_division",
        "court_location",
        "court_case_number",
        "court_date",
        "filing_deadline",
        "client_name",
        "opposing_party",
    ]
    payload: dict[str, Any] = {}
    for field in fields:
        value = getattr(case, field, None)
        if value in (None, ""):
            continue
        if isinstance(value, datetime):
            payload[field] = value.isoformat()
        elif isinstance(value, date):
            payload[field] = value.isoformat()
        else:
            payload[field] = value
    case_id_value = getattr(case, "id", None)
    if case_id_value is not None:
        payload.setdefault("case_id", str(case_id_value))
    title_value = getattr(case, "title", None)
    if isinstance(title_value, str) and title_value:
        payload.setdefault("case_title", title_value)
    organization = getattr(case, "organization", None)
    organization_id_value = getattr(case, "organization_id", None)
    if organization_id_value is not None:
        payload.setdefault("organization_id", str(organization_id_value))
    if organization is not None:
        name = getattr(organization, "name", None)
        if isinstance(name, str) and name:
            payload.setdefault("organization_name", name)
    return payload


def collect_requested_providers(
    config_chain: Sequence[str],
    provider_chain: Sequence[str] | None,
    stage_map: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[str]:
    sequence: list[str] = []

    def _add(value: str) -> None:
        lowered = value.strip().lower()
        if lowered and lowered not in sequence:
            sequence.append(lowered)

    if stage_map:
        for payload in stage_map.values():
            raw_providers = payload.get("providers")
            if isinstance(raw_providers, Sequence):
                for provider in cast(Sequence[object], raw_providers):
                    if isinstance(provider, str):
                        _add(provider)
            provider_value = payload.get("provider")
            if isinstance(provider_value, str):
                _add(provider_value)

    if provider_chain:
        for provider in provider_chain:
            _add(provider)

    for provider in config_chain:
        _add(provider)

    return sequence
