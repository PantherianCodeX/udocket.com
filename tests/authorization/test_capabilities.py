from __future__ import annotations

from rest_framework.test import APIRequestFactory

from apps.platform.accounts.models import Organization, User
from apps.platform.artifacts.models import FieldVisibilityRule
from apps.platform.authorization.capabilities import allowed_field_actions, has_capability, role_capabilities
from apps.platform.authorization.models import PermissionPreset, PresetCapability, PresetFieldPolicy, Role, RoleCapability
from apps.platform.cases.models import Case, CaseMembership
from apps.platform.cases.serializers import CaseSerializer


def test_role_capabilities_scoped_by_organization(db):
    org = Organization.objects.create(id="ORG-CAPS", name="Caps Org")
    role = Role.objects.create(name="Owner", organization=org)
    RoleCapability.objects.create(role=role, capability="case.share")

    caps_with_org = role_capabilities("OWNER", organization_id=org.id)
    assert "case.share" in caps_with_org
    caps_global = role_capabilities("OWNER")
    assert "case.share" not in caps_global


def test_allowed_field_actions_uses_org_presets(db):
    org = Organization.objects.create(id="ORG-CAPS2", name="Caps Org 2")
    preset = PermissionPreset.objects.create(name="Owner Core Org", organization=org)
    role = Role.objects.create(name="Owner", organization=org)
    role.presets.add(preset)
    PresetFieldPolicy.objects.create(
        preset=preset,
        resource="ARTIFACT",
        type="SUMMARY",
        field_name="path",
        actions=["view", "download"],
    )

    acts = allowed_field_actions(
        "OWNER",
        "SUMMARY",
        "path",
        organization_id=org.id,
        resource="ARTIFACT",
    )
    assert acts == {"view", "download"}


def test_has_capability_honors_membership_organization(db):
    org = Organization.objects.create(id="ORG-CAPS3", name="Caps Org 3")
    case = Case.objects.create(id="CASE-CAP", title="Case Cap", organization=org)
    user = User.objects.create_user(username="tenant-user", password="x")
    role = Role.objects.create(name="Contributor", organization=org)
    RoleCapability.objects.create(role=role, capability="case.update")
    CaseMembership.objects.create(case=case, user=user, role="CONTRIBUTOR")
    # Attach preset so global contributor defaults remain unchanged
    preset = PermissionPreset.objects.create(name="Contrib Org", organization=org)
    role.presets.add(preset)
    PresetCapability.objects.create(preset=preset, capability="artifact.download")

    assert has_capability(user, case.id, "case.update") is True
    assert has_capability(user, case.id, "artifact.download") is True
    # Another case without membership should fail
    other_case = Case.objects.create(id="CASE-CAP-2", title="Other", organization=org)
    assert has_capability(user, other_case.id, "case.update") is False


def test_case_field_visibility_respects_rules(db):
    org = Organization.objects.create(id="ORG-CAPS4", name="Caps Org 4")
    case = Case.objects.create(id="CASE-CAP3", title="Sensitive", organization=org)
    user = User.objects.create_user(username="client-user", password="x")
    CaseMembership.objects.create(case=case, user=user, role="CLIENT")

    FieldVisibilityRule.objects.create(
        resource=FieldVisibilityRule.Resource.CASE,
        type="CASE",
        field_name="organization",
        allowed_roles=["OWNER"],
    )

    factory = APIRequestFactory()
    request = factory.get("/cases/")
    request.user = user
    serializer = CaseSerializer(instance=case, context={"request": request})
    data = serializer.data
    assert "organization" not in data
    assert data["title"] == "Sensitive"
