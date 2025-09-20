from django.db import models
from django.conf import settings


class CaseArtifact(models.Model):
    """Generic artifact record; full schema to follow in Step 4."""

    id = models.BigAutoField(primary_key=True)
    case_id = models.CharField(max_length=36)
    job_id = models.CharField(max_length=36, null=True, blank=True)
    type = models.CharField(max_length=32)
    title = models.CharField(max_length=200, blank=True)
    path = models.TextField()
    checksum = models.CharField(max_length=64, blank=True)
    schema_version = models.CharField(max_length=16, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["case_id", "type"], name="artifact_case_type_idx"),
            models.Index(fields=["created_at"], name="artifact_created_idx"),
        ]
        unique_together = ("case_id", "type", "title")

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.case_id}:{self.type}:{self.title or self.path}"


class FieldVisibilityRule(models.Model):
    """Defines which roles can see which fields on an artifact type.

    Example: type='TRANSCRIPT', field_name='path', allowed_roles=['OWNER','CONTRIBUTOR']
    """

    type = models.CharField(max_length=32)
    field_name = models.CharField(max_length=64)
    allowed_roles = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("type", "field_name")
        indexes = [models.Index(fields=["type", "field_name"])]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.type}:{self.field_name}"
