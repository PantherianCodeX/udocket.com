from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.platform.cases.models import Case, CaseMembership
from apps.platform.accounts.models import Organization
from apps.platform.accounts.utils import user_accessible_organizations
from apps.platform.jobs.models import Job
from apps.platform.operations.tasks import transcribe_job
from apps.platform.operations.storage import ensure_case_dirs
from apps.platform.authorization.models import PermissionPreset, Role
from apps.platform.authorization.capabilities import role_capabilities
from apps.platform.artifacts.registry import ARTIFACT_FIELD_REGISTRY
from django.contrib.auth import logout
from apps.platform.tenancy import accessible_organization_ids
import logging

log = logging.getLogger("apps.platform.ui")


def _ensure_authenticated(request: HttpRequest) -> HttpResponse | None:
    """Gate UI views when dev-open mode is disabled."""

    user = getattr(request, "user", None)
    if user and getattr(user, "is_authenticated", False):
        return None
    if getattr(settings, "PLATFORM_DEV_OPEN", False):
        return None
    login_url = getattr(settings, "LOGIN_URL", "/admin/login/")
    if request.method == "GET":
        return redirect(login_url)
    return HttpResponse("Authentication required", status=401)


def _accessible_organizations(request: HttpRequest):
    """Return organizations current request may interact with."""

    user = getattr(request, "user", None)
    if user and getattr(user, "is_authenticated", False):
        if getattr(user, "is_superuser", False):
            return Organization.objects.all().order_by("name")
        return user_accessible_organizations(user)
    if getattr(settings, "PLATFORM_DEV_OPEN", False):
        return Organization.objects.all().order_by("name")
    return Organization.objects.none()


@require_http_methods(["GET", "POST"])
def index(request: HttpRequest) -> HttpResponse:
    auth_response = _ensure_authenticated(request)
    if auth_response:
        return auth_response

    org_qs = _accessible_organizations(request)
    organizations = list(org_qs)
    cases_qs = Case.objects.select_related("organization")
    cases = cases_qs.for_user(getattr(request, "user", None)).order_by("-created_at")

    if request.method == "POST":
        case_id = (request.POST.get("case_id") or "").strip()
        title = (request.POST.get("title") or "").strip() or case_id
        org_id = (request.POST.get("organization_id") or "").strip()

        if not case_id:
            context = {
                "cases": cases,
                "organizations": organizations,
                "selected_org_id": org_id,
                "error": "Case ID is required",
            }
            return render(request, "ui/index.html", context)

        organization = None
        if org_id:
            organization = next((org for org in organizations if str(org.id) == org_id), None)
        if organization is None:
            context = {
                "cases": cases,
                "organizations": organizations,
                "selected_org_id": org_id,
                "error": "Select a valid organization",
            }
            return render(request, "ui/index.html", context)

        existing = Case.objects.filter(pk=case_id).select_related("organization").first()
        if existing:
            if existing.organization_id != organization.id:
                context = {
                    "cases": cases,
                    "organizations": organizations,
                    "selected_org_id": org_id,
                    "error": "Case already exists in a different organization.",
                }
                return render(request, "ui/index.html", context)
            case = existing
        else:
            case = Case.objects.create(id=case_id, title=title, organization=organization)
            user = getattr(request, "user", None)
            if user and getattr(user, "is_authenticated", False):
                CaseMembership.objects.get_or_create(
                    case=case,
                    user=user,
                    defaults={"role": CaseMembership.Role.OWNER},
                )
        return redirect("ui-case-detail", case_id=case_id)

    context = {
        "cases": cases,
        "organizations": organizations,
        "selected_org_id": None,
    }
    return render(request, "ui/index.html", context)


@require_http_methods(["GET", "POST"])
def case_detail(request: HttpRequest, case_id: str) -> HttpResponse:
    auth_response = _ensure_authenticated(request)
    if auth_response:
        return auth_response

    cases_qs = Case.objects.select_related("organization")
    case = cases_qs.for_user(getattr(request, "user", None)).filter(pk=case_id).first()
    if not case:
        raise Http404

    if request.method == "POST":
        # Legacy non-HTMX POST fallback; delegate to create_job then redirect
        response = create_job(request, case_id)
        # If HTMX, the handler returned a row; for plain POST redirect back
        if request.headers.get("HX-Request"):
            return response
        return redirect("ui-case-detail", case_id=case_id)

    jobs_qs = Job.objects.select_related("case")
    jobs = jobs_qs.for_user(getattr(request, "user", None)).filter(case=case)
    return render(request, "ui/case_detail.html", {"case": case, "jobs": jobs})


def jobs(request: HttpRequest) -> HttpResponse:
    auth_response = _ensure_authenticated(request)
    if auth_response:
        return auth_response

    jobs_qs = Job.objects.select_related("case")
    all_jobs = jobs_qs.for_user(getattr(request, "user", None))[:200]
    return render(request, "ui/jobs.html", {"jobs": all_jobs})


@require_http_methods(["GET"])
def permissions_overview(request: HttpRequest) -> HttpResponse:
    auth_response = _ensure_authenticated(request)
    if auth_response:
        return auth_response

    user = getattr(request, "user", None)
    dev_open = getattr(settings, "PLATFORM_DEV_OPEN", False)
    org_ids = accessible_organization_ids(user)

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

    preset_qs = (
        PermissionPreset.objects.select_related("organization")
        .prefetch_related("capabilities", "field_policies")
        .order_by("name")
    )
    role_qs = Role.objects.select_related("organization").prefetch_related("presets").order_by("name")

    if not (dev_open and (not user or not getattr(user, "is_authenticated", False))):
        if org_ids:
            preset_qs = preset_qs.filter(
                models.Q(organization__isnull=True) | models.Q(organization_id__in=org_ids)
            )
            role_qs = role_qs.filter(
                models.Q(organization__isnull=True) | models.Q(organization_id__in=org_ids)
            )
        else:
            preset_qs = preset_qs.filter(organization__isnull=True)
            role_qs = role_qs.filter(organization__isnull=True)

    presets = []
    for preset in preset_qs:
        caps = sorted(pc.capability for pc in preset.capabilities.all())
        policies = [
            {
                "resource": fp.resource,
                "type": fp.type,
                "field": fp.field_name,
                "actions": list(fp.actions or []),
            }
            for fp in preset.field_policies.all()
        ]
        presets.append(
            {
                "uuid": str(preset.uuid) if preset.uuid else None,
                "name": preset.name,
                "description": preset.description,
                "system": preset.system,
                "organization": preset.organization_id,
                "organization_name": preset.organization.name if preset.organization else None,
                "capabilities": caps,
                "field_policies": policies,
            }
        )

    roles = []
    for role in role_qs:
        caps = role_capabilities(role.name, organization_id=role.organization_id)
        roles.append(
            {
                "uuid": str(role.uuid) if role.uuid else None,
                "name": role.name,
                "system": role.system,
                "organization": role.organization_id,
                "organization_name": role.organization.name if role.organization else None,
                "presets": [p.name for p in role.presets.all()],
                "capabilities": sorted(caps),
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
    auth_response = _ensure_authenticated(request)
    if auth_response:
        return auth_response

    cases_qs = Case.objects.select_related("organization")
    case = cases_qs.for_user(getattr(request, "user", None)).filter(pk=case_id).first()
    if not case:
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
        organization=case.organization,
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
