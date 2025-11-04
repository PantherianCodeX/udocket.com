from __future__ import annotations

import json
from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path

from ...config.paths import resolve_data_root
from .base import CaseNumberScheme, SchemeBundle

# Keep jurisdiction data co-located under reference/data/**
DEFAULT_SCHEMES_ROOT = resolve_data_root()


def _iter_scheme_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("case_number_schemes.json"):
        yield p


def _load_bundle(path: Path) -> SchemeBundle:
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return SchemeBundle.model_validate(raw)


@lru_cache(maxsize=64)
def discover_scheme_bundles(root: str | None = None) -> list[SchemeBundle]:
    base = Path(root).resolve() if root else DEFAULT_SCHEMES_ROOT
    out: list[SchemeBundle] = []
    for p in sorted(_iter_scheme_files(base)):
        out.append(_load_bundle(p))
    return out


@lru_cache(maxsize=256)
def schemes_by_court(root: str | None = None) -> dict[str, list[CaseNumberScheme]]:
    idx: dict[str, list[CaseNumberScheme]] = {}
    for b in discover_scheme_bundles(root):
        for s in b.data:
            idx.setdefault(s.court_key, []).append(s)
    return idx


def all_schemes(root: str | None = None) -> list[CaseNumberScheme]:
    out: list[CaseNumberScheme] = []
    for b in discover_scheme_bundles(root):
        out.extend(b.data)
    return out
