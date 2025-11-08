from __future__ import annotations

# pyright: strict
from typing import Any, cast
from uuid import UUID

from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.platform.artifacts.models import CaseArtifact
from apps.platform.operations.utils import append_job_log, update_job_meta

from ..auth import ensure_authenticated
from ..contexts import user_can_review_case
from ..selectors import job_telemetry_payload
from ..transcripts import (
    default_transcript_title,
    ensure_transcript_artifact,
    unique_transcript_title,
)
from .utils import CaseArtifactLike, resolve_job


@require_http_methods(["POST"])
def case_job_create_artifact(request: HttpRequest, case_id: str, job_id: UUID) -> JsonResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return cast(JsonResponse, auth_response)

    job = resolve_job(case_id, job_id, request)
    case = job.case

    user = getattr(request, "user", None)
    dev_open = getattr(settings, "PLATFORM_DEV_OPEN", False)
    can_manage = False
    if dev_open:
        can_manage = True
    elif user and getattr(user, "is_authenticated", False):
        if (
            case.reviewer_id
            and str(user.id) == str(case.reviewer_id)
            or user_can_review_case(user, case)
        ):
            can_manage = True
    if not can_manage:
        return JsonResponse({"status": "error", "detail": "Forbidden"}, status=403)

    telemetry_dict = job_telemetry_payload(job, request, ui_mode=True)

    existing: CaseArtifact | None = (
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
        return JsonResponse(
            {"status": "error", "detail": "Transcript not found for this job."}, status=404
        )

    artifact_obj: CaseArtifactLike = cast(CaseArtifactLike, artifact)

    title_input = (request.POST.get("title") or "").strip()
    metadata_changed = False
    title_changed = False
    if title_input:
        desired_title = unique_transcript_title(
            str(case.id), title_input, getattr(case, "organization_id", None)
        )
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
    metadata: dict[str, Any]
    if isinstance(raw_metadata, dict):
        metadata = dict(cast(dict[str, Any], raw_metadata))
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

    update_fields: list[str] = []
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
