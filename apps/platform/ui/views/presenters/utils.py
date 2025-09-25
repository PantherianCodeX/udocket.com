from __future__ import annotations

import re
from typing import Any

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
    display = getattr(user, 'display_name', None)
    if display:
        return display
    getter = getattr(user, 'get_full_name', None)
    if callable(getter):
        full_name = getter()
        if full_name:
            return full_name
    email = getattr(user, 'email', None)
    if email:
        return email
    username = getattr(user, 'username', None)
    if username:
        return username
    pk = getattr(user, 'pk', None)
    return str(pk) if pk is not None else ''

