from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from db.session import SessionLocal
from db.models.case import Case
from db.models.job import Job
from uuid import uuid4
from config.settings import settings

router = APIRouter()
templates = Jinja2Templates(directory="apps/admin/app/templates")

@router.get("/admin/cases")
def list_cases(request: Request):
    with SessionLocal() as s:
        items = s.query(Case).order_by(Case.created_at.desc()).all()
    return templates.TemplateResponse("cases_list.html", {"request": request, "cases": items})

@router.get("/admin/cases/new")
def new_case(request: Request):
    return templates.TemplateResponse("case_form.html", {"request": request})

@router.post("/admin/cases")
def create_case(request: Request, title: str = Form(...), reference: str = Form(""),
                party_1: str = Form(""), party_2: str = Form(""), notes: str = Form("")):
    cid = str(uuid4())
    with SessionLocal() as s:
        c = Case(id=cid, title=title.strip(), reference=reference.strip(),
                 party_1=party_1.strip(), party_2=party_2.strip(), notes=notes)
        s.add(c); s.commit()
    return RedirectResponse(url=f"/admin/cases/{cid}", status_code=303)

@router.get("/admin/cases/{case_id}")
def case_detail(request: Request, case_id: str):
    with SessionLocal() as s:
        c = s.get(Case, case_id)
        if not c: raise HTTPException(404)
        jobs = s.query(Job).filter(Job.case_id==case_id).order_by(Job.created_at.desc()).all()
    api_base = f"http://{request.url.hostname}:{settings.API_PORT}"
    return templates.TemplateResponse("case_detail.html", {"request": request, "case": c, "jobs": jobs, "api_base": api_base})
