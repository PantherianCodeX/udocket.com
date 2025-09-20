from __future__ import annotations

import uuid

from django.db import models


class JobQuerySet(models.QuerySet):
    def for_user(self, user):
        from apps.platform import tenancy

        return tenancy.scope_jobs(self, user)


class Job(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING"
        RUNNING = "RUNNING"
        SUCCEEDED = "SUCCEEDED"
        FAILED = "FAILED"

    class Mode(models.TextChoices):
        BATCH = "batch"
        ON_DEMAND = "on-demand"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey("cases.Case", on_delete=models.PROTECT, related_name="jobs")
    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.PROTECT,
        related_name="jobs",
        editable=False,
    )
    audio_input = models.TextField()
    mode = models.CharField(max_length=16, choices=Mode.choices, default=Mode.ON_DEMAND)
    diarization = models.BooleanField(default=False)
    language = models.CharField(max_length=16, default="en-CA")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True)
    error_message = models.TextField(null=True, blank=True)
    transcript_path = models.TextField(null=True, blank=True)
    duration_s = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True, db_index=True)
    finished_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    objects = JobQuerySet.as_manager()

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.id} {self.status}"

    def save(self, *args, **kwargs):  # type: ignore[override]
        if self.case_id and self.organization_id is None:
            try:
                self.organization_id = self.case.organization_id
            except Exception:
                pass
        super().save(*args, **kwargs)
