# pyright: strict

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from apps.platform.admin import TenantScopedAdminMixin
from apps.platform.cases.models import Case
from apps.platform.operations.models import AuditEvent
from apps.platform.tenancy import scope_cases

if TYPE_CHECKING:
    from django.contrib.admin import ModelAdmin as _ModelAdmin

    class AuditEventAdminBase(_ModelAdmin): ...
else:
    AuditEventAdminBase = admin.ModelAdmin


def _to_str_set(values: Iterable[Any]) -> set[str]:
    return {str(v) for v in values if v is not None}


@admin.register(AuditEvent)
class AuditEventAdmin(TenantScopedAdminMixin, AuditEventAdminBase):
    tenant_field = None
    list_display = ("id", "ts", "actor", "case_id", "event")
    list_filter = ("event", "ts")
    date_hierarchy = "ts"
    ordering = ("-ts",)
    search_fields = ("actor", "case_id", "event")

    def scope_queryset(
        self,
        request: HttpRequest,
        queryset: QuerySet[AuditEvent],
    ) -> QuerySet[AuditEvent]:
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return queryset.none()

        active_org_getter = getattr(self, "_active_org_id", None)
        active_org_id = active_org_getter(request) if callable(active_org_getter) else None
        if getattr(user, "is_superuser", False):
            if not active_org_id:
                return queryset
            org_case_ids = Case.objects.filter(organization_id=active_org_id).values_list(
                "id", flat=True
            )
            case_ids = _to_str_set(org_case_ids)
        else:
            allowed_cases = scope_cases(Case.objects.all(), user).values_list("id", flat=True)
            case_ids = _to_str_set(allowed_cases)
            if active_org_id:
                case_ids &= _to_str_set(
                    Case.objects.filter(id__in=case_ids, organization_id=active_org_id).values_list(
                        "id", flat=True
                    )
                )

        if not case_ids:
            return queryset.none()
        return queryset.filter(case_id__in=case_ids)
