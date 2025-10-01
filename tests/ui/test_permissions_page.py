from __future__ import annotations

import pytest

from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.platform.accounts.models import Organization, OrganizationMembership
from apps.platform.authorization.models import PermissionPreset, PresetCapability, Role


@pytest.mark.django_db
def test_permissions_overview_scopes_by_organization(client, settings):
    settings.PLATFORM_DEV_OPEN = False

    org_a = Organization.objects.create(id="org-a", name="Org A")
    org_b = Organization.objects.create(id="org-b", name="Org B")

    preset_a = PermissionPreset.objects.create(name="Demo Preset", organization=org_a)
    PresetCapability.objects.create(preset=preset_a, capability="case.view")
    role_a = Role.objects.create(name="Demo Role", organization=org_a)
    role_a.presets.add(preset_a)

    preset_b = PermissionPreset.objects.create(name="Other Preset", organization=org_b)
    PresetCapability.objects.create(preset=preset_b, capability="case.view")
    role_b = Role.objects.create(name="Other Role", organization=org_b)
    role_b.presets.add(preset_b)

    user = get_user_model().objects.create_user(username="alice", password="secret")
    OrganizationMembership.objects.create(user=user, organization=org_a)
    client.force_login(user)

    resp = client.get(reverse("ui-permissions"))
    assert resp.status_code == 200
    content = resp.content.decode()
    assert "Permission Catalog" in content
    assert "Demo Preset" in content
    assert "Demo Role" in content
    assert "Org A" in content
    assert "Other Preset" not in content
    assert "Other Role" not in content


@pytest.mark.django_db
def test_permissions_overview_requires_auth_when_closed(client, settings):
    settings.PLATFORM_DEV_OPEN = False
    resp = client.get(reverse("ui-permissions"))
    assert resp.status_code == 302
    assert settings.LOGIN_URL in resp.headers.get("Location", "")
