from __future__ import annotations
from pathlib import Path
from packages.udocket_core.reference.catalogs.base import CatalogBundle
from packages.udocket_core.reference.utils import safe_dump

def test_catalogbundle_uses_schema_alias(tmp_path: Path):
    # Minimal bundle instance round-trip to ensure 'schema' alias is honored
    minimal = {
        "schema": "udocket.reference.catalog.bundle.v1",
        "db": {"type": "postgresql", "tables": {}},
        "data": [],
        "meta": {"test": "ok"}
    }
    bundle = CatalogBundle.model_validate(minimal)
    dumped = safe_dump(bundle)
    # 'schema' must exist; 'schema_id' must not (alias used)
    assert "schema" in dumped
    assert "schema_id" not in dumped
    assert dumped["schema"] == "udocket.reference.catalog.bundle.v1"
