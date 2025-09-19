from fastapi import APIRouter, HTTPException
from typing import Optional, Annotated
from pydantic import BaseModel, Field, ConfigDict, field_validator
from sqlalchemy.orm import Session
from db.session import SessionLocal
from db.models.case import Case
from uuid import uuid4

router = APIRouter()

class CaseIn(BaseModel):
    model_config = ConfigDict(frozen=True)
    title: Annotated[str, Field(min_length=1, max_length=200)]
    reference: Annotated[Optional[str], Field(default=None, max_length=100)] = None
    party_1: Annotated[Optional[str], Field(default=None, max_length=120)] = None
    party_2: Annotated[Optional[str], Field(default=None, max_length=120)] = None
    notes: Optional[str] = None

    @field_validator('title', 'reference', 'party_1', 'party_2', mode='before')
    @classmethod
    def _strip(cls, v):
        if v is None:
            return v
        return str(v).strip()

@router.post("", status_code=201)
def create_case(body: CaseIn):
    with SessionLocal() as s:
        cid = str(uuid4())
        c = Case(id=cid, **body.model_dump())
        s.add(c); s.commit()
        return {"id": cid}

@router.get("/{case_id}")
def get_case(case_id: str):
    with SessionLocal() as s:
        c = s.get(Case, case_id)
        if not c: raise HTTPException(404)
        return {"id": c.id, "title": c.title, "reference": c.reference,
                "party_1": c.party_1, "party_2": c.party_2, "notes": c.notes}
