from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from db.session import SessionLocal
from db.models.case import Case
from db.models.job import Job

router = APIRouter()
templates = Jinja2Templates(directory="apps/admin/app/templates")

@router.get("/admin")
def dashboard(request: Request):
    with SessionLocal() as s:
        cases_count = s.query(Case).count()
        jobs_pending = s.query(Job).filter(Job.status=="PENDING").count()
        jobs_running = s.query(Job).filter(Job.status=="RUNNING").count()
        jobs_done = s.query(Job).filter(Job.status=="SUCCEEDED").count()
        jobs_failed = s.query(Job).filter(Job.status=="FAILED").count()
    return templates.TemplateResponse("dashboard.html", {"request": request,
        "cases_count": cases_count, "jobs_pending": jobs_pending, "jobs_running": jobs_running,
        "jobs_done": jobs_done, "jobs_failed": jobs_failed})