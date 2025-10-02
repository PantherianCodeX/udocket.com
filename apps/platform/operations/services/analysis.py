from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, cast
import json

from apps.platform.cases.models import Case
from apps.platform.operations.storage import ensure_case_dirs, ops_dir as storage_ops_dir


def case_paths(case_id: str, organization_id: Optional[str] = None) -> Tuple[Path, Path, Path]:
    base = ensure_case_dirs(case_id, organization_id)
    return base, base / "transcript", base / "analysis"


def ops_dir(case_id: str, organization_id: Optional[str] = None) -> Path:
    return storage_ops_dir(case_id, organization_id)


def resolve_case_relative(path_str: str, case_dir: Path) -> Optional[Path]:
    candidate = Path(path_str)
    if candidate.exists():
        return candidate
    candidate = case_dir / path_str
    if candidate.exists():
        return candidate
    return None


def load_summary_timeline_events(
    meta: Mapping[str, Any],
    case_dir: Path,
) -> Tuple[List[Dict[str, Any]], Optional[Path]]:
    file_value = cast(Optional[str], meta.get("summary_timeline_file"))
    if not file_value:
        return [], None
    seeds_path = resolve_case_relative(file_value, case_dir)
    if not seeds_path:
        return [], None
    try:
        payload: Any = json.loads(seeds_path.read_text(encoding="utf-8"))
    except Exception:  # pragma: no cover - malformed file
        return [], None
    events_candidate: Sequence[Any]
    if isinstance(payload, dict):
        events_value = payload.get("events")
        events_candidate = cast(Sequence[Any], events_value) if isinstance(events_value, list) else ()
    elif isinstance(payload, list):
        events_candidate = payload
    else:
        events_candidate = ()
    events: List[Dict[str, Any]] = []
    raw_events: Sequence[Any] = events_candidate
    for item in raw_events:
        if not isinstance(item, dict):
            continue
        event_map = cast(Mapping[str, Any], item)
        labels_value = event_map.get("labels")
        labels_list = [str(label) for label in labels_value] if isinstance(labels_value, (list, tuple)) else []
        events.append(
            {
                "ts_start": event_map.get("ts_start"),
                "ts_end": event_map.get("ts_end"),
                "speaker": event_map.get("speaker"),
                "text": str(event_map.get("text") or ""),
                "labels": labels_list,
            }
        )
    if not events:
        return [], None
    return events, seeds_path


def load_summary_entity_hints(
    meta: Mapping[str, Any],
    case_dir: Path,
) -> Tuple[Optional[Dict[str, Any]], Optional[Path]]:
    file_value = cast(Optional[str], meta.get("summary_entity_file"))
    if not file_value:
        return None, None
    hints_path = resolve_case_relative(file_value, case_dir)
    if not hints_path:
        return None, None
    try:
        payload: Any = json.loads(hints_path.read_text(encoding="utf-8"))
    except Exception:  # pragma: no cover - malformed file
        return None, None
    if not isinstance(payload, dict):
        return None, None
    payload_dict: Dict[str, Any] = {str(key): value for key, value in payload.items()}
    return payload_dict, hints_path


def latest_transcript(case_id: str, organization_id: Optional[str] = None) -> Optional[Path]:
    _, transcript_dir, _ = case_paths(case_id, organization_id)
    if not transcript_dir.exists():
        return None
    files = sorted(
        (p for p in transcript_dir.glob("*__transcript.txt") if p.is_file()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return files[0] if files else None


def case_intake_payload(case: Optional[Case]) -> Dict[str, Any]:
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
    payload: Dict[str, Any] = {}
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
    payload.setdefault("case_id", str(case.id))
    payload.setdefault("case_title", case.title)
    organization = getattr(case, "organization", None)
    if organization is not None:
        payload.setdefault("organization_id", str(case.organization_id))
        name = getattr(organization, "name", None)
        if isinstance(name, str) and name:
            payload.setdefault("organization_name", name)
    return payload


def collect_requested_providers(
    config_chain: Sequence[str],
    provider_chain: Optional[Sequence[str]],
    stage_map: Optional[Mapping[str, Mapping[str, Any]]] = None,
) -> List[str]:
    sequence: List[str] = []

    def _add(value: Any) -> None:
        if not value or not isinstance(value, str):
            return
        lowered = value.strip().lower()
        if lowered and lowered not in sequence:
            sequence.append(lowered)

    if stage_map:
        for payload in stage_map.values():
            raw_providers = payload.get("providers")
            if isinstance(raw_providers, (list, tuple)):
                for item in raw_providers:
                    if isinstance(item, str):
                        _add(item)
            provider_value = payload.get("provider")
            if isinstance(provider_value, str):
                _add(provider_value)

    if provider_chain:
        for item in provider_chain:
            if isinstance(item, str):
                _add(item)

    for item in config_chain:
        _add(item)

    return sequence
