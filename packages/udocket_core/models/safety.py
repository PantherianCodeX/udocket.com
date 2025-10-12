# filename: udocket_models/safety.py
from __future__ import annotations
from typing import List
from .core import UBase

class Safety(UBase):
    legal_advice_prohibited: bool = True
    disclaimer: str = "This summary reflects recorded information and public filings. It does not provide legal advice."
    allowed_phrases: List[str] = ["as filed", "as alleged", "per docket", "as recorded", "per practice note", "per order"]
    blocked_terms: List[str] = ["should", "must", "argue", "move", "file now", "we recommend", "advise that"]
    mask_fields: List[str] = ["email", "phone"]
    confidence_floor: float = 0.6
