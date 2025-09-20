from __future__ import annotations

from typing import Iterable
from django.conf import settings
from apps.platform.cases.models import CaseMembership
from apps.platform.authorization.models import Role, RoleCapability, PermissionPreset, PresetCapability, PresetFieldPolicy
from apps.platform.artifacts.registry import artifact_field


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
    # From presets attached to role
    try:
        r = Role.objects.filter(slug=role_slug).prefetch_related("presets__capabilities").first()
        if r:
            pcaps = PresetCapability.objects.filter(preset__in=r.presets.all()).values_list("capability", flat=True)
            caps.update(pcaps)
    except Exception:
        pass
    return caps


def allowed_field_actions(role_slug: str | None, artifact_type: str, field_name: str) -> set[str]:
    """Return allowed actions for a type.field based on attached presets.

    If no presets found, return an empty set (caller may fall back to default rules).
    """
    if not role_slug:
        return set()
    try:
        r = Role.objects.filter(slug=role_slug).prefetch_related("presets__field_policies").first()
        if not r:
            return set()
        acts: set[str] = set()
        for fp in PresetFieldPolicy.objects.filter(
            preset__in=r.presets.all(), type=artifact_type, field_name=field_name
        ):
            acts.update(a.lower() for a in (fp.actions or []))
        if acts:
            return acts
        meta = artifact_field(artifact_type, field_name)
        return set(a.lower() for a in (meta.default_actions if meta else []))
    except Exception:
        return set()


# Present allow-listed capability choices in admin/forms
CAPABILITIES: set[str] = set().union(*DEFAULT_CAPS.values())
CAPABILITY_CHOICES: list[tuple[str, str]] = sorted(((c, c) for c in CAPABILITIES), key=lambda x: x[0])


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
