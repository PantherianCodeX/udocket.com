from fastapi import APIRouter, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from uuid import uuid4
from hashlib import sha256
from db.session import SessionLocal
from db.models.job import Job
from db.models.case import Case
from packages.udocket_core.storage.paths import audio_path, transcript_path
from config.settings import settings

router = APIRouter()

def _mime_allowed(mime: str) -> bool:
    allowed = set([m.strip() for m in settings.ALLOWED_AUDIO_MIME.split(",")])
    return mime in allowed

@router.post("", status_code=201)
async def upload(case_id: str, file: UploadFile = File(...)):
    if not _mime_allowed(file.content_type):
        raise HTTPException(400, f"Unsupported file type: {file.content_type}")

    job_id = str(uuid4())
    with SessionLocal() as s:
        if not s.get(Case, case_id): raise HTTPException(404, "Case not found")

    data = await file.read()
    dest = audio_path(case_id, job_id, file.filename)
    dest.write_bytes(data)

    with SessionLocal() as s:
        j = Job(id=job_id, case_id=case_id, audio_path=str(dest), status="PENDING",
                file_sha256=sha256(data).hexdigest())
        s.add(j); s.commit()

    return {"job_id": job_id, "status": "PENDING"}

@router.get("/{job_id}")
def status(job_id: str):
    with SessionLocal() as s:
        j = s.get(Job, job_id)
        if not j: raise HTTPException(404)
        payload = {"job_id": j.id, "status": j.status, "case_id": j.case_id}
        if j.status == "SUCCEEDED" and j.transcript_path:
            payload["download"] = f"/transcriptions/{job_id}/download"
        if j.error_message:
            payload["error"] = j.error_message
        return payload

@router.get("/{job_id}/download")
def download(job_id: str):
    from fastapi.responses import FileResponse
    with SessionLocal() as s:
        j = s.get(Job, job_id)
        if not j or j.status != "SUCCEEDED" or not j.transcript_path:
            raise HTTPException(404)
        return FileResponse(j.transcript_path, media_type="text/plain",
                            filename=f"{job_id}__transcript.txt")