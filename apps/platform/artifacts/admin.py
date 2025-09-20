from django.contrib import admin
from apps.platform.artifacts.models import CaseArtifact, FieldVisibilityRule


@admin.register(CaseArtifact)
class CaseArtifactAdmin(admin.ModelAdmin):
    list_display = ("id", "case_id", "type", "title", "created_at")
    list_filter = ("type",)
    search_fields = ("case_id", "title", "path")


@admin.register(FieldVisibilityRule)
class FieldVisibilityRuleAdmin(admin.ModelAdmin):
    list_display = ("type", "field_name", "allowed_roles", "created_at")
    list_filter = ("type",)
    search_fields = ("type", "field_name")
