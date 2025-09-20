from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user storing Keycloak subject ID and local profile info.

    For SSO, we map Keycloak 'sub' to kc_sub.
    """

    kc_sub = models.CharField(max_length=64, unique=True, null=True, blank=True)
    display_name = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.username or self.email or f"user:{self.pk}"

