# filename: udocket_models/deadlines.py
from __future__ import annotations
from typing import Optional, List
from pydantic import Field
from .core import UBase, IdStr, Provenance
from .enums import DeadlineCategoryEnum, RuleInstrumentEnum

class RuleBasis(UBase):
    instrument: RuleInstrumentEnum
    citation: Optional[str] = Field(default=None, max_length=100)

class DeadlineEntry(UBase):
    id: IdStr
    label: str = Field(max_length=200)
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    category: DeadlineCategoryEnum
    rule_basis: Optional[RuleBasis] = None
    source_text: str = Field(max_length=500)
    provenance: Optional[Provenance] = None

class Deadlines(UBase):
    entries: List[DeadlineEntry] = []
