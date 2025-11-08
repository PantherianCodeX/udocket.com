"""Watchfiles filters used during local development."""

from __future__ import annotations

from watchfiles import PythonFilter


class PythonAndHTMLFilter(PythonFilter):
    """Extends the stock Python filter to also react to template edits."""

    _extra_suffixes = (".html", ".htm")

    def __call__(self, change, path: str) -> bool:  # type: ignore[override]
        lowered = path.lower()
        if lowered.endswith(self._extra_suffixes):
            return True
        return super().__call__(change, path)
