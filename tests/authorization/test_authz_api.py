from __future__ import annotations

from rest_framework.test import APIClient


def test_authz_registry_endpoint(db, settings):
    settings.PLATFORM_DEV_OPEN = True
    c = APIClient()
    r = c.get("/api/v1/authz/registry/")
    assert r.status_code == 200
    data = r.json()
    # Expect common artifact types present
    assert "TRANSCRIPT" in data and "path" in data["TRANSCRIPT"]


def test_authz_presets_and_roles_endpoints(db, settings):
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
