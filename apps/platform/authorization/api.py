from __future__ import annotations

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.platform.artifacts.registry import ARTIFACT_FIELD_REGISTRY
from apps.platform.authorization.models import PermissionPreset, PresetCapability, PresetFieldPolicy, Role
from apps.platform.authorization.capabilities import role_capabilities


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
def list_presets(_request):
    presets = []
    for p in PermissionPreset.objects.all().order_by("slug"):
        caps = list(PresetCapability.objects.filter(preset=p).values_list("capability", flat=True))
        fps = [
            {"type": fp.type, "field": fp.field_name, "actions": list(fp.actions or [])}
            for fp in PresetFieldPolicy.objects.filter(preset=p)
        ]
        presets.append({
            "slug": p.slug,
            "name": p.name,
            "description": p.description,
            "system": p.system,
            "capabilities": caps,
            "field_policies": fps,
        })
    return Response({"presets": presets})


@api_view(["GET"])
@permission_classes([AllowAny])
def list_roles(_request):
    roles = []
    for r in Role.objects.all().prefetch_related("presets").order_by("slug"):
        roles.append({
            "slug": r.slug,
            "name": r.name,
            "system": r.system,
            "presets": [p.slug for p in r.presets.all()],
            "capabilities": sorted(list(role_capabilities(r.slug))),
        })
    return Response({"roles": roles})
