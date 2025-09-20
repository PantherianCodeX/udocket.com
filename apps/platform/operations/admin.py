from django.contrib import admin
from apps.platform.operations.models import AuditEvent, TaskRun


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("id", "ts", "actor", "case_id", "event")
    list_filter = ("event", "ts")
    date_hierarchy = "ts"
    ordering = ("-ts",)
    search_fields = ("actor", "case_id", "event")


@admin.register(TaskRun)
class TaskRunAdmin(admin.ModelAdmin):
    list_display = ("id", "task_name", "task_id", "status", "job_id", "case_id", "started_at", "finished_at")
    list_filter = ("status", "task_name", "started_at")
    date_hierarchy = "started_at"
    ordering = ("-started_at",)
    search_fields = ("task_id", "job_id", "case_id")
