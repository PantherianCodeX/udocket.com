# filename: udocket_models/outputs.py
from __future__ import annotations
from typing import List, Dict
from pydantic import Field
from .core import UBase, IdStr

class RenderSection(UBase):
    heading: str = Field(pattern=r"^(CASE_OVERVIEW|KEY_PEOPLE_AND_ROLES|TIMELINE_OF_EVENTS|MAIN_ISSUES|NEXT_STEPS_NEUTRAL|CASE_SUMMARY|PARTIES_AND_ROLES|FACTUAL_BACKGROUND|ISSUES_PRESENTED|EVIDENCE_AND_SUPPORTING_FACTS|PROCEDURAL_STATUS_AND_NEXT_KNOWN_STEPS)$")
    content_refs: List[str]

class RenderPlan(UBase):
    id: IdStr
    audience: str = Field(pattern=r"^(CLIENT|LAWYER)$")
    tone: str = Field(default="NEUTRAL_DESCRIPTIVE", pattern=r"^NEUTRAL_DESCRIPTIVE$")
    sections: List[RenderSection]
    docx_placeholders: Dict[str, str] = {}

class Outputs(UBase):
    render_plans: List[RenderPlan]
