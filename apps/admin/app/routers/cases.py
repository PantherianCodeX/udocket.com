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
from typing import Optional
import base64
import shutil
import os
import mimetypes
from datetime import datetime
import json

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
    # Compute case-level updated timestamp from jobs
    last_update = None
    try:
        for j in jobs:
            t = j.finished_at or j.started_at or j.created_at
            if t and (last_update is None or t > last_update):
                last_update = t
    except Exception:
        last_update = None
    return templates.TemplateResponse(
        "case_detail.html",
        {"request": request, "case": c, "jobs": jobs, "api_base": api_base, "case_last_update": last_update},
    )

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
            # Try to enrich with agent metadata from per-job ops JSON
            meta = {}
            try:
                ops = case_dir(case_id) / 'ops' / f"{j.id}_transcription_log.json"
                if ops.exists():
                    meta = json.loads(ops.read_text(encoding='utf-8'))
            except Exception:
                meta = {}
            payload.append({
                "id": j.id,
                "description": original_name(j.audio_path or ""),
                "status": j.status,
                "mode": j.transcription_mode or "batch",
                "diarization": bool(j.diarization),
                "diagnostics": bool(getattr(j, 'diagnostics', False)),
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
                # Agent meta (if present)
                "audio_sha256_remote": meta.get("audio_sha256_remote"),
                "audio_content_md5_b64": meta.get("audio_content_md5_b64"),
                "audio_size_bytes_remote": meta.get("audio_size_bytes_remote"),
                "transcript_sha256": meta.get("transcript_sha256"),
                "azure_region": meta.get("azure_region"),
                "language": meta.get("language"),
                "diarization_enabled": meta.get("diarization_enabled"),
                "num_speakers": meta.get("num_speakers"),
                "segments": meta.get("segments"),
                "avg_confidence": meta.get("avg_confidence"),
                "azure_transcription_url": meta.get("azure_transcription_url"),
                "attempts_used": meta.get("attempts_used"),
            })
    return JSONResponse(payload)

@router.get("/admin/api/cases/{case_id}/jobs/{job_id}/log")
def job_log(case_id: str, job_id: str):
    """Return human-readable transcription log text for a job, enriched with JSON metadata if present."""
    ops_dir = case_dir(case_id) / 'ops'
    text_path = ops_dir / f"{job_id}_transcription.log"
    json_path = ops_dir / f"{job_id}_transcription_log.json"
    text = None
    meta = None
    if text_path.exists():
        try:
            text = text_path.read_text(encoding='utf-8')
        except Exception:
            text = None
    if json_path.exists():
        try:
            meta = json.loads(json_path.read_text(encoding='utf-8'))
        except Exception:
            meta = None
    if not text and not meta:
        return JSONResponse({"error": "no_log_found"}, status_code=404)
    # Enrich: append a compact summary of meta for readability
    if meta:
        fields = [
            ("status", meta.get("status")),
            ("error_message", meta.get("error_message")),
            ("language", meta.get("language")),
            ("azure_region", meta.get("azure_region")),
            ("diarization", meta.get("diarization_enabled")),
            ("audio_file", meta.get("audio_file")),
            ("audio_sha256", meta.get("audio_sha256")),
            ("audio_sha256_remote", meta.get("audio_sha256_remote")),
            ("audio_content_md5_b64", meta.get("audio_content_md5_b64")),
            ("audio_size_bytes_remote", meta.get("audio_size_bytes_remote")),
            ("transcript_file", meta.get("transcript_file")),
            ("transcript_sha256", meta.get("transcript_sha256")),
            ("word_count", meta.get("word_count")),
            ("attempts_used", meta.get("attempts_used")),
            ("azure_transcription_url", meta.get("azure_transcription_url")),
            ("timestamp_utc", meta.get("timestamp_utc")),
        ]
        lines = ["", "--- Details ------------------------------------------------------------"]
        for k, v in fields:
            if v is not None and v != "":
                lines.append(f"{k}: {v}")
        if not text:
            text = ""  # fallback
        text = text.rstrip() + "\n" + "\n".join(lines) + "\n"
    return JSONResponse({"text": text or "", "json": meta})

def _blob_service_client():
    # Lazy import to avoid mandatory dependency at process start
    try:
        from azure.storage.blob import BlobServiceClient
    except Exception as e:
        raise HTTPException(500, f"azure-storage-blob not installed: {e}")
    if settings.AZURE_BLOB_CONNECTION_STRING:
        return BlobServiceClient.from_connection_string(settings.AZURE_BLOB_CONNECTION_STRING)
    if not settings.AZURE_BLOB_ACCOUNT or not settings.AZURE_BLOB_KEY:
        raise HTTPException(500, "Missing Azure Blob credentials (AZURE_BLOB_ACCOUNT/AZURE_BLOB_KEY or connection string)")
    account_url = f"https://{settings.AZURE_BLOB_ACCOUNT}.blob.core.windows.net"
    return BlobServiceClient(account_url=account_url, credential=settings.AZURE_BLOB_KEY)

def _original_from_path(p: str) -> Optional[str]:
    try:
        base = str(p).rsplit("/", 1)[-1]
        return base.split("__", 1)[-1] if "__" in base else base
    except Exception:
        return None

@router.post("/admin/api/cases/{case_id}/jobs/{job_id}/refresh-remote")
def refresh_remote_hashes(case_id: str, job_id: str):
    """Best-effort: fetch remote blob size + hashes and persist to per-job ops JSON.
    Requires Azure Blob credentials configured for the admin service.
    """
    # Look up job to get original name
    with SessionLocal() as s:
        j = s.get(Job, job_id)
        if not j or j.case_id != case_id:
            raise HTTPException(404)
        original = _original_from_path(j.audio_path or "")
        if not original:
            raise HTTPException(400, "job has no audio_path")

    if not settings.AZURE_BLOB_CONTAINER:
        raise HTTPException(500, "AZURE_BLOB_CONTAINER is not configured")
    blob_name = f"cases/{case_id}/audio/{job_id}__{original}"

    try:
        bsc = _blob_service_client()
        container = bsc.get_container_client(settings.AZURE_BLOB_CONTAINER)
        blob = container.get_blob_client(blob_name)
        props = blob.get_blob_properties()
        # Content-MD5 is bytes; encode to base64 if present
        md5_b64 = None
        try:
            raw_md5 = getattr(props, 'content_settings', None).content_md5 if getattr(props, 'content_settings', None) else None
            if raw_md5:
                md5_b64 = base64.b64encode(raw_md5).decode('ascii')
        except Exception:
            md5_b64 = None
        size = getattr(props, 'size', None) or getattr(props, 'blob_size', None)

        # Compute SHA-256 if size <= threshold (default 200 MB)
        import hashlib
        import os
        max_mb = int(os.getenv("BATCH_HASH_MAX_MB", "200"))
        remote_sha256 = None
        if size is None or size <= max_mb * 1024 * 1024:
            h = hashlib.sha256()
            stream = blob.download_blob()
            for chunk in stream.chunks():
                if chunk:
                    h.update(chunk)
            remote_sha256 = h.hexdigest()

        # Persist into per-job JSON meta so polling UI picks it up
        ops_dir = case_dir(case_id) / 'ops'
        ops_dir.mkdir(parents=True, exist_ok=True)
        json_path = ops_dir / f"{job_id}_transcription_log.json"
        data = {}
        try:
            if json_path.exists():
                data = json.loads(json_path.read_text(encoding='utf-8'))
        except Exception:
            data = {}
        if remote_sha256 is not None:
            data["audio_sha256_remote"] = remote_sha256
        if md5_b64 is not None:
            data["audio_content_md5_b64"] = md5_b64
        if size is not None:
            data["audio_size_bytes_remote"] = size
        try:
            json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
        except Exception:
            # Non-fatal; still return values
            pass

        return JSONResponse({
            "audio_sha256_remote": remote_sha256,
            "audio_content_md5_b64": md5_b64,
            "audio_size_bytes_remote": size,
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"refresh_remote_failed: {e}")

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
