from fastapi import APIRouter, Request, UploadFile, File, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from hashlib import sha256
from uuid import uuid4
from db.session import SessionLocal
from db.models.case import Case
from db.models.job import Job
from packages.udocket_core.storage.paths import audio_path
from config.settings import settings

router = APIRouter()
templates = Jinja2Templates(directory="apps/admin/app/templates")

def _mime_allowed(mime: str) -> bool:
    allowed = set([m.strip() for m in settings.ALLOWED_AUDIO_MIME.split(",")])
    return mime in allowed

@router.get("/admin/cases/{case_id}/upload-audio")
def upload_form(request: Request, case_id: str):
    return templates.TemplateResponse("upload_form.html", {"request": request, "case_id": case_id})

@router.post("/admin/cases/{case_id}/upload-audio")
async def upload_audio(case_id: str, file: UploadFile = File(...)):
    if not _mime_allowed(file.content_type):
        raise HTTPException(400, f"Unsupported type: {file.content_type}")
    data = await file.read()
    job_id = str(uuid4())
    dest = audio_path(case_id, job_id, file.filename)
    dest.write_bytes(data)

    with SessionLocal() as s:
        if not s.get(Case, case_id): raise HTTPException(404, "Case not found")
        j = Job(id=job_id, case_id=case_id, audio_path=str(dest), status="PENDING",
                file_sha256=sha256(data).hexdigest())
        s.add(j); s.commit()
    return RedirectResponse(url=f"/admin/cases/{case_id}", status_code=303)