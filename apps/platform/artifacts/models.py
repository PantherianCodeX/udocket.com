# pyright: strict

from __future__ import annotations

from datetime import datetime
import uuid
from typing import Any, TYPE_CHECKING, Optional, cast

from django.db import models
from simple_history.models import HistoricalRecords

if TYPE_CHECKING:
    from apps.platform.accounts.models import Organization
    from apps.platform.cases.models import Case


class CaseArtifactQuerySet(models.QuerySet["CaseArtifact"]):
    def for_user(self, user: Any) -> "CaseArtifactQuerySet":
        from apps.platform import tenancy

        return cast("CaseArtifactQuerySet", tenancy.scope_artifacts(self, user))


class CaseArtifactManager(models.Manager["CaseArtifact"]):
    def get_queryset(self) -> CaseArtifactQuerySet:
        return cast(CaseArtifactQuerySet, super().get_queryset())

    def for_user(self, user: Any) -> CaseArtifactQuerySet:
        return self.get_queryset().for_user(user)


class CaseArtifact(models.Model):
    @classmethod
    def typed_objects(cls) -> CaseArtifactManager:
        return cast(CaseArtifactManager, cls.objects)
    """Generic artifact record; full schema to follow in Step 4."""

    id: models.BigAutoField[int, int] = models.BigAutoField(primary_key=True)
    case_id: models.CharField[str, str] = models.CharField(max_length=36)
    # Optional FK for normalization; kept nullable for backcompat while migrating
    case_fk: models.ForeignKey["Case", Optional["Case"]] = models.ForeignKey(
        "cases.Case",
        on_delete=models.PROTECT,
        related_name="artifacts",
        null=True,
        blank=True,
    )
    organization: models.ForeignKey["Organization", "Organization"] = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.PROTECT,
        related_name="artifacts",
        editable=False,
    )
    job_id: models.CharField[Optional[str], Optional[str]] = models.CharField(max_length=36, null=True, blank=True)
    type: models.CharField[str, str] = models.CharField(max_length=32)
    title: models.CharField[str, str] = models.CharField(max_length=200, blank=True)
    path: models.TextField[str, str] = models.TextField()
    checksum: models.CharField[str, str] = models.CharField(max_length=64, blank=True)
    schema_version: models.CharField[str, str] = models.CharField(max_length=16, blank=True)
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True)
    metadata: models.JSONField[dict[str, Any], dict[str, Any]] = models.JSONField(default=dict, blank=True)
    history: HistoricalRecords["CaseArtifact"] = HistoricalRecords()

    objects = CaseArtifactManager()

    @classmethod
    def scoped(cls) -> CaseArtifactManager:
        return cls.typed_objects()

    class Meta:
        indexes = [
            models.Index(fields=["case_id", "type"], name="artifact_case_type_idx"),
            models.Index(fields=["created_at"], name="artifact_created_idx"),
        ]
        unique_together = ("case_id", "type", "title")

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.case_id}:{self.type}:{self.title or self.path}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        organization_id_value = cast(uuid.UUID | None, getattr(self, "organization_id", None))
        if organization_id_value is None:
            resolved_org_id: uuid.UUID | None = None
            case_fk_id_value = cast(uuid.UUID | None, getattr(self, "case_fk_id", None))
            if case_fk_id_value is not None:
                case_fk = getattr(self, "case_fk", None)
                if case_fk is not None:
                    resolved_org_id = cast(uuid.UUID | None, getattr(case_fk, "organization_id", None))
            elif self.case_id:
                from apps.platform.cases.models import Case  # local import to avoid circular

                resolved_org_id = Case.objects.filter(id=self.case_id).values_list(
                    "organization_id", flat=True
                ).first()
            if resolved_org_id is not None:
                self.organization_id = resolved_org_id
        super().save(*args, **kwargs)
