from __future__ import annotations

import pytest

from apps.platform.accounts.models import Organization, User
from apps.platform.cases.models import Case, CaseMembership
from apps.platform.ui.views.cases.membership import reconcile_case_memberships


@pytest.mark.django_db
def test_reconcile_case_memberships_assigns_roles():
    org = Organization.objects.create(id="org-mem", name="Org")
    case = Case.objects.create(id="case-mem", title="Case", organization=org)

    owner = User.objects.create_user(username="owner", password="pw")
    CaseMembership.objects.create(case=case, user=owner, role=CaseMembership.Role.OWNER)

    reviewer = User.objects.create_user(username="reviewer", password="pw")
    client = User.objects.create_user(username="client", password="pw")
    contributor = User.objects.create_user(username="contrib", password="pw")

    update_fields = reconcile_case_memberships(
        case,
        reviewer_id=str(reviewer.id),
        client_user_id=str(client.id),
        owner_id=str(owner.id),
        contributor_ids=[str(contributor.id)],
    )

    assert set(update_fields) == {"reviewer", "client_user"}
    assert str(case.reviewer_id) == str(reviewer.id)
    assert str(case.client_user_id) == str(client.id)

    owner_members = CaseMembership.objects.filter(case=case, role=CaseMembership.Role.OWNER)
    assert {str(mem.user_id) for mem in owner_members} == {str(owner.id)}

    contributor_members = CaseMembership.objects.filter(case=case, role=CaseMembership.Role.CONTRIBUTOR)
    assert {str(mem.user_id) for mem in contributor_members} == {str(contributor.id)}


@pytest.mark.django_db
def test_reconcile_case_memberships_removes_roles():
    org = Organization.objects.create(id="org-rem", name="Org")
    case = Case.objects.create(id="case-rem", title="Case", organization=org)

    reviewer = User.objects.create_user(username="reviewer-rem", password="pw")
    client = User.objects.create_user(username="client-rem", password="pw")
    CaseMembership.objects.create(case=case, user=reviewer, role=CaseMembership.Role.REVIEWER)
    CaseMembership.objects.create(case=case, user=client, role=CaseMembership.Role.CLIENT)
    case.reviewer = reviewer
    case.client_user = client
    case.save(update_fields=["reviewer", "client_user"])

    update_fields = reconcile_case_memberships(
        case,
        reviewer_id="",
        client_user_id="",
        owner_id="",
        contributor_ids=[],
    )

    assert "reviewer" in update_fields
    assert "client_user" in update_fields
    assert case.reviewer is None
    assert case.client_user is None

    assert CaseMembership.objects.filter(case=case, role=CaseMembership.Role.REVIEWER).count() == 1
    assert CaseMembership.objects.filter(case=case, role=CaseMembership.Role.CLIENT).count() == 1
