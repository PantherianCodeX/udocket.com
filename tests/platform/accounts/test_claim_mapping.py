from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.platform.accounts.models import Organization, OrganizationMembership
from apps.platform.accounts.utils import apply_claim_mappings
from apps.platform.cases.models import Case, CaseMembership


@pytest.mark.django_db
def test_apply_claim_mappings_syncs_organizations(settings):
    settings.OIDC_ORG_CLAIM = "organizations"
    settings.OIDC_ORG_ID_FIELD = "id"
    settings.OIDC_ORG_NAME_FIELD = "name"
    settings.OIDC_ORG_ROLES_FIELD = "roles"
    settings.OIDC_ORG_DEFAULT_ROLE = OrganizationMembership.Role.MEMBER
    settings.OIDC_ORG_ROLE_MAP = {"admin": "ADMIN", "member": "MEMBER", "superuser": "SUPERUSER"}
    user = get_user_model().objects.create_user(username="kc-user")

    claims = {
        "organizations": [
            {"id": "org-alpha", "name": "Alpha Org", "roles": ["admin"]},
            {"id": "org-beta", "name": "Beta Org", "roles": ["member"]},
        ]
    }
    apply_claim_mappings(user, claims, sync_cases=False)

    memberships = OrganizationMembership.objects.filter(user=user).select_related("organization")
    assert memberships.count() == 2
    alpha = memberships.get(organization__kc_organization_id="org-alpha")
    assert alpha.role == OrganizationMembership.Role.ADMIN
    beta = memberships.get(organization__kc_organization_id="org-beta")
    assert beta.role == OrganizationMembership.Role.MEMBER

    # Remove alpha from claims; membership should be removed
    claims = {
        "organizations": [
            {"id": "org-beta", "name": "Beta Org", "roles": ["member"]},
        ]
    }
    apply_claim_mappings(user, claims, sync_cases=False)
    memberships = OrganizationMembership.objects.filter(user=user)
    assert memberships.count() == 1
    assert memberships.first().organization.kc_organization_id == "org-beta"


@pytest.mark.django_db
def test_apply_claim_mappings_syncs_cases(settings):
    settings.OIDC_ORG_CLAIM = "organizations"
    settings.OIDC_CASE_MEMBERSHIPS_CLAIM = "cases"
    settings.OIDC_CASE_ID_FIELD = "id"
    settings.OIDC_CASE_ROLE_FIELD = "role"
    settings.OIDC_CASE_ROLE_MAP = {"owner": "OWNER", "reviewer": "REVIEWER"}
    settings.OIDC_CASE_DEFAULT_ROLE = CaseMembership.Role.CONTRIBUTOR
    settings.OIDC_SYNC_MEMBERSHIPS = True

    org = Organization.objects.create(name="Org One", kc_organization_id="org-one")
    case = Case.objects.create(id="CASE-001", title="Sample", organization=org)
    user = get_user_model().objects.create_user(username="kc-user")

    claims = {
        "organizations": [
            {"id": "org-one", "name": "Org One", "roles": ["owner"]},
        ],
        "cases": [
            {"id": case.id, "role": "reviewer"},
        ],
    }
    apply_claim_mappings(user, claims, sync_cases=True)

    membership = CaseMembership.objects.get(user=user, case=case)
    assert membership.role == CaseMembership.Role.REVIEWER
    org_membership = OrganizationMembership.objects.get(user=user, organization=org)
    assert org_membership.role == OrganizationMembership.Role.ADMIN
