from __future__ import annotations

# pyright: strict
from django.db.utils import IntegrityError

from apps.platform.artifacts.models import CaseArtifact
from apps.platform.cases.models import Case
from apps.platform.jobs.models import Job
from apps.platform.operations.storage import ops_dir as storage_ops_dir
from packages.udocket_common.json_utils import read_json_object
from packages.udocket_common.text import unique_title

from .common import JobTelemetryPayload, as_dict
from .presenters.jobs import friendly_job_title  # lazy usage inside helpers


def candidate_transcript_paths(job: Job, telemetry: JobTelemetryPayload | None) -> list[str]:
    paths: list[str] = []
    if isinstance(job.transcript_path, str) and job.transcript_path:
        paths.append(job.transcript_path)
    transcript_payload = as_dict((telemetry or {}).get("transcript"))
    path_from_telem = transcript_payload.get("path")
    if isinstance(path_from_telem, str) and path_from_telem and path_from_telem not in paths:
        paths.append(path_from_telem)
    return paths


def default_transcript_title(job: Job, telemetry: JobTelemetryPayload | None) -> str:
    transcript_payload = as_dict((telemetry or {}).get("transcript"))
    title_value = transcript_payload.get("title")
    if isinstance(title_value, str) and title_value.strip():
        return title_value.strip()
    meta = as_dict((telemetry or {}).get("metadata"))
    job_title = meta.get("job_title")
    if isinstance(job_title, str) and job_title.strip():
        return job_title.strip()
    return friendly_job_title(job, telemetry)


def unique_transcript_title(
    case_id: str, base_title: str, organization_id: str | None = None
) -> str:
    base = (base_title or "").strip() or "Transcript"
    base = base[:180]
    titles: set[str] = set(
        CaseArtifact.objects.filter(case_id=case_id, type="TRANSCRIPT").values_list(
            "title", flat=True
        )
    )
    try:
        ops_dir = storage_ops_dir(case_id, organization_id)
        if ops_dir.exists():
            for meta_path in ops_dir.glob("*_transcription_log.json"):
                payload = read_json_object(meta_path)
                title_value = payload.get("job_title") or payload.get("transcript_title")
                if isinstance(title_value, str) and title_value.strip():
                    titles.add(title_value.strip())
    except Exception:
        pass

    candidate = unique_title(base, titles)
    if len(candidate) <= 200:
        return candidate

    if "-" in candidate:
        _stem, suffix = candidate.rsplit("-", 1)
        trimmed = base[: max(0, 200 - len(suffix) - 1)] or base[:200]
        return f"{trimmed}-{suffix}"[:200]

    return candidate[:200]


def ensure_transcript_artifact(
    *,
    case_id: str,
    case: Case,
    job: Job,
    telemetry: JobTelemetryPayload | None = None,
    title: str | None = None,
    organization_id: str | None = None,
    metadata_source: str = "ui.transcript_promote",
) -> CaseArtifact | None:
    artifact = (
        CaseArtifact.objects.filter(case_id=str(case_id), job_id=str(job.id), type="TRANSCRIPT")
        .order_by("-created_at")
        .first()
    )
    if artifact:
        return artifact

    candidate_paths = candidate_transcript_paths(job, telemetry)
    if not candidate_paths:
        return None

    for path in candidate_paths:
        existing = (
            CaseArtifact.objects.filter(case_id=str(case_id), type="TRANSCRIPT", path=path)
            .order_by("-created_at")
            .first()
        )
        if existing:
            return existing

    base_title = title or default_transcript_title(job, telemetry)
    attempts = 0
    while attempts < 3:
        attempts += 1
        candidate_title = unique_transcript_title(str(case_id), base_title, organization_id)
        metadata = {"created_via": metadata_source}
        for path in candidate_paths:
            try:
                artifact = CaseArtifact.objects.create(
                    case_id=str(case_id),
                    case_fk=case,
                    job_id=str(job.id),
                    type="TRANSCRIPT",
                    title=candidate_title,
                    path=path,
                    metadata=metadata,
                )
                return artifact
            except IntegrityError:
                break
            except Exception:
                continue
    return None
