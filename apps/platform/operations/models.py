from django.db import models


class AuditEvent(models.Model):
    id = models.BigAutoField(primary_key=True)
    ts = models.DateTimeField(auto_now_add=True)
    actor = models.CharField(max_length=128, blank=True)
    case_id = models.CharField(max_length=36, blank=True)
    event = models.CharField(max_length=64)
    data = models.JSONField(default=dict, blank=True)


class TaskRun(models.Model):
    id = models.BigAutoField(primary_key=True)
    task_name = models.CharField(max_length=200)
    task_id = models.CharField(max_length=64, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=32, default="PENDING")
    job_id = models.CharField(max_length=36, blank=True)
    case_id = models.CharField(max_length=36, blank=True)
    meta = models.JSONField(default=dict, blank=True)
