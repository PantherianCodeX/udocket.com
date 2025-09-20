from django.contrib import admin
from apps.platform.jobs.models import Job


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("id", "case", "mode", "status", "created_at", "finished_at")
    list_filter = ("status", "mode")
    search_fields = ("id", "case__id")

