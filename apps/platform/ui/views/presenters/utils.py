from __future__ import annotations

import re
from typing import Any

from ..constants import STATUS_SORT_ORDER


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
