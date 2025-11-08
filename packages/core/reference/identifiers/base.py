from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

TransformOp = Literal[
    "UPPER",
    "LOWER",
    "TRIM",
    "REMOVE_CHARS",  # arg: "chars"
    "KEEP_ALNUM",
    "REGEX_SUB",  # arg: {"pattern": "...", "repl": "..."}
]


class Transform(BaseModel):
    op: TransformOp
    arg: Any | None = None


class RegexRule(BaseModel):
    """Anchored regex with optional transforms. Use named groups for parsed parts."""

    pattern: str
    flags: list[Literal["IGNORECASE", "MULTILINE"]] = Field(default_factory=list)
    transforms: list[Transform] = Field(default_factory=list)


class ConstraintDecl(BaseModel):
    """
    Constraints applied after regex match.
    - year_range: {"group": "year", "min": 0, "max": 99} (applies to 2-digit years)
    - length: {"group": "seq", "min": 6, "max": 6}
    - enum: {"group": "div", "allowed": ["CR","CV"]}
    - in_catalog_location_codes: {"group": "loc"}  # code present in court_catalog locations
    """

    kind: Literal["year_range", "length", "enum", "in_catalog_location_codes"]
    group: str
    min: int | None = None
    max: int | None = None
    allowed: list[str] | None = None


class DerivationDecl(BaseModel):
    """
    Derived fields post-parse.
    - YEAR_2_TO_4: {"src": "year", "century_floor": 1980, "dest": "year4"}
    - MAP: {"src": "loc", "mapping": {"01": "Calgary"}, "dest": "loc_label"}
    - JOIN: {"src": ["year4","loc","seq"], "sep": "-", "dest": "normalized"}
    """

    kind: Literal["YEAR_2_TO_4", "MAP", "JOIN"]
    src: Any
    dest: str
    century_floor: int | None = None
    mapping: dict[str, str] | None = None
    sep: str | None = None


class CaseNumberScheme(BaseModel):
    """Generic scheme describing a jurisdiction’s case number format."""

    model_config = ConfigDict(extra="forbid")

    key: str  # e.g., "udocket.case_number.v1/CA-AB-KB"
    kind: Literal["CASE_NUMBER"]
    court_key: str  # e.g., "CA-AB-KB"
    rules: list[RegexRule]
    constraints: list[ConstraintDecl] = Field(default_factory=list)
    derivations: list[DerivationDecl] = Field(default_factory=list)
    examples_valid: list[str] = Field(default_factory=list)
    examples_invalid: list[str] = Field(default_factory=list)


class SchemeBundle(BaseModel):
    """Container for a set of schemes (JSON overlay)."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")
    schema_id: str = Field(alias="schema")
    data: list[CaseNumberScheme]
    meta: dict[str, Any] = Field(default_factory=dict)  # source_urls, last_updated, version, etc.


class CaseNumber(BaseModel):
    """Result of validating a case number string."""

    model_config = ConfigDict(extra="forbid")
    value: str
    court_key: str
    scheme_key: str
    normalized: str | None = None
    parts: dict[str, str] = Field(default_factory=dict)
