from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..taxonomy.categories import (
    CountryCode,
    CourtLevel,
    Division,
    FilingCategory,
    HearingCategory,
    OrderCategory,
)
from ..taxonomy.namespace import LocalCode

# -------------------------
# Core reference models
# -------------------------


class Location(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str = Field(..., pattern=r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$")
    display_name: str
    city: str | None = None
    is_base_point: bool = False
    admin_base_slug: str | None = Field(
        None, description="If circuit, the base registry handling filings."
    )
    divisions_served: set[Division] = Field(default_factory=set)
    notes: str | None = None


class HearingCode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: LocalCode
    label: str
    category: HearingCategory
    divisions: set[Division] = Field(default_factory=set)


class FilingCode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: LocalCode
    label: str
    category: FilingCategory


class OrderCode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: LocalCode
    label: str
    category: OrderCategory


class Court(BaseModel):
    """
    A single court (e.g., CA-AB-ACJ). Contains locations (base & circuits) and
    jurisdiction-scoped local codes for hearings/filings/orders that map to global categories.
    """

    model_config = ConfigDict(extra="forbid")

    key: str = Field(..., pattern=r"^[A-Z]{2}[-][A-Z0-9_-]{2,}$")  # e.g., CA-AB-ACJ
    country: CountryCode
    subnational: str | None = None  # e.g., "AB", "NY"
    level: CourtLevel
    formal_name: str
    short_name: str
    divisions: set[Division] = Field(default_factory=set)
    locations: list[Location] = Field(default_factory=list)
    hearing_codes: list[HearingCode] = Field(default_factory=list)
    filing_codes: list[FilingCode] = Field(default_factory=list)
    order_codes: list[OrderCode] = Field(default_factory=list)

    @field_validator("locations")
    @classmethod
    def _no_duplicate_slugs(cls, v: list[Location]) -> list[Location]:
        seen = set()
        for loc in v:
            if loc.slug in seen:
                raise ValueError(f"Duplicate location slug: {loc.slug}")
            seen.add(loc.slug)
        return v

    @model_validator(mode="after")
    def _integrity(self) -> Court:
        # 1) At least one base point
        if not any(l.is_base_point for l in self.locations):
            raise ValueError(f"Court {self.key}: must define at least one base point location")

        # Build lookup for admin base checks
        by_slug = {l.slug: l for l in self.locations}

        # 2) admin_base_slug must refer to an existing base
        for loc in self.locations:
            if loc.admin_base_slug:
                base = by_slug.get(loc.admin_base_slug)
                if base is None:
                    raise ValueError(
                        f"Court {self.key}: location '{loc.slug}' references missing admin_base_slug='{loc.admin_base_slug}'"
                    )
                if not base.is_base_point:
                    raise ValueError(
                        f"Court {self.key}: admin_base_slug='{loc.admin_base_slug}' for '{loc.slug}' must point to a base location"
                    )

        # 3) divisions_served subset of Court.divisions (for all locations)
        court_divs = set(self.divisions)
        for loc in self.locations:
            if not set(loc.divisions_served).issubset(court_divs) and loc.divisions_served:
                raise ValueError(
                    f"Court {self.key}: location '{loc.slug}' has divisions {sorted(loc.divisions_served)} "
                    f"not subset of court divisions {sorted(court_divs)}"
                )

        # 4) LocalCode uniqueness within the court
        def _accumulate_codes(seq, name):
            seen_codes: set[str] = set()
            for item in seq:
                code = item.code.code
                if code in seen_codes:
                    raise ValueError(f"Court {self.key}: duplicate {name} LocalCode '{code}'")
                seen_codes.add(code)

        _accumulate_codes(self.hearing_codes, "hearing")
        _accumulate_codes(self.filing_codes, "filing")
        _accumulate_codes(self.order_codes, "order")

        # 5) Hearing code divisions subset of court divisions
        for h in self.hearing_codes:
            if h.divisions and not set(h.divisions).issubset(court_divs):
                raise ValueError(
                    f"Court {self.key}: hearing code '{h.code.code}' divisions {sorted(h.divisions)} "
                    f"not subset of court divisions {sorted(court_divs)}"
                )

        return self


class CourtCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    country: CountryCode
    subnational: str | None = None
    courts: dict[str, Court] = Field(default_factory=dict)
    note: str | None = None

    @field_validator("courts")
    @classmethod
    def _keys_match(cls, v: dict[str, Court], info) -> dict[str, Court]:
        for key, court in v.items():
            if key != court.key:
                raise ValueError(f"Court dict key '{key}' must equal Court.key '{court.key}'.")
        return v

    @model_validator(mode="after")
    def _prefix_enforced(self) -> CourtCatalog:
        """
        Ensure Court.key prefix matches country/subnational: f"{country}-{subnational}-"
        When subnational is None, we only enforce the country prefix.
        """
        prefix = f"{self.country.value}-"
        for court in self.courts.values():
            if not court.key.startswith(prefix):
                raise ValueError(f"Court {court.key}: key must start with '{prefix}'")
            if self.subnational:
                region_prefix = f"{self.country.value}-{self.subnational}-"
                if not court.key.startswith(region_prefix):
                    raise ValueError(f"Court {court.key}: key must start with '{region_prefix}'")
        return self


# -------------------------
# JSON bundle (data-only) wrapper + DB hints
# -------------------------


class DBTableHint(BaseModel):
    table: str
    pk: list[str]
    fk: Mapping[str, list[str]] | None = None
    unique: list[list[str]] | None = None
    indexes: list[list[str]] | None = None


class CatalogDBInfo(BaseModel):
    type: str = Field(..., pattern=r"^(postgresql)$")
    tables: Mapping[str, DBTableHint]  # e.g., 'jurisdictions', 'courts', etc.


class CatalogMeta(BaseModel):
    model_config = ConfigDict(extra="allow")
    source_urls: list[str] = Field(default_factory=list)
    version: str | None = None
    last_updated: str | None = None
    notes: str | None = Field(default=None, description="Notes about scope, limits, etc.")


class CatalogBundle(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    schema_id: str = Field(
        ...,
        alias="schema",
        pattern=r"^udocket\.reference\.catalog\.bundle\.v1$",
        description="JSON schema identifier; serialized/deserialized as 'schema'.",
    )
    db: CatalogDBInfo
    data: list[CourtCatalog]
    meta: CatalogMeta = Field(default_factory=CatalogMeta)
