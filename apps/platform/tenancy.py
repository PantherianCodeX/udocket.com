from __future__ import annotations

"""Shared helpers for tenant-aware filtering."""

from typing import Sequence

from django.apps import apps
from django.conf import settings
from django.db.models import Q, QuerySet

__all__ = [
    "organization_ids_for_user",
    "case_ids_for_user",
    "scope_cases",
    "scope_jobs",
    "scope_artifacts",
    "accessible_organization_ids",
]


def _is_dev_open() -> bool:
    return bool(getattr(settings, "PLATFORM_DEV_OPEN", False))


def organization_ids_for_user(user) -> Sequence[str]:
    if not user or not getattr(user, "is_authenticated", False):
        return []
    OrganizationMembership = apps.get_model("accounts", "OrganizationMembership")
    return list(
        OrganizationMembership.objects.filter(user=user).values_list("organization_id", flat=True)
    )


def case_ids_for_user(user) -> Sequence[str]:
    if not user or not getattr(user, "is_authenticated", False):
        return []
    CaseMembership = apps.get_model("cases", "CaseMembership")
    return list(CaseMembership.objects.filter(user=user).values_list("case_id", flat=True))


def _return_when_unauthenticated(qs: QuerySet, user) -> QuerySet:
    if user and getattr(user, "is_authenticated", False):
        return qs
    return qs if _is_dev_open() else qs.none()


def scope_cases(qs: QuerySet, user) -> QuerySet:
    qs = _return_when_unauthenticated(qs, user)
    if not user or not getattr(user, "is_authenticated", False):
        return qs
    org_ids = organization_ids_for_user(user)
    case_ids = case_ids_for_user(user)
    filters = Q()
    if case_ids:
        filters |= Q(id__in=case_ids)
    if org_ids:
        filters |= Q(organization_id__in=org_ids)
    if not filters:
        return qs.none()
    return qs.filter(filters).distinct()


def scope_jobs(qs: QuerySet, user) -> QuerySet:
    qs = _return_when_unauthenticated(qs, user)
    if not user or not getattr(user, "is_authenticated", False):
        return qs
    org_ids = organization_ids_for_user(user)
    case_ids = case_ids_for_user(user)
    filters = Q()
    if case_ids:
        filters |= Q(case_id__in=case_ids)
    if org_ids:
        filters |= Q(organization_id__in=org_ids)
        filters |= Q(case__organization_id__in=org_ids)
    if not filters:
        return qs.none()
    return qs.filter(filters).distinct()


def scope_artifacts(qs: QuerySet, user) -> QuerySet:
    qs = _return_when_unauthenticated(qs, user)
    if not user or not getattr(user, "is_authenticated", False):
        return qs
    org_ids = organization_ids_for_user(user)
    case_ids = case_ids_for_user(user)
    filters = Q()
    if case_ids:
        filters |= Q(case_id__in=case_ids)
        filters |= Q(case_fk__id__in=case_ids)
    if org_ids:
        filters |= Q(organization_id__in=org_ids)
        filters |= Q(case_fk__organization_id__in=org_ids)
    if not filters:
        return qs.none()
    return qs.filter(filters).distinct()


def accessible_organization_ids(user) -> set[str]:
    """Return organization IDs the user may access.

    Superusers gain access to all organizations, authenticated users receive
    organizations via direct membership and any cases they are a member of.
    When PLATFORM_DEV_OPEN is enabled, unauthenticated access falls back to
    all organizations to preserve local developer workflows.
    """

    if _is_dev_open() and (not user or not getattr(user, "is_authenticated", False)):
        Organization = apps.get_model("accounts", "Organization")
        return set(str(org_id) for org_id in Organization.objects.values_list("id", flat=True))

    if not user or not getattr(user, "is_authenticated", False):
        return set()

    if getattr(user, "is_superuser", False):
        Organization = apps.get_model("accounts", "Organization")
        return set(str(org_id) for org_id in Organization.objects.values_list("id", flat=True))

    org_ids = set(str(org_id) for org_id in organization_ids_for_user(user))
    case_ids = case_ids_for_user(user)
    if case_ids:
        Case = apps.get_model("cases", "Case")
        case_orgs = (
            Case.objects.filter(id__in=case_ids)
            .exclude(organization_id__isnull=True)
            .values_list("organization_id", flat=True)
        )
        org_ids.update(str(org_id) for org_id in case_orgs if org_id)
    return org_ids
