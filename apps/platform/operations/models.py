import uuid

from django.db import models


class LLMProviderCredential(models.Model):
    id = models.BigAutoField(primary_key=True)
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
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
    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("organization", "provider")


class LLMConfiguration(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="llm_configurations",
    )
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    target = models.CharField(max_length=64, default="summary")
    provider_chain = models.JSONField(default=list, blank=True)
    stage_map = models.JSONField(default=dict, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("organization", "name", "target")


class AuditEvent(models.Model):
    id = models.BigAutoField(primary_key=True)
    ts = models.DateTimeField(auto_now_add=True)
    actor = models.CharField(max_length=128, blank=True)
    case_id = models.CharField(max_length=36, blank=True)
    event = models.CharField(max_length=64)
    data = models.JSONField(default=dict, blank=True)


class GuardianSettings(models.Model):
    id = models.BigAutoField(primary_key=True)
    organization = models.OneToOneField(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="guardian_settings",
    )
    instructions = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Guardian Settings"
        verbose_name_plural = "Guardian Settings"

    def __str__(self) -> str:  # pragma: no cover - representational
        return f"GuardianSettings(org={self.organization_id})"
