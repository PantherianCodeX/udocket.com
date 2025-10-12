# filename: udocket_models/evidence.py
from __future__ import annotations
from typing import List, Optional
from pydantic import Field
from .core import UBase, IdStr, Provenance
from .enums import EvidenceKindEnum, EvidenceOriginEnum

class EvidenceItem(UBase):
    id: IdStr
    kind: EvidenceKindEnum
    title: str = Field(max_length=300)
    origin: EvidenceOriginEnum
    file_ref: Optional[str] = Field(default=None, max_length=400)
    exhibit_label: Optional[str] = Field(default=None, max_length=50)
    linked_fact_ids: List[IdStr] = []
    provenance: Optional[Provenance] = None

class EvidenceBundle(UBase):
    items: List[EvidenceItem] = []
    summary: Optional[str] = Field(default=None, max_length=20000)
