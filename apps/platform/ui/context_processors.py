from __future__ import annotations

# pyright: strict
import os
import re
import subprocess
from typing import Any, TypedDict, cast

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest

from apps.platform.accounts.models import Organization
from apps.platform.accounts.utils import (
    resolve_request_organization,
    user_accessible_organizations,
)


class NavChild(TypedDict, total=False):
    key: str
    label: str
    href: str
    patterns: list[str]
    active: bool


class NavItem(TypedDict, total=False):
    key: str
    label: str
    href: str
    patterns: list[str]
    children: list[NavChild]
    active: bool


def _normalize_patterns(raw: Any) -> list[str]:
    if isinstance(raw, list):
        patterns: list[str] = []
        for candidate_obj in cast(list[object], raw):
            if isinstance(candidate_obj, (str, bytes)):
                patterns.append(str(candidate_obj))
        return patterns
    if isinstance(raw, (str, bytes)):
        return [str(raw)]
    return []


def ui_context(request: HttpRequest) -> dict[str, Any]:
    """Inject active organization and choices into templates."""

    active_org: Organization | None = None
    try:
        active_org = resolve_request_organization(request, required=False)
    except PermissionDenied:
        active_org = None

    org_choices: list[Organization] = []
    user = getattr(request, "user", None)
    if user and getattr(user, "is_authenticated", False):
        org_choices = list(user_accessible_organizations(user))

    path = getattr(request, "path", "") or ""

    nav_items: list[NavItem] = [
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
            "href": "/audit/permissions/",
            "patterns": [r"^/audit/"],
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
                    "href": "/audit/permissions/",
                    "patterns": [r"^/audit/permissions/"],
                },
            ],
        },
    ]

    for item in nav_items:
        patterns = _normalize_patterns(item.get("patterns"))
        active = any(re.search(pattern, path) for pattern in patterns)
        children = item.get("children") or []
        normalized_children: list[NavChild] = []
        for child in children:
            child_patterns = _normalize_patterns(child.get("patterns"))
            child_active = any(re.search(pattern, path) for pattern in child_patterns)
            child["patterns"] = child_patterns
            child["active"] = child_active
            normalized_children.append(child)
            if child_active:
                active = True
        item["children"] = normalized_children
        item["patterns"] = patterns
        item["active"] = active

    return {
        "ui_active_org": active_org,
        "ui_org_choices": org_choices,
        "ui_nav_items": nav_items,
    }


def app_version(_: HttpRequest) -> dict[str, str]:
    """Expose build/version string for footer display."""

    build = os.getenv("APP_BUILD")
    if build:
        return {"APP_BUILD": build}

    sha = os.getenv("GIT_SHA")
    if sha:
        return {"APP_BUILD": sha[:12]}

    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
        )
        return {"APP_BUILD": out.decode("utf-8").strip()}
    except Exception:
        return {"APP_BUILD": "dev"}
