from __future__ import annotations

from typing import Any

from django.http import HttpRequest
from django.utils import timezone

from apps.platform.operations.models import AuditEvent


def emit(
    request: HttpRequest,
    *,
    case_id: str | None,
    event: str,
    data: dict[str, Any] | None = None,
) -> None:
    try:
        user = getattr(request, "user", None)
        actor = getattr(user, "username", None) or getattr(user, "email", None) or "anonymous"
        AuditEvent.objects.create(
            ts=timezone.now(),
            actor=str(actor),
            case_id=case_id or "",
            event=event,
            data=data or {},
        )
    except Exception:
        # Never raise from audit
        return
