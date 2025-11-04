# pyright: strict

from __future__ import annotations

from django.conf import settings
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from packages.udocket_common.json_utils import JSONObject, JSONValue, coerce_json_value


class DiagnosticsViewSet(viewsets.ViewSet):
    @action(detail=False, methods=["get"], url_path="whoami")
    def whoami(self, request: Request) -> Response:
        user = getattr(request, "user", None)
        authenticated = bool(user and getattr(user, "is_authenticated", False))

        def _attr(source: object, name: str) -> JSONValue:
            return coerce_json_value(getattr(source, name, None))

        payload: JSONObject = {
            "authenticated": authenticated,
            "username": _attr(user, "username"),
            "email": _attr(user, "email"),
            "is_staff": _attr(user, "is_staff"),
            "kc_sub": _attr(user, "kc_sub"),
            "display_name": _attr(user, "display_name"),
            "settings": _settings_snapshot(),
        }
        return Response(payload)


def _settings_snapshot() -> JSONObject:
    snapshot: JSONObject = {
        "DEBUG": bool(getattr(settings, "DEBUG", False)),
        "MEDIA_ROOT": coerce_json_value(getattr(settings, "MEDIA_ROOT", None)),
        "PLATFORM_DEV_OPEN": coerce_json_value(getattr(settings, "PLATFORM_DEV_OPEN", None)),
        "OIDC_JWKS_URL": coerce_json_value(getattr(settings, "OIDC_JWKS_URL", None)),
        "OIDC_ISSUER": coerce_json_value(getattr(settings, "OIDC_ISSUER", None)),
        "OIDC_AUDIENCE": coerce_json_value(getattr(settings, "OIDC_AUDIENCE", None)),
        "OIDC_SYNC_MEMBERSHIPS": bool(getattr(settings, "OIDC_SYNC_MEMBERSHIPS", False)),
    }
    discovery_url = getattr(settings, "OIDC_OP_DISCOVERY_ENDPOINT", None) or getattr(
        settings, "OIDC_DISCOVERY_URL", None
    )
    snapshot["OIDC_DISCOVERY_URL"] = coerce_json_value(discovery_url)
    return snapshot
