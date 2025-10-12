from __future__ import annotations

import pytest

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.platform.accounts.models import Organization, OrganizationMembership
from apps.platform.authorization.models import PermissionPreset, Role
from tests._typing import DatabaseFixture, SettingsFixture


def test_authz_registry_endpoint(db: DatabaseFixture, settings: SettingsFixture):
    settings.PLATFORM_DEV_OPEN = True
    c = APIClient()
    r = c.get("/api/v1/authz/registry/")
    assert r.status_code == 200
    data = r.json()
    # Expect common artifact types present
    assert "TRANSCRIPT" in data and "path" in data["TRANSCRIPT"]


def test_authz_presets_and_roles_endpoints(db: DatabaseFixture, settings: SettingsFixture):
    settings.PLATFORM_DEV_OPEN = True
    c = APIClient()
    rp = c.get("/api/v1/authz/presets/")
    rr = c.get("/api/v1/authz/roles/")
    assert rp.status_code == 200 and rr.status_code == 200
    presets = rp.json().get("presets")
    roles = rr.json().get("roles")
    assert isinstance(presets, list)
    assert isinstance(roles, list)
    if presets:
        assert "organization" in presets[0]
        assert "uuid" in presets[0]
    if roles:
        assert "organization" in roles[0]
        assert "uuid" in roles[0]


@pytest.mark.django_db
def test_authz_presets_require_auth_when_closed(settings: SettingsFixture):
    settings.PLATFORM_DEV_OPEN = False
    c = APIClient()
    resp = c.get("/api/v1/authz/presets/")
    assert resp.status_code == 401


@pytest.mark.django_db
def test_authz_endpoints_scope_to_user_org(settings: SettingsFixture):
    settings.PLATFORM_DEV_OPEN = False
    org_a = Organization.objects.create(name="API Org A")
    org_b = Organization.objects.create(name="API Org B")

    preset_a = PermissionPreset.objects.create(name="API Preset A", organization=org_a)
    preset_b = PermissionPreset.objects.create(name="API Preset B", organization=org_b)
    role_a = Role.objects.create(name="API Role A", organization=org_a)
    role_b = Role.objects.create(name="API Role B", organization=org_b)
    role_a.presets.add(preset_a)
    role_b.presets.add(preset_b)

    user = get_user_model().objects.create_user(username="api-user", password="secret")
    OrganizationMembership.objects.create(user=user, organization=org_a)

    c = APIClient()
    c.force_authenticate(user=user)

    rp = c.get("/api/v1/authz/presets/")
    rr = c.get("/api/v1/authz/roles/")

    assert rp.status_code == 200
    assert rr.status_code == 200

    preset_names = {p["name"] for p in rp.json().get("presets", [])}
    role_names = {r["name"] for r in rr.json().get("roles", [])}

    assert "API Preset A" in preset_names
    assert "API Role A" in role_names
    assert "API Preset B" not in preset_names
    assert "API Role B" not in role_names