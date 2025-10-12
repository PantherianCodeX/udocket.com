# filename: udocket_models/core.py
from __future__ import annotations
from typing import Optional, Annotated
from pydantic import BaseModel, Field, ConfigDict, StringConstraints

IdStr = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_-]{2,64}$")]

class UBase(BaseModel):
    """Unified base model with consistent Pydantic v2 config for udocket."""
    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
        extra='forbid',
        use_enum_values=True,
        str_strip_whitespace=True,
        frozen=False,
        json_schema_serialization_defaults_required=True
    )

class Money(UBase):
    currency: str = Field('CAD', description="ISO currency (default CAD)")
    value: float = Field(ge=0)

class Provenance(UBase):
    source_type: str = Field(
        description="Where did the datum come from?",
        pattern=r"^(DOCKET|COURT_FILING|COURT_ORDER|HEARING_RECORD|INTERVIEW|CLIENT_DOCUMENT|EMAIL_OR_MESSAGE|PUBLIC_WEBSITE|SYSTEM_DERIVED|OTHER)$"
    )
    source_id: str = Field(min_length=1, max_length=256)
    verbatim: bool = False
    confidence: float = Field(ge=0, le=1)
    page: Optional[int] = Field(default=None, ge=1)
    paragraph: Optional[str] = Field(default=None, max_length=50)
    timestamp: Optional[float] = Field(default=None, ge=0)
