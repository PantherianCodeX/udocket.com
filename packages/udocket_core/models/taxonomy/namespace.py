from __future__ import annotations
import re
from pydantic import BaseModel, Field, field_validator

# e.g., "CA.AB.ACJ.HRG.CRIM.DOCKET" or "US.NY.NYCO.SUP.COMDIV.HRG.PRELIM_CONF"
_CODE_RE = re.compile(r"^[A-Z]{2}(?:\.[A-Z0-9]{2,}){2,}$")

class LocalCode(BaseModel):
    code: str = Field(..., description="Namespaced jurisdictional code, e.g., CA.AB.ACJ.HRG.CRIM.DOCKET")

    @field_validator("code")
    @classmethod
    def _valid(cls, v: str) -> str:
        if not _CODE_RE.match(v):
            raise ValueError("Invalid LocalCode format; expected 'CC.SS.COURT.DOMAIN.SPEC...'.")
        return v

    def namespace(self) -> str:
        return ".".join(self.code.split(".")[:-1])
