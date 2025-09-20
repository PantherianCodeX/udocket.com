from django.contrib import admin
from apps.platform.jobs.models import Job


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("id", "case", "organization", "mode", "status", "created_at", "finished_at")
    list_filter = ("status", "mode", "organization", "created_at")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    search_fields = ("id", "case__id", "organization__name")
    autocomplete_fields = ["case"]
