from __future__ import annotations

import uuid

import typing

from django.contrib.auth.models import AbstractUser
from django.db import models


class Organization(models.Model):
    id = models.CharField(primary_key=True, max_length=64)
    uid = models.UUIDField(editable=False, unique=True, null=True, blank=True)
    name = models.CharField(max_length=200)
    display_name = models.CharField(max_length=200, blank=True)
    address_line1 = models.CharField(max_length=200, blank=True)
    address_line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=120, blank=True)
    province = models.CharField(max_length=120, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=120, blank=True)
    contact_name = models.CharField(max_length=120, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.name

    def save(self, *args, **kwargs):  # type: ignore[override]
        if not self.uid:
            self.uid = uuid.uuid4()
        super().save(*args, **kwargs)

    if typing.TYPE_CHECKING:  # pragma: no cover - typing aids
        id: str
        uid: uuid.UUID | None
        name: str


class User(AbstractUser):
    """Custom user storing Keycloak subject ID and local profile info.

    For SSO, we map Keycloak 'sub' to kc_sub.
    """

    kc_sub = models.CharField(max_length=64, unique=True, null=True, blank=True)
    display_name = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.username or self.email or f"user:{self.pk}"


class OrganizationMembership(models.Model):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        MANAGER = "MANAGER", "Manager"
        MEMBER = "MEMBER", "Member"
        SUPERUSER = "SUPERUSER", "Superuser"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="org_memberships")
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.MEMBER)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("organization", "user")
        verbose_name = "Organization membership"
        verbose_name_plural = "Organization memberships"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.organization_id}:{self.user_id}:{self.role}"

    if typing.TYPE_CHECKING:  # pragma: no cover - typing aids
        from apps.platform.accounts.models import Organization, User

        organization: Organization
        organization_id: str
        user: User
        user_id: int
