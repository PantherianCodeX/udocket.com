import time, datetime, sys, json, logging
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import select, update
from db.session import SessionLocal, engine, ensure_jobs_schema
from db.base import Base
from db.models.case import Case  # ensure table is registered
from db.models.job import Job
from packages.udocket_core.storage.paths import transcript_path, case_dir
from config.settings import settings
from apps.worker.app.runner import run_cmd
from apps.worker.app.blob_upload import upload_with_sas
from packages.udocket_core.audio import probe_audio_metadata

# Ensure tables exist (useful when worker starts before API/Admin)
Base.metadata.create_all(bind=engine)
ensure_jobs_schema()

# Configure process-wide logging once, to stdout, avoiding duplicate handlers
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(process)d %(levelname)s worker: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)
log = logging.getLogger("worker")


def is_job_cancelled(job_id: str) -> bool:
    try:
        with SessionLocal() as session:
            obj = session.get(Job, job_id)
            return obj is None or obj.status == "CANCELLED"
    except Exception:
        return False

def claim_pending(session: Session):
    # Atomically claim a single pending job to avoid duplicate processing across workers.
    job_id = session.execute(
        select(Job.id).where(Job.status == "PENDING").order_by(Job.created_at).limit(1)
    ).scalar_one_or_none()
    if not job_id:
        return None
    now = datetime.datetime.utcnow()
    res = session.execute(
        update(Job)
        .where(Job.id == job_id, Job.status == "PENDING")
        .values(status="RUNNING", started_at=now)
    )
    session.commit()
    if res.rowcount == 1:
        return session.get(Job, job_id)
    return None

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
    if getattr(job, 'diagnostics', False):
        cmd += " --diagnostics"
    return cmd

def probe_audio(path: str) -> dict:
    try:
        meta = probe_audio_metadata(path)
    except Exception:
        meta = {}
    if not meta:
        return {'duration_sec': None, 'bitrate_kbps': None, 'channels': None, 'sample_rate_hz': None}
    dur = meta.get('audio_duration_s')
    br = meta.get('audio_bitrate_kbps')
    return {
        'duration_sec': int(round(dur)) if isinstance(dur, (int, float)) else None,
        'bitrate_kbps': int(br) if isinstance(br, (int, float)) else None,
        'channels': meta.get('audio_channels'),
        'sample_rate_hz': meta.get('audio_sample_rate_hz'),
    }

def main():
    log.info("starting; polling for jobs...")
    last_idle_log = 0.0
    while True:
        with SessionLocal() as s:
            job = claim_pending(s)
            if not job:
                now = time.monotonic()
                if now - last_idle_log > 10:
                    log.info("idle; no pending jobs")
                    last_idle_log = now
                time.sleep(settings.POLL_INTERVAL_SEC); continue

            try:
                log.info(f"claimed job {job.id} case={job.case_id} mode={job.transcription_mode} diar={job.diarization}")
                cmd = build_agent_cmd(job)
                # Probe audio technicals if not already set
                if job.audio_path and (job.audio_bitrate_kbps is None or job.audio_channels is None or job.audio_duration_sec is None):
                    info = probe_audio(job.audio_path)
                    job.audio_bitrate_kbps = info.get('bitrate_kbps')
                    job.audio_channels = info.get('channels')
                    job.audio_duration_sec = info.get('duration_sec')
                    job.sample_rate_hz = info.get('sample_rate_hz')
                    s.commit()
                try:
                    s.refresh(job)
                except Exception:
                    pass
                if job.status == "CANCELLED":
                    job.finished_at = datetime.datetime.utcnow()
                    s.commit()
                    log.info(f"job {job.id} cancellation detected before execution; skipping")
                    continue
            except Exception as e:
                job.finished_at = datetime.datetime.utcnow()
                job.status = "FAILED"
                job.error_message = (str(e) or "upload/build command failed")[:2000]
                s.commit()
                log.error(f"job {job.id} failed to build cmd: {job.error_message}")
                continue

            try:
                rc, out, err = run_cmd(cmd, settings.JOB_TIMEOUT_SEC, cancel_check=lambda job_id=job.id: is_job_cancelled(job_id))
            except Exception as e:
                job.finished_at = datetime.datetime.utcnow()
                job.status = "FAILED"
                job.error_message = (str(e) or "agent execution failed")[:2000]
                s.commit()
                log.error(f"job {job.id} execution error: {job.error_message}")
                continue

            job.finished_at = datetime.datetime.utcnow()
            try:
                s.refresh(job)
            except Exception:
                pass

            if job.status == "CANCELLED" or rc == 125:
                job.status = "CANCELLED"
                if not job.error_message:
                    job.error_message = "Cancelled by user"
                s.commit()
                log.info(f"job {job.id} cancelled")
                continue

            if rc == 0:
                tpath = transcript_path(job.case_id, job.id)
                if tpath.exists():
                    job.transcript_path = str(tpath)
                    # Persist transcript stats
                    try:
                        st = tpath.stat()
                        job.transcript_bytes = st.st_size
                    except Exception:
                        job.transcript_bytes = None
                    try:
                        txt = tpath.read_text(encoding='utf-8', errors='ignore')
                        job.transcript_words = len([w for w in txt.split() if w])
                    except Exception:
                        job.transcript_words = None
                job.status = "SUCCEEDED"
                job.error_message = None
                log.info(f"job {job.id} succeeded")
            else:
                job.status = "FAILED"
                job.error_message = (err or b"").decode("utf-8")[:2000]
                log.error(f"job {job.id} failed: {job.error_message}")
            s.commit()

if __name__ == "__main__":
    main()
