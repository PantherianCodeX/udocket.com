from __future__ import annotations

from typing import Iterable, Optional

from django.conf import settings
from django.db.models import Q

from apps.platform.artifacts.registry import artifact_field
from apps.platform.authorization.models import (
    PermissionPreset,
    PresetCapability,
    PresetFieldPolicy,
    Role,
    RoleCapability,
)
from apps.platform.cases.models import CaseMembership

# Hard-coded defaults as a safe baseline; DB can override/extend
DEFAULT_CAPS: dict[str, set[str]] = {
    "OWNER": {
        "case.view",
        "case.update",
        "job.create",
        "artifact.view",
        "artifact.download",
        "artifact.field.path.view",
        "artifact.field.checksum.view",
    },
    "CONTRIBUTOR": {
        "case.view",
        "job.create",
        "artifact.view",
        "artifact.download",
        "artifact.field.path.view",
        "artifact.field.checksum.view",
    },
    "REVIEWER": {
        "case.view",
        "artifact.view",
        "artifact.field.checksum.view",
    },
    "AUDITOR": {
        "case.view",
        "artifact.view",
        "artifact.field.checksum.view",
    },
    "EXTERNAL": {
        "case.view",
        "artifact.view",
    },
    "CLIENT": {
        "case.view",
        "artifact.view",
        "artifact.download",
    },
}


def _roles_for_name(role_name: str, organization_id: Optional[str]) -> Iterable[Role]:
    qs = Role.objects.filter(name__iexact=role_name)
    if organization_id:
        qs = qs.filter(Q(organization__id=organization_id) | Q(organization__isnull=True))
    else:
        qs = qs.filter(organization__isnull=True)
    return qs


def _caps_from_db(role_name: str, organization_id: Optional[str]) -> set[str]:
    caps: set[str] = set()
    try:
        for role in _roles_for_name(role_name, organization_id):
            caps.update(
                RoleCapability.objects.filter(role=role).values_list("capability", flat=True)
            )
    except Exception:
        pass
    return caps


def role_capabilities(role_name: str, organization_id: Optional[str] = None) -> set[str]:
    caps = set(DEFAULT_CAPS.get(role_name, set()))
    caps.update(_caps_from_db(role_name, organization_id))
    try:
        preset_ids: set[int] = set()
        for role in _roles_for_name(role_name, organization_id):
            preset_ids.update(role.presets.values_list("id", flat=True))
        if preset_ids:
            pcaps = PresetCapability.objects.filter(preset_id__in=preset_ids).values_list(
                "capability", flat=True
            )
            caps.update(pcaps)
    except Exception:
        pass
    return caps


def allowed_field_actions(
    role_name: str | None,
    target_type: str,
    field_name: str,
    *,
    organization_id: Optional[str] = None,
    resource: str = "ARTIFACT",
) -> set[str]:
    """Return allowed actions for a type.field based on attached presets."""

    if not role_name:
        return set()
    acts: set[str] = set()
    try:
        preset_ids: set[int] = set()
        for role in _roles_for_name(role_name, organization_id):
            preset_ids.update(role.presets.values_list("id", flat=True))
        if preset_ids:
            for fp in PresetFieldPolicy.objects.filter(
                preset_id__in=preset_ids,
                resource=resource,
                type=target_type,
                field_name=field_name,
            ):
                acts.update(a.lower() for a in (fp.actions or []))
    except Exception:
        return acts
    if acts:
        return acts
    meta = artifact_field(target_type, field_name)
    return set(a.lower() for a in (meta.default_actions if meta else []))


# Present allow-listed capability choices in admin/forms
CAPABILITIES: set[str] = set().union(*DEFAULT_CAPS.values())
CAPABILITY_CHOICES: list[tuple[str, str]] = sorted(((c, c) for c in CAPABILITIES), key=lambda x: x[0])


def has_capability(user, case_id: str | None, capability: str) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return bool(getattr(settings, "PLATFORM_DEV_OPEN", True))
    if not case_id:
        return False
    try:
        membership = (
            CaseMembership.objects.select_related("case__organization")
            .filter(user=user, case_id=case_id)
            .first()
        )
        if not membership:
            return False
        org_id = None
        if membership.case and membership.case.organization_id:
            org_id = membership.case.organization_id
        return capability in role_capabilities(membership.role, organization_id=org_id)
    except Exception:
        return False
