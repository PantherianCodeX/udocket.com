from __future__ import annotations
from typing import Dict, List, Optional, Set, Mapping
from pydantic import BaseModel, Field, ConfigDict, field_validator

from ..taxonomy.categories import (
    CountryCode, CourtLevel, Division, HearingCategory, FilingCategory, OrderCategory
)
from ..taxonomy.namespace import LocalCode

# -------------------------
# Core reference models
# -------------------------

class CourtLocation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str = Field(..., pattern=r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$")
    display_name: str
    city: Optional[str] = None
    is_base_point: bool = False
    admin_base_slug: Optional[str] = Field(
        None, description="If circuit, the base registry handling filings."
    )
    divisions_served: Set[Division] = Field(default_factory=set)
    notes: Optional[str] = None

class LocalHearingType(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: LocalCode
    label: str
    category: HearingCategory
    divisions: Set[Division] = Field(default_factory=set)

class LocalFilingType(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: LocalCode
    label: str
    category: FilingCategory

class LocalOrderType(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: LocalCode
    label: str
    category: OrderCategory

class Court(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(..., pattern=r"^[A-Z]{2}[-][A-Z0-9_-]{2,}$")  # e.g., CA-AB-ACJ
    country: CountryCode
    subnational: Optional[str] = None  # e.g., "AB", "NY"
    level: CourtLevel
    formal_name: str
    short_name: str
    divisions: Set[Division] = Field(default_factory=set)
    locations: List[CourtLocation] = Field(default_factory=list)
    hearing_codes: List[LocalHearingType] = Field(default_factory=list)
    filing_codes:  List[LocalFilingType]  = Field(default_factory=list)
    order_codes:   List[LocalOrderType]   = Field(default_factory=list)

    @field_validator("locations")
    @classmethod
    def _no_duplicate_slugs(cls, v: List[CourtLocation]) -> List[CourtLocation]:
        seen = set()
        for loc in v:
            if loc.slug in seen:
                raise ValueError(f"Duplicate location slug: {loc.slug}")
            seen.add(loc.slug)
        return v

class JurisdictionCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")
    country: CountryCode
    subnational: Optional[str] = None
    courts: Dict[str, Court] = Field(default_factory=dict)
    note: Optional[str] = None

    @field_validator("courts")
    @classmethod
    def _keys_match(cls, v: Dict[str, Court]) -> Dict[str, Court]:
        for key, court in v.items():
            if key != court.key:
                raise ValueError(f"Court dict key '{key}' must equal Court.key '{court.key}'.")
        return v

# -------------------------
# JSON bundle (data-only) wrapper + DB hints
# -------------------------

class DBTableHint(BaseModel):
    table: str
    pk: List[str]
    fk: Mapping[str, List[str]] | None = None
    unique: List[List[str]] | None = None
    indexes: List[List[str]] | None = None

class CatalogDBInfo(BaseModel):
    type: str = Field(..., pattern=r"^(postgresql)$")
    tables: Mapping[str, DBTableHint]  # e.g., 'jurisdictions', 'courts', etc.

class CatalogBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_id: str = Field(
        ...,
        alias="schema",
        pattern=r"^udocket\.reference\.catalog\.bundle\.v1$",
        description="JSON schema identifier; serialized/deserialized as 'schema'.",
    )
    db: CatalogDBInfo
    data: List[JurisdictionCatalog]
    meta: Dict[str, str] | None = None
