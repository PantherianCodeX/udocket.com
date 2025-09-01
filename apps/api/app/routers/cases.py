from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from db.session import SessionLocal
from db.models.case import Case
from uuid import uuid4

router = APIRouter()

class CaseIn(BaseModel):
    title: str
    reference: str | None = None
    party_1: str | None = None
    party_2: str | None = None
    notes: str | None = None

@router.post("", status_code=201)
def create_case(body: CaseIn):
    with SessionLocal() as s:
        cid = str(uuid4())
        c = Case(id=cid, **body.dict())
        s.add(c); s.commit()
        return {"id": cid}

@router.get("/{case_id}")
def get_case(case_id: str):
    with SessionLocal() as s:
        c = s.get(Case, case_id)
        if not c: raise HTTPException(404)
        return {"id": c.id, "title": c.title, "reference": c.reference,
                "party_1": c.party_1, "party_2": c.party_2, "notes": c.notes}