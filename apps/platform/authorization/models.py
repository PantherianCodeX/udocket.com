from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models

from apps.platform.artifacts.registry import artifact_field


FIELD_ACTION_ALLOWLIST = {"view", "download", "update", "create", "delete"}


def _normalize_actions(actions: list[str] | tuple[str, ...] | None) -> list[str]:
    normalized: list[str] = []
    if not actions:
        return normalized
    for act in actions:
        sval = (act or "").strip().lower()
        if not sval:
            continue
        if sval not in FIELD_ACTION_ALLOWLIST:
            raise ValidationError({"actions": f"Unsupported action '{sval}'"})
        if sval not in normalized:
            normalized.append(sval)
    return normalized

class Role(models.Model):
    """Global role catalog for configurable RBAC.

    These roles can be mapped to external IAM roles or to CaseMemberships.
    """

    slug = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    system = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    # Attach preset bundles to roles
    # Defined below but string-referenced to avoid ordering issues
    presets = models.ManyToManyField("authorization.PermissionPreset", blank=True, related_name="roles")

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


class PermissionPreset(models.Model):
    slug = models.SlugField(max_length=64, unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    system = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["slug"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.name or self.slug


class PresetCapability(models.Model):
    preset = models.ForeignKey(PermissionPreset, on_delete=models.CASCADE, related_name="capabilities")
    capability = models.CharField(max_length=100, db_index=True)

    class Meta:
        unique_together = ("preset", "capability")
        indexes = [models.Index(fields=["capability"])]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.preset.slug}:{self.capability}"


class PresetFieldPolicy(models.Model):
    preset = models.ForeignKey(PermissionPreset, on_delete=models.CASCADE, related_name="field_policies")
    type = models.CharField(max_length=32)  # artifact type
    field_name = models.CharField(max_length=64)
    actions = models.JSONField(default=list, blank=True)  # e.g., ["view", "update", "create", "download"]
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("preset", "type", "field_name")
        indexes = [models.Index(fields=["type", "field_name"])]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.preset.slug}:{self.type}.{self.field_name}"

    def clean(self) -> None:  # pragma: no cover - validated in tests
        super().clean()
        if self.type:
            self.type = self.type.upper()
        self.field_name = (self.field_name or "").strip()
        if not self.field_name:
            raise ValidationError({"field_name": "Field name is required."})
        if artifact_field(self.type, self.field_name) is None:
            raise ValidationError({
                "field_name": f"Unknown artifact field: {self.type}.{self.field_name}",
            })
        raw_actions = self.actions
        if raw_actions in (None, ""):
            raw_list: list[str] = []
        elif isinstance(raw_actions, (list, tuple)):
            raw_list = list(raw_actions)
        else:
            raise ValidationError({"actions": "Actions must be provided as a list."})
        self.actions = _normalize_actions(raw_list)

    def save(self, *args, **kwargs):  # type: ignore[override]
        self.full_clean()
        return super().save(*args, **kwargs)
