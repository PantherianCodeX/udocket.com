# pyright: strict

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TypedDict, cast

from apps.platform.cases.models import Case
from apps.platform.operations.storage import ensure_case_paths
from apps.platform.operations.storage import ops_dir as storage_ops_dir
from packages.udocket_common.json_utils import (
    JSONObject,
    coerce_json_object,
    coerce_object_list,
    coerce_str_list,
    read_json_value,
)
from packages.udocket_common.operations import (
    CaseIntakeBuilder,
    ComposeStageMap,
)


def case_paths(case_id: str, organization_id: str | None = None) -> tuple[Path, Path, Path]:
    paths = ensure_case_paths(case_id, organization_id)
    return paths.root, paths.transcript, paths.analysis


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


def _timeline_event_objects(payload: object) -> list[JSONObject]:
    if isinstance(payload, Mapping):
        payload_mapping = coerce_json_object(cast(Mapping[object, object], payload))
        events_value = payload_mapping.get("events")
        return [coerce_json_object(item) for item in coerce_object_list(events_value)]
    return [coerce_json_object(item) for item in coerce_object_list(payload)]


def _normalize_timestamp(value: object) -> float | int | str | None:
    if isinstance(value, (float, int, str)):
        return value
    return None


def _extract_labels(value: object) -> list[str]:
    return coerce_str_list(value, unique=False)


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
    payload = read_json_value(seeds_path)
    if payload is None:
        return [], None
    raw_events = _timeline_event_objects(payload)
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
) -> tuple[JSONObject | None, Path | None]:
    file_value = meta.get("summary_entity_file")
    if not isinstance(file_value, str) or not file_value:
        return None, None
    hints_path = resolve_case_relative(file_value, case_dir)
    if not hints_path:
        return None, None
    payload = read_json_value(hints_path)
    if not isinstance(payload, Mapping):
        return None, None
    payload_dict = coerce_json_object(cast(Mapping[object, object], payload))
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


def case_intake_payload(case: Case | None) -> JSONObject:
    if case is None:
        return {}
    builder = CaseIntakeBuilder()
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
    for field in fields:
        value = getattr(case, field, None)
        builder.assign(field, value)
    case_id_value = getattr(case, "id", None)
    if case_id_value is not None:
        builder.ensure("case_id", str(case_id_value))
    title_value = getattr(case, "title", None)
    if isinstance(title_value, str) and title_value:
        builder.ensure("case_title", title_value)
    organization = getattr(case, "organization", None)
    organization_id_value = getattr(case, "organization_id", None)
    if organization_id_value is not None:
        builder.ensure("organization_id", str(organization_id_value))
    if organization is not None:
        name = getattr(organization, "name", None)
        if isinstance(name, str) and name:
            builder.ensure("organization_name", name)
    return builder.build().to_json()


def collect_requested_providers(
    config_chain: Sequence[str],
    provider_chain: Sequence[str] | None,
    stage_map: ComposeStageMap | None = None,
) -> list[str]:
    sequence: list[str] = []

    def _add(value: str) -> None:
        lowered = value.strip().lower()
        if lowered and lowered not in sequence:
            sequence.append(lowered)

    if stage_map:
        for provider in stage_map.providers():
            _add(provider)

    if provider_chain:
        for provider in provider_chain:
            _add(provider)

    for provider in config_chain:
        _add(provider)

    return sequence
