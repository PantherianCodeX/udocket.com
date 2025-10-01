from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Mapping

from django.template.loader import render_to_string

from ..constants import STATUS_SORT_ORDER, STATUS_CLASS_MAP


def safe_lower(value: Any) -> str:
    """Return a lowercase string representation suitable for filters/sorts."""
    return str(value or "").strip().lower()


def humanize_label(value: Any) -> str:
    """Normalize strings into a human-friendly label."""
    raw = str(value or "")
    if not raw:
        return ""
    text = raw.replace(".", " ").replace("-", " ")
    text = re.sub(r"[_\s]+", " ", text).strip()
    return text.title() if text else ""


def status_sort_value(status: str) -> str:
    """Provide a deterministic status sort key based on configured order."""
    normalized = (status or "").strip().upper()
    rank = STATUS_SORT_ORDER.get(normalized, 900)
    return f"{rank:03d}-{normalized}"


def status_class(status: str) -> str:
    """Map a status label to the configured pill class."""
    return STATUS_CLASS_MAP.get(status, "border-white/20 bg-white/5 text-slate-200")


def user_label(user: Any) -> str:
    """Return a human-friendly label for a user instance."""
    if not user:
        return ""
    display = getattr(user, "display_name", None)
    if isinstance(display, str) and display:
        return display
    if display is not None:
        text = str(display)
        if text:
            return text
    getter = getattr(user, "get_full_name", None)
    if callable(getter):
        full_name = getter()
        if isinstance(full_name, str) and full_name:
            return full_name
        if full_name is not None:
            text = str(full_name)
            if text:
                return text
    email = getattr(user, "email", None)
    if isinstance(email, str) and email:
        return email
    username = getattr(user, "username", None)
    if isinstance(username, str) and username:
        return username
    pk = getattr(user, "pk", None)
    return str(pk) if pk is not None else ""


def render_notes_panel_html(
    *,
    job_id: str | None,
    entries: Iterable[Mapping[str, Any]] | None,
    updated_at: str | None,
    updated_by: str | None,
    user_can_add: bool,
) -> str:
    job_identifier = str(job_id) if job_id is not None else ""
    context: Dict[str, Any] = {
        "job_id": job_identifier,
        "notes_entries": list(entries or []),
        "notes_updated_at": updated_at,
        "notes_updated_by": updated_by,
        "user_can_add_notes": user_can_add,
    }
    return render_to_string("platform_ui/components/notes/team_notes_panel.html", context)


def render_audio_brief_panel_html(**context: Any) -> str:
    return render_to_string("platform_ui/components/jobs/_audio_brief.html", context)
