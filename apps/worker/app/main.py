import time, datetime, sys
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import select
from db.session import SessionLocal, engine
from db.base import Base
from db.models.case import Case  # ensure table is registered
from db.models.job import Job
from packages.udocket_core.storage.paths import transcript_path, case_dir
from config.settings import settings
from apps.worker.app.runner import run_cmd
from apps.worker.app.blob_upload import upload_with_sas

# Ensure tables exist (useful when worker starts before API/Admin)
Base.metadata.create_all(bind=engine)

def claim_pending(session: Session):
    job = session.execute(select(Job).where(Job.status=="PENDING")).scalars().first()
    if job:
        job.status = "RUNNING"
        job.started_at = datetime.datetime.utcnow()
        session.commit()
    return job

def build_agent_cmd(job: Job) -> str:
    case_directory = case_dir(job.case_id)
    audio_arg = job.audio_path
    if job.transcription_mode == "batch":
        # Upload source to Azure Blob and pass HTTPS SAS URL to agent
        try:
            original_name = job.audio_path.split("__", 1)[-1]
        except Exception:
            original_name = job.audio_path.rsplit("/", 1)[-1]
        audio_arg = upload_with_sas(Path(job.audio_path), job.case_id, job.id, original_name)

    cmd = settings.AGENT_CMD_TEMPLATE.format(
        audio=audio_arg,
        case_id=job.case_id,
        case_dir=str(case_directory),
        outdir=str(case_directory / "transcript"),
        lang=settings.LANGUAGE
    )
    cmd += f' --mode "{job.transcription_mode}"'
    if job.transcription_mode == "batch" and job.diarization:
        cmd += " --diarization"
    return cmd

def main():
    print("[worker] starting; polling for jobs...", file=sys.stderr, flush=True)
    last_idle_log = 0.0
    while True:
        with SessionLocal() as s:
            job = claim_pending(s)
            if not job:
                now = time.monotonic()
                if now - last_idle_log > 10:
                    print("[worker] idle; no pending jobs", file=sys.stderr, flush=True)
                    last_idle_log = now
                time.sleep(settings.POLL_INTERVAL_SEC); continue

            try:
                print(f"[worker] claimed job {job.id} case={job.case_id} mode={job.transcription_mode} diar={job.diarization}", file=sys.stderr, flush=True)
                cmd = build_agent_cmd(job)
            except Exception as e:
                job.finished_at = datetime.datetime.utcnow()
                job.status = "FAILED"
                job.error_message = (str(e) or "upload/build command failed")[:2000]
                s.commit()
                print(f"[worker] job {job.id} failed to build cmd: {job.error_message}", file=sys.stderr, flush=True)
                continue

            try:
                rc, out, err = run_cmd(cmd, settings.JOB_TIMEOUT_SEC)
            except Exception as e:
                job.finished_at = datetime.datetime.utcnow()
                job.status = "FAILED"
                job.error_message = (str(e) or "agent execution failed")[:2000]
                s.commit()
                print(f"[worker] job {job.id} execution error: {job.error_message}", file=sys.stderr, flush=True)
                continue

            job.finished_at = datetime.datetime.utcnow()

            if rc == 0:
                tpath = transcript_path(job.case_id, job.id)
                if tpath.exists():
                    job.transcript_path = str(tpath)
                job.status = "SUCCEEDED"
                job.error_message = None
                print(f"[worker] job {job.id} succeeded", file=sys.stderr, flush=True)
            else:
                job.status = "FAILED"
                job.error_message = (err or b"").decode("utf-8")[:2000]
                print(f"[worker] job {job.id} failed: {job.error_message}", file=sys.stderr, flush=True)
            s.commit()

if __name__ == "__main__":
    main()
