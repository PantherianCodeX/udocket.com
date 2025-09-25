from __future__ import annotations

# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.platform.accounts.models import OrganizationMembership, User
from apps.platform.accounts.utils import resolve_request_organization
from apps.platform.authorization.capabilities import has_capability
from apps.platform.cases.models import Case, CaseMembership
from apps.platform.jobs.models import Job
from apps.platform.tenancy import scope_jobs

from .auth import ensure_authenticated
from .common import JobTelemetryPayload
from .contexts import compute_case_tool_state, get_case_and_org
from .presenters.cases import (
    analysis_modules_context,
    case_field_specs,
    case_progress_context,
)
from .selectors import job_telemetry_map

from .jobs import create_job


@require_http_methods(["GET", "POST"])
def case_detail(request: HttpRequest, case_id: str) -> HttpResponse:
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

    if request.method == "POST":
        # Legacy non-HTMX POST fallback; delegate to create_job then redirect
        response = create_job(request, case_id)
        # If HTMX, the handler returned a row; for plain POST redirect back
        if request.headers.get("HX-Request"):
            return response
        return redirect("ui-case-detail", case_id=case_id)

    state = compute_case_tool_state(request, case)
    tool_panels = state["tool_panels"]
    developer_cards = state["developer_cards"]
    case_header = state["case_header"]
    job_summary = state["job_summary"]
    latest_activity_ts = state["latest_activity_ts"]

    raw_tool = (request.GET.get("tool") or request.GET.get("module") or "").strip().lower()
    tool_aliases = {
        "": "case-details",
        "case": "case-details",
        "details": "case-details",
        "case-details": "case-details",
        "setup": "case-details",
        "intake": "case-details",
        "intake-form": "case-details",
        "transcribe": "transcribe",
        "transcription": "transcribe",
        "summary": "summary",
        "summaries": "summary",
        "timeline": "timeline",
    }
    initial_tool_key = tool_aliases.get(raw_tool, raw_tool if raw_tool in tool_panels else None)
    if not initial_tool_key or initial_tool_key not in tool_panels:
        initial_tool_key = "case-details"
    initial_panel = tool_panels.get(initial_tool_key)

    context = {
        "case": case,
        "job_summary": job_summary,
        "latest_activity_ts": latest_activity_ts,
        "case_header": case_header,
        "case_developer_cards": developer_cards,
        "initial_tool_key": initial_tool_key,
        "initial_tool_panel": initial_panel,
    }
    return render(request, "platform_ui/cases/detail.html", context)



@require_http_methods(["GET"])
def case_analysis_module(request: HttpRequest, case_id: str, agent: str) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    case, _ = get_case_and_org(request, case_id)

    jobs_qs = (
        Job.objects.select_related("case", "case__organization", "reviewed_by")
        .filter(case=case)
        .order_by("-created_at")
    )
    jobs_scoped = scope_jobs(jobs_qs, getattr(request, "user", None))
    jobs_list = list(jobs_scoped)
    telemetry_map: Dict[str, JobTelemetryPayload] = job_telemetry_map(jobs_list, request)

    modules = analysis_modules_context(request, case, jobs_list, telemetry_map)
    module = next((item for item in modules if item.get("key") == agent), None)
    if not module:
        raise Http404

    return render(request, "platform_ui/partials/analysis_module.html", {"module": module, "case": case})



@require_http_methods(["POST"])
def case_update_title(request: HttpRequest, case_id: str) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    case, _ = get_case_and_org(request, case_id)
    new_title = (request.POST.get("title") or "").strip()
    if not new_title:
        new_title = case.title or case.id
    if new_title != case.title:
        case.title = new_title
        case.save(update_fields=["title"])
    return render(request, "platform_ui/partials/case_title.html", {"case": case})



@require_http_methods(["POST"])
def case_details_update(request: HttpRequest, case_id: str) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    case, _ = get_case_and_org(request, case_id)

    dev_open = getattr(settings, "PLATFORM_DEV_OPEN", False)
    user = getattr(request, "user", None)
    if not dev_open:
        if not user or not getattr(user, "is_authenticated", False) or not has_capability(user, str(case.id), "case.update"):
            return HttpResponse("Forbidden", status=403)

    form_errors: Dict[str, str] = {}
    case_updates: Dict[str, Any] = {}
    specs = case_field_specs()

    for spec in specs:
        name = spec["name"]
        field_type = spec.get("type", "text")
        raw_value = request.POST.get(name)

        if field_type in {"text", "textarea", "choice"}:
            case_updates[name] = raw_value or ""
            continue

        if field_type == "datetime":
            if raw_value:
                try:
                    dt = datetime.strptime(raw_value, "%Y-%m-%dT%H:%M")
                    aware = timezone.make_aware(dt, timezone.get_current_timezone())
                    case_updates[name] = aware
                except Exception:
                    form_errors[name] = "Enter a valid date and time."
            else:
                case_updates[name] = None
            continue

        if field_type == "date":
            if raw_value:
                try:
                    case_updates[name] = datetime.strptime(raw_value, "%Y-%m-%d").date()
                except Exception:
                    form_errors[name] = "Enter a valid date."
            else:
                case_updates[name] = None
            continue

    reviewer_id = (request.POST.get("reviewer_id") or "").strip()
    client_user_id = (request.POST.get("client_user_id") or "").strip()
    owner_id = (request.POST.get("owner_id") or "").strip()
    contributor_ids = set((request.POST.getlist("contributor_ids") or []) if hasattr(request, 'POST') else [])
    representation_value = (request.POST.get("representation") or "").strip()
    engagement_value = (request.POST.get("engagement_model") or "standard").strip().lower()

    if form_errors:
        state = compute_case_tool_state(request, case)
        panel = state["tool_panels"].get("case-details")
        if panel:
            panel_body = panel.get("body_context", {})
            panel_body["form_errors"] = form_errors
        return render(request, "platform_ui/tools/_panel.html", {"panel": panel}, status=400)

    update_fields: List[str] = []
    for field_name, value in case_updates.items():
        if hasattr(case, field_name) and getattr(case, field_name) != value:
            setattr(case, field_name, value)
            update_fields.append(field_name)

    if representation_value and representation_value != case.representation:
        case.representation = representation_value
        update_fields.append("representation")

    if engagement_value == "legal_aid":
        if not case.legal_aid:
            case.legal_aid = True
            update_fields.append("legal_aid")
        if case.pro_bono:
            case.pro_bono = False
            update_fields.append("pro_bono")
    elif engagement_value == "pro_bono":
        if not case.pro_bono:
            case.pro_bono = True
            update_fields.append("pro_bono")
        if case.legal_aid:
            case.legal_aid = False
            update_fields.append("legal_aid")
    else:
        if case.legal_aid:
            case.legal_aid = False
            update_fields.append("legal_aid")
        if case.pro_bono:
            case.pro_bono = False
            update_fields.append("pro_bono")

    if reviewer_id:
        reviewer = User.objects.filter(pk=reviewer_id).first()
        if reviewer and str(case.reviewer_id) != str(reviewer.pk):
            OrganizationMembership.objects.get_or_create(
                organization=case.organization,
                user=reviewer,
                defaults={"role": OrganizationMembership.Role.MEMBER},
            )
            CaseMembership.objects.get_or_create(
                case=case,
                user=reviewer,
                defaults={"role": CaseMembership.Role.REVIEWER},
            )
            case.reviewer = reviewer
            update_fields.append("reviewer")
    else:
        if case.reviewer_id is not None:
            case.reviewer = None
            update_fields.append("reviewer")

    if client_user_id:
        client_user = User.objects.filter(pk=client_user_id).first()
        if client_user and str(case.client_user_id) != str(client_user.pk):
            OrganizationMembership.objects.get_or_create(
                organization=case.organization,
                user=client_user,
                defaults={"role": OrganizationMembership.Role.MEMBER},
            )
            CaseMembership.objects.get_or_create(
                case=case,
                user=client_user,
                defaults={"role": CaseMembership.Role.CLIENT},
            )
            case.client_user = client_user
            update_fields.append("client_user")
    else:
        if case.client_user_id is not None:
            case.client_user = None
            update_fields.append("client_user")

    current_owner_memberships = case.memberships.filter(role=CaseMembership.Role.OWNER)
    current_owner_ids = {str(m.user_id) for m in current_owner_memberships if m.user_id}

    if owner_id:
        owner_user = User.objects.filter(pk=owner_id).first()
        if owner_user and owner_id not in current_owner_ids:
            OrganizationMembership.objects.get_or_create(
                organization=case.organization,
                user=owner_user,
                defaults={"role": OrganizationMembership.Role.MEMBER},
            )
            membership, _ = CaseMembership.objects.get_or_create(
                case=case,
                user=owner_user,
                defaults={"role": CaseMembership.Role.OWNER},
            )
            if membership.role != CaseMembership.Role.OWNER:
                membership.role = CaseMembership.Role.OWNER
                membership.save(update_fields=["role"])
        demote_ids = {oid for oid in current_owner_ids if oid != owner_id}
    else:
        demote_ids = current_owner_ids

    if demote_ids:
        CaseMembership.objects.filter(
            case=case,
            user_id__in=demote_ids,
            role=CaseMembership.Role.OWNER,
        ).update(role=CaseMembership.Role.CONTRIBUTOR)

    # Sync contributors (add/remove) — excludes owners/reviewer/client
    existing_contributors = set(
        str(m.user_id)
        for m in case.memberships.filter(role=CaseMembership.Role.CONTRIBUTOR).all()
        if m.user_id
    )
    to_add = contributor_ids - existing_contributors
    to_remove = existing_contributors - contributor_ids
    if to_add:
        for uid in to_add:
            user_obj = User.objects.filter(pk=uid).first()
            if not user_obj:
                continue
            OrganizationMembership.objects.get_or_create(
                organization=case.organization,
                user=user_obj,
                defaults={"role": OrganizationMembership.Role.MEMBER},
            )
            CaseMembership.objects.get_or_create(
                case=case,
                user=user_obj,
                defaults={"role": CaseMembership.Role.CONTRIBUTOR},
            )
    if to_remove:
        CaseMembership.objects.filter(
            case=case,
            role=CaseMembership.Role.CONTRIBUTOR,
            user_id__in=list(to_remove),
        ).delete()

    if update_fields:
        case.save(update_fields=list(set(update_fields)))

    state = compute_case_tool_state(request, case)
    panel = state["tool_panels"].get("case-details")
    response = render(request, "platform_ui/tools/_panel.html", {"panel": panel})
    trigger_payload = {
        "case-view-refreshed": {
            "tools": ["case-details"],
            "header_html": render_to_string(
                "platform_ui/tools/_case_header.html",
                {"case": case, "case_header": state["case_header"]},
            ),
            "cards_html": render_to_string(
                "platform_ui/tools/_developer_cards.html",
                {"case": case, "cards": state["developer_cards"], "active_tool": "case-details"},
            ),
            "active_tool": "case-details",
        }
    }
    response["HX-Trigger"] = json.dumps(trigger_payload)
    return response



@require_http_methods(["GET"])
def case_tool_panel(request: HttpRequest, case_id: str, tool_key: str) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    case, _ = get_case_and_org(request, case_id)
    state = compute_case_tool_state(request, case)
    panels = state["tool_panels"]

    aliases = {
        "case": "case-details",
        "details": "case-details",
        "case-details": "case-details",
        "intake": "case-details",
        "intake-form": "case-details",
        "transcription": "transcribe",
        "transcribe": "transcribe",
        "summary": "summary",
        "timeline": "timeline",
    }
    resolved_key = aliases.get(tool_key.strip().lower(), tool_key.strip().lower())
    panel = panels.get(resolved_key)
    if not panel:
        raise Http404

    response = render(request, "platform_ui/tools/_panel.html", {"panel": panel})
    response["HX-Trigger"] = json.dumps({"case-view-refreshed": {"tools": [resolved_key], "active_tool": resolved_key}})
    return response



@require_http_methods(["POST"])
def case_assign_reviewer(request: HttpRequest, case_id: str) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    case, _ = get_case_and_org(request, case_id)

    dev_open = getattr(settings, "PLATFORM_DEV_OPEN", False)
    user = getattr(request, "user", None)
    if not dev_open:
        if not user or not getattr(user, "is_authenticated", False) or not has_capability(user, str(case.id), "case.update"):
            return HttpResponse("Forbidden", status=403)

    reviewer_id = (request.POST.get("reviewer_id") or "").strip()
    if reviewer_id:
        try:
            reviewer = User.objects.get(pk=reviewer_id)
        except User.DoesNotExist:
            return HttpResponse("Reviewer not found", status=404)
        OrganizationMembership.objects.get_or_create(
            organization=case.organization,
            user=reviewer,
            defaults={"role": OrganizationMembership.Role.MEMBER},
        )
        membership, created = CaseMembership.objects.get_or_create(
            case=case,
            user=reviewer,
            defaults={"role": CaseMembership.Role.REVIEWER},
        )
        if not created and membership.role != CaseMembership.Role.REVIEWER:
            membership.role = CaseMembership.Role.REVIEWER
            membership.save(update_fields=["role"])
        case.reviewer = reviewer
        case.save(update_fields=["reviewer", "updated_at"])
    else:
        if case.reviewer_id is not None:
            case.reviewer = None
            case.save(update_fields=["reviewer", "updated_at"])

    jobs_qs = (
        Job.objects.select_related("case", "case__organization", "reviewed_by")
        .filter(case=case)
        .order_by("-created_at")
    )
    jobs_list = list(scope_jobs(jobs_qs, getattr(request, "user", None)))
    telemetry_map = job_telemetry_map(jobs_list, request)
    context = {"case": case, **case_progress_context(case, jobs_list, telemetry_map)}
    return render(request, "platform_ui/partials/case_progress.html", context)



@require_http_methods(["POST"])
def case_assign_client(request: HttpRequest, case_id: str) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    case, _ = get_case_and_org(request, case_id)

    dev_open = getattr(settings, "PLATFORM_DEV_OPEN", False)
    user = getattr(request, "user", None)
    if not dev_open:
        if not user or not getattr(user, "is_authenticated", False) or not has_capability(user, str(case.id), "case.update"):
            return HttpResponse("Forbidden", status=403)

    client_id = (request.POST.get("client_id") or "").strip()
    email = (request.POST.get("client_email") or "").strip()
    name = (request.POST.get("client_name") or "").strip()

    client_user: Optional[User] = None
    if client_id:
        try:
            client_user = User.objects.get(pk=client_id)
        except User.DoesNotExist:
            return HttpResponse("Client not found", status=404)
    else:
        if not email:
            return HttpResponse("Client email is required", status=400)
        client_user = User.objects.filter(email__iexact=email).first()
        if client_user is None:
            username = email or f"client-{uuid.uuid4().hex[:10]}"
            base_username = username
            idx = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}-{idx}"[:150]
                idx += 1
            client_user = User.objects.create_user(username=username, email=email, password=None)
            if name:
                client_user.first_name = name.split(" ")[0]
                if " " in name.strip():
                    client_user.last_name = name.strip().split(" ", 1)[1]
                client_user.display_name = name
                client_user.save(update_fields=["first_name", "last_name", "display_name"])
        elif name:
            if not client_user.display_name:
                client_user.display_name = name
                client_user.save(update_fields=["display_name"])

    assert client_user is not None  # for mypy-like reasoning

    OrganizationMembership.objects.get_or_create(
        organization=case.organization,
        user=client_user,
        defaults={"role": OrganizationMembership.Role.MEMBER},
    )
    membership, created = CaseMembership.objects.get_or_create(
        case=case,
        user=client_user,
        defaults={"role": CaseMembership.Role.CLIENT},
    )
    if not created and membership.role != CaseMembership.Role.CLIENT:
        membership.role = CaseMembership.Role.CLIENT
        membership.save(update_fields=["role"])

    case.client_user = client_user
    if name and not case.client_name:
        case.client_name = name
        case.save(update_fields=["client_user", "client_name", "updated_at"])
    else:
        case.save(update_fields=["client_user", "updated_at"])

    jobs_qs = (
        Job.objects.select_related("case", "case__organization", "reviewed_by")
        .filter(case=case)
        .order_by("-created_at")
    )
    jobs_list = list(scope_jobs(jobs_qs, getattr(request, "user", None)))
    telemetry_map = job_telemetry_map(jobs_list, request)
    context = {"case": case, **case_progress_context(case, jobs_list, telemetry_map)}
    return render(request, "platform_ui/partials/case_progress.html", context)
