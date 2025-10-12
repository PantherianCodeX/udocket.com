# filename: udocket_models/issues.py
from __future__ import annotations
from typing import List, Optional
from pydantic import Field
from .core import UBase, IdStr, Provenance

class Issue(UBase):
    id: IdStr
    question: str = Field(min_length=5, max_length=300)
    linked_filings: List[IdStr] = []
    neutral_summary: Optional[str] = Field(default=None, max_length=20000)
    policy_check: str = Field(default="OK", pattern=r"^(OK|RISK_ADVICE_LANGUAGE)$")
    provenance: Optional[Provenance] = None

class IssuesFrame(UBase):
    issues: List[Issue] = []
