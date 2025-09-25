from __future__ import annotations

from typing import Dict, List

from django.conf import settings
from django.db import models
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from apps.platform.artifacts.registry import ARTIFACT_FIELD_REGISTRY
from apps.platform.authorization.capabilities import role_capabilities
from apps.platform.authorization.models import PermissionPreset, Role
from apps.platform.tenancy import accessible_organization_ids

from .auth import _ensure_authenticated


@require_http_methods(["GET"])
def permissions_overview(request: HttpRequest) -> HttpResponse:
    auth_response = _ensure_authenticated(request)
    if auth_response:
        return auth_response

    user = getattr(request, "user", None)
    dev_open = getattr(settings, "PLATFORM_DEV_OPEN", False)
    org_ids = accessible_organization_ids(user)

    registry: Dict[str, Dict[str, Dict[str, object]]] = {
        artifact_type: {
            field: {
                "default_actions": list(meta.default_actions or ()),
                "description": meta.description,
            }
            for field, meta in fields.items()
        }
        for artifact_type, fields in ARTIFACT_FIELD_REGISTRY.items()
    }

    preset_qs = (
        PermissionPreset.objects.select_related("organization")
        .prefetch_related("capabilities")
        .order_by("name")
    )
    role_qs = Role.objects.select_related("organization").prefetch_related("presets").order_by("name")

    if not (dev_open and (not user or not getattr(user, "is_authenticated", False))):
        if org_ids:
            preset_qs = preset_qs.filter(
                models.Q(organization__isnull=True) | models.Q(organization_id__in=org_ids)
            )
            role_qs = role_qs.filter(
                models.Q(organization__isnull=True) | models.Q(organization_id__in=org_ids)
            )
        else:
            preset_qs = preset_qs.filter(organization__isnull=True)
            role_qs = role_qs.filter(organization__isnull=True)

    presets: List[Dict[str, object]] = []
    for preset in preset_qs:
        caps = sorted(pc.capability for pc in preset.capabilities.all())
        presets.append(
            {
                "uuid": str(preset.uuid) if preset.uuid else None,
                "name": preset.name,
                "description": preset.description,
                "system": preset.system,
                "organization": preset.organization_id,
                "organization_name": preset.organization.name if preset.organization else None,
                "capabilities": caps,
                "field_policies": [],
            }
        )

    roles: List[Dict[str, object]] = []
    for role in role_qs:
        caps = role_capabilities(role.name, organization_id=role.organization_id)
        roles.append(
            {
                "uuid": str(role.uuid) if role.uuid else None,
                "name": role.name,
                "system": role.system,
                "organization": role.organization_id,
                "organization_name": role.organization.name if role.organization else None,
                "presets": [p.name for p in role.presets.all()],
                "capabilities": sorted(caps),
            }
        )

    context = {"registry": registry, "presets": presets, "roles": roles}
    return render(request, "platform_ui/permissions/index.html", context)
