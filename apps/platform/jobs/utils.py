from __future__ import annotations

from typing import Iterable
import re

_UNIQUE_SUFFIX_RE = re.compile(r"(?:\(|-)(\d+)\)?$")


def unique_title(base: str, existing: Iterable[str]) -> str:
    """Return a title unique within *existing* by adding -n suffixes.

    Titles are compared case-sensitively. Existing titles ending with ``-n`` (or
    legacy ``(n)`` values) will be considered when computing the next suffix.
    ``existing`` can be any
    iterable and is consumed entirely in memory.
    """

    base_clean = base.strip() or "Untitled"
    candidates = list(existing)
    if base_clean not in candidates:
        return base_clean

    max_idx = 0
    for title in candidates:
        if not title.startswith(base_clean):
            continue
        match = _UNIQUE_SUFFIX_RE.search(title)
        if not match:
            continue
        try:
            idx = int(match.group(1))
        except Exception:
            continue
        if idx > max_idx:
            max_idx = idx

    return f"{base_clean}-{max_idx + 1}"
