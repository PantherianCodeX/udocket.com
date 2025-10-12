# filename: udocket_models/parties.py
from __future__ import annotations
from typing import List, Optional
from pydantic import Field
from .core import UBase, IdStr, Provenance
from .enums import PartyRoleEnum, PartyKindEnum, RepresentativeTypeEnum

class Party(UBase):
    id: IdStr
    name: str = Field(min_length=2, max_length=200)
    role: PartyRoleEnum
    kind: PartyKindEnum
    aliases: List[str] = []
    contact_city: Optional[str] = Field(default=None, max_length=100)
    representation_ids: List[IdStr] = []
    provenance: Optional[Provenance] = None

class Representative(UBase):
    id: IdStr
    name: str = Field(min_length=2, max_length=200)
    firm: Optional[str] = Field(default=None, max_length=200)
    bar_id: Optional[str] = Field(default=None, max_length=100)
    represents: List[IdStr] = []
    type: RepresentativeTypeEnum
    provenance: Optional[Provenance] = None

class Actors(UBase):
    parties: List[Party]
    representatives: List[Representative] = []
