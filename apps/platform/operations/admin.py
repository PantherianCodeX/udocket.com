from __future__ import annotations

from typing import Iterable, Sequence

from django.contrib import admin
from django.db.models import Q, QuerySet

from apps.platform.admin import TenantScopedAdminMixin
from apps.platform.operations.models import AuditEvent, TaskRun
from apps.platform.tenancy import scope_cases, scope_jobs
from apps.platform.cases.models import Case
from apps.platform.jobs.models import Job


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


@admin.register(TaskRun)
class TaskRunAdmin(TenantScopedAdminMixin, admin.ModelAdmin):
    tenant_field = None
    list_display = ("id", "task_name", "task_id", "status", "job_id", "case_id", "started_at", "finished_at")
    list_filter = ("status", "task_name", "started_at")
    date_hierarchy = "started_at"
    ordering = ("-started_at",)
    search_fields = ("task_id", "job_id", "case_id")

    def scope_queryset(self, request, queryset: QuerySet[TaskRun]):  # type: ignore[override]
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return queryset.none()

        active_org_id = self._active_org_id(request)
        if getattr(user, "is_superuser", False):
            if not active_org_id:
                return queryset
            case_ids = _to_str_set(
                Case.objects.filter(organization_id=active_org_id).values_list("id", flat=True)
            )
            job_ids = _to_str_set(
                Job.objects.filter(organization_id=active_org_id).values_list("id", flat=True)
            )
        else:
            case_ids = _to_str_set(scope_cases(Case.objects.all(), user).values_list("id", flat=True))
            job_ids = _to_str_set(scope_jobs(Job.objects.all(), user).values_list("id", flat=True))
            if active_org_id:
                if case_ids:
                    case_ids &= _to_str_set(
                        Case.objects.filter(id__in=case_ids, organization_id=active_org_id).values_list("id", flat=True)
                    )
                if job_ids:
                    job_ids &= _to_str_set(
                        Job.objects.filter(id__in=job_ids, organization_id=active_org_id).values_list("id", flat=True)
                    )

        filters = Q()
        if case_ids:
            filters |= Q(case_id__in=case_ids)
        if job_ids:
            filters |= Q(job_id__in=job_ids)
        if not filters:
            return queryset.none()
        return queryset.filter(filters)
