from __future__ import annotations

import pytest

from django.urls import reverse

from apps.platform.authorization.models import (
    PermissionPreset,
    PresetCapability,
    PresetFieldPolicy,
    Role,
)


@pytest.mark.django_db
def test_permissions_overview_page(client):
    preset = PermissionPreset.objects.create(slug="demo", name="Demo Preset")
    PresetCapability.objects.create(preset=preset, capability="case.view")
    PresetFieldPolicy.objects.create(
        preset=preset,
        type="TRANSCRIPT",
        field_name="path",
        actions=["view"],
    )
    role = Role.objects.create(slug="DEMO", name="Demo Role")
    role.presets.add(preset)

    resp = client.get(reverse("ui-permissions"))
    assert resp.status_code == 200
    content = resp.content.decode()
    assert "Permission Catalog" in content
    assert "Demo Preset" in content
    assert "Demo Role" in content
