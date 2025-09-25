from __future__ import annotations

import json
from typing import Any, Dict, Optional, cast
from uuid import UUID

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.platform.artifacts.models import CaseArtifact

from ..auth import ensure_authenticated
from ..contexts import job_detail_context, user_can_review_case
from ..selectors import job_telemetry_payload
from ..transcripts import ensure_transcript_artifact
from .utils import CaseArtifactLike, resolve_job
from apps.platform.operations.utils import append_job_log, update_job_meta


@require_http_methods(["GET"])
def case_job_title_form(request: HttpRequest, case_id: str, job_id: UUID) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    job = resolve_job(case_id, job_id, request)
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

    job = resolve_job(case_id, job_id, request)
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

    assert artifact is not None
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
