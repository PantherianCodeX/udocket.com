# pyright: strict

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, TYPE_CHECKING, Optional, cast

from django.conf import settings
from django.db import models

if TYPE_CHECKING:  # pragma: no cover
    from apps.platform.accounts.models import Organization, User
    from apps.platform.cases.models import Case


class JobQuerySet(models.QuerySet["Job"]):
    def for_user(self, user: Any) -> "JobQuerySet":
        from apps.platform import tenancy

        return cast("JobQuerySet", tenancy.scope_jobs(self, user))


class JobManager(models.Manager["Job"]):
    def get_queryset(self) -> JobQuerySet:
        return cast(JobQuerySet, super().get_queryset())

    def for_user(self, user: Any) -> JobQuerySet:
        return self.get_queryset().for_user(user)


class Job(models.Model):
    @classmethod
    def typed_objects(cls) -> JobManager:
        return cast(JobManager, cls.objects)
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

    id: models.UUIDField[uuid.UUID, uuid.UUID] = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    case: models.ForeignKey["Case", "Case"] = models.ForeignKey(
        "cases.Case",
        on_delete=models.PROTECT,
        related_name="jobs",
    )
    organization: models.ForeignKey["Organization", "Organization"] = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.PROTECT,
        related_name="jobs",
        editable=False,
    )
    audio_input: models.TextField[str, str] = models.TextField()
    mode: models.CharField[str, str] = models.CharField(
        max_length=16,
        choices=Mode.choices,
        default=Mode.ON_DEMAND,
    )
    diarization: models.BooleanField[bool, bool] = models.BooleanField(default=False)
    language: models.CharField[str, str] = models.CharField(max_length=16, default="en-CA")
    status: models.CharField[str, str] = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    error_message: models.TextField[Optional[str], Optional[str]] = models.TextField(null=True, blank=True)
    transcript_path: models.TextField[Optional[str], Optional[str]] = models.TextField(null=True, blank=True)
    duration_s: models.FloatField[Optional[float], Optional[float]] = models.FloatField(null=True, blank=True)
    display_title: models.CharField[str, str] = models.CharField(max_length=255, blank=True)
    agent_type: models.CharField[str, str] = models.CharField(max_length=64, blank=True, db_index=True)
    agent_label: models.CharField[str, str] = models.CharField(max_length=128, blank=True)
    job_kind: models.CharField[str, str] = models.CharField(max_length=64, blank=True, db_index=True)
    source_job: models.ForeignKey["Job", Optional["Job"]] = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="child_jobs",
    )
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True)
    started_at: models.DateTimeField[Optional[datetime], Optional[datetime]] = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )
    finished_at: models.DateTimeField[Optional[datetime], Optional[datetime]] = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )
    upload_progress: models.FloatField[Optional[float], Optional[float]] = models.FloatField(null=True, blank=True)
    review_status: models.CharField[str, str] = models.CharField(
        max_length=16,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING,
        db_index=True,
    )
    reviewed_at: models.DateTimeField[Optional[datetime], Optional[datetime]] = models.DateTimeField(null=True, blank=True)
    reviewed_by: models.ForeignKey["User", Optional["User"]] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_jobs",
    )
    review_comment: models.TextField[str, str] = models.TextField(blank=True)
    review_activity_id: models.UUIDField[Optional[uuid.UUID], Optional[uuid.UUID]] = models.UUIDField(
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:
        ordering = ["-created_at"]

    objects = JobManager()

    @classmethod
    def scoped(cls) -> JobManager:
        return cls.typed_objects()

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.id} {self.status}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        case_id_value = cast(uuid.UUID | None, getattr(self, "case_id", None))
        organization_id_value = cast(uuid.UUID | None, getattr(self, "organization_id", None))
        if case_id_value is not None and organization_id_value is None:
            case_org_id = cast(uuid.UUID | None, getattr(self.case, "organization_id", None))
            if case_org_id is not None:
                self.organization_id = case_org_id
        super().save(*args, **kwargs)


class JobNote(models.Model):
    @classmethod
    def typed_objects(cls) -> models.Manager["JobNote"]:
        return cast(models.Manager["JobNote"], cls.objects)

    @classmethod
    def scoped(cls) -> models.Manager["JobNote"]:
        return cls.typed_objects()
    id: models.UUIDField[uuid.UUID, uuid.UUID] = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    job: models.ForeignKey[Job, Job] = models.ForeignKey(
        "jobs.Job",
        on_delete=models.CASCADE,
        related_name="notes",
    )
    text: models.TextField[str, str] = models.TextField()
    created_by: models.ForeignKey["User", Optional["User"]] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="job_notes",
    )
    created_by_name: models.CharField[str, str] = models.CharField(max_length=255, blank=True)
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["job", "-created_at"])]

    def __str__(self) -> str:  # pragma: no cover - simple repr
        job_id = cast(str | None, getattr(self, "job_id", None))
        return f"JobNote(job={job_id})"
