from __future__ import annotations
from typing import Any
from pydantic import BaseModel

def safe_dump(model: BaseModel) -> dict[str, Any]:
    """
    Canonical JSON dump for all udocket models:
    - JSON-ready mode
    - Use field aliases (e.g., CatalogBundle.schema_id -> "schema")
    - Exclude None to reduce noise
    """
    return model.model_dump(mode="json", by_alias=True, exclude_none=True)

def safe_dump_list(models: list[BaseModel]) -> list[dict[str, Any]]:
    return [safe_dump(m) for m in models]
