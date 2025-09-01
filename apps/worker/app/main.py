import time, datetime
from sqlalchemy.orm import Session
from sqlalchemy import select
from db.session import SessionLocal, engine
from db.base import Base
from db.models.case import Case  # ensure table is registered
from db.models.job import Job
from packages.udocket_core.storage.paths import transcript_path, case_dir
from config.settings import settings
from apps.worker.app.runner import run_cmd

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
    return settings.AGENT_CMD_TEMPLATE.format(
        audio=job.audio_path,
        case_id=job.case_id,
        case_dir=str(case_directory),
        outdir=str(case_directory / "transcript"),
        lang=settings.LANGUAGE
    )

def main():
    while True:
        with SessionLocal() as s:
            job = claim_pending(s)
            if not job:
                time.sleep(settings.POLL_INTERVAL_SEC); continue

            cmd = build_agent_cmd(job)
            rc, out, err = run_cmd(cmd, settings.JOB_TIMEOUT_SEC)
            job.finished_at = datetime.datetime.utcnow()

            if rc == 0:
                tpath = transcript_path(job.case_id, job.id)
                if tpath.exists():
                    job.transcript_path = str(tpath)
                job.status = "SUCCEEDED"
                job.error_message = None
            else:
                job.status = "FAILED"
                job.error_message = (err or b"").decode("utf-8")[:2000]
            s.commit()

if __name__ == "__main__":
    main()
