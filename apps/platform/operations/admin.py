from __future__ import annotations

from typing import Iterable

from django.contrib import admin
from django.db.models import QuerySet

from apps.platform.admin import TenantScopedAdminMixin
from apps.platform.operations.models import AuditEvent
from apps.platform.tenancy import scope_cases
from apps.platform.cases.models import Case


def _to_str_set(values: Iterable) -> set[str]:
    return {str(v) for v in values if v is not None}


@admin.register(AuditEvent)
class AuditEventAdmin(TenantScopedAdminMixin, admin.ModelAdmin):
    tenant_field = None
    list_display = ("id", "ts", "actor", "case_id", "event")
    list_filter = ("event", "ts")
    date_hierarchy = "ts"
    ordering = ("-ts",)
    search_fields = ("actor", "case_id", "event")

    def scope_queryset(self, request, queryset: QuerySet[AuditEvent]):  # type: ignore[override]
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return queryset.none()

        active_org_id = self._active_org_id(request)
        if getattr(user, "is_superuser", False):
            if not active_org_id:
                return queryset
            org_case_ids = Case.objects.filter(organization_id=active_org_id).values_list("id", flat=True)
            case_ids = _to_str_set(org_case_ids)
        else:
            allowed_cases = scope_cases(Case.objects.all(), user).values_list("id", flat=True)
            case_ids = _to_str_set(allowed_cases)
            if active_org_id:
                case_ids &= _to_str_set(
                    Case.objects.filter(id__in=case_ids, organization_id=active_org_id).values_list("id", flat=True)
                )

        if not case_ids:
            return queryset.none()
        return queryset.filter(case_id__in=case_ids)
