from __future__ import annotations

from apps.platform.accounts.models import Organization, User
from apps.platform.authorization.capabilities import has_capability, role_capabilities
from apps.platform.authorization.models import Role, RoleCapability
from apps.platform.cases.models import Case, CaseMembership


def test_role_capabilities_scoped_by_organization(db):
    org = Organization.objects.create(name="Caps Org")
    role = Role.objects.create(name="Owner", organization=org)
    RoleCapability.objects.create(role=role, capability="case.share")

    caps_with_org = role_capabilities("OWNER", organization_id=str(org.id))
    assert "case.share" in caps_with_org
    caps_global = role_capabilities("OWNER")
    assert "case.share" not in caps_global

def test_has_capability_honors_membership_organization(db):
    org = Organization.objects.create(name="Caps Org 3")
    case = Case.objects.create(id="CASE-CAP", title="Case Cap", organization=org)
    user = User.objects.create_user(username="tenant-user", password="x")
    role = Role.objects.create(name="Contributor", organization=org)
    RoleCapability.objects.create(role=role, capability="case.update")
    CaseMembership.objects.create(case=case, user=user, role="CONTRIBUTOR")
    assert has_capability(user, case.id, "case.update") is True
    # Another case without membership should fail
    other_case = Case.objects.create(id="CASE-CAP-2", title="Other", organization=org)
    assert has_capability(user, other_case.id, "case.update") is False
