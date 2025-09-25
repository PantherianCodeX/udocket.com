from __future__ import annotations

import json
import logging
import uuid
from uuid import UUID
from typing import Any, Dict, Iterable, List, Optional, Protocol, cast

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.platform.accounts.models import Organization
from apps.platform.accounts.utils import resolve_request_organization
from apps.platform.artifacts.models import CaseArtifact
from apps.platform.cases.models import Case
from apps.platform.jobs.models import Job
from apps.platform.jobs.utils import unique_title
from apps.platform.operations.storage import ensure_case_dirs, ops_dir as storage_ops_dir
from apps.platform.operations.tasks import transcribe_job
from apps.platform.operations.utils import append_job_log, update_job_meta

from .auth import ensure_authenticated
from .common import JobRow, JobTelemetryPayload
from .contexts import compute_case_tool_state, get_case_and_org, job_detail_context, user_can_review_case
from .constants import CASE_JOB_TABLE_COLUMNS
from .presenters.job_actions import build_job_action_entries
from .presenters.jobs import build_job_rows, friendly_job_title
from .selectors import job_telemetry_payload
from .transcripts import ensure_transcript_artifact, unique_transcript_title, default_transcript_title

log = logging.getLogger("apps.platform.ui")


class _TaskWithDelay(Protocol):
    def delay(self, *args: Any, **kwargs: Any) -> Any:
        ...


class CaseArtifactLike(Protocol):
    id: UUID
    title: str
    metadata: Any

    def save(self, *args: Any, **kwargs: Any) -> None:
        ...


def _resolve_job(case_id: str, job_id: UUID, request: HttpRequest) -> Job:
    case, _ = get_case_and_org(request, case_id)
    job = (
        Job.objects.select_related("case", "case__organization", "reviewed_by")
        .filter(case=case, pk=job_id)
        .first()
    )
    if not job:
        raise Http404
    return job


def _resolve_case(case_id: str, request: HttpRequest) -> Case:
    case, _ = get_case_and_org(request, case_id)
    return case


transcribe_job_task: _TaskWithDelay = cast(_TaskWithDelay, transcribe_job)


def _fallback_job_row(job: Job, telemetry: JobTelemetryPayload) -> JobRow:
    return {
        "job": job,
        "telemetry": telemetry,
        "title": friendly_job_title(job, telemetry),
        "children": [],
        "actions": [],
    }


@require_http_methods(["GET"])
def case_job_title_form(request: HttpRequest, case_id: str, job_id: UUID) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    job = _resolve_job(case_id, job_id, request)
    case = job.case

    edit_flag = str(request.GET.get("edit") or request.GET.get("title_edit") or "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    context = job_detail_context(request, job, title_edit=edit_flag)
    context["case"] = case
    return render(request, "platform_ui/partials/job_detail_title_form.html", context)


@require_http_methods(["POST"])
def case_job_update_title(request: HttpRequest, case_id: str, job_id: UUID) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    job = _resolve_job(case_id, job_id, request)
    case = job.case

    user = getattr(request, "user", None)
    dev_open = getattr(settings, "PLATFORM_DEV_OPEN", False)
    can_edit = False
    if dev_open:
        can_edit = True
    elif user and getattr(user, "is_authenticated", False):
        if case.reviewer_id and str(user.id) == str(case.reviewer_id):
            can_edit = True
        elif user_can_review_case(user, case):
            can_edit = True
    if not can_edit:
        return HttpResponse("Forbidden", status=403)

    new_title = (request.POST.get("title") or "").strip()
    title_error: Optional[str] = None
    if not new_title:
        title_error = "Title cannot be empty."

    telemetry_dict = job_telemetry_payload(job, request, ui_mode=True)

    artifact: Optional[CaseArtifact] = (
        CaseArtifact.objects.filter(case_id=str(case.id), job_id=str(job.id), type="TRANSCRIPT")
        .order_by("-created_at")
        .first()
    )

    if not title_error:
        conflict_qs = CaseArtifact.objects.filter(case_id=str(case.id), type="TRANSCRIPT", title=new_title)
        if artifact:
            conflict_qs = conflict_qs.exclude(pk=artifact.pk)
        if conflict_qs.exists():
            title_error = "A transcript with that title already exists in this case."

    if not title_error:
        if artifact is None:
            artifact = ensure_transcript_artifact(
                case_id=str(case.id),
                case=case,
                job=job,
                telemetry=telemetry_dict,
                title=new_title,
                organization_id=getattr(case, "organization_id", None),
                metadata_source="ui.job_title",
            )
        if artifact is None:
            title_error = "Transcript not found for this job."

    if title_error:
        context = job_detail_context(
            request,
            job,
            telemetry=telemetry_dict,
            title_error=title_error,
            title_edit=True,
        )
        context["case"] = case
        context["job_title"] = new_title or context.get("job_title")
        return render(request, "platform_ui/partials/job_detail_title_form.html", context, status=400)

    assert artifact is not None  # Narrowing for type checkers
    artifact_obj: CaseArtifactLike = cast(CaseArtifactLike, artifact)

    artifact_obj.title = new_title
    raw_metadata = getattr(artifact_obj, "metadata", None)
    metadata: Dict[str, Any]
    if isinstance(raw_metadata, dict):
        metadata = dict(cast(Dict[str, Any], raw_metadata))
    else:
        metadata = {}
    metadata.update({
        "transcript_title": new_title,
        "job_title": new_title,
        "title_updated_at": timezone.now().isoformat(),
    })
    if user and getattr(user, "is_authenticated", False):
        metadata["title_updated_by"] = str(getattr(user, "id", ""))
    artifact_obj.metadata = metadata
    artifact_obj.save(update_fields=["title", "metadata"])

    update_job_meta(
        str(case.id),
        case.organization_id,
        str(job.id),
        {"job_title": new_title, "transcript_title": new_title},
    )

    append_job_log(
        str(job.case_id),
        str(job.organization_id) if job.organization_id is not None else None,
        str(job.id),
        f"Transcript title set to '{new_title}'",
    )

    context = job_detail_context(request, job)
    context["case"] = case
    trigger = json.dumps({"job-title-updated": {"job_id": str(job.id), "title": new_title}})
    response = render(request, "platform_ui/partials/job_detail_title_form.html", context)
    response["HX-Trigger"] = trigger
    return response


@require_http_methods(["POST"])
def case_job_create_artifact(request: HttpRequest, case_id: str, job_id: UUID) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    job = _resolve_job(case_id, job_id, request)
    case = job.case

    user = getattr(request, "user", None)
    dev_open = getattr(settings, "PLATFORM_DEV_OPEN", False)
    can_manage = False
    if dev_open:
        can_manage = True
    elif user and getattr(user, "is_authenticated", False):
        if case.reviewer_id and str(user.id) == str(case.reviewer_id):
            can_manage = True
        elif user_can_review_case(user, case):
            can_manage = True
    if not can_manage:
        return JsonResponse({"status": "error", "detail": "Forbidden"}, status=403)

    telemetry_dict = job_telemetry_payload(job, request, ui_mode=True)

    existing: Optional[CaseArtifact] = (
        CaseArtifact.objects.filter(case_id=str(case.id), job_id=str(job.id), type="TRANSCRIPT")
        .order_by("-created_at")
        .first()
    )

    artifact = existing or ensure_transcript_artifact(
        case_id=str(case.id),
        case=case,
        job=job,
        telemetry=telemetry_dict,
        organization_id=getattr(case, "organization_id", None),
        metadata_source="ui.transcript_promote",
    )

    if artifact is None:
        return JsonResponse({"status": "error", "detail": "Transcript not found for this job."}, status=404)

    artifact_obj: CaseArtifactLike = cast(CaseArtifactLike, artifact)

    title_input = (request.POST.get("title") or "").strip()
    metadata_changed = False
    title_changed = False
    if title_input:
        desired_title = unique_transcript_title(str(case.id), title_input, getattr(case, "organization_id", None))
        if artifact_obj.title != desired_title:
            artifact_obj.title = desired_title
            title_changed = True
    elif not artifact_obj.title:
        default_title = default_transcript_title(job, telemetry_dict)
        unique_transcript_title_val = unique_transcript_title(
            str(case.id), default_title, getattr(case, "organization_id", None)
        )
        if artifact_obj.title != unique_transcript_title_val:
            artifact_obj.title = unique_transcript_title_val
            title_changed = True

    raw_metadata = getattr(artifact_obj, "metadata", None)
    metadata: Dict[str, Any]
    if isinstance(raw_metadata, dict):
        metadata = dict(cast(Dict[str, Any], raw_metadata))
    else:
        metadata = {}
    if metadata.get("created_via") is None:
        metadata["created_via"] = "ui.transcript_promote"
        metadata_changed = True
    metadata["last_promoted_at"] = timezone.now().isoformat()
    metadata_changed = True
    if user and getattr(user, "is_authenticated", False):
        metadata["last_promoted_by"] = str(getattr(user, "id", ""))
    if title_changed:
        metadata["job_title"] = artifact_obj.title
        metadata["transcript_title"] = artifact_obj.title
    artifact_obj.metadata = metadata

    update_fields: List[str] = []
    if title_changed:
        update_fields.append("title")
    if metadata_changed or title_changed:
        update_fields.append("metadata")
    if update_fields:
        artifact_obj.save(update_fields=update_fields)

    was_created = existing is None
    log_message = "Transcript promoted to case artifact"
    if title_changed and not was_created:
        log_message = f"Transcript artifact updated: {artifact_obj.title}"
    org_id = str(job.organization_id) if job.organization_id is not None else None
    append_job_log(str(job.case_id), org_id, str(job.id), log_message)
    update_job_meta(
        str(case.id),
        case.organization_id,
        str(job.id),
        {"transcript_artifact_id": str(artifact_obj.id)},
    )

    return JsonResponse(
        {
            "status": "ok",
            "artifact_id": artifact_obj.id,
            "title": artifact_obj.title,
            "created": was_created,
        }
    )


@require_http_methods(["GET"])
def case_job_row(request: HttpRequest, case_id: str, job_id: UUID) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    case = _resolve_case(case_id, request)
    try:
        job = (
            Job.objects.select_related("case", "case__organization").filter(case=case, pk=job_id).first()
        )
    except Job.DoesNotExist:
        job = None
    if not job:
        raise Http404

    telemetry_dict: JobTelemetryPayload = job_telemetry_payload(job, request, ui_mode=True)
    telemetry_map: Dict[str, JobTelemetryPayload] = {str(job.id): telemetry_dict}
    _, flat_rows = build_job_rows([job], telemetry_map)
    if not flat_rows:
        fallback_row = _fallback_job_row(job, telemetry_dict)
        fallback_row["actions"] = build_job_action_entries(
            job,
            telemetry_dict,
            can_review=user_can_review_case(getattr(request, "user", None), job.case),
            is_child=False,
        )
        return render(
            request,
            "platform_ui/partials/job_row.html",
            {
                "row": fallback_row,
                "table_columns": CASE_JOB_TABLE_COLUMNS,
            },
        )

    row = flat_rows[0]
    row["actions"] = build_job_action_entries(
        job,
        telemetry_dict,
        can_review=user_can_review_case(getattr(request, "user", None), job.case),
        is_child=False,
    )
    return render(
        request,
        "platform_ui/partials/job_row.html",
        {
            "row": cast(Any, row),
            "table_columns": CASE_JOB_TABLE_COLUMNS,
        },
    )


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
                try:
                    payload = json.loads(meta_path.read_text(encoding="utf-8"))
                except Exception:
                    continue
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
    transcribe_job_task.delay(
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
        state = compute_case_tool_state(request, case)
        panel = state["tool_panels"].get("transcribe")
        if panel:
            response = render(request, "platform_ui/tools/_panel.html", {"panel": panel})
            trigger_payload = {
                "job-enqueued": {
                    "job_id": str(job.id),
                    "status": job.status,
                    "force_wav": force_wav_conversion,
                },
                "case-view-refreshed": {
                    "tools": ["transcribe"],
                    "active_tool": "transcribe",
                    "header_html": render_to_string(
                        "platform_ui/tools/_case_header.html",
                        {"case": case, "case_header": state["case_header"]},
                    ),
                    "cards_html": render_to_string(
                        "platform_ui/tools/_developer_cards.html",
                        {
                            "case": case,
                            "cards": state["developer_cards"],
                            "active_tool": "transcribe",
                        },
                    ),
                },
            }
            response["HX-Trigger"] = json.dumps(trigger_payload)
            return response

    telemetry_map: Dict[str, JobTelemetryPayload] = {str(job.id): telemetry_dict}
    _, flat_rows = build_job_rows([job], telemetry_map)
    if flat_rows:
        row = cast(JobRow, flat_rows[0])  # pyright: ignore[reportUnnecessaryCast]
    else:
        row = _fallback_job_row(job, telemetry_dict)

    row["actions"] = build_job_action_entries(
        job,
        telemetry_dict,
        can_review=user_can_review_case(getattr(request, "user", None), job.case),
        is_child=False,
    )
    return render(
        request,
        "platform_ui/partials/job_row.html",
        {
            "row": row,
            "table_columns": CASE_JOB_TABLE_COLUMNS,
        },
    )
