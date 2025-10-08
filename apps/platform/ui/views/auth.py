from __future__ import annotations

# pyright: strict

from dataclasses import dataclass
from typing import TypedDict

from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import redirect_to_login
from django.db.models import Count
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseRedirect,
)
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods

from apps.platform.accounts.models import OrganizationMembership
from apps.platform.accounts.utils import (
    get_active_admin_org,
    set_active_admin_org_id,
    user_accessible_organizations,
)
from apps.platform.cases.models import Case


def _safe_next_url(request: HttpRequest) -> str | None:
    """Validate a `next` parameter coming from the request."""

    candidate = (request.GET.get("next") or request.POST.get("next") or "").strip()
    if not candidate:
        return None
    if url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    if candidate.startswith("/"):
        return candidate
    return None


@dataclass(frozen=True, slots=True)
class OrganizationOption:
    id: str
    name: str
    case_count: int
    role_labels: tuple[str, ...]
    is_active: bool


class LoginTemplateContext(TypedDict):
    form: AuthenticationForm
    next_url: str | None
    oidc_login_url: str | None


class OrganizationSelectContext(TypedDict):
    organizations: tuple[OrganizationOption, ...]
    next_url: str | None


def ensure_authenticated(request: HttpRequest) -> HttpResponse | None:
    """Gate UI views when dev-open mode is disabled."""

    user = getattr(request, "user", None)
    if user and getattr(user, "is_authenticated", False):
        return None
    if getattr(settings, "PLATFORM_DEV_OPEN", False):
        return None
    if request.method == "GET":
        return redirect_to_login(request.get_full_path())
    return HttpResponse("Authentication required", status=401)



def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("ui-index")


@require_http_methods(["GET", "POST"])
def login_view(request: HttpRequest) -> HttpResponse:
    next_url = _safe_next_url(request)
    if getattr(request, "user", None) and getattr(request.user, "is_authenticated", False):
        return redirect(next_url or "ui-organization-gate")

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect(next_url or "ui-organization-gate")

    oidc_login_url: str | None
    if getattr(settings, "OIDC_ENABLED", False):
        try:
            oidc_login_url = reverse("oidc_authentication_init")
        except Exception:
            oidc_login_url = "/oidc/authenticate/"
    else:
        oidc_login_url = None

    context: LoginTemplateContext = {
        "form": form,
        "next_url": next_url,
        "oidc_login_url": oidc_login_url,
    }
    return render(request, "platform_ui/auth/login.html", context)


@require_http_methods(["GET"])
def organization_gate(request: HttpRequest) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response is not None:
        return auth_response

    user = getattr(request, "user", None)
    organizations = list(user_accessible_organizations(user))
    if not organizations:
        set_active_admin_org_id(request, None)
        context: OrganizationSelectContext = {
            "organizations": tuple(),
            "next_url": None,
        }
        return render(request, "platform_ui/auth/organization_select.html", context)

    if len(organizations) == 1:
        single = organizations[0]
        set_active_admin_org_id(request, str(single.id))
        return redirect(_safe_next_url(request) or "ui-index")

    active_org = get_active_admin_org(request)
    active_org_id = str(active_org.id) if active_org else None

    membership_roles = OrganizationMembership.objects.filter(
        organization__in=organizations,
        user=user,
    )
    roles_by_org: dict[str, set[str]] = {}
    for membership in membership_roles:
        org_id = str(getattr(membership, "organization_id"))
        labels = roles_by_org.setdefault(org_id, set())
        labels.add(membership.get_role_display())

    is_global_superuser = bool(user and getattr(user, "is_superuser", False))

    case_totals_qs = (
        Case.typed_objects()
        .filter(organization__in=organizations)
        .values("organization_id")
        .annotate(total=Count("id"))
    )
    case_totals: dict[str, int] = {}
    for row in case_totals_qs:
        org_id_raw = row.get("organization_id")
        if org_id_raw is None:
            continue
        org_id = str(org_id_raw)
        case_totals[org_id] = int(row.get("total") or 0)

    options: list[OrganizationOption] = []
    for org in organizations:
        org_id = str(org.id)
        role_labels = roles_by_org.get(org_id)
        if role_labels:
            roles = tuple(sorted(role_labels))
        elif is_global_superuser:
            roles = ("Superuser",)
        else:
            roles = ("Member",)
        options.append(
            OrganizationOption(
                id=org_id,
                name=org.name,
                case_count=case_totals.get(org_id, 0),
                role_labels=roles,
                is_active=active_org_id == org_id,
            )
        )

    context: OrganizationSelectContext = {
        "organizations": tuple(options),
        "next_url": _safe_next_url(request),
    }
    return render(request, "platform_ui/auth/organization_select.html", context)


@require_http_methods(["POST"])
def select_organization(request: HttpRequest) -> HttpResponse:
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return redirect("ui-index")

    org_id = (request.POST.get("organization_id") or "").strip()
    next_url = _safe_next_url(request) or request.META.get("HTTP_REFERER") or reverse("ui-index")

    if not org_id:
        set_active_admin_org_id(request, None)
        return HttpResponseRedirect(next_url)

    accessible_ids = {
        str(value) for value in user_accessible_organizations(user).values_list("id", flat=True)
    }
    if org_id in accessible_ids or getattr(user, "is_superuser", False):
        set_active_admin_org_id(request, org_id)

    return HttpResponseRedirect(next_url)
