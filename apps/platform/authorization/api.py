from __future__ import annotations

from django.conf import settings
from django.db import models
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.platform.artifacts.registry import ARTIFACT_FIELD_REGISTRY
from apps.platform.authorization.models import PermissionPreset, Role
from apps.platform.authorization.capabilities import role_capabilities
from apps.platform.tenancy import accessible_organization_ids


def _auth_guard(request):
    user = getattr(request, "user", None)
    if getattr(settings, "PLATFORM_DEV_OPEN", False):
        return None
    if user and getattr(user, "is_authenticated", False):
        return None
    return Response({"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)


def _filter_by_org(queryset, user):
    dev_open = getattr(settings, "PLATFORM_DEV_OPEN", False)
    if dev_open and (not user or not getattr(user, "is_authenticated", False)):
        return queryset
    org_ids = accessible_organization_ids(user)
    if org_ids:
        return queryset.filter(
            models.Q(organization__isnull=True) | models.Q(organization_id__in=org_ids)
        )
    return queryset.filter(organization__isnull=True)


@api_view(["GET"])
@permission_classes([AllowAny])
def registry_fields(_request):
    """Return the artifact field registry for Permission Builder UIs."""
    out = {
        atype: {
            fname: {"default_actions": list(meta.default_actions or ()), "description": meta.description}
            for fname, meta in fields.items()
        }
        for atype, fields in ARTIFACT_FIELD_REGISTRY.items()
    }
    return Response(out)


@api_view(["GET"])
@permission_classes([AllowAny])
def list_presets(request):
    guard = _auth_guard(request)
    if guard:
        return guard

    user = getattr(request, "user", None)
    preset_qs = (
        PermissionPreset.objects.select_related("organization")
        .prefetch_related("capabilities")
        .order_by("name")
    )
    preset_qs = _filter_by_org(preset_qs, user)

    presets = []
    for preset in preset_qs:
        caps = sorted(pc.capability for pc in preset.capabilities.all())
        presets.append(
            {
                "uuid": str(preset.uuid) if preset.uuid else None,
                "name": preset.name,
                "description": preset.description,
                "system": preset.system,
                "organization": preset.organization_id,
                "capabilities": caps,
                "field_policies": [],
            }
        )
    return Response({"presets": presets})


@api_view(["GET"])
@permission_classes([AllowAny])
def list_roles(request):
    guard = _auth_guard(request)
    if guard:
        return guard

    user = getattr(request, "user", None)
    role_qs = Role.objects.select_related("organization").prefetch_related("presets").order_by("name")
    role_qs = _filter_by_org(role_qs, user)

    roles = []
    for role in role_qs:
        caps = role_capabilities(role.name, organization_id=role.organization_id)
        roles.append(
            {
                "uuid": str(role.uuid) if role.uuid else None,
                "name": role.name,
                "system": role.system,
                "organization": role.organization_id,
                "presets": [p.name for p in role.presets.all()],
                "capabilities": sorted(list(caps)),
            }
        )
    return Response({"roles": roles})
