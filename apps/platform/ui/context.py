from __future__ import annotations

from typing import Any, Dict, List, Optional

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest

from apps.platform.accounts.models import Organization
from apps.platform.accounts.utils import (
    resolve_request_organization,
    user_accessible_organizations,
)


def ui_context(request: HttpRequest) -> Dict[str, Any]:
    """Inject active organization and choices into templates."""

    active_org: Optional[Organization] = None
    try:
        active_org = resolve_request_organization(request, required=False)
    except PermissionDenied:
        active_org = None

    org_choices: List[Organization] = []
    user = getattr(request, "user", None)
    if user and getattr(user, "is_authenticated", False):
        org_choices = list(user_accessible_organizations(user))

    return {
        "ui_active_org": active_org,
        "ui_org_choices": org_choices,
    }
