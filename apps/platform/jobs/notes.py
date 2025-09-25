from __future__ import annotations

from datetime import datetime
from typing import Iterable, List, Dict

from .models import JobNote


def _isoformat_value(dt) -> str | None:
    if not dt:
        return None
    try:
        return dt.isoformat(timespec="seconds")
    except TypeError:  # pragma: no cover - Python < 3.11 compatibility
        return dt.isoformat()


def serialize_note(note: JobNote) -> Dict[str, str | None]:
    return {
        "id": str(note.id),
        "text": note.text,
        "created_at": _isoformat_value(note.created_at),
        "created_by": str(note.created_by_id) if note.created_by_id else None,
        "created_by_label": note.created_by_name or None,
    }


def serialize_notes(notes: Iterable[JobNote]) -> List[Dict[str, str | None]]:
    return [serialize_note(note) for note in notes]
