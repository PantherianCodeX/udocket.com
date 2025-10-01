from __future__ import annotations

import base64
import json
import logging
from typing import Any, Dict

from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt

log = logging.getLogger("apps.platform.ui")


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
        payload: Dict[str, Any] = json.loads(body)
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
