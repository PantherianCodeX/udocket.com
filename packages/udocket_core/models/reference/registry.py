from __future__ import annotations
import json, os
from pathlib import Path
from typing import Dict, Any, List
from .base import CatalogBundle, JurisdictionCatalog
from .plugin_protocol import validate_catalogs

# Directory walking is data-only. No code-defined data.
# Override search root with UDOCKET_DATA_DIR if you want to ship data out-of-package.
DEFAULT_DATA_ROOT = Path(__file__).resolve().parents[2] / "data" / "reference"

def _iter_bundle_files(root: Path | None = None) -> List[Path]:
    base = Path(root) if root else DEFAULT_DATA_ROOT
    return sorted([p for p in base.rglob("*.json") if p.name.endswith("catalog.json")])

def _load_bundle(p: Path) -> CatalogBundle:
    with p.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return CatalogBundle.model_validate(raw)

def discover_catalogs(data_root: str | Path | None = None) -> List[JurisdictionCatalog]:
    root = Path(data_root) if data_root else Path(os.getenv("UDOCKET_DATA_DIR", DEFAULT_DATA_ROOT))
    bundles = [_load_bundle(p) for p in _iter_bundle_files(root)]
    catalogs: List[JurisdictionCatalog] = []
    for b in bundles:
        catalogs.extend(b.data)
    validate_catalogs(catalogs)
    catalogs.sort(key=lambda c: (c.country.value, c.subnational or "", ",".join(sorted(c.courts.keys()))))
    return catalogs

def export_registry_json(data_root: str | Path | None = None) -> Dict[str, Any]:
    items = [c.model_dump(mode="json") for c in discover_catalogs(data_root)]
    return {"schema": "udocket.reference.catalogs.v1", "items": items, "count": len(items)}
