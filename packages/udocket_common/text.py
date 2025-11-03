from __future__ import annotations

# pyright: strict

"""String-related helpers shared across packages."""

import re

__all__ = ["slugify"]


def slugify(text: str, *, separator: str = "-", allowed: str = "a-z0-9") -> str:
    """Return a slug composed of ``allowed`` characters separated by ``separator``.

    This helper is dependency-free and shared by CLI tooling and docs pipelines.
    ``allowed`` defaults to lowercase alphanumerics; callers can override the
    separator to generate dotted slugs (e.g., make command groups).
    """

    pattern = fr"[^{allowed}]+"
    slug = re.sub(pattern, separator, text.lower())
    if separator:
        slug = re.sub(fr"{re.escape(separator)}+", separator, slug)
        return slug.strip(separator)
    return slug.strip()
