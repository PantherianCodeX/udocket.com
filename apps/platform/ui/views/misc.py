from __future__ import annotations

# pyright: strict
import base64
import logging
from typing import Any

from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt

log = logging.getLogger("apps.platform.ui")
from packages.common.json_utils import parse_json_value


def favicon(request: HttpRequest) -> HttpResponse:
    """Serve a tiny in-memory PNG favicon to avoid 404 noise."""
    data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
    )
    resp = HttpResponse(data, content_type="image/png")
    resp["Cache-Control"] = "public, max-age=86400"
    return resp


@csrf_exempt
def ui_log(request: HttpRequest) -> HttpResponse:
    try:
        body = request.body.decode("utf-8") if request.body else "{}"
        parsed = parse_json_value(body)
        payload: dict[str, Any]
        if isinstance(parsed, dict):
            payload = {str(key): value for key, value in parsed.items()}
        else:
            raise ValueError("Invalid JSON payload")
    except Exception:
        payload = {"raw": request.body.decode("utf-8", errors="ignore") if request.body else ""}

    log.error(
        "client_ui_error",
        extra={
            "user_id": str(getattr(getattr(request, "user", None), "id", "")) or None,
            "path": request.path,
            "payload": payload,
            "user_agent": request.META.get("HTTP_USER_AGENT"),
            "referer": request.META.get("HTTP_REFERER"),
        },
    )
    return HttpResponse(status=204)
