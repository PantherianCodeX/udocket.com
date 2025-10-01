from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from apps.platform.admin import TenantScopedAdminMixin
from apps.platform.artifacts.models import CaseArtifact
from apps.platform.tenancy import scope_artifacts


@admin.register(CaseArtifact)
class CaseArtifactAdmin(TenantScopedAdminMixin, SimpleHistoryAdmin):
    list_display = ("id", "case_id", "organization", "type", "title", "created_at")
    list_filter = ("type", "organization", "created_at")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    search_fields = ("case_id", "title", "path")
    readonly_fields = ("created_at",)
    fieldsets = (
        (None, {"fields": ("case_fk", "case_id", "organization", "job_id", "type", "title")}),
        ("File", {"fields": ("path", "checksum", "schema_version")}),
        ("Metadata", {"fields": ("metadata", "created_at")}),
    )

    def scope_queryset(self, request, queryset):  # type: ignore[override]
        return scope_artifacts(queryset, request.user)
