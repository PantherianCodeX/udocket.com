from __future__ import annotations

from typing import Callable, Optional, cast

from django.db import connection
from django.conf import settings
from django.http import HttpRequest, HttpResponse


def org_session_middleware(
    get_response: Callable[[HttpRequest], HttpResponse]
) -> Callable[[HttpRequest], HttpResponse]:
    def middleware(request: HttpRequest) -> HttpResponse:
        header_name = getattr(settings, "ORG_HEADER_NAME", "HTTP_X_ORGANIZATION_ID")
        org_id: Optional[str] = cast(Optional[str], request.META.get(header_name))
        user = getattr(request, "user", None)
        # Only set when on Postgres and a valid organization header is present and user is a member
        if connection.vendor == "postgresql" and org_id and user and getattr(user, "is_authenticated", False):
            try:
                from apps.platform.accounts.models import OrganizationMembership

                if OrganizationMembership.objects.filter(user=user, organization_id=org_id).exists():
                    with connection.cursor() as cur:
                        cur.execute("SET LOCAL app.current_organization = %s", [str(org_id)])
            except Exception:
                pass
        response: HttpResponse = get_response(request)
        return response

    return middleware
