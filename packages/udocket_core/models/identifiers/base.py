from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict

TransformOp = Literal[
    "UPPER",
    "LOWER",
    "TRIM",
    "REMOVE_CHARS",   # arg: "chars"
    "KEEP_ALNUM",
    "REGEX_SUB"       # arg: {"pattern": "...", "repl": "..."}
]

class Transform(BaseModel):
    op: TransformOp
    arg: Optional[Any] = None

class RegexRule(BaseModel):
    """Anchored regex with optional transforms. Use named groups for parsed parts."""
    pattern: str
    flags: List[Literal["IGNORECASE", "MULTILINE"]] = Field(default_factory=list)
    transforms: List[Transform] = Field(default_factory=list)

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
    min: Optional[int] = None
    max: Optional[int] = None
    allowed: Optional[List[str]] = None

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
    century_floor: Optional[int] = None
    mapping: Optional[Dict[str, str]] = None
    sep: Optional[str] = None

class IdentifierScheme(BaseModel):
    """Generic scheme describing a jurisdiction’s case number format."""
    model_config = ConfigDict(extra="forbid")

    key: str                      # e.g., "udocket.case_number.v1/CA-AB-KB"
    kind: Literal["CASE_NUMBER"]
    court_key: str                # e.g., "CA-AB-KB"
    rules: List[RegexRule]
    constraints: List[ConstraintDecl] = Field(default_factory=list)
    derivations: List[DerivationDecl] = Field(default_factory=list)
    examples_valid: List[str] = Field(default_factory=list)
    examples_invalid: List[str] = Field(default_factory=list)

class SchemeBundle(BaseModel):
    """Container for a set of schemes (JSON overlay)."""
    model_config = ConfigDict(populate_by_name=True, extra="allow")
    schema_id: str = Field(alias="schema")
    data: List[IdentifierScheme]
    meta: Dict[str, Any] = Field(default_factory=dict)  # source_urls, last_updated, version, etc.

class CaseNumber(BaseModel):
    """Result of validating a case number string."""
    model_config = ConfigDict(extra="forbid")
    value: str
    court_key: str
    scheme_key: str
    normalized: Optional[str] = None
    parts: Dict[str, str] = Field(default_factory=dict)
