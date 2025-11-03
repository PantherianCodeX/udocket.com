from __future__ import annotations

 
import uuid
from typing import Iterable, Optional, cast

from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.platform.accounts.models import Organization
from apps.platform.accounts.utils import resolve_request_organization
from apps.platform.artifacts.models import CaseArtifact
from apps.platform.cases.models import Case
from apps.platform.jobs.models import Job
from apps.platform.jobs.utils import unique_title
from apps.platform.operations.storage import ensure_case_dirs, ops_dir as storage_ops_dir
from apps.platform.operations.utils import update_job_meta
from packages.udocket_common.json_utils import read_json_object

from ..auth import ensure_authenticated
from ..common import JobRow
from ..contexts import compute_case_tool_state, user_can_review_case
from ..cases.helpers import render_case_panel_with_refresh
from ..constants import CASE_JOB_TABLE_COLUMNS
from ..presenters.job_actions import build_job_action_entries
from ..presenters.jobs import build_job_rows
from ..selectors import job_telemetry_payload
from .utils import fallback_job_row, get_transcribe_job_task, log


@require_http_methods(["POST"])
def create_job(request: HttpRequest, case_id: str) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    try:
        active_org = cast(Organization, resolve_request_organization(request, required=True))
    except PermissionDenied:
        return redirect("ui-index")

    cases_qs = Case.objects.select_related("organization")
    case = cases_qs.for_user(getattr(request, "user", None)).filter(pk=case_id).first()
    if not isinstance(case, Case):
        raise Http404
    if getattr(case, "organization_id", None) != getattr(active_org, "id", None):
        raise Http404

    mode = request.POST.get("mode") or Job.Mode.ON_DEMAND
    diarization = bool(request.POST.get("diarization"))
    language = request.POST.get("language") or "en-CA"
    upload = request.FILES.get("audio")
    sas_url = (request.POST.get("audio_url") or "").strip()

    if diarization and mode != Job.Mode.BATCH:
        mode = Job.Mode.BATCH

    job_id = uuid.uuid4()
    case_dir = ensure_case_dirs(case_id, case.organization_id)
    audio_dir = case_dir / "audio"

    force_wav_conversion = str(request.POST.get("force_wav") or "").lower() in {"1", "true", "yes", "on"}

    if upload:
        dest = audio_dir / f"{job_id}__{upload.name}"
        with dest.open("wb") as handle:
            chunks_iter = cast(Iterable[bytes], upload.chunks())
            for chunk_bytes in chunks_iter:
                handle.write(chunk_bytes)
        audio_input = str(dest)
    elif sas_url:
        audio_input = sas_url
        if mode != Job.Mode.BATCH:
            mode = Job.Mode.BATCH
    else:
        return HttpResponse("Upload a file or provide a SAS URL.", status=400)

    case_org = cast(Optional[Organization], getattr(case, "organization", None))

    job = Job.objects.create(
        id=job_id,
        case=case,
        organization=case_org,
        audio_input=audio_input,
        mode=mode,
        diarization=diarization,
        language=language,
    )

    existing_titles: set[str] = set(
        CaseArtifact.objects.filter(case_id=str(case.id), type="TRANSCRIPT").values_list("title", flat=True)
    )
    ops_dir = storage_ops_dir(str(case.id), case.organization_id)
    try:
        if ops_dir.exists():
            for meta_path in ops_dir.glob("*_transcription_log.json"):
                payload = read_json_object(meta_path)
                title_value = payload.get("job_title") or payload.get("transcript_title")
                if isinstance(title_value, str) and title_value.strip():
                    existing_titles.add(title_value.strip())
    except Exception:
        pass

    job_title = unique_title("Transcript", existing_titles)
    try:
        update_job_meta(str(case.id), case.organization_id, str(job.id), {"job_title": job_title})
    except Exception:
        pass

    log.info(
        "ui enqueue job",
        extra={
            "job_id": str(job.id),
            "case_id": case_id,
            "mode": mode,
            "force_wav_conversion": force_wav_conversion,
        },
    )
    get_transcribe_job_task().delay(
        case_id=str(case.id),
        job_id=str(job.id),
        audio_input=audio_input,
        mode=mode,
        diarization=diarization,
        language=language,
        force_wav_conversion=force_wav_conversion,
    )

    telemetry_dict = job_telemetry_payload(job, request, ui_mode=True)

    if request.headers.get("HX-Request"):
        state = compute_case_tool_state(request, case, active_tool="transcribe")
        panel = state["tool_panels"].get("transcribe")
        if panel:
            return render_case_panel_with_refresh(
                request,
                panel,
                case=case,
                state=state,
                active_tool="transcribe",
                tools=["transcribe"],
                extra_triggers={
                    "job-enqueued": {
                        "job_id": str(job.id),
                        "status": job.status,
                        "force_wav": force_wav_conversion,
                    }
                },
            )

    telemetry_map = {str(job.id): telemetry_dict}
    note_counts = {str(job.id): 0}
    _, flat_rows = build_job_rows([job], telemetry_map, note_counts=note_counts)
    row: JobRow
    if flat_rows:
        row = flat_rows[0]
    else:
        row = fallback_job_row(job, telemetry_dict)

    row["actions"] = build_job_action_entries(
        job,
        telemetry_dict,
        can_review=user_can_review_case(getattr(request, "user", None), job.case),
        is_child=False,
    )
    return render(
        request,
        "platform_ui/components/jobs/job_row.html",
        {
            "row": row,
            "table_columns": CASE_JOB_TABLE_COLUMNS,
        },
    )
