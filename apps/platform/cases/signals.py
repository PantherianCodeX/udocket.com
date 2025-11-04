from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver
from guardian.shortcuts import assign_perm

from apps.platform.cases.models import CaseMembership

ROLE_PERMS = {
    "OWNER": [
        "view_case",
        "change_case",
    ],
    "CONTRIBUTOR": [
        "view_case",
    ],
    "REVIEWER": [
        "view_case",
    ],
    "AUDITOR": [
        "view_case",
    ],
    "EXTERNAL": [
        "view_case",
    ],
}


@receiver(post_save, sender=CaseMembership)
def grant_case_perms(
    sender, instance: CaseMembership, created: bool, **kwargs
):  # pragma: no cover - side-effect
    if not created:
        return
    perms = ROLE_PERMS.get(instance.role, [])
    for p in perms:
        try:
            assign_perm(p, instance.user, instance.case)
        except Exception:
            pass
