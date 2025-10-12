# filename: udocket_models/proceedings.py
from __future__ import annotations
from typing import List, Optional
from pydantic import Field
from .core import UBase, IdStr, Provenance
from .enums import (
    CountryEnum, LanguageEnum, CourtLevelEnum, CourtDivisionEnum,
    CaseTypeEnum, CaseSubTypeEnum, DocketStatusEnum, PostureEnum,
    FilingTypeEnum, OrderTypeEnum, HearingTypeEnum, HearingStatusEnum
)

class Jurisdiction(UBase):
    """Globalized jurisdiction block (AB defaults shown by reference modules)."""
    country: CountryEnum
    subnational: Optional[str] = Field(default=None, description="e.g., AB, NY, or FED")
    level: CourtLevelEnum
    court_name: str = Field(description="Stable programmatic court identifier")
    division: CourtDivisionEnum = CourtDivisionEnum.UNKNOWN_DIVISION
    city: Optional[str] = Field(default=None, max_length=100)
    language: LanguageEnum = LanguageEnum.en

class JudgeTeamMember(UBase):
    name: str = Field(min_length=3, max_length=200)
    role: str = Field(pattern=r"^(ASSIGNED_JUSTICE|APPLICATIONS_JUDGE|DUTY_JUSTICE|CASE_MANAGEMENT_JUSTICE|APPEAL_JUSTICE|UNKNOWN_JUDICIAL_ROLE)$")

class CaseHeader(UBase):
    style_of_cause: str = Field(min_length=3, max_length=300)
    file_number: str = Field(min_length=2, max_length=100)
    case_type: CaseTypeEnum = CaseTypeEnum.UNKNOWN_CASE_TYPE
    subtype: CaseSubTypeEnum = CaseSubTypeEnum.UNKNOWN_SUBTYPE
    filing_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    status: DocketStatusEnum
    summary_text: Optional[str] = Field(default=None, max_length=20000)
    judge_team: List[JudgeTeamMember] = []

class Filing(UBase):
    id: IdStr
    filing_type: FilingTypeEnum
    title: Optional[str] = Field(default=None, max_length=300)
    filed_by_party_id: Optional[IdStr] = None
    date_filed: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    summary: Optional[str] = Field(default=None, max_length=20000)
    provenance: Optional[Provenance] = None

class Order(UBase):
    id: IdStr
    order_type: OrderTypeEnum
    title: Optional[str] = Field(default=None, max_length=300)
    date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    summary: Optional[str] = Field(default=None, max_length=20000)
    provenance: Optional[Provenance] = None

class Hearing(UBase):
    id: IdStr
    hearing_type: HearingTypeEnum
    date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    status: HearingStatusEnum
    location_text: Optional[str] = Field(default=None, max_length=200)
    notes: Optional[str] = Field(default=None, max_length=20000)
    provenance: Optional[Provenance] = None

class ProceduralRecord(UBase):
    posture: PostureEnum
    filings: List[Filing] = []
    orders: List[Order] = []
    hearings: List[Hearing] = []
    commercial_list: Optional[dict] = Field(
        default={"on_list": False, "centre": "UNKNOWN_CENTRE"},
        description="AB Commercial List convenience field (centre: CALGARY/EDMONTON/UNKNOWN_CENTRE)"
    )
