from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from ...reference.taxonomy.categories import FilingCategory, HearingCategory, OrderCategory


class HearingStatus(str):
    SCHEDULED = "SCHEDULED"
    HEARD = "HEARD"
    ADJOURNED = "ADJOURNED"
    CANCELLED = "CANCELLED"
    RESERVED = "RESERVED"
    UNKNOWN_STATUS = "UNKNOWN_STATUS"


class Hearing(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    hearing_type: HearingCategory = Field(..., description="Portable category (global)")
    hearing_local_code: str = Field(..., description="Jurisdictional local code (namespaced)")
    date: date  # ISO-8601 parsed by Pydantic
    status: str = Field(default=HearingStatus.UNKNOWN_STATUS)
    location_text: str | None = None
    notes: str | None = None


class Filing(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    filing_type: FilingCategory
    filing_local_code: str = Field(..., description="Jurisdictional local code")
    title: str | None = None
    date_filed: date  # ISO-8601
    summary: str | None = None


class Order(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    order_type: OrderCategory
    order_local_code: str = Field(..., description="Jurisdictional local code")
    title: str | None = None
    date: date  # ISO-8601
    summary: str | None = None
