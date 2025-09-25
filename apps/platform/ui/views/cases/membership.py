from __future__ import annotations

# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false

from typing import Iterable, List, Set

from apps.platform.accounts.models import OrganizationMembership, User
from apps.platform.cases.models import Case, CaseMembership


def reconcile_case_memberships(
    case: Case,
    *,
    reviewer_id: str,
    client_user_id: str,
    owner_id: str,
    contributor_ids: Iterable[str],
) -> List[str]:
    update_fields: List[str] = []
    contributor_set: Set[str] = {value for value in contributor_ids if value}

    if reviewer_id:
        reviewer = User.objects.filter(pk=reviewer_id).first()
        if reviewer and str(case.reviewer_id) != str(reviewer.pk):
            OrganizationMembership.objects.get_or_create(
                organization=case.organization,
                user=reviewer,
                defaults={"role": OrganizationMembership.Role.MEMBER},
            )
            CaseMembership.objects.get_or_create(
                case=case,
                user=reviewer,
                defaults={"role": CaseMembership.Role.REVIEWER},
            )
            case.reviewer = reviewer
            update_fields.append("reviewer")
    else:
        if case.reviewer_id is not None:
            case.reviewer = None
            update_fields.append("reviewer")

    if client_user_id:
        client_user = User.objects.filter(pk=client_user_id).first()
        if client_user and str(case.client_user_id) != str(client_user.pk):
            OrganizationMembership.objects.get_or_create(
                organization=case.organization,
                user=client_user,
                defaults={"role": OrganizationMembership.Role.MEMBER},
            )
            CaseMembership.objects.get_or_create(
                case=case,
                user=client_user,
                defaults={"role": CaseMembership.Role.CLIENT},
            )
            case.client_user = client_user
            update_fields.append("client_user")
    else:
        if case.client_user_id is not None:
            case.client_user = None
            update_fields.append("client_user")

    current_owner_memberships = case.memberships.filter(role=CaseMembership.Role.OWNER)
    current_owner_ids = {str(m.user_id) for m in current_owner_memberships if m.user_id}

    if owner_id:
        owner_user = User.objects.filter(pk=owner_id).first()
        if owner_user and owner_id not in current_owner_ids:
            OrganizationMembership.objects.get_or_create(
                organization=case.organization,
                user=owner_user,
                defaults={"role": OrganizationMembership.Role.MEMBER},
            )
            membership, _ = CaseMembership.objects.get_or_create(
                case=case,
                user=owner_user,
                defaults={"role": CaseMembership.Role.OWNER},
            )
            if membership.role != CaseMembership.Role.OWNER:
                membership.role = CaseMembership.Role.OWNER
                membership.save(update_fields=["role"])
        demote_ids = {oid for oid in current_owner_ids if oid != owner_id}
    else:
        demote_ids = current_owner_ids

    if demote_ids:
        CaseMembership.objects.filter(
            case=case,
            user_id__in=demote_ids,
            role=CaseMembership.Role.OWNER,
        ).update(role=CaseMembership.Role.CONTRIBUTOR)

    existing_contributors = {
        str(m.user_id)
        for m in case.memberships.filter(role=CaseMembership.Role.CONTRIBUTOR)
        if m.user_id
    }
    to_add = contributor_set - existing_contributors
    to_remove = existing_contributors - contributor_set

    if to_add:
        for uid in to_add:
            user_obj = User.objects.filter(pk=uid).first()
            if not user_obj:
                continue
            OrganizationMembership.objects.get_or_create(
                organization=case.organization,
                user=user_obj,
                defaults={"role": OrganizationMembership.Role.MEMBER},
            )
            CaseMembership.objects.get_or_create(
                case=case,
                user=user_obj,
                defaults={"role": CaseMembership.Role.CONTRIBUTOR},
            )

    if to_remove:
        CaseMembership.objects.filter(
            case=case,
            role=CaseMembership.Role.CONTRIBUTOR,
            user_id__in=list(to_remove),
        ).delete()

    return list(dict.fromkeys(update_fields))
