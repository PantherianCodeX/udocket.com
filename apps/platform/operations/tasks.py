from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from packages.udocket_core.agents import (
    TranscriptionAgent,
    TranscriptionConfig,
)
from apps.platform.operations.channels import send_job_update, send_case_update
from apps.platform.jobs.models import Job
from apps.platform.artifacts.models import CaseArtifact
from apps.platform.operations.blob_upload import upload_with_sas
from apps.platform.operations.models import TaskRun
from apps.platform.cases.models import Case
from apps.platform.operations.audit import emit as audit_emit
import re
import json
import logging

log = logging.getLogger("apps.platform.operations.tasks")


@shared_task(bind=True)
def transcribe_job(
    self,
    *,
    case_id: str,
    job_id: str,
    audio_input: str,
    mode: str = "on-demand",
    diarization: bool = False,
    language: Optional[str] = None,
) -> Dict[str, Any]:
    """Run transcription using the importable agent.

    Arguments are explicit to decouple from legacy DB schema.
    """
    case_dir = Path(settings.MEDIA_ROOT) / "cases" / case_id
    cfg = TranscriptionConfig.from_env()
    agent = TranscriptionAgent(cfg)

    # Update DB status and notify; record TaskRun
    try:
        job_obj = Job.objects.get(pk=job_id)
        job_obj.status = Job.Status.RUNNING
        job_obj.started_at = timezone.now()
        job_obj.save(update_fields=["status", "started_at"])
    except Exception:
        job_obj = None
    log.info("job claimed", extra={"job_id": job_id, "case_id": case_id, "mode": mode, "diarization": diarization})
    send_job_update(job_id, event="job.started", status="RUNNING", case_id=case_id)

    # Create a TaskRun row for reproducibility
    tr = TaskRun(
        task_name="transcribe_job",
        task_id=getattr(self.request, "id", None) or "",
        status="RUNNING",
        job_id=job_id,
        case_id=case_id,
        meta={"mode": mode, "diarization": diarization, "language": language},
    )
    try:
        tr.save()
    except Exception:
        tr = None

    # Run the agent; only this block determines success vs. failure
    try:
        # If batch mode and the input is a local file, upload to Azure Blob to obtain SAS URL
        ai = audio_input
        if mode == "batch" and not (str(audio_input).startswith("http://") or str(audio_input).startswith("https://")):
            try:
                log.info("uploading source to blob", extra={"job_id": job_id})
                ai = upload_with_sas(Path(audio_input), case_id, job_id)
                log.info("uploaded source to blob", extra={"job_id": job_id})
            except Exception:
                try:
                    # Legacy fallback (used in FastAPI worker)
                    from apps.worker.app.blob_upload import upload_with_sas as legacy_upload

                    log.warning("blob upload failed; trying legacy uploader", extra={"job_id": job_id})
                    ai = legacy_upload(Path(audio_input), case_id, job_id)
                except Exception as e:
                    log.error("blob upload failed (both paths)", extra={"job_id": job_id, "error": str(e)})
                    raise

        result = agent.transcribe(
            input=ai,
            case_id=case_id,
            case_dir=case_dir,
            job_id=job_id,
            language=language,
            mode=mode,
            diarization=diarization,
        )
    except Exception as e:
        log.error("job failed", extra={"job_id": job_id, "error": str(e)})
        payload = {
            "status": "FAILED",
            "job_id": job_id,
            "case_id": case_id,
            "error": str(e)[:1000],
        }
        try:
            if job_obj is None:
                job_obj = Job.objects.get(pk=job_id)
            job_obj.status = Job.Status.FAILED
            job_obj.finished_at = timezone.now()
            job_obj.error_message = payload["error"]
            job_obj.save(update_fields=["status", "finished_at", "error_message"])
        except Exception:
            pass
        try:
            if tr is not None:
                tr.status = "FAILED"
                tr.finished_at = timezone.now()
                tr.save(update_fields=["status", "finished_at"])
        except Exception:
            pass
        try:
            send_job_update(job_id, event="job.failed", **payload)
        except Exception:
            pass
        raise

    # If agent succeeded, persist results; notification errors won't flip status
    payload: Dict[str, Any] = {
            "status": "SUCCEEDED",
            "job_id": job_id,
            "case_id": case_id,
            "transcript_file": str(result.transcript_file),
            "duration_s": result.duration_s,
            "language": result.language,
            "region": result.region,
        }
    try:
        if job_obj is None:
            job_obj = Job.objects.get(pk=job_id)
        job_obj.status = Job.Status.SUCCEEDED
        job_obj.finished_at = timezone.now()
        job_obj.transcript_path = str(result.transcript_file)
        job_obj.duration_s = result.duration_s
        job_obj.save(update_fields=["status", "finished_at", "transcript_path", "duration_s"])
        # Register artifact with checksum
        try:
            import hashlib

            h = hashlib.sha256()
            with open(result.transcript_file, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            CaseArtifact.objects.create(
                case_id=str(case_id),
                case_fk=Job.objects.filter(pk=job_id).values_list('case', flat=True).first(),
                job_id=str(job_id),
                type="TRANSCRIPT",
                title=f"Transcript {job_id}",
                path=str(result.transcript_file),
                checksum=h.hexdigest(),
                schema_version="v1",
                metadata={
                    "language": result.language,
                    "region": result.region,
                    "duration_s": result.duration_s,
                },
            )
        except Exception:
            pass
    except Exception:
        pass
    log.info("job succeeded", extra={"job_id": job_id, "transcript": str(result.transcript_file)})
    try:
        if tr is not None:
            tr.status = "SUCCEEDED"
            tr.finished_at = timezone.now()
            tr.save(update_fields=["status", "finished_at"])
    except Exception:
        pass
    try:
        send_job_update(job_id, event="job.succeeded", **payload)
    except Exception:
        pass
    try:
        send_case_update(case_id, event="artifact.created", kind="transcript", job_id=job_id)
    except Exception:
        pass
    return payload


# ----------------------
# Analysis task helpers
# ----------------------

def _case_paths(case_id: str) -> tuple[Path, Path, Path]:
    base = Path(settings.MEDIA_ROOT) / "cases" / case_id
    return base, base / "transcript", base / "analysis"


def _ops_dir(case_id: str) -> Path:
    return (Path(settings.MEDIA_ROOT) / "cases" / case_id / "ops").resolve()


def _latest_transcript(case_id: str) -> Path | None:
    _, tdir, _ = _case_paths(case_id)
    if not tdir.exists():
        return None
    fx = sorted((p for p in tdir.glob("*__transcript.txt") if p.is_file()), key=lambda p: p.stat().st_mtime, reverse=True)
    return fx[0] if fx else None


def _write_json(p: Path, data: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_jsonl(p: Path, data: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


@shared_task(bind=True)
def summarize_job(self, *, case_id: str, job_id: str) -> Dict[str, Any]:
    case_dir, _, analysis_dir = _case_paths(case_id)
    job = Job.objects.get(pk=job_id)
    src = Path(job.transcript_path) if job.transcript_path else _latest_transcript(case_id)
    if not src or not src.exists():
        raise RuntimeError("No transcript found to summarize")

    out = analysis_dir / f"{job_id}__summary_v1.md"
    text = Path(src).read_text(encoding="utf-8", errors="ignore")
    # Simple offline summary: first 200 lines or 2000 chars
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    head = "\n".join(lines[:200])
    if len(head) > 2000:
        head = head[:2000] + "\n…"
    content = f"# Summary for {job_id}\n\nGenerated from transcript: {src.name}\n\n{head}\n"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")

    # Register artifact
    try:
        import hashlib

        h = hashlib.sha256()
        with open(out, "rb") as f:
            for ch in iter(lambda: f.read(65536), b""):
                h.update(ch)
        CaseArtifact.objects.create(
            case_id=case_id,
            case_fk=job.case,
            job_id=str(job_id),
            type="SUMMARY",
            title=f"Summary {job_id}",
            path=str(out),
            checksum=h.hexdigest(),
            schema_version="v1",
            metadata={"source_transcript": str(src)},
        )
    except Exception:
        pass
    audit_emit(None, case_id=case_id, event="analysis.summary.created", data={"job_id": job_id, "file": str(out)})
    # Ops logs
    try:
        opsd = _ops_dir(case_id)
        meta = {
            "case_id": case_id,
            "job_id": job_id,
            "artifact": str(out),
            "checksum": h.hexdigest() if 'h' in locals() else None,
            "source_transcript": str(src),
            "ts": timezone.now().isoformat(),
            "schema_version": "v1",
            "status": "ok",
        }
        _write_json(opsd / f"{job_id}__summary_log.json", meta)
        _append_jsonl(opsd / "ops_summary.jsonl", meta)
    except Exception:
        pass
    try:
        send_case_update(case_id, event="artifact.created", kind="summary", job_id=job_id)
    except Exception:
        pass
    return {"status": "ok", "summary_file": str(out)}


@shared_task(bind=True)
def timeline_job(self, *, case_id: str, job_id: str) -> Dict[str, Any]:
    _, _, analysis_dir = _case_paths(case_id)
    job = Job.objects.get(pk=job_id)
    src = Path(job.transcript_path) if job.transcript_path else _latest_transcript(case_id)
    if not src or not src.exists():
        raise RuntimeError("No transcript found to build timeline")
    rx = re.compile(r"^\[(\d{2}):(\d{2})\]\s+(?:SPK_(\d+):\s+)?(.*)$")
    events: list[dict[str, Any]] = []
    for ln in src.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = rx.match(ln.strip())
        if not m:
            continue
        mm, ss, spk, text = m.groups()
        ts = int(mm) * 60 + int(ss)
        events.append({
            "ts_start": ts,
            "ts_end": None,
            "speaker": f"SPK_{spk}" if spk else None,
            "text": text.strip(),
            "labels": [],
        })
    out = analysis_dir / f"{job_id}__timeline_v1.json"
    _write_json(out, events)
    try:
        import hashlib

        h = hashlib.sha256()
        with open(out, "rb") as f:
            for ch in iter(lambda: f.read(65536), b""):
                h.update(ch)
        CaseArtifact.objects.create(
            case_id=case_id,
            case_fk=job.case,
            job_id=str(job_id),
            type="TIMELINE",
            title=f"Timeline {job_id}",
            path=str(out),
            checksum=h.hexdigest(),
            schema_version="v1",
            metadata={"source_transcript": str(src), "events": len(events)},
        )
    except Exception:
        pass
    audit_emit(None, case_id=case_id, event="analysis.timeline.created", data={"job_id": job_id, "events": len(events)})
    try:
        opsd = _ops_dir(case_id)
        meta = {
            "case_id": case_id,
            "job_id": job_id,
            "artifact": str(out),
            "checksum": h.hexdigest() if 'h' in locals() else None,
            "source_transcript": str(src),
            "events": len(events),
            "ts": timezone.now().isoformat(),
            "schema_version": "v1",
            "status": "ok",
        }
        _write_json(opsd / f"{job_id}__timeline_log.json", meta)
        _append_jsonl(opsd / "ops_timeline.jsonl", meta)
    except Exception:
        pass
    try:
        send_case_update(case_id, event="artifact.created", kind="timeline", job_id=job_id)
    except Exception:
        pass
    return {"status": "ok", "timeline_file": str(out), "events": len(events)}


@shared_task(bind=True)
def graph_job(self, *, case_id: str, job_id: str) -> Dict[str, Any]:
    _, _, analysis_dir = _case_paths(case_id)
    job = Job.objects.get(pk=job_id)
    src = Path(job.transcript_path) if job.transcript_path else _latest_transcript(case_id)
    if not src or not src.exists():
        raise RuntimeError("No transcript found to extract entities/graph")
    text = src.read_text(encoding="utf-8", errors="ignore")
    # Extremely lightweight: pick capitalized tokens as candidate entities (demo only)
    tokens = re.findall(r"\b([A-Z][a-zA-Z]{2,})\b", text)
    names = sorted(set(tokens))[:50]
    entities = [{
        "id": f"E{i+1}",
        "name": n,
        "type": "OTHER",
        "mentions": [],
    } for i, n in enumerate(names)]
    graph = {"nodes": [{"id": e["id"], "label": e["name"], "type": e["type"]} for e in entities], "edges": []}
    entities_file = analysis_dir / f"{job_id}__entities_v1.json"
    graph_file = analysis_dir / f"{job_id}__graph_v1.json"
    _write_json(entities_file, {"entities": entities})
    _write_json(graph_file, graph)
    try:
        import hashlib

        h1 = hashlib.sha256(entities_file.read_bytes()).hexdigest()
        h2 = hashlib.sha256(graph_file.read_bytes()).hexdigest()
        CaseArtifact.objects.create(
            case_id=case_id,
            case_fk=job.case,
            job_id=str(job_id),
            type="ENTITIES",
            title=f"Entities {job_id}",
            path=str(entities_file),
            checksum=h1,
            schema_version="v1",
            metadata={"source_transcript": str(src), "entities": len(entities)},
        )
        CaseArtifact.objects.create(
            case_id=case_id,
            case_fk=job.case,
            job_id=str(job_id),
            type="GRAPH",
            title=f"Graph {job_id}",
            path=str(graph_file),
            checksum=h2,
            schema_version="v1",
            metadata={"source_transcript": str(src), "nodes": len(graph["nodes"]), "edges": 0},
        )
    except Exception:
        pass
    audit_emit(None, case_id=case_id, event="analysis.graph.created", data={"job_id": job_id, "entities": len(entities)})
    try:
        opsd = _ops_dir(case_id)
        meta = {
            "case_id": case_id,
            "job_id": job_id,
            "entities_file": str(entities_file),
            "graph_file": str(graph_file),
            "entities_checksum": h1 if 'h1' in locals() else None,
            "graph_checksum": h2 if 'h2' in locals() else None,
            "source_transcript": str(src),
            "entities": len(entities),
            "edges": 0,
            "ts": timezone.now().isoformat(),
            "schema_version": "v1",
            "status": "ok",
        }
        _write_json(opsd / f"{job_id}__graph_log.json", meta)
        _append_jsonl(opsd / "ops_graph.jsonl", meta)
    except Exception:
        pass
    try:
        send_case_update(case_id, event="artifact.created", kind="graph", job_id=job_id)
    except Exception:
        pass
    return {"status": "ok", "entities_file": str(entities_file), "graph_file": str(graph_file), "entities": len(entities), "edges": 0}
