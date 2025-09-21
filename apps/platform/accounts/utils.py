from __future__ import annotations

from typing import Iterable, Optional

from django.contrib.auth import get_user_model
from django.db import models

from apps.platform.accounts.models import Organization, OrganizationMembership

AdminOrgChoice = dict[str, str]

_SESSION_KEY = "admin_active_org_id"


def user_accessible_organizations(user) -> models.QuerySet[Organization]:
    """Return queryset of organizations the user may manage."""
    if not user or not getattr(user, "is_authenticated", False):
        return Organization.objects.none()
    if getattr(user, "is_superuser", False):
        return Organization.objects.all().order_by("name")
    org_ids = OrganizationMembership.objects.filter(user=user).values_list("organization_id", flat=True)
    return Organization.objects.filter(id__in=org_ids).order_by("name")


def user_accessible_org_ids(user) -> list[str]:
    return list(user_accessible_organizations(user).values_list("id", flat=True))


def get_active_admin_org_id(request) -> Optional[str]:
    org = get_active_admin_org(request)
    return org.id if org else None


def get_active_admin_org(request) -> Optional[Organization]:
    session = getattr(request, "session", None)
    if session is None:
        request.admin_active_org = None  # type: ignore[attr-defined]
        request.admin_active_org_id = None  # type: ignore[attr-defined]
        return None

    user = getattr(request, "user", None)
    orgs_qs = user_accessible_organizations(user)
    accessible = list(orgs_qs)
    stored = session.get(_SESSION_KEY)
    if stored and stored not in {org.id for org in accessible}:
        stored = None
    if not stored and len(accessible) == 1:
        stored = accessible[0].id
        session[_SESSION_KEY] = stored
    if stored:
        for org in accessible:
            if org.id == stored:
                request.admin_active_org = org  # type: ignore[attr-defined]
                request.admin_active_org_id = stored  # type: ignore[attr-defined]
                return org
    request.admin_active_org = None  # type: ignore[attr-defined]
    request.admin_active_org_id = None  # type: ignore[attr-defined]
    if not accessible:
        session.pop(_SESSION_KEY, None)
    return None


def set_active_admin_org_id(request, org_id: Optional[str]) -> None:
    session = getattr(request, "session", None)
    if session is None:
        return
    if org_id:
        session[_SESSION_KEY] = str(org_id)
    else:
        session.pop(_SESSION_KEY, None)
    session.modified = True


def admin_org_choices(request) -> list[AdminOrgChoice]:
    orgs = user_accessible_organizations(getattr(request, "user", None))
    return [{"id": org.id, "name": org.name} for org in orgs]
