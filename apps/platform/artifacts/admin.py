from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from apps.platform.artifacts.models import CaseArtifact, FieldVisibilityRule


@admin.register(CaseArtifact)
class CaseArtifactAdmin(SimpleHistoryAdmin):
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


@admin.register(FieldVisibilityRule)
class FieldVisibilityRuleAdmin(admin.ModelAdmin):
    list_display = ("type", "field_name", "allowed_roles", "created_at")
    list_filter = ("type", "created_at")
    date_hierarchy = "created_at"
    ordering = ("type", "field_name")
    search_fields = ("type", "field_name")
