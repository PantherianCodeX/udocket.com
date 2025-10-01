from __future__ import annotations

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.conf import settings


class DiagnosticsViewSet(viewsets.ViewSet):
    @action(detail=False, methods=["get"], url_path="whoami")
    def whoami(self, request):
        u = getattr(request, "user", None)
        data = {
            "authenticated": bool(u and getattr(u, "is_authenticated", False)),
            "username": getattr(u, "username", None),
            "email": getattr(u, "email", None),
            "is_staff": getattr(u, "is_staff", None),
            "kc_sub": getattr(u, "kc_sub", None),
            "display_name": getattr(u, "display_name", None),
            "settings": {
                "DEBUG": getattr(settings, "DEBUG", False),
                "MEDIA_ROOT": getattr(settings, "MEDIA_ROOT", None),
                "PLATFORM_DEV_OPEN": getattr(settings, "PLATFORM_DEV_OPEN", None),
                "OIDC_JWKS_URL": getattr(settings, "OIDC_JWKS_URL", None),
                "OIDC_ISSUER": getattr(settings, "OIDC_ISSUER", None),
                "OIDC_AUDIENCE": getattr(settings, "OIDC_AUDIENCE", None),
                "OIDC_DISCOVERY_URL": getattr(settings, "OIDC_OP_DISCOVERY_ENDPOINT", None) or getattr(settings, "OIDC_DISCOVERY_URL", None),
                "OIDC_SYNC_MEMBERSHIPS": getattr(settings, "OIDC_SYNC_MEMBERSHIPS", False),
            },
        }
        return Response(data)

