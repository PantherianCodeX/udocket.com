from __future__ import annotations

from typing import Iterable
from django.conf import settings
from apps.platform.cases.models import CaseMembership
from apps.platform.authorization.models import Role, RoleCapability


# Hard-coded defaults as a safe baseline; DB can override/extend
DEFAULT_CAPS: dict[str, set[str]] = {
    "OWNER": {
        "case.view", "case.update", "job.create",
        "artifact.view", "artifact.download",
        "artifact.field.path.view", "artifact.field.checksum.view",
    },
    "CONTRIBUTOR": {
        "case.view", "case.update", "job.create",
        "artifact.view", "artifact.download",
        "artifact.field.path.view", "artifact.field.checksum.view",
    },
    "REVIEWER": {
        "case.view", "artifact.view", "artifact.field.checksum.view",
    },
    "AUDITOR": {
        "case.view", "artifact.view", "artifact.field.checksum.view",
    },
    "EXTERNAL": {
        "case.view", "artifact.view",
    },
}


def _caps_from_db(role_slug: str) -> set[str]:
    caps = set()
    try:
        r = Role.objects.filter(slug=role_slug).first()
        if not r:
            return caps
        caps.update(RoleCapability.objects.filter(role=r).values_list("capability", flat=True))
    except Exception:
        pass
    return caps


def role_capabilities(role_slug: str) -> set[str]:
    caps = set(DEFAULT_CAPS.get(role_slug, set()))
    caps.update(_caps_from_db(role_slug))
    return caps


def has_capability(user, case_id: str | None, capability: str) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return bool(getattr(settings, "PLATFORM_DEV_OPEN", True))
    if not case_id:
        return False
    try:
        m = CaseMembership.objects.filter(user=user, case_id=case_id).first()
        if not m:
            return False
        return capability in role_capabilities(m.role)
    except Exception:
        return False
