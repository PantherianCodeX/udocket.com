from __future__ import annotations

from pathlib import Path
from typing import Optional

from django.conf import settings

from apps.platform.cases.models import Case

_DEFAULT_ORG_SLUG = "unassigned"


def _case_org(case_id: str, fallback: Optional[str] = None) -> str:
    value = (
        Case.objects.filter(pk=case_id)
        .values_list("organization_id", flat=True)
        .first()
    )
    return str(value or fallback or _DEFAULT_ORG_SLUG)


def tenant_case_root(case_id: str, organization_id: Optional[str] = None) -> Path:
    org = organization_id or _case_org(case_id)
    return Path(settings.MEDIA_ROOT) / "tenants" / org / "cases" / case_id


def ensure_case_dirs(case_id: str, organization_id: Optional[str] = None) -> Path:
    base = tenant_case_root(case_id, organization_id)
    for sub in ("audio", "transcript", "analysis", "ops"):
        (base / sub).mkdir(parents=True, exist_ok=True)
    return base


def ops_dir(case_id: str, organization_id: Optional[str] = None) -> Path:
    return (tenant_case_root(case_id, organization_id) / "ops").resolve()

