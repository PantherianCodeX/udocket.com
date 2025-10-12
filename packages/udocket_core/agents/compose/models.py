from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from models.taxonomy.categories import HearingCategory, FilingCategory, OrderCategory

# These are the writer-facing types the udocket agent uses to render neutral summaries.
# They carry global categories (portable) + a jurisdiction-scoped local code string.

class Hearing(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    hearing_type: HearingCategory = Field(..., description="Portable category (global)")
    hearing_local_code: str = Field(..., description="Jurisdictional local code (namespaced)")
    date: str
    status: str
    location_text: Optional[str] = None
    notes: Optional[str] = None

class Filing(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    filing_type: FilingCategory
    filing_local_code: str = Field(..., description="Jurisdictional local code")
    title: Optional[str] = None
    date_filed: str
    summary: Optional[str] = None

class Order(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    order_type: OrderCategory
    order_local_code: str = Field(..., description="Jurisdictional local code")
    title: Optional[str] = None
    date: str
    summary: Optional[str] = None
