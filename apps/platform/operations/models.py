from django.db import models


class LLMProviderSetting(models.Model):
    id = models.BigAutoField(primary_key=True)
    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="llm_provider_settings",
    )
    stage_key = models.CharField(max_length=128)
    provider = models.CharField(max_length=64)
    model = models.CharField(max_length=128, blank=True)
    fallbacks = models.JSONField(default=list, blank=True)
    allow_local_fallback = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("organization", "stage_key")


class LLMProviderCredential(models.Model):
    id = models.BigAutoField(primary_key=True)
    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="llm_provider_credentials",
    )
    provider = models.CharField(max_length=64)
    display_name = models.CharField(max_length=128, blank=True)
    endpoint = models.CharField(max_length=255, blank=True)
    api_key_encrypted = models.TextField(blank=True)
    models_payload = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("organization", "provider")


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
