"""Admin utilities for tenancy-aware behaviors."""

from __future__ import annotations

from django.db.models import QuerySet
from django.http import HttpRequest

from apps.platform.accounts.utils import get_active_admin_org


class TenantScopedAdminMixin:
    """Align Django admin access with tenancy-aware UI scoping."""

    tenant_field: str | None = "organization"

    def scope_queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        """Subclasses must return a queryset filtered to user-visible rows."""
        return queryset

    def get_queryset(self, request: HttpRequest) -> QuerySet:  # type: ignore[override]
        queryset = super().get_queryset(request)  # type: ignore[misc]
        scoped = self.scope_queryset(request, queryset)
        return self._filter_active_org(request, scoped)

    def has_module_permission(self, request: HttpRequest) -> bool:  # type: ignore[override]
        if request.user.is_superuser:
            return True
        return self._user_can_access_admin(request)

    def has_view_permission(self, request: HttpRequest, obj=None) -> bool:  # type: ignore[override]
        if request.user.is_superuser:
            return True
        if not self._user_can_access_admin(request):
            return False
        return self._object_in_scope(request, obj)

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:  # type: ignore[override]
        if request.user.is_superuser:
            return True
        if obj is None:
            return self._user_can_access_admin(request)
        return self._object_in_scope(request, obj)

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:  # type: ignore[override]
        if request.user.is_superuser:
            return True
        if obj is None:
            return self._user_can_access_admin(request)
        return self._object_in_scope(request, obj)

    def has_add_permission(self, request: HttpRequest) -> bool:  # type: ignore[override]
        if request.user.is_superuser:
            return True
        return self._user_can_access_admin(request)

    def _user_can_access_admin(self, request: HttpRequest) -> bool:
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and user.is_staff)

    def _object_in_scope(self, request: HttpRequest, obj) -> bool:
        if obj is None:
            return True
        queryset = self.model._default_manager.filter(pk=getattr(obj, "pk", obj))
        queryset = self.scope_queryset(request, queryset)
        queryset = self._filter_active_org(request, queryset)
        return queryset.exists()

    def _filter_active_org(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        field = getattr(self, "tenant_field", None)
        if not field:
            return queryset
        model_field = f"{field}_id"
        if not hasattr(queryset.model, model_field):
            return queryset
        active_org = get_active_admin_org(request)
        if active_org is None:
            return queryset
        return queryset.filter(**{model_field: active_org.id})

    def _active_org_id(self, request: HttpRequest) -> str | None:
        active_org = get_active_admin_org(request)
        return getattr(active_org, "id", None)


__all__ = ["TenantScopedAdminMixin"]
