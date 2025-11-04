# pyright: strict

from __future__ import annotations

import uuid
from datetime import datetime
from typing import cast

from django.contrib.auth.models import AbstractUser
from django.db import models

from packages.udocket_common.django.typing import TypedManager, get_typed_manager


class Organization(models.Model):
    @classmethod
    def typed_objects(cls) -> TypedManager[Organization]:
        return get_typed_manager(cls)

    @classmethod
    def scoped(cls) -> TypedManager[Organization]:
        return cls.typed_objects()

    id: models.UUIDField[uuid.UUID, uuid.UUID] = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    name: models.CharField[str, str] = models.CharField(max_length=200)
    kc_organization_id: models.CharField[str | None, str | None] = models.CharField(
        max_length=128,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Keycloak organization identifier.",
    )
    display_name: models.CharField[str, str] = models.CharField(max_length=200, blank=True)
    address_line1: models.CharField[str, str] = models.CharField(max_length=200, blank=True)
    address_line2: models.CharField[str, str] = models.CharField(max_length=200, blank=True)
    city: models.CharField[str, str] = models.CharField(max_length=120, blank=True)
    province: models.CharField[str, str] = models.CharField(max_length=120, blank=True)
    postal_code: models.CharField[str, str] = models.CharField(max_length=20, blank=True)
    country: models.CharField[str, str] = models.CharField(max_length=120, blank=True)
    contact_name: models.CharField[str, str] = models.CharField(max_length=120, blank=True)
    contact_email: models.EmailField[str, str] = models.EmailField(blank=True)
    contact_phone: models.CharField[str, str] = models.CharField(max_length=50, blank=True)
    notes: models.TextField[str, str] = models.TextField(blank=True)
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.name


class User(AbstractUser):
    """Custom user storing Keycloak subject ID and local profile info.

    For SSO, we map Keycloak 'sub' to kc_sub.
    """

    @classmethod
    def typed_objects(cls) -> TypedManager[User]:
        return get_typed_manager(cls)

    @classmethod
    def scoped(cls) -> TypedManager[User]:
        return cls.typed_objects()

    kc_sub: models.CharField[str | None, str | None] = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
    )
    display_name: models.CharField[str | None, str | None] = models.CharField(
        max_length=200,
        null=True,
        blank=True,
    )

    def __str__(self) -> str:  # pragma: no cover - trivial
        username = cast(str | None, getattr(self, "username", None))
        if username:
            return username
        email = cast(str | None, getattr(self, "email", None))
        if email:
            return email
        return f"user:{self.pk}"


class OrganizationMembership(models.Model):
    @classmethod
    def typed_objects(cls) -> TypedManager[OrganizationMembership]:
        return get_typed_manager(cls)

    @classmethod
    def scoped(cls) -> TypedManager[OrganizationMembership]:
        return cls.typed_objects()

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        MANAGER = "MANAGER", "Manager"
        MEMBER = "MEMBER", "Member"
        SUPERUSER = "SUPERUSER", "Superuser"

    organization: models.ForeignKey[Organization, Organization] = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user: models.ForeignKey[User, User] = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="org_memberships",
    )
    role: models.CharField[str, str] = models.CharField(
        max_length=16,
        choices=Role.choices,
        default=Role.MEMBER,
    )
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("organization", "user")
        verbose_name = "Organization membership"
        verbose_name_plural = "Organization memberships"

    def __str__(self) -> str:  # pragma: no cover - trivial
        organization_id = cast(str | None, getattr(self, "organization_id", None))
        user_id = cast(int | None, getattr(self, "user_id", None))
        role = cast(str | None, getattr(self, "role", None))
        return f"{organization_id}:{user_id}:{role}"
