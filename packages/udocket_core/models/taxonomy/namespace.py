from __future__ import annotations
import re
from pydantic import BaseModel, Field, field_validator

# Strict canonical shape:
#   CC.SS.COURT.DOMAIN.DIVISION.SPEC...
# - CC: country (2 letters)
# - SS: subnational/sector (2–3 alnum; e.g., AB, FED)
# - COURT: code (2–10, may include '-'; e.g., KB, ACJ, ABCA, FCA)
# - DOMAIN: FILING | HEARING | ORDER
# - DIVISION: one of the whitelisted divisions below
# - SPEC: 1+ segments of [A-Z0-9_]+
_LOCALCODE_RE: ClassVar[re.Pattern] = re.compile(
    r"^(?P<CC>[A-Z]{2})\."
    r"(?P<SS>[A-Z0-9]{2,3})\."
    r"(?P<COURT>[A-Z0-9-]{2,10})\."
    r"(?P<DOMAIN>FILING|HEARING|ORDER)\."
    r"(?P<DIVISION>CIVIL|FAMILY|CRIMINAL|YOUTH|TRAFFIC|PROBATE|APPLICATIONS|APPEALS|COMMERCIAL)"
    r"(?:\.(?P<SPEC>[A-Z0-9_]+))+$"
)

class LocalCode(BaseModel):
    code: str = Field(..., description="Namespaced jurisdictional code, e.g., CA.AB.ACJ.HRG.CRIM.DOCKET")

    @field_validator("code")
    @classmethod
    def _valid(cls, v: str) -> str:
        if not _LOCALCODE_RE.match(v):
            raise ValueError("Invalid LocalCode format; expected 'CC.SS.COURT.DOMAIN.DIVISION.SPEC...'.")
        return v

    def namespace(self) -> str:
        return ".".join(self.code.split(".")[:-1])
