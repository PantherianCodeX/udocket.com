# filename: udocket_models/comms.py
from __future__ import annotations
from typing import List, Optional
from pydantic import Field
from .core import UBase, IdStr

class InterviewSegment(UBase):
    start_ts: float = Field(ge=0)
    end_ts: float = Field(ge=0)
    speaker_label: Optional[str] = Field(default=None, max_length=100)
    text: str = Field(min_length=1, max_length=20000)
    extracted: Optional[dict] = Field(
        default=None,
        description="Optional extraction hints: dates[], party_ids[], links_to_fact_ids[]"
    )
    confidence: float = Field(default=0.5, ge=0, le=1)
    safety_flags: List[str] = ["NONE"]

class Interview(UBase):
    id: IdStr
    participant_role: str = Field(pattern=r"^(CLIENT|WITNESS|COUNSEL|OTHER)$")
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    segments: List[InterviewSegment]

class Communications(UBase):
    interviews: List[Interview] = []
