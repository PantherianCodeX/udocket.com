# filename: udocket_models/meta.py
from __future__ import annotations
from typing import List, Optional
from pydantic import Field
from .core import UBase

class Meta(UBase):
    schema_version: str = "AB-LLM-2.0"
    created_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
    generated_by: str = Field(max_length=120)
    source_index: List[str] = []
    confidence_overall: Optional[float] = Field(default=None, ge=0, le=1)
