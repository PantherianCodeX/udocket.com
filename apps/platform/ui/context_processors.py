from __future__ import annotations

import os
import subprocess
import re
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

    path = getattr(request, "path", "") or ""

    nav_items: List[Dict[str, Any]] = [
        {
            "key": "cases",
            "label": "Cases",
            "href": "/",
            "patterns": [r"^/$", r"^/cases/"],
        },
        {
            "key": "jobs",
            "label": "Jobs",
            "href": "/jobs/",
            "patterns": [r"^/jobs/"],
        },
        {
            "key": "artifacts",
            "label": "Artifacts",
            "href": "/artifacts/",
            "patterns": [r"^/artifacts/"],
        },
        {
            "key": "audit",
            "label": "Audit",
            "href": "/audit/guardian/",
            "patterns": [r"^/audit/", r"^/permissions/"],
            "children": [
                {
                    "key": "guardian",
                    "label": "Guardian",
                    "href": "/audit/guardian/",
                    "patterns": [r"^/audit/guardian/"],
                },
                {
                    "key": "permissions",
                    "label": "Permissions Catalog",
                    "href": "/permissions/",
                    "patterns": [r"^/permissions/"],
                },
            ],
        },
    ]

    for item in nav_items:
        patterns = item.get("patterns", [])
        active = any(re.search(pattern, path) for pattern in patterns)
        children = item.get("children") or []
        for child in children:
            child_patterns = child.get("patterns", [])
            child_active = any(re.search(pattern, path) for pattern in child_patterns)
            child["active"] = child_active
            if child_active:
                active = True
        item["active"] = active

    return {
        "ui_active_org": active_org,
        "ui_org_choices": org_choices,
        "ui_nav_items": nav_items,
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
