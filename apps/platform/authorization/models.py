from __future__ import annotations

from django.db import models


class Role(models.Model):
    """Global role catalog for configurable RBAC.

    These roles can be mapped to external IAM roles or to CaseMemberships.
    """

    slug = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    system = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["slug"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.name or self.slug


class RoleCapability(models.Model):
    """Assigns capabilities (string keys) to roles.

    Capabilities are strings constrained by application code, e.g.:
      - case.view, case.update
      - job.create
      - artifact.view, artifact.download
      - artifact.field.path.view
    """

    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="capabilities")
    capability = models.CharField(max_length=100, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("role", "capability")
        indexes = [models.Index(fields=["capability"])]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.role.slug}:{self.capability}"
