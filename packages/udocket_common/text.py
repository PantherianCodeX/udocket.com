from __future__ import annotations

# pyright: strict

"""String-related helpers shared across packages."""

import re
from collections.abc import Iterable

__all__ = ["prompt_lines", "prompt_paragraphs", "slugify", "unique_title"]
_UNIQUE_SUFFIX_RE = re.compile(r"(?:\(|-)(\d+)\)?$")


def slugify(text: str, *, separator: str = "-", allowed: str = "a-z0-9") -> str:
    """Return a slug composed of ``allowed`` characters separated by ``separator``.

    This helper is dependency-free and shared by CLI tooling and docs pipelines.
    ``allowed`` defaults to lowercase alphanumerics; callers can override the
    separator to generate dotted slugs (e.g., make command groups).
    """

    pattern = rf"[^{allowed}]+"
    slug = re.sub(pattern, separator, text.lower())
    if separator:
        slug = re.sub(rf"{re.escape(separator)}+", separator, slug)
        return slug.strip(separator)
    return slug.strip()


def unique_title(base: str, existing: Iterable[str]) -> str:
    """Return a title unique within *existing* by appending a numeric suffix.

    Titles are compared case-sensitively. Existing values ending with ``-n`` or
    legacy ``(n)`` suffixes are honored when computing the next available index.
    """

    base_clean = base.strip() or "Untitled"
    candidates = list(existing)

    max_idx = 0
    for title in candidates:
        if title == base_clean:
            max_idx = max(max_idx, 0)
            continue
        if not title.startswith(base_clean):
            continue
        match = _UNIQUE_SUFFIX_RE.search(title)
        if not match:
            continue
        try:
            idx = int(match.group(1))
        except Exception:
            continue
        max_idx = max(max_idx, idx)

    return f"{base_clean}-{max_idx + 1}"


def prompt_lines(*parts: str, trailing_newline: bool = False) -> str:
    """Join *parts* with single newlines while trimming trailing whitespace per line.

    Each argument may include embedded newlines. Empty strings are preserved as blank
    lines between sections. The result omits trailing blank lines unless
    ``trailing_newline`` is requested.
    """

    lines: list[str] = []
    for part in parts:
        if part == "":
            lines.append("")
            continue
        for raw_line in part.splitlines():
            lines.append(raw_line.rstrip())

    while lines and lines[-1] == "":
        lines.pop()

    text = "\n".join(lines)
    if trailing_newline and text:
        return f"{text}\n"
    return text


def prompt_paragraphs(*paragraphs: str, trailing_newline: bool = False) -> str:
    """Join *paragraphs* with blank lines, respecting whitespace discipline."""

    blocks: list[str] = []
    for paragraph in paragraphs:
        block = prompt_lines(paragraph)
        if block:
            blocks.append(block)

    text = "\n\n".join(blocks)
    if trailing_newline and text:
        return f"{text}\n"
    return text
