# pyright: strict

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from django.db import models

from packages.common.django.typing import TypedManager, get_typed_manager

if TYPE_CHECKING:
    from apps.platform.accounts.models import Organization


class Role(models.Model):
    @classmethod
    def typed_objects(cls) -> TypedManager[Role]:
        return get_typed_manager(cls)

    @classmethod
    def scoped(cls) -> TypedManager[Role]:
        return cls.typed_objects()

    """Global role catalog for configurable RBAC.

    These roles can be mapped to external IAM roles or CaseMemberships.
    """

    uuid: models.UUIDField[uuid.UUID | None, uuid.UUID | None] = models.UUIDField(
        editable=False,
        unique=True,
        null=True,
        blank=True,
    )
    name: models.CharField[str, str] = models.CharField(max_length=100)
    description: models.TextField[str, str] = models.TextField(blank=True)
    system: models.BooleanField[bool, bool] = models.BooleanField(default=False)
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True)
    organization: models.ForeignKey[Organization, Organization | None] = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="authorization_roles",
        null=True,
        blank=True,
    )
    # Attach preset bundles to roles
    # Defined below but string-referenced to avoid ordering issues
    presets: models.ManyToManyField[PermissionPreset, PermissionPreset] = models.ManyToManyField(
        "authorization.PermissionPreset",
        blank=True,
        related_name="roles",
    )

    class Meta:
        ordering = ["name"]
        unique_together = ("organization", "name")

    def __str__(self) -> str:  # pragma: no cover - trivial
        label = self.name or str(self.uuid)
        organization_identifier = getattr(self, "organization_id", None)
        if organization_identifier:
            return f"{label} ({organization_identifier})"
        return label

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.uuid:
            self.uuid = uuid.uuid4()
        super().save(*args, **kwargs)


class RoleCapability(models.Model):
    @classmethod
    def typed_objects(cls) -> TypedManager[RoleCapability]:
        return get_typed_manager(cls)

    @classmethod
    def scoped(cls) -> TypedManager[RoleCapability]:
        return cls.typed_objects()

    """Assigns capabilities (string keys) to roles.

    Capabilities are strings constrained by application code, e.g.:
      - case.view, case.update
      - job.create
      - artifact.view, artifact.download
      - artifact.field.path.view
    """

    role: models.ForeignKey[Role, Role] = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="capabilities",
    )
    capability: models.CharField[str, str] = models.CharField(max_length=100, db_index=True)
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("role", "capability")
        indexes = [models.Index(fields=["capability"])]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.role.name}:{self.capability}"


class PermissionPreset(models.Model):
    @classmethod
    def typed_objects(cls) -> TypedManager[PermissionPreset]:
        return get_typed_manager(cls)

    @classmethod
    def scoped(cls) -> TypedManager[PermissionPreset]:
        return cls.typed_objects()

    uuid: models.UUIDField[uuid.UUID | None, uuid.UUID | None] = models.UUIDField(
        editable=False,
        unique=True,
        null=True,
        blank=True,
    )
    name: models.CharField[str, str] = models.CharField(max_length=120)
    description: models.TextField[str, str] = models.TextField(blank=True)
    system: models.BooleanField[bool, bool] = models.BooleanField(default=False)
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True)
    organization: models.ForeignKey[Organization, Organization | None] = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="authorization_presets",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["name"]
        unique_together = ("organization", "name")

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.name or str(self.uuid)

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.uuid:
            self.uuid = uuid.uuid4()
        super().save(*args, **kwargs)


class PresetCapability(models.Model):
    @classmethod
    def typed_objects(cls) -> TypedManager[PresetCapability]:
        return get_typed_manager(cls)

    @classmethod
    def scoped(cls) -> TypedManager[PresetCapability]:
        return cls.typed_objects()

    preset: models.ForeignKey[PermissionPreset, PermissionPreset] = models.ForeignKey(
        PermissionPreset,
        on_delete=models.CASCADE,
        related_name="capabilities",
    )
    capability: models.CharField[str, str] = models.CharField(max_length=100, db_index=True)

    class Meta:
        unique_together = ("preset", "capability")
        indexes = [models.Index(fields=["capability"])]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.preset.name}:{self.capability}"
