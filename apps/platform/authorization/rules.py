from __future__ import annotations

import rules
from apps.platform.cases.models import CaseMembership


@rules.predicate
def is_case_member(user, case) -> bool:
    try:
        if not user or not getattr(user, "is_authenticated", False):
            return False
        return CaseMembership.objects.filter(case=case, user=user).exists()
    except Exception:
        return False


@rules.predicate
def is_case_owner(user, case) -> bool:
    try:
        if not user or not getattr(user, "is_authenticated", False):
            return False
        return CaseMembership.objects.filter(case=case, user=user, role=CaseMembership.Role.OWNER).exists()
    except Exception:
        return False


@rules.predicate
def can_contribute(user, case) -> bool:
    try:
        if not user or not getattr(user, "is_authenticated", False):
            return False
        return CaseMembership.objects.filter(
            case=case,
            user=user,
            role__in=[CaseMembership.Role.OWNER, CaseMembership.Role.CONTRIBUTOR],
        ).exists()
    except Exception:
        return False


# Example permissions (not yet wired to Django perms system)
rules.add_perm("cases.view_case", is_case_member)
rules.add_perm("cases.change_case", can_contribute)
