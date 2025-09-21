from __future__ import annotations

from typing import Iterable, Optional

from django.contrib.auth import get_user_model
from django.db import models
from django.core.exceptions import PermissionDenied
from django.conf import settings

from apps.platform.accounts.models import Organization, OrganizationMembership
from apps.platform.cases.models import CaseMembership

AdminOrgChoice = dict[str, str]

_SESSION_KEY = "admin_active_org_id"


def user_accessible_organizations(user) -> models.QuerySet[Organization]:
    """Return queryset of organizations the user may manage."""
    if not user or not getattr(user, "is_authenticated", False):
        return Organization.objects.none()
    if getattr(user, "is_superuser", False):
        return Organization.objects.all().order_by("name")
    memberships = OrganizationMembership.objects.filter(user=user)
    if memberships.filter(role=OrganizationMembership.Role.SUPERUSER).exists():
        return Organization.objects.all().order_by("name")
    direct_ids = memberships.values_list("organization_id", flat=True)
    case_ids = (
        CaseMembership.objects.filter(user=user)
        .values_list("case__organization_id", flat=True)
        .distinct()
    )
    org_ids = set(direct_ids) | set(case_ids)
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


def resolve_request_organization(request, *, required: bool = True) -> Optional[Organization]:
    """Resolve the active organization for the current request.

    Preference order:
      1. Explicit header (`ORG_HEADER_NAME`) when the authenticated user is a
         member (or superuser).
      2. Admin-selected organization stored in session.
      3. Single accessible organization for the user.

    Raises PermissionDenied when `required` and no organization can be
    determined.
    """

    user = getattr(request, "user", None)
    header_name = getattr(settings, "ORG_HEADER_NAME", "HTTP_X_ORGANIZATION_ID")
    header_org_id = request.META.get(header_name)

    def _get_org(org_id: str | None) -> Optional[Organization]:
        if not org_id:
            return None
        return Organization.objects.filter(id=org_id).first()

    if header_org_id:
        org = _get_org(header_org_id)
        if org and user and getattr(user, "is_authenticated", False):
            if OrganizationMembership.objects.filter(user=user, role=OrganizationMembership.Role.SUPERUSER).exists():
                return org
            if OrganizationMembership.objects.filter(organization=org, user=user).exists():
                return org
        # Ignore spoofed headers when unauthenticated or not a member.

    active = get_active_admin_org(request)
    if active is not None:
        return active

    if user and getattr(user, "is_authenticated", False):
        accessible = user_accessible_organizations(user)
        count = accessible.count()
        if count == 1:
            return accessible.first()

    if required:
        raise PermissionDenied("Organization context is required for this action.")
    return None


def sync_user_access_flags(user) -> None:
    """Synchronize Django staff/superuser flags from organization roles."""

    if not user or not getattr(user, "pk", None):
        return

    roles = set(
        OrganizationMembership.objects.filter(user=user).values_list("role", flat=True)
    )

    is_super = OrganizationMembership.Role.SUPERUSER in roles
    is_staff = is_super or OrganizationMembership.Role.ADMIN in roles

    updates: list[str] = []
    if user.is_superuser != is_super:
        user.is_superuser = is_super
        updates.append("is_superuser")
    if user.is_staff != is_staff:
        user.is_staff = is_staff
        updates.append("is_staff")
    if updates:
        user.save(update_fields=updates)
