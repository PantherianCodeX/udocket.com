from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from db.session import SessionLocal
from db.models.case import Case
from db.models.job import Job
from packages.udocket_core.storage.paths import case_dir
from uuid import uuid4
from config.settings import settings
from pathlib import Path
import shutil
import os
import mimetypes
from datetime import datetime

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
                party_1: str = Form(...), party_2: str = Form(...), notes: str = Form(""), client_role: str = Form(None)):
    cid = str(uuid4())
    with SessionLocal() as s:
        c = Case(id=cid, title=title.strip(), reference=reference.strip(),
                 party_1=party_1.strip(), party_2=party_2.strip(), client_role=(client_role or None), notes=notes)
        s.add(c); s.commit()
    # Proactively create case folder structure on case creation
    try:
        case_dir(cid)
        print(f"[admin] created case folders for {cid}")
    except Exception as e:
        print(f"[admin] warning: could not create case folders for {cid}: {e}")
    return RedirectResponse(url=f"/admin/cases/{cid}", status_code=303)

@router.get("/admin/cases/{case_id}")
def case_detail(request: Request, case_id: str):
    with SessionLocal() as s:
        c = s.get(Case, case_id)
        if not c: raise HTTPException(404)
        jobs = s.query(Job).filter(Job.case_id==case_id).order_by(Job.created_at.desc()).all()
    api_base = f"http://{request.url.hostname}:{settings.API_PORT}"
    return templates.TemplateResponse("case_detail.html", {"request": request, "case": c, "jobs": jobs, "api_base": api_base})

@router.get("/admin/cases/{case_id}/edit")
def edit_case(request: Request, case_id: str):
    with SessionLocal() as s:
        c = s.get(Case, case_id)
        if not c:
            raise HTTPException(404)
    return templates.TemplateResponse("case_edit.html", {"request": request, "case": c})

@router.post("/admin/cases/{case_id}")
def update_case(request: Request, case_id: str,
                title: str = Form(...), reference: str = Form(""),
                party_1: str = Form(...), party_2: str = Form(...), notes: str = Form(""), client_role: str = Form(None)):
    with SessionLocal() as s:
        c = s.get(Case, case_id)
        if not c:
            raise HTTPException(404)
        c.title = title.strip()
        c.reference = reference.strip()
        c.party_1 = party_1.strip()
        c.party_2 = party_2.strip()
        c.client_role = (client_role or None)
        c.notes = notes
        s.add(c)
        s.commit()
    return RedirectResponse(url=f"/admin/cases/{case_id}", status_code=303)

@router.get("/admin/api/cases/{case_id}/jobs")
def case_jobs_json(case_id: str):
    with SessionLocal() as s:
        c = s.get(Case, case_id)
        if not c:
            raise HTTPException(404)
        jobs = s.query(Job).filter(Job.case_id==case_id).order_by(Job.created_at.desc()).all()
        def original_name(p: str) -> str:
            try:
                base = str(p).rsplit("/", 1)[-1]
                return base.split("__", 1)[-1] if "__" in base else base
            except Exception:
                return str(p)
        payload = []
        for j in jobs:
            payload.append({
                "id": j.id,
                "description": original_name(j.audio_path or ""),
                "status": j.status,
                "mode": j.transcription_mode or "batch",
                "diarization": bool(j.diarization),
                "transcript": bool(j.transcript_path),
                "error": j.error_message or "",
                "created_at": j.created_at.isoformat() if j.created_at else None,
                "started_at": j.started_at.isoformat() if j.started_at else None,
                "finished_at": j.finished_at.isoformat() if j.finished_at else None,
                "sha256": j.file_sha256 or "",
                "audio_path": j.audio_path or "",
                "audio_bytes": j.audio_bytes,
                "audio_mtime": (j.audio_mtime.isoformat() if j.audio_mtime else None),
                "audio_mime": j.audio_mime,
                "audio_ext": j.audio_ext,
                "audio_bitrate_kbps": j.audio_bitrate_kbps,
                "audio_channels": j.audio_channels,
                "audio_duration_sec": j.audio_duration_sec,
                "sample_rate_hz": j.sample_rate_hz,
                "transcript_words": j.transcript_words,
                "transcript_bytes": j.transcript_bytes,
            })
    return JSONResponse(payload)

@router.get("/admin/cases/{case_id}/delete")
def delete_case_confirm(request: Request, case_id: str):
    with SessionLocal() as s:
        c = s.get(Case, case_id)
        if not c: raise HTTPException(404)
    return templates.TemplateResponse("case_delete_confirm.html", {"request": request, "case": c})

@router.post("/admin/cases/{case_id}/delete")
def delete_case(request: Request, case_id: str, confirm: str = Form("")):
    # NOTE: Once auth/users are added, gate this to sys-admins only.
    with SessionLocal() as s:
        c = s.get(Case, case_id)
        if not c:
            raise HTTPException(404)
        if confirm.strip() != c.id:
            # Failed confirmation – bounce back
            return templates.TemplateResponse("case_delete_confirm.html", {"request": request, "case": c, "error": "Confirmation text did not match Case ID."})
        # Delete related jobs first to avoid FK constraint issues
        s.query(Job).filter(Job.case_id == case_id).delete(synchronize_session=False)
        s.delete(c)
        s.commit()
    # Remove files on disk (best-effort)
    base = Path(settings.STORAGE_ROOT) / "media" / "cases" / case_id
    try:
        shutil.rmtree(base, ignore_errors=True)
    except Exception:
        pass
    return RedirectResponse(url=f"/admin/cases", status_code=303)
