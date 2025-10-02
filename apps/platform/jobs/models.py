from __future__ import annotations

import typing
import uuid

from django.conf import settings
from django.db import models
from typing import Any

if typing.TYPE_CHECKING:  # pragma: no cover
    from apps.platform.cases.models import Case


class JobQuerySet(models.QuerySet["Job"]):
    def for_user(self, user: Any) -> "JobQuerySet":
        from apps.platform import tenancy

        return typing.cast("JobQuerySet", tenancy.scope_jobs(self, user))


class Job(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING"
        RUNNING = "RUNNING"
        CONVERTING = "CONVERTING"
        UPLOADING = "UPLOADING"
        CANCELLING = "CANCELLING"
        SUCCEEDED = "SUCCEEDED"
        FAILED = "FAILED"
        CANCELLED = "CANCELLED"
        CORRUPTED = "CORRUPTED"

    class Mode(models.TextChoices):
        BATCH = "batch"
        ON_DEMAND = "on-demand"

    class ReviewStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

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
    display_title = models.CharField(max_length=255, blank=True)
    agent_type = models.CharField(max_length=64, blank=True, db_index=True)
    agent_label = models.CharField(max_length=128, blank=True)
    job_kind = models.CharField(max_length=64, blank=True, db_index=True)
    source_job = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="child_jobs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True, db_index=True)
    finished_at = models.DateTimeField(null=True, blank=True, db_index=True)
    upload_progress = models.FloatField(null=True, blank=True)
    review_status = models.CharField(
        max_length=16,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING,
        db_index=True,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_jobs",
    )
    review_comment = models.TextField(blank=True)
    review_activity_id = models.UUIDField(null=True, blank=True, editable=False)

    class Meta:
        ordering = ["-created_at"]

    objects = JobQuerySet.as_manager()

    if typing.TYPE_CHECKING:  # pragma: no cover - typing aids
        from datetime import datetime

        id: uuid.UUID
        case_id: uuid.UUID
        organization_id: uuid.UUID | None
        case: "Case"
        mode: str
        status: str
        transcript_path: str | None
        finished_at: datetime | None
        started_at: datetime | None
        created_at: datetime
        review_status: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.id} {self.status}"

    def save(self, *args, **kwargs):  # type: ignore[override]
        if self.case_id and self.organization_id is None:
            try:
                self.organization_id = self.case.organization_id
            except Exception:
                pass
        super().save(*args, **kwargs)


class JobNote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="notes")
    text = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="job_notes",
    )
    created_by_name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["job", "-created_at"])]

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return f"JobNote(job={self.job_id})"
