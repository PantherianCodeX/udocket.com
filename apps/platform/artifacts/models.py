from django.db import models


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
            models.Index(fields=["case_id", "type"]),
        ]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.case_id}:{self.type}:{self.title or self.path}"

