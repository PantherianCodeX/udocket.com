# pyright: strict

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from django.db import models

from packages.common.django.typing import TypedManager, get_typed_manager

if TYPE_CHECKING:
    from apps.platform.accounts.models import Organization


class LLMProviderCredential(models.Model):
    id: models.BigAutoField[int, int] = models.BigAutoField(primary_key=True)
    uid: models.UUIDField[uuid.UUID, uuid.UUID] = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True
    )
    organization: models.ForeignKey[Organization, Organization] = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="llm_provider_credentials",
    )
    provider: models.CharField[str, str] = models.CharField(max_length=64)
    display_name: models.CharField[str, str] = models.CharField(max_length=128, blank=True)
    endpoint: models.CharField[str, str] = models.CharField(max_length=255, blank=True)
    api_key_encrypted: models.TextField[str, str] = models.TextField(blank=True)
    models_payload: models.JSONField[list[dict[str, Any]], list[dict[str, Any]]] = models.JSONField(
        default=list, blank=True
    )
    metadata: models.JSONField[dict[str, Any], dict[str, Any]] = models.JSONField(
        default=dict, blank=True
    )
    is_enabled: models.BooleanField[bool, bool] = models.BooleanField(default=True)
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("organization", "provider")

    @classmethod
    def typed_objects(cls) -> TypedManager[LLMProviderCredential]:
        return get_typed_manager(cls)

    @classmethod
    def scoped(cls) -> TypedManager[LLMProviderCredential]:
        return cls.typed_objects()


class LLMConfiguration(models.Model):
    id: models.UUIDField[uuid.UUID, uuid.UUID] = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    organization: models.ForeignKey[Organization, Organization] = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="llm_configurations",
    )
    name: models.CharField[str, str] = models.CharField(max_length=128)
    description: models.TextField[str, str] = models.TextField(blank=True)
    target: models.CharField[str, str] = models.CharField(max_length=64, default="summary")
    provider_chain: models.JSONField[list[str], list[str]] = models.JSONField(
        default=list, blank=True
    )
    stage_map: models.JSONField[dict[str, dict[str, Any]], dict[str, dict[str, Any]]] = (
        models.JSONField(default=dict, blank=True)
    )
    is_default: models.BooleanField[bool, bool] = models.BooleanField(default=False)
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("organization", "name", "target")

    @classmethod
    def typed_objects(cls) -> TypedManager[LLMConfiguration]:
        return get_typed_manager(cls)

    @classmethod
    def scoped(cls) -> TypedManager[LLMConfiguration]:
        return cls.typed_objects()


class AuditEvent(models.Model):
    id: models.BigAutoField[int, int] = models.BigAutoField(primary_key=True)
    ts: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True)
    actor: models.CharField[str, str] = models.CharField(max_length=128, blank=True)
    case_id: models.CharField[str, str] = models.CharField(max_length=36, blank=True)
    event: models.CharField[str, str] = models.CharField(max_length=64)
    data: models.JSONField[dict[str, Any], dict[str, Any]] = models.JSONField(
        default=dict, blank=True
    )

    @classmethod
    def typed_objects(cls) -> TypedManager[AuditEvent]:
        return get_typed_manager(cls)

    @classmethod
    def scoped(cls) -> TypedManager[AuditEvent]:
        return cls.typed_objects()


class GuardianSettings(models.Model):
    id: models.BigAutoField[int, int] = models.BigAutoField(primary_key=True)
    organization: models.OneToOneField[Organization, Organization] = models.OneToOneField(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="guardian_settings",
    )
    instructions: models.JSONField[list[dict[str, Any]], list[dict[str, Any]]] = models.JSONField(
        default=list, blank=True
    )
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Guardian Settings"
        verbose_name_plural = "Guardian Settings"

    def __str__(self) -> str:  # pragma: no cover - representational
        organization_id = getattr(self, "organization_id", None)
        return f"GuardianSettings(org={organization_id})"

    @classmethod
    def typed_objects(cls) -> TypedManager[GuardianSettings]:
        return get_typed_manager(cls)

    @classmethod
    def scoped(cls) -> TypedManager[GuardianSettings]:
        return cls.typed_objects()
