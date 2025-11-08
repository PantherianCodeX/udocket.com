from __future__ import annotations

import re
import shutil
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse, QueryDict
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.platform.accounts.models import Organization
from apps.platform.accounts.utils import resolve_request_organization
from apps.platform.cases.models import Case
from apps.platform.jobs.models import Job
from apps.platform.operations.channels import send_job_update
from apps.platform.operations.storage import ensure_case_dirs
from apps.platform.operations.utils import append_job_log, update_job_meta
from packages.common.json_utils import parse_json_value

from ..auth import ensure_authenticated
from ..contexts import user_can_review_case
from ..selectors import job_telemetry_payload
from ..transcripts import ensure_transcript_artifact

FIXTURE_ROOT = (
    Path(settings.BASE_DIR)
    / "tests"
    / "udocket_core"
    / "fixtures"
    / "transcripts"
    / "CASE-DEMO"
    / "transcript"
)
DEFAULT_LANGUAGE = "en-CA"
MAX_UPLOAD_BYTES = 512 * 1024  # 512 KiB for dev fixtures


@dataclass(slots=True)
class UploadResult:
    job: Job
    label: str


@require_http_methods(["GET", "POST"])
def summary_upload_transcript_text(
    request: HttpRequest, case_id: str
) -> HttpResponse | JsonResponse:
    """Render modal or handle transcript text injection for analyzer testing."""

    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    try:
        active_org = resolve_request_organization(request, required=True)
    except PermissionDenied:
        return redirect("ui-index")

    case = _get_case_for_request(request, case_id, active_org)
    if request.method == "GET":
        fixtures = _collect_fixture_transcripts()
        context = {
            "case": case,
            "fixtures": fixtures,
            "fixture_root": str(FIXTURE_ROOT),
        }
        return render(
            request,
            "platform_ui/components/modals/summary_text_upload_modal.html",
            context,
        )

    try:
        result = _handle_text_upload(request, case)
    except ValueError as exc:
        return JsonResponse({"status": "error", "detail": str(exc)}, status=400)
    except PermissionError as exc:
        return JsonResponse({"status": "error", "detail": str(exc)}, status=403)

    return JsonResponse(
        {
            "status": "ok",
            "job_id": str(result.job.id),
            "label": result.label,
        }
    )


def _get_case_for_request(request: HttpRequest, case_id: str, organization: Organization) -> Case:
    cases_qs = Case.objects.select_related("organization")
    case = cases_qs.for_user(getattr(request, "user", None)).filter(pk=case_id).first()
    if not isinstance(case, Case):
        raise Http404
    if getattr(case, "organization_id", None) != getattr(organization, "id", None):
        raise Http404
    return case


def _collect_fixture_transcripts() -> Iterable[dict[str, Any]]:
    if not FIXTURE_ROOT.exists():
        return []
    fixtures: list[dict[str, Any]] = []
    for path in sorted(FIXTURE_ROOT.glob("*.txt")):
        try:
            size = path.stat().st_size
        except OSError:
            size = None
        fixtures.append(
            {
                "name": path.name,
                "display": _derive_label(path.name),
                "bytes": size,
            }
        )
    return fixtures


def _handle_text_upload(request: HttpRequest, case: Case) -> UploadResult:
    payload: dict[str, Any] = {}
    if request.content_type and "application/json" in request.content_type:
        if request.body:
            parsed = parse_json_value(request.body.decode("utf-8"))
            if not isinstance(parsed, dict):
                raise ValueError("Invalid JSON payload")
            payload = {str(key): value for key, value in parsed.items()}
    elif isinstance(request.POST, QueryDict):
        payload = request.POST.dict()

    fixture_name = _extract_fixture_name(payload)
    upload_file = request.FILES.get("transcript_text")

    if fixture_name and upload_file:
        raise ValueError("Provide either a fixture to import or upload a file, not both.")
    if not fixture_name and not upload_file:
        raise ValueError("Select a fixture transcript or upload a .txt file.")

    user = getattr(request, "user", None)
    if user and not user_can_review_case(user, case):
        # Eventually restrict to superadmins; for now require review capability for safety.
        raise PermissionError("Insufficient permissions to inject transcripts.")

    if fixture_name:
        source_path = _resolve_fixture_path(fixture_name)
        return _register_transcript_file(
            case, source_path, source_label=_derive_label(source_path.name)
        )

    assert upload_file is not None  # guarded above
    if upload_file.size and upload_file.size > MAX_UPLOAD_BYTES:
        raise ValueError("Upload too large for dev helper (max 512 KiB).")
    original_name = upload_file.name or "transcript.txt"
    if not original_name.lower().endswith(".txt"):
        raise ValueError("Only .txt transcript files are supported.")

    case_dir = ensure_case_dirs(str(case.id), case.organization_id)
    transcript_dir = case_dir / "transcript"
    transcript_dir.mkdir(parents=True, exist_ok=True)
    job_id = uuid.uuid4()
    label_hint = _derive_label(original_name)
    safe_name = _sanitize_filename(original_name)
    destination = transcript_dir / f"{job_id}__{safe_name}"

    with destination.open("wb") as dest_handle:
        for chunk in upload_file.chunks():
            dest_handle.write(chunk)

    return _finalize_job_record(
        case=case,
        job_id=job_id,
        transcript_path=destination,
        original_name=safe_name,
        preferred_label=label_hint,
    )


def _resolve_fixture_path(fixture_name: str) -> Path:
    candidate = (FIXTURE_ROOT / fixture_name).resolve()
    try:
        candidate.relative_to(FIXTURE_ROOT.resolve())
    except ValueError as exc:  # pragma: no cover - path traversal guard
        raise ValueError("Invalid fixture selection.") from exc
    if not candidate.exists() or not candidate.is_file():
        raise ValueError("Fixture transcript not found.")
    if not candidate.name.lower().endswith(".txt"):
        raise ValueError("Fixture is not a .txt file.")

    return candidate


def _register_transcript_file(case: Case, source_path: Path, *, source_label: str) -> UploadResult:
    job_id = uuid.uuid4()
    case_dir = ensure_case_dirs(str(case.id), case.organization_id)
    transcript_dir = case_dir / "transcript"
    transcript_dir.mkdir(parents=True, exist_ok=True)

    safe_name = _sanitize_filename(source_path.name)
    destination = transcript_dir / f"{job_id}__{safe_name}"
    try:
        shutil.copy2(source_path, destination)
    except Exception as exc:  # pragma: no cover - filesystem failure
        raise ValueError(f"Unable to copy fixture transcript: {exc}") from exc

    return _finalize_job_record(
        case=case,
        job_id=job_id,
        transcript_path=destination,
        original_name=safe_name,
        preferred_label=source_label,
    )


def _finalize_job_record(
    *,
    case: Case,
    job_id: uuid.UUID,
    transcript_path: Path,
    original_name: str,
    preferred_label: str | None = None,
) -> UploadResult:
    label = preferred_label or _derive_label(original_name)
    if not label:
        label = "Transcript"

    now = timezone.now()
    job = Job.objects.create(
        id=job_id,
        case=case,
        organization=case.organization,
        audio_input=f"text://{original_name}",
        mode=Job.Mode.BATCH,
        diarization=False,
        language=DEFAULT_LANGUAGE,
        status=Job.Status.SUCCEEDED,
        transcript_path=str(transcript_path),
        finished_at=now,
        started_at=now,
        upload_progress=1.0,
        review_status=Job.ReviewStatus.APPROVED,
    )

    transcript_bytes = None
    transcript_sha = None
    try:
        transcript_bytes = transcript_path.stat().st_size
        transcript_sha = _sha256_file(transcript_path)
    except OSError:
        pass

    update_job_meta(
        str(case.id),
        case.organization_id,
        str(job.id),
        {
            "status": "succeeded",
            "job_kind": "audio:transcript-text",
            "agent_type": "transcription.text-upload",
            "agent": "text-upload",
            "transcript_path": str(transcript_path),
            "transcript_title": label,
            "job_title": label,
            "language": job.language,
            "timestamp_utc": now.isoformat(),
            "transcript_sha256": transcript_sha,
            "transcript_bytes": transcript_bytes,
            "source": "ui.summary_text_upload",
        },
    )

    append_job_log(
        str(case.id),
        case.organization_id,
        str(job.id),
        f"Transcript text registered via summary UI helper ({label})",
    )

    telemetry_dict = job_telemetry_payload(job, None, ui_mode=True)
    ensure_transcript_artifact(
        case_id=str(case.id),
        case=case,
        job=job,
        telemetry=telemetry_dict,
        organization_id=getattr(case, "organization_id", None),
        metadata_source="ui.summary_text_upload",
    )

    send_job_update(
        str(job.id),
        event="job.succeeded",
        status=Job.Status.SUCCEEDED,
        case_id=str(case.id),
        review_status=Job.ReviewStatus.APPROVED,
        transcript_path=str(transcript_path),
        transcript_file=str(transcript_path),
        transcript_title=label,
    )

    return UploadResult(job=job, label=label)


def _sanitize_filename(name: str) -> str:
    base = Path(name).name
    if not base.lower().endswith(".txt"):
        base = f"{base}.txt"
    stem, suffix = Path(base).stem, Path(base).suffix
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-._") or "transcript"
    return f"{safe_stem}{suffix.lower()}"


def _derive_label(filename: str) -> str:
    stem = Path(filename).stem
    lowered = stem.lower()
    if lowered.endswith("__transcript"):
        stem = stem[: -len("__transcript")]
    return stem or "Transcript"


def _extract_fixture_name(payload: dict[str, Any]) -> str | None:
    raw = payload.get("fixture_name")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def _sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
