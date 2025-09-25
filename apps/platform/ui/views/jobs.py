from __future__ import annotations

# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportOptionalMemberAccess=false

import json
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, cast

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.platform.accounts.utils import resolve_request_organization
from apps.platform.artifacts.models import CaseArtifact
from apps.platform.authorization.capabilities import has_capability
from apps.platform.cases.models import Case
from apps.platform.jobs.models import Job
from apps.platform.jobs.utils import unique_title
from apps.platform.operations.storage import ensure_case_dirs, ops_dir as storage_ops_dir
from apps.platform.operations.tasks import transcribe_job
from apps.platform.operations.utils import append_job_log, job_log_path, update_job_meta
from apps.platform.tenancy import scope_jobs

from .auth import ensure_authenticated
from .common import JobTelemetryPayload
from .contexts import (
    compute_case_tool_state,
    get_case_and_org,
    job_detail_context,
    user_can_review_case,
)
from .constants import CASE_JOB_TABLE_COLUMNS, DEFAULT_TABLE_FILTERS, GLOBAL_JOB_TABLE_COLUMNS
from .presenters.cases import table_config
from .presenters.job_actions import build_job_action_entries
from .presenters.jobs import build_job_rows, friendly_job_title
from .selectors import job_telemetry_map, job_telemetry_payload
from .transcripts import ensure_transcript_artifact, unique_transcript_title, default_transcript_title


log = logging.getLogger("apps.platform.ui")


class _TaskWithDelay(Protocol):
    def delay(self, *args: Any, **kwargs: Any) -> Any:
        ...


transcribe_job_task: _TaskWithDelay = cast(_TaskWithDelay, transcribe_job)


@require_http_methods(["GET"])
def case_job_transcript(request: HttpRequest, case_id: str, job_id: uuid.UUID) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    case, _ = get_case_and_org(request, case_id)
    job = (
        Job.objects.select_related("case", "case__organization", "reviewed_by")
        .filter(case=case, pk=job_id)
        .first()
    )
    if not job:
        raise Http404

    transcript_path = job.transcript_path
    transcript_text = ""
    if transcript_path and Path(transcript_path).exists():
        try:
            with Path(transcript_path).open("r", encoding="utf-8", errors="replace") as handle:
                transcript_text = handle.read(20000)
                if handle.read(1):
                    transcript_text += "\n…"
        except Exception:
            transcript_text = ""

    telemetry = job_telemetry_payload(job, request, ui_mode=True)
    download_url = None
    artifacts = telemetry.get("artifacts") or []
    for art in artifacts:
        if (art.get("type") or "").upper() == "TRANSCRIPT" and art.get("download_url"):
            download_url = art.get("download_url")
            break

    friendly_title = friendly_job_title(job, telemetry, None)
    modal_created = job.finished_at or job.started_at or job.created_at
    context = {
        "title": friendly_title,
        "job_id": job.id,
        "created_at": modal_created,
        "modal_heading": "Transcript Preview",
        "modal_title_text": friendly_title,
        "modal_text": transcript_text,
        "modal_text_id": f"modal-text-{job.id}",
        "modal_download_url": download_url,
        "modal_download_label": "Download transcript",
        "modal_copy_label": "Copy transcript",
        "modal_close_label": "Close",
        "modal_empty_text": "Transcript not available for this job.",
    }
    return render(request, "platform_ui/partials/transcript_modal.html", context)



@require_http_methods(["GET"])
def case_job_logs_modal(request: HttpRequest, case_id: str, job_id: uuid.UUID) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    case, _ = get_case_and_org(request, case_id)
    job = (
        Job.objects.select_related("case", "case__organization")
        .filter(case=case, pk=job_id)
        .first()
    )
    if not job:
        raise Http404

    log_path = job_log_path(str(case.id), getattr(job, "organization_id", None), str(job.id))
    if not log_path.exists():
        log_text = "No log entries recorded for this job yet."
    else:
        try:
            text = log_path.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001
            text = "Unable to read log contents."
        if len(text) > 50000:
            text = text[-50000:]
            text = "…" + text
        log_text = text

    telemetry = job_telemetry_payload(job, request, ui_mode=True)
    friendly_title = friendly_job_title(job, telemetry, None)
    modal_created = job.finished_at or job.started_at or job.created_at
    meta_items = []
    if log_path.exists():
        meta_items.append({"label": "Log path", "copy_text": str(log_path), "display": str(log_path)})
    context = {
        "title": friendly_title,
        "job_id": str(job.id),
        "created_at": modal_created,
        "modal_heading": "Job Logs",
        "modal_title_text": friendly_title,
        "modal_text": log_text,
        "modal_text_id": f"modal-log-{job.id}",
        "modal_download_url": f"/api/v1/jobs/{job.id}/logs/",
        "modal_download_label": "Download log",
        "modal_copy_label": "Copy log",
        "modal_close_label": "Close",
        "modal_empty_text": "No log entries recorded for this job.",
        "modal_meta_items": meta_items,
    }
    return render(request, "platform_ui/partials/log_modal.html", context)



def jobs(request: HttpRequest) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    try:
        organization = resolve_request_organization(request, required=True)
    except PermissionDenied:
        raise Http404
    jobs_qs = Job.objects.select_related("case", "case__organization", "reviewed_by")
    scoped = scope_jobs(jobs_qs, getattr(request, "user", None))
    scoped = scoped.filter(organization=organization)
    jobs_list = list(scoped[:200])

    telemetry_map = job_telemetry_map(jobs_list, request)

    job_ids = [str(job.id) for job in jobs_list]
    transcript_artifacts: Dict[str, CaseArtifact] = {}
    if job_ids:
        for art in (
            CaseArtifact.objects.filter(job_id__in=job_ids, type="TRANSCRIPT")
            .order_by("-created_at")
        ):
            key = art.job_id or ""
            if key and key not in transcript_artifacts:
                transcript_artifacts[key] = art

    display_rows, flat_rows = build_job_rows(jobs_list, telemetry_map, transcript_artifacts)

    user = getattr(request, "user", None)
    for row in flat_rows:
        job_obj: Optional[Job] = row.get("job")
        can_review = False
        case_obj: Optional[Case] = None
        if job_obj:
            case_obj = getattr(job_obj, "case", None)
            if isinstance(case_obj, Case):
                can_review = user_can_review_case(user, case_obj)
        row["actions"] = build_job_action_entries(
            job_obj,
            row.get("telemetry"),
            can_review=can_review,
            is_child=bool(row.get("is_child")),
        )
        if case_obj:
            display_meta = row.setdefault("display", {})
            display_meta["case"] = {
                "title": case_obj.title,
                "id": str(case_obj.id),
            }

    context = {
        "active_org": organization,
        "job_rows": display_rows,
        "job_columns": list(GLOBAL_JOB_TABLE_COLUMNS),
        "job_column_ids": [col["id"] for col in GLOBAL_JOB_TABLE_COLUMNS],
        "job_filters": DEFAULT_TABLE_FILTERS,
        "job_total": len(display_rows),
        "job_show_identifiers": False,
        "jobs_table": table_config(
            panel_key="jobs",
            title="Jobs",
            pill="Live updates",
            rows=display_rows,
            columns=GLOBAL_JOB_TABLE_COLUMNS,
            column_ids=[col["id"] for col in GLOBAL_JOB_TABLE_COLUMNS],
            filters=DEFAULT_TABLE_FILTERS,
            empty_message="No jobs yet.",
            show_identifiers=False,
            case_id=None,
        ),
    }
    return render(request, "platform_ui/jobs/index.html", context)



@require_http_methods(["GET"])
def job_detail_panel(request: HttpRequest, job_id: str) -> HttpResponse:
    try:
        auth_response = ensure_authenticated(request)
        if auth_response:
            return auth_response

        jobs_qs = Job.objects.select_related("case", "case__organization", "reviewed_by").filter(pk=job_id)
        job = scope_jobs(jobs_qs, getattr(request, "user", None)).first()
        if not job:
            raise Http404

        # Support forcing the title editor open via query param for HTMX swaps
        title_edit = str(request.GET.get("title_edit") or "").lower() in {"1", "true", "yes", "on"}
        context = job_detail_context(request, job, title_edit=title_edit)
        template = (
            "platform_ui/partials/job_detail_audio_conversion.html"
            if context.get("job_kind", "").lower() == "audio_conversion"
            else "platform_ui/partials/job_detail.html"
        )
        return render(request, template, context)
    except Http404:
        raise
    except Exception as exc:  # noqa: BLE001
        log.exception("job_detail_panel error", extra={"job_id": job_id})
        return HttpResponse(
            '<div class="space-y-2 text-xs text-rose-200">'
            "<p>Unable to load job detail.</p>"
            f"<p class=\"font-mono text-[10px] text-rose-300\">{exc}</p>"
            "</div>",
            status=500,
        )



@require_http_methods(["GET"])
def case_job_detail_panel(request: HttpRequest, case_id: str, job_id: str) -> HttpResponse:
    try:
        auth_response = ensure_authenticated(request)
        if auth_response:
            return auth_response

        case, _ = get_case_and_org(request, case_id)
        job = (
            Job.objects.select_related("case", "case__organization", "reviewed_by")
            .filter(case=case, pk=job_id)
            .first()
        )
        if not job:
            raise Http404

        # Support forcing the title editor open via query param for HTMX swaps
        title_edit = str(request.GET.get("title_edit") or "").lower() in {"1", "true", "yes", "on"}
        context = job_detail_context(request, job, title_edit=title_edit)
        context["case"] = case
        template = (
            "platform_ui/partials/job_detail_audio_conversion.html"
            if context.get("job_kind", "").lower() == "audio_conversion"
            else "platform_ui/partials/job_detail.html"
        )
        return render(request, template, context)
    except Http404:
        raise
    except Exception as exc:  # noqa: BLE001
        log.exception(
            "case_job_detail_panel error", extra={"job_id": job_id, "case_id": case_id}
        )
        return HttpResponse(
            '<div class="space-y-2 text-xs text-rose-200">'
            "<p>Unable to load job detail.</p>"
            f"<p class=\"font-mono text-[10px] text-rose-300\">{exc}</p>"
            "</div>",
            status=500,
        )



@require_http_methods(["GET"])
def case_job_title_form(request: HttpRequest, case_id: str, job_id: str) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    case, _ = get_case_and_org(request, case_id)
    job = (
        Job.objects.select_related("case", "case__organization", "reviewed_by")
        .filter(case=case, pk=job_id)
        .first()
    )
    if not job:
        raise Http404

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
def case_job_update_title(request: HttpRequest, case_id: str, job_id: str) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    case, _ = get_case_and_org(request, case_id)
    job = (
        Job.objects.select_related("case", "case__organization", "reviewed_by")
        .filter(case=case, pk=job_id)
        .first()
    )
    if not job:
        raise Http404

    user = getattr(request, "user", None)
    dev_open = getattr(settings, "PLATFORM_DEV_OPEN", False)
    can_edit = False
    if dev_open:
        can_edit = True
    elif user and getattr(user, "is_authenticated", False):
        if case.reviewer_id and str(user.id) == str(case.reviewer_id):
            can_edit = True
        elif has_capability(user, str(case.id), "case.update"):
            can_edit = True
    if not can_edit:
        return HttpResponse("Forbidden", status=403)

    new_title = (request.POST.get("title") or "").strip()
    title_error: Optional[str] = None
    if not new_title:
        title_error = "Title cannot be empty."

    telemetry_dict = job_telemetry_payload(job, request, ui_mode=True)

    artifact = (
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
        artifact = artifact or ensure_transcript_artifact(
            case_id=str(case.id),
            case=case,
            job=job,
            telemetry=telemetry_dict,
            title=new_title,
            organization_id=getattr(case, "organization_id", None),
            metadata_source="ui.job_title",
        )
        if not artifact:
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

    artifact.title = new_title
    if isinstance(artifact.metadata, dict):
        metadata = dict(artifact.metadata)
    else:
        metadata = {}
    metadata.update({
        "transcript_title": new_title,
        "job_title": new_title,
        "title_updated_at": timezone.now().isoformat(),
    })
    if user and getattr(user, "is_authenticated", False):
        metadata["title_updated_by"] = str(getattr(user, "id", ""))
    artifact.metadata = metadata
    artifact.save(update_fields=["title", "metadata"])

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
def case_job_create_artifact(request: HttpRequest, case_id: str, job_id: str) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    case, _ = get_case_and_org(request, case_id)
    job = (
        Job.objects.select_related("case", "case__organization", "reviewed_by")
        .filter(case=case, pk=job_id)
        .first()
    )
    if not job:
        raise Http404

    user = getattr(request, "user", None)
    dev_open = getattr(settings, "PLATFORM_DEV_OPEN", False)
    can_manage = False
    if dev_open:
        can_manage = True
    elif user and getattr(user, "is_authenticated", False):
        if case.reviewer_id and str(user.id) == str(case.reviewer_id):
            can_manage = True
        elif has_capability(user, str(case.id), "case.update"):
            can_manage = True
    if not can_manage:
        return JsonResponse({"status": "error", "detail": "Forbidden"}, status=403)

    telemetry_dict = job_telemetry_payload(job, request, ui_mode=True)

    existing = (
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

    if not artifact:
        return JsonResponse(
            {"status": "error", "detail": "Transcript not found for this job."},
            status=404,
        )

    title_input = (request.POST.get("title") or "").strip()
    metadata_changed = False
    title_changed = False
    if title_input:
        desired_title = unique_transcript_title(str(case.id), title_input, getattr(case, "organization_id", None))
        if artifact.title != desired_title:
            artifact.title = desired_title
            title_changed = True
    elif not artifact.title:
        default_title = default_transcript_title(job, telemetry_dict)
        unique_transcript_title_val = unique_transcript_title(
            str(case.id), default_title, getattr(case, "organization_id", None)
        )
        if artifact.title != unique_transcript_title_val:
            artifact.title = unique_transcript_title_val
            title_changed = True

    metadata = artifact.metadata or {}
    if not isinstance(metadata, dict):
        metadata = {}
    else:
        metadata = dict(metadata)
    if metadata.get("created_via") is None:
        metadata["created_via"] = "ui.transcript_promote"
        metadata_changed = True
    metadata["last_promoted_at"] = timezone.now().isoformat()
    metadata_changed = True
    if user and getattr(user, "is_authenticated", False):
        metadata["last_promoted_by"] = str(getattr(user, "id", ""))
    if title_changed:
        metadata["job_title"] = artifact.title
        metadata["transcript_title"] = artifact.title
    artifact.metadata = metadata

    update_fields: List[str] = []
    if title_changed:
        update_fields.append("title")
    if metadata_changed or title_changed:
        update_fields.append("metadata")
    if update_fields:
        artifact.save(update_fields=update_fields)

    was_created = existing is None
    log_message = "Transcript promoted to case artifact"
    if title_changed and not was_created:
        log_message = f"Transcript artifact updated: {artifact.title}"
    org_id = str(job.organization_id) if job.organization_id is not None else None
    append_job_log(str(job.case_id), org_id, str(job.id), log_message)
    update_job_meta(
        str(case.id),
        case.organization_id,
        str(job.id),
        {"transcript_artifact_id": str(artifact.id)},
    )

    return JsonResponse(
        {
            "status": "ok",
            "artifact_id": artifact.id,
            "title": artifact.title,
            "created": was_created,
        }
    )



@require_http_methods(["GET"])
def case_job_row(request: HttpRequest, case_id: str, job_id: str) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    case, _ = get_case_and_org(request, case_id)
    job = (
        Job.objects.select_related("case", "case__organization")
        .filter(case=case, pk=job_id)
        .first()
    )
    if not job:
        raise Http404

    telemetry_dict = job_telemetry_payload(job, request, ui_mode=True)
    telemetry_map: Dict[str, JobTelemetryPayload] = {str(job.id): telemetry_dict}
    _, flat_rows = build_job_rows([job], telemetry_map)
    row = (
        flat_rows[0]
        if flat_rows
        else {
            "job": job,
            "telemetry": telemetry_dict,
            "title": friendly_job_title(job, telemetry_dict),
            "children": [],
            "actions": [],
        }
    )
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



@require_http_methods(["POST"])
def create_job(request: HttpRequest, case_id: str) -> HttpResponse:
    """Create a job and return a table row partial (HTMX) or JSON as needed."""
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    try:
        active_org = resolve_request_organization(request, required=True)
    except PermissionDenied:
        return redirect("ui-index")

    cases_qs = Case.objects.select_related("organization")
    case = cases_qs.for_user(getattr(request, "user", None)).filter(pk=case_id).first()
    if not case or case.organization_id != getattr(active_org, "id", None):
        raise Http404

    mode = request.POST.get("mode") or Job.Mode.ON_DEMAND
    diarization = bool(request.POST.get("diarization"))
    language = request.POST.get("language") or "en-CA"
    up = request.FILES.get("audio")
    sas_url = (request.POST.get("audio_url") or "").strip()

    if diarization and mode != Job.Mode.BATCH:
        mode = Job.Mode.BATCH

    job_id = uuid.uuid4()
    case_dir = ensure_case_dirs(case_id, case.organization_id)
    audio_dir = case_dir / "audio"
    audio_input: str

    force_wav_conversion = str(request.POST.get("force_wav") or "").lower() in {"1", "true", "yes", "on"}

    if up:
        dest = audio_dir / f"{job_id}__{up.name}"
        with dest.open("wb") as f:
            for chunk in up.chunks():
                f.write(chunk)
        audio_input = str(dest)
    elif sas_url:
        audio_input = sas_url
        if mode != Job.Mode.BATCH:
            mode = Job.Mode.BATCH
    else:
        return HttpResponse("Upload a file or provide a SAS URL.", status=400)

    job = Job.objects.create(
        id=job_id,
        case=case,
        organization=case.organization,
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
    row = (
        flat_rows[0]
        if flat_rows
        else {
            "job": job,
            "telemetry": telemetry_dict,
            "title": friendly_job_title(job, telemetry_dict),
            "children": [],
            "actions": [],
        }
    )
    row["actions"] = build_job_action_entries(
        job,
        telemetry_dict,
        can_review=user_can_review_case(getattr(request, "user", None), job.case),
        is_child=False,
    )
    response = render(
        request,
        "platform_ui/partials/job_row.html",
        {
            "row": row,
            "table_columns": CASE_JOB_TABLE_COLUMNS,
        },
    )
    return response
