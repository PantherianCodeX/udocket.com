from __future__ import annotations

import pytest

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware

from apps.platform.accounts.models import Organization, OrganizationMembership
from apps.platform.accounts.utils import (
    resolve_request_organization,
    set_active_admin_org_id,
    user_accessible_organizations,
)


def _req(user=None, headers=None):
    factory = RequestFactory()
    request = factory.get("/", **(headers or {}))
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(request)
    request.session.save()
    request.user = user
    return request


@pytest.mark.django_db
def test_resolve_organization_header_requires_membership(settings):
    settings.PLATFORM_DEV_OPEN = False
    org = Organization.objects.create(name="Header Org")
    other_org = Organization.objects.create(name="Other Org")
    user = get_user_model().objects.create_user(username="alice", password="x")
    OrganizationMembership.objects.create(user=user, organization=org)

    request = _req(user=user, headers={"HTTP_X_ORGANIZATION_ID": str(org.id)})
    resolved = resolve_request_organization(request)
    assert resolved == org

    spoofed = _req(user=user, headers={"HTTP_X_ORGANIZATION_ID": str(other_org.id)})
    spoofed_org = resolve_request_organization(spoofed)
    assert spoofed_org == org


@pytest.mark.django_db
def test_resolve_organization_uses_admin_selection(settings):
    settings.PLATFORM_DEV_OPEN = False
    org = Organization.objects.create(name="Session Org")
    user = get_user_model().objects.create_user(username="bob", password="x")
    OrganizationMembership.objects.create(user=user, organization=org)

    request = _req(user=user)
    set_active_admin_org_id(request, str(org.id))
    request.session.save()

    resolved = resolve_request_organization(request)
    assert resolved == org


@pytest.mark.django_db
def test_resolve_organization_superuser_accepts_header(settings):
    settings.PLATFORM_DEV_OPEN = False
    org = Organization.objects.create(name="Super Org")
    su = get_user_model().objects.create_user(username="root", password="x")
    OrganizationMembership.objects.create(
        user=su,
        organization=org,
        role=OrganizationMembership.Role.SUPERUSER,
    )

    request = _req(user=su, headers={"HTTP_X_ORGANIZATION_ID": str(org.id)})
    resolved = resolve_request_organization(request)
    assert resolved == org


@pytest.mark.django_db
def test_superuser_membership_sees_all_orgs(settings):
    settings.PLATFORM_DEV_OPEN = False
    org_a = Organization.objects.create(name="Org A")
    org_b = Organization.objects.create(name="Org B")
    user = get_user_model().objects.create_user(username="power", password="x")
    OrganizationMembership.objects.create(
        user=user,
        organization=org_a,
        role=OrganizationMembership.Role.SUPERUSER,
    )

    request = _req(user=user)
    resolved = resolve_request_organization(request, required=False)
    assert resolved is None
    org_ids = {org.id for org in user_accessible_organizations(user)}
    assert {org_a.id, org_b.id}.issubset(org_ids)
