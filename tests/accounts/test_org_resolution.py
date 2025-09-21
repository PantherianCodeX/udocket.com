from __future__ import annotations

import pytest

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware

from apps.platform.accounts.models import Organization, OrganizationMembership
from apps.platform.accounts.utils import (
    resolve_request_organization,
    set_active_admin_org_id,
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
    org = Organization.objects.create(id="org-hdr", name="Header Org")
    other_org = Organization.objects.create(id="org-other", name="Other Org")
    user = get_user_model().objects.create_user(username="alice", password="x")
    OrganizationMembership.objects.create(user=user, organization=org)

    request = _req(user=user, headers={"HTTP_X_ORGANIZATION_ID": org.id})
    resolved = resolve_request_organization(request)
    assert resolved == org

    spoofed = _req(user=user, headers={"HTTP_X_ORGANIZATION_ID": other_org.id})
    spoofed_org = resolve_request_organization(spoofed)
    assert spoofed_org == org


@pytest.mark.django_db
def test_resolve_organization_uses_admin_selection(settings):
    settings.PLATFORM_DEV_OPEN = False
    org = Organization.objects.create(id="org-session", name="Session Org")
    user = get_user_model().objects.create_user(username="bob", password="x")
    OrganizationMembership.objects.create(user=user, organization=org)

    request = _req(user=user)
    set_active_admin_org_id(request, org.id)
    request.session.save()

    resolved = resolve_request_organization(request)
    assert resolved == org


@pytest.mark.django_db
def test_resolve_organization_superuser_accepts_header(settings):
    settings.PLATFORM_DEV_OPEN = False
    org = Organization.objects.create(id="org-super", name="Super Org")
    su = get_user_model().objects.create_superuser(username="root", password="x")

    request = _req(user=su, headers={"HTTP_X_ORGANIZATION_ID": org.id})
    resolved = resolve_request_organization(request)
    assert resolved == org
