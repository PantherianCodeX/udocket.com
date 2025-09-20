from __future__ import annotations

import uuid
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_page

from apps.platform.cases.models import Case
from apps.platform.jobs.models import Job
from apps.platform.operations.tasks import transcribe_job
from apps.platform.operations.storage import ensure_case_dirs
from apps.platform.authorization.models import (
    PermissionPreset,
    PresetCapability,
    PresetFieldPolicy,
    Role,
)
from apps.platform.authorization.capabilities import role_capabilities
from apps.platform.artifacts.registry import ARTIFACT_FIELD_REGISTRY
from django.contrib.auth import logout
import logging

log = logging.getLogger("apps.platform.ui")


@require_http_methods(["GET", "POST"])
def index(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        case_id = (request.POST.get("case_id") or "").strip()
        title = (request.POST.get("title") or "").strip() or case_id
        if not case_id:
            return render(request, "ui/index.html", {"cases": Case.objects.all(), "error": "Case ID is required"})
        Case.objects.get_or_create(id=case_id, defaults={"title": title})
        return redirect("ui-case-detail", case_id=case_id)
    return render(request, "ui/index.html", {"cases": Case.objects.all()})


@require_http_methods(["GET", "POST"])
def case_detail(request: HttpRequest, case_id: str) -> HttpResponse:
    try:
        case = Case.objects.get(pk=case_id)
    except Case.DoesNotExist:
        raise Http404

    if request.method == "POST":
        # Legacy non-HTMX POST fallback; delegate to create_job then redirect
        response = create_job(request, case_id)
        # If HTMX, the handler returned a row; for plain POST redirect back
        if request.headers.get("HX-Request"):
            return response
        return redirect("ui-case-detail", case_id=case_id)

    jobs = Job.objects.filter(case=case)
    return render(request, "ui/case_detail.html", {"case": case, "jobs": jobs})


def jobs(request: HttpRequest) -> HttpResponse:
    all_jobs = Job.objects.select_related("case").all()[:200]
    return render(request, "ui/jobs.html", {"jobs": all_jobs})


@require_http_methods(["GET"])
@cache_page(30)
def permissions_overview(request: HttpRequest) -> HttpResponse:
    registry = {
        artifact_type: {
            field: {
                "default_actions": list(meta.default_actions or ()),
                "description": meta.description,
            }
            for field, meta in fields.items()
        }
        for artifact_type, fields in ARTIFACT_FIELD_REGISTRY.items()
    }

    presets = []
    for preset in PermissionPreset.objects.all().order_by("slug"):
        caps = list(
            PresetCapability.objects.filter(preset=preset).values_list("capability", flat=True)
        )
        policies = [
            {
                "type": fp.type,
                "field": fp.field_name,
                "actions": list(fp.actions or []),
            }
            for fp in PresetFieldPolicy.objects.filter(preset=preset)
        ]
        presets.append(
            {
                "slug": preset.slug,
                "name": preset.name,
                "description": preset.description,
                "system": preset.system,
                "capabilities": caps,
                "field_policies": policies,
            }
        )

    roles = []
    for role in Role.objects.all().prefetch_related("presets").order_by("slug"):
        roles.append(
            {
                "slug": role.slug,
                "name": role.name,
                "system": role.system,
                "presets": [p.slug for p in role.presets.all()],
                "capabilities": sorted(role_capabilities(role.slug)),
            }
        )

    context = {"registry": registry, "presets": presets, "roles": roles}
    return render(request, "ui/permissions.html", context)


def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("ui-index")


@require_http_methods(["POST"])
def create_job(request: HttpRequest, case_id: str) -> HttpResponse:
    """Create a job and return a table row partial (HTMX) or JSON as needed."""
    try:
        case = Case.objects.get(pk=case_id)
    except Case.DoesNotExist:
        raise Http404

    mode = request.POST.get("mode") or Job.Mode.ON_DEMAND
    diarization = bool(request.POST.get("diarization"))
    language = request.POST.get("language") or "en-CA"
    up = request.FILES.get("audio")
    sas_url = (request.POST.get("audio_url") or "").strip()

    job_id = uuid.uuid4()
    case_dir = ensure_case_dirs(case_id, case.organization_id)
    audio_dir = case_dir / "audio"
    audio_input: str

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
        audio_input=audio_input,
        mode=mode,
        diarization=diarization,
        language=language,
    )

    log.info("ui enqueue job", extra={"job_id": str(job.id), "case_id": case_id, "mode": mode})
    transcribe_job.delay(
        case_id=str(case.id),
        job_id=str(job.id),
        audio_input=audio_input,
        mode=mode,
        diarization=diarization,
        language=language,
    )

    # HTMX partial for immediate row insert
    return render(request, "ui/_job_row.html", {"j": job})
