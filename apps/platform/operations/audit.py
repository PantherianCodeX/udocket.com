# pyright: strict

from __future__ import annotations

from collections.abc import Mapping

from django.http import HttpRequest
from django.utils import timezone

from apps.platform.operations.models import AuditEvent


def emit(
    request: HttpRequest,
    *,
    case_id: str | None,
    event: str,
    data: Mapping[str, object] | None = None,
) -> None:
    try:
        user = getattr(request, "user", None)
        actor = (
            getattr(user, "username", None)
            or getattr(user, "email", None)
            or "anonymous"
        )
        payload = dict(data) if data is not None else {}
        AuditEvent.typed_objects().create(
            ts=timezone.now(),
            actor=str(actor),
            case_id=case_id or "",
            event=event,
            data=payload,
        )
    except Exception:
        # Never raise from audit
        return
