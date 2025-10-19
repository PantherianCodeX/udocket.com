# pyright: strict

from __future__ import annotations

import logging
import uuid
from collections.abc import Iterable as IterableABC, Mapping as MappingABC
from typing import Any, Optional, Sequence

from django.db import models, transaction
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest
from django.conf import settings

from apps.platform.accounts.models import Organization, OrganizationMembership
from apps.platform.cases.models import Case, CaseMembership

AdminOrgChoice = dict[str, str]

_SESSION_KEY = "admin_active_org_id"
logger = logging.getLogger("apps.platform.accounts.utils")


def user_accessible_organizations(user: Any) -> models.QuerySet[Organization]:
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
    org_ids: set[uuid.UUID] = set()
    for raw_value in list(direct_ids) + list(case_ids):
        if not raw_value:
            continue
        try:
            org_ids.add(uuid.UUID(str(raw_value)))
        except (ValueError, TypeError, AttributeError):
            continue
    if not org_ids:
        return Organization.objects.none()
    return Organization.objects.filter(id__in=org_ids).order_by("name")


def user_accessible_org_ids(user: Any) -> list[str]:
    return [str(org_id) for org_id in user_accessible_organizations(user).values_list("id", flat=True)]


def get_active_admin_org_id(request: HttpRequest) -> Optional[str]:
    org = get_active_admin_org(request)
    return str(org.id) if org else None


def get_active_admin_org(request: HttpRequest) -> Optional[Organization]:
    session = getattr(request, "session", None)
    if session is None:
        request.admin_active_org = None  # type: ignore[attr-defined]
        request.admin_active_org_id = None  # type: ignore[attr-defined]
        return None

    user = getattr(request, "user", None)
    orgs_qs = user_accessible_organizations(user)
    accessible = list(orgs_qs)
    stored = session.get(_SESSION_KEY)
    if stored and stored not in {str(org.id) for org in accessible}:
        logger.warning(
            "admin session organization no longer permitted", extra={"org_id": stored}
        )
        stored = None
    if stored:
        for org in accessible:
            if str(org.id) == stored:
                request.admin_active_org = org  # type: ignore[attr-defined]
                request.admin_active_org_id = stored  # type: ignore[attr-defined]
                return org
    request.admin_active_org = None  # type: ignore[attr-defined]
    request.admin_active_org_id = None  # type: ignore[attr-defined]
    if not accessible:
        session.pop(_SESSION_KEY, None)
    return None


def set_active_admin_org_id(request: HttpRequest, org_id: Optional[str]) -> None:
    session = getattr(request, "session", None)
    if session is None:
        return
    if org_id:
        session[_SESSION_KEY] = str(org_id)
    else:
        session.pop(_SESSION_KEY, None)
    session.modified = True


def admin_org_choices(request: HttpRequest) -> list[AdminOrgChoice]:
    orgs = user_accessible_organizations(getattr(request, "user", None))
    return [{"id": str(org.id), "name": org.name} for org in orgs]


def resolve_request_organization(
    request: HttpRequest, *, required: bool = True
) -> Optional[Organization]:
    """Resolve the active organization for the current request.

    Preference order:
      1. Explicit header (`ORG_HEADER_NAME`) when the authenticated user is a
         member (or superuser).
      2. Admin-selected organization stored in session.

    Raises PermissionDenied when `required` and no organization can be
    determined. No implicit organization fallbacks are performed.
    """

    user = getattr(request, "user", None)
    header_name = getattr(settings, "ORG_HEADER_NAME", "HTTP_X_ORGANIZATION_ID")
    header_org_id = request.META.get(header_name)

    def _get_org(org_id: str | None) -> Optional[Organization]:
        if not org_id:
            return None
        try:
            parsed = uuid.UUID(str(org_id))
        except (TypeError, ValueError):
            return None
        return Organization.objects.filter(id=parsed).first()

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

    # Fallback: when user has exactly one accessible organization, prefer it.
    if user and getattr(user, "is_authenticated", False):
        orgs_qs = user_accessible_organizations(user)
        try:
            count = orgs_qs.count()
        except Exception:  # pragma: no cover - defensive
            count = 0
        if count == 1:
            only_org = next(iter(orgs_qs), None)
            if isinstance(only_org, Organization):
                return only_org

    if required:
        raise PermissionDenied("Organization context is required for this action.")
    return None


def sync_user_access_flags(user: Any) -> None:
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


def _normalize_roles(raw_roles: Any) -> list[str]:
    if raw_roles is None:
        return []
    if isinstance(raw_roles, str):
        role = raw_roles.strip()
        return [role] if role else []
    if isinstance(raw_roles, IterableABC):
        roles: list[str] = []
        for item in raw_roles:
            text = str(item).strip()
            if text:
                roles.append(text)
        return roles
    return []


def _normalize_entries(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, MappingABC):
        return [value]
    if isinstance(value, IterableABC) and not isinstance(value, (str, bytes, bytearray)):
        return list(value)
    return [value]


def _map_role(remote_roles: Sequence[str], mapping: MappingABC[str, str], default_role: str, *, valid_roles: set[str]) -> str:
    for role in remote_roles:
        key = role.strip().lower()
        if not key:
            continue
        mapped = mapping.get(key)
        if mapped and mapped in valid_roles:
            return mapped
    if default_role in valid_roles:
        return default_role
    return next(iter(valid_roles))


def sync_organization_memberships_from_claims(user: Any, claims: MappingABC[str, Any]) -> None:
    claim_name = getattr(settings, "OIDC_ORG_CLAIM", "organizations") or "organizations"
    raw_entries = claims.get(claim_name)
    entries = _normalize_entries(raw_entries)
    if not entries:
        return

    org_id_field = getattr(settings, "OIDC_ORG_ID_FIELD", "id") or "id"
    org_name_field = getattr(settings, "OIDC_ORG_NAME_FIELD", "name") or "name"
    org_roles_field = getattr(settings, "OIDC_ORG_ROLES_FIELD", "roles") or "roles"
    default_role = str(getattr(settings, "OIDC_ORG_DEFAULT_ROLE", OrganizationMembership.Role.MEMBER)).upper()
    role_map_raw = getattr(settings, "OIDC_ORG_ROLE_MAP", {})
    if isinstance(role_map_raw, MappingABC):
        role_map = {str(k).lower(): str(v).upper() for k, v in role_map_raw.items()}
    else:
        role_map = {}
    valid_roles = {choice for choice, _ in OrganizationMembership.Role.choices}

    active_ids: set[uuid.UUID] = set()
    with transaction.atomic():
        for entry in entries:
            org_id_value: str | None = None
            org_name_value: str | None = None
            remote_roles: list[str] = []

            if isinstance(entry, MappingABC):
                raw_id = entry.get(org_id_field) or entry.get("id")
                if raw_id is not None:
                    org_id_value = str(raw_id).strip()
                raw_name = entry.get(org_name_field)
                if raw_name:
                    org_name_value = str(raw_name).strip()
                remote_roles = _normalize_roles(entry.get(org_roles_field))
            else:
                text = str(entry).strip()
                if ":" in text:
                    org_id_value, _, role_part = text.partition(":")
                    remote_roles = _normalize_roles(role_part.split("|"))
                else:
                    org_id_value = text

            if not org_id_value:
                logger.debug("Skipping organization entry without identifier", extra={"entry": entry})
                continue

            organization = Organization.objects.filter(kc_organization_id=org_id_value).first()
            if not organization and org_name_value:
                organization = Organization.objects.filter(kc_organization_id__isnull=True, name=org_name_value).first()
            created = False
            if not organization:
                organization = Organization(name=org_name_value or org_id_value, display_name=org_name_value or "", kc_organization_id=org_id_value)
                organization.save()
                created = True
            updates: list[str] = []
            if organization.kc_organization_id != org_id_value:
                organization.kc_organization_id = org_id_value
                updates.append("kc_organization_id")
            if org_name_value:
                if organization.name != org_name_value:
                    organization.name = org_name_value
                    updates.append("name")
                if not organization.display_name or organization.display_name != org_name_value:
                    organization.display_name = org_name_value
                    updates.append("display_name")
            if updates:
                organization.save(update_fields=list(dict.fromkeys(updates)))
            if created:
                logger.info(
                    "Created organization from Keycloak",
                    extra={"kc_id": org_id_value, "org_name": organization.name},
                )

            local_role = _map_role(remote_roles, role_map, default_role, valid_roles=valid_roles)
            membership, created = OrganizationMembership.objects.get_or_create(
                organization=organization,
                user=user,
                defaults={"role": local_role},
            )
            if not created and membership.role != local_role:
                membership.role = local_role
                membership.save(update_fields=["role"])
            active_ids.add(organization.id)

        if active_ids:
            OrganizationMembership.objects.filter(user=user).exclude(organization_id__in=active_ids).delete()


def sync_case_memberships_from_claims(user: Any, claims: MappingABC[str, Any]) -> None:
    claim_name = getattr(settings, "OIDC_CASE_MEMBERSHIPS_CLAIM", "").strip()
    if not claim_name:
        return
    raw_entries = claims.get(claim_name)
    entries = _normalize_entries(raw_entries)
    if not entries:
        return

    case_id_field = getattr(settings, "OIDC_CASE_ID_FIELD", "id") or "id"
    case_role_field = getattr(settings, "OIDC_CASE_ROLE_FIELD", "role") or "role"
    default_role = str(getattr(settings, "OIDC_CASE_DEFAULT_ROLE", CaseMembership.Role.CONTRIBUTOR)).upper()
    role_map_raw = getattr(settings, "OIDC_CASE_ROLE_MAP", {})
    if isinstance(role_map_raw, MappingABC):
        role_map = {str(k).lower(): str(v).upper() for k, v in role_map_raw.items()}
    else:
        role_map = {}
    valid_roles = {choice for choice, _ in CaseMembership.Role.choices}

    active_case_ids: set[str] = set()
    with transaction.atomic():
        for entry in entries:
            case_id_value: str | None = None
            remote_roles: list[str] = []

            if isinstance(entry, MappingABC):
                raw_id = entry.get(case_id_field) or entry.get("id")
                if raw_id:
                    case_id_value = str(raw_id).strip()
                remote_roles = _normalize_roles(entry.get(case_role_field))
            else:
                text = str(entry).strip()
                if ":" in text:
                    case_id_value, _, role_part = text.partition(":")
                    remote_roles = _normalize_roles(role_part.split("|"))
                else:
                    case_id_value = text

            if not case_id_value:
                logger.debug("Skipping case membership entry without identifier", extra={"entry": entry})
                continue

            try:
                case = Case.objects.get(pk=case_id_value)
            except Case.DoesNotExist:
                logger.warning("Case from claim not found locally", extra={"case_id": case_id_value})
                continue

            local_role = _map_role(remote_roles, role_map, default_role, valid_roles=valid_roles)
            membership, created = CaseMembership.objects.get_or_create(
                case=case,
                user=user,
                defaults={"role": local_role},
            )
            if not created and membership.role != local_role:
                membership.role = local_role
                membership.save(update_fields=["role"])
            active_case_ids.add(case.id)

        if active_case_ids:
            CaseMembership.objects.filter(user=user).exclude(case_id__in=active_case_ids).delete()


def apply_claim_mappings(user: Any, claims: MappingABC[str, Any], *, sync_cases: bool) -> None:
    sync_organization_memberships_from_claims(user, claims)
    if sync_cases:
        sync_case_memberships_from_claims(user, claims)
    sync_user_access_flags(user)
