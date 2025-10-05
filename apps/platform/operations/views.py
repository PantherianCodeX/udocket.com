# pyright: strict

from __future__ import annotations

from typing import Any, Mapping

from django.conf import settings
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response


class DiagnosticsViewSet(viewsets.ViewSet):
    @action(detail=False, methods=["get"], url_path="whoami")
    def whoami(self, request: Request) -> Response:
        user = getattr(request, "user", None)
        authenticated = bool(user and getattr(user, "is_authenticated", False))
        def _attr(source: object, name: str) -> Any:
            return getattr(source, name, None)

        payload: dict[str, Any] = {
            "authenticated": authenticated,
            "username": _attr(user, "username"),
            "email": _attr(user, "email"),
            "is_staff": _attr(user, "is_staff"),
            "kc_sub": _attr(user, "kc_sub"),
            "display_name": _attr(user, "display_name"),
            "settings": _settings_snapshot(),
        }
        return Response(payload)


def _settings_snapshot() -> Mapping[str, Any]:
    return {
        "DEBUG": getattr(settings, "DEBUG", False),
        "MEDIA_ROOT": getattr(settings, "MEDIA_ROOT", None),
        "PLATFORM_DEV_OPEN": getattr(settings, "PLATFORM_DEV_OPEN", None),
        "OIDC_JWKS_URL": getattr(settings, "OIDC_JWKS_URL", None),
        "OIDC_ISSUER": getattr(settings, "OIDC_ISSUER", None),
        "OIDC_AUDIENCE": getattr(settings, "OIDC_AUDIENCE", None),
        "OIDC_DISCOVERY_URL": getattr(settings, "OIDC_OP_DISCOVERY_ENDPOINT", None)
        or getattr(settings, "OIDC_DISCOVERY_URL", None),
        "OIDC_SYNC_MEMBERSHIPS": getattr(settings, "OIDC_SYNC_MEMBERSHIPS", False),
    }
