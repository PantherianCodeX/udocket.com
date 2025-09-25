from __future__ import annotations

import os
import subprocess
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


def app_version(_: HttpRequest) -> Dict[str, str]:
    """Expose build/version string for footer display."""

    build = os.getenv("APP_BUILD")
    if build:
        return {"APP_BUILD": build}

    sha = os.getenv("GIT_SHA")
    if sha:
        return {"APP_BUILD": sha[:12]}

    try:
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL)
        return {"APP_BUILD": out.decode("utf-8").strip()}
    except Exception:
        return {"APP_BUILD": "dev"}
