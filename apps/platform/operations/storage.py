# pyright: strict

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from django.conf import settings

from apps.platform.cases.models import Case
from packages.udocket_common.paths import CasePaths, build_case_paths

_DEFAULT_ORG_SLUG = "unassigned"


def _case_org(case_id: str, fallback: str | None = None) -> str:
    values = Case.typed_objects().filter(pk=case_id).values_list("organization_id", flat=True)
    first_value = next((value for value in list(values) if value), None)
    return str(first_value or fallback or _DEFAULT_ORG_SLUG)


def tenant_case_root(case_id: str, organization_id: str | UUID | None = None) -> Path:
    org_value = str(organization_id) if organization_id else _case_org(case_id)
    media_root = Path(str(settings.MEDIA_ROOT))
    return media_root / "tenants" / org_value / "cases" / case_id


def case_paths(case_id: str, organization_id: str | UUID | None = None) -> CasePaths:
    return build_case_paths(tenant_case_root(case_id, organization_id))


def ensure_case_paths(case_id: str, organization_id: str | UUID | None = None) -> CasePaths:
    paths = case_paths(case_id, organization_id)
    paths.ensure()
    return paths


def ensure_case_dirs(case_id: str, organization_id: str | UUID | None = None) -> Path:
    return ensure_case_paths(case_id, organization_id).root


def ops_dir(case_id: str, organization_id: str | UUID | None = None) -> Path:
    return case_paths(case_id, organization_id).ops.resolve()
