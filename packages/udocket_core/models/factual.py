# filename: udocket_models/factual.py
from __future__ import annotations
from typing import List, Optional
from pydantic import Field
from .core import UBase, IdStr, Provenance
from .enums import NeutralityEnum

class FactUnit(UBase):
    id: IdStr
    date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    participants: List[IdStr] = []
    statement: str = Field(min_length=1, max_length=20000)
    neutrality: NeutralityEnum
    linked_evidence_ids: List[IdStr] = []
    provenance: Optional[Provenance] = None

class FactualRecord(UBase):
    facts: List[FactUnit] = []
    chronology_summary: Optional[str] = Field(default=None, max_length=20000)
