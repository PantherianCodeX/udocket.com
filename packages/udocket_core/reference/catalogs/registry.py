from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from ...config.paths import resolve_data_root
from ..utils import safe_dump
from .base import CatalogBundle, Court, CourtCatalog
from .plugin_protocol import validate_catalogs

# Directory walking is data-only. Override via env or settings to point elsewhere.
DEFAULT_DATA_ROOT = resolve_data_root()


def _iter_bundle_files(root: Path | None = None) -> list[Path]:
    base = Path(root) if root else DEFAULT_DATA_ROOT
    return sorted([p for p in base.rglob("*.json") if p.name.endswith("court_catalog.json")])


def _load_bundle(p: Path) -> CatalogBundle:
    with p.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return CatalogBundle.model_validate(raw)


def _check_cross_catalog_localcode_uniqueness(catalogs: list[CourtCatalog]) -> None:
    """
    Enforce that LocalCodes are unique *across* courts (strong guard).
    If two courts must share a code, set env UDOCKET_ALLOW_LOCALCODE_DUPLICATES=1.
    """
    allow_dupes = os.getenv("UDOCKET_ALLOW_LOCALCODE_DUPLICATES") == "1"
    seen: dict[str, tuple[str, str]] = {}  # code -> (court_key, jurisdiction_key)
    errors: list[str] = []

    def scan_court(court: Court, juris_key: str):
        for seq in (court.hearing_codes, court.filing_codes, court.order_codes):
            for item in seq:
                code = item.code.code
                owner = seen.get(code)
                if owner and (owner[0] != court.key):
                    msg = (
                        f"LocalCode '{code}' appears in courts '{owner[0]}' and '{court.key}' "
                        f"(jurisdictions: {owner[1]} vs {juris_key})"
                    )
                    if allow_dupes:
                        print(f"[udocket] WARNING: {msg}")  # soft warning
                    else:
                        errors.append(msg)
                else:
                    seen[code] = (court.key, juris_key)

    for cat in catalogs:
        juris_id = f"{cat.country.value}-{cat.subnational or 'NA'}"
        for court in cat.courts.values():
            scan_court(court, juris_id)

    if errors:
        raise ValueError("Cross-catalog LocalCode duplicates detected:\n- " + "\n- ".join(errors))


def discover_catalogs(data_root: str | Path | None = None) -> list[CourtCatalog]:
    if data_root:
        root = Path(data_root)
    else:
        legacy_override = os.getenv("COURT_CATALOG_ROOT")
        root = Path(legacy_override).expanduser() if legacy_override else DEFAULT_DATA_ROOT
    bundles = [_load_bundle(p) for p in _iter_bundle_files(root)]
    catalogs: list[CourtCatalog] = []
    for b in bundles:
        catalogs.extend(b.data)

    # Per-catalog validation (structure)
    validate_catalogs(catalogs)

    # Cross-catalog guard rails
    _check_cross_catalog_localcode_uniqueness(catalogs)

    # Deterministic ordering
    catalogs.sort(
        key=lambda c: (c.country.value, c.subnational or "", ",".join(sorted(c.courts.keys())))
    )
    return catalogs


def export_registry_json(data_root: str | Path | None = None) -> dict[str, Any]:
    # Enforce canonical serialization (aliases, json-ready, no None)
    items = [safe_dump(c) for c in discover_catalogs(data_root)]
    return {"schema": "udocket.reference.catalogs.v1", "items": items, "count": len(items)}
