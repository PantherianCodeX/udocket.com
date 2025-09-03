from fastapi import APIRouter, Request, UploadFile, File, HTTPException, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from hashlib import sha256
from typing import Literal
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
async def upload_audio(
    case_id: str,
    transcription_mode: Literal["batch", "on-demand"] = Form("on-demand"),
    diarization: bool = Form(False),
    file: UploadFile = File(...),
):
    if diarization and transcription_mode != "batch":
        raise HTTPException(400, "Diarization only supported in batch mode")
    if not _mime_allowed(file.content_type):
        raise HTTPException(400, f"Unsupported type: {file.content_type}")
    data = await file.read()
    job_id = str(uuid4())
    dest = audio_path(case_id, job_id, file.filename)
    # Ensure directories and write file
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    print(f"[admin] upload: case={case_id} job={job_id} name={file.filename} bytes={len(data)} -> {dest}")

    with SessionLocal() as s:
        if not s.get(Case, case_id): raise HTTPException(404, "Case not found")
        j = Job(
            id=job_id,
            case_id=case_id,
            audio_path=str(dest),
            status="PENDING",
            file_sha256=sha256(data).hexdigest(),
            transcription_mode=transcription_mode,
            diarization=diarization,
        )
        s.add(j); s.commit()
    return RedirectResponse(url=f"/admin/cases/{case_id}", status_code=303)
