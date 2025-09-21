from __future__ import annotations

from typing import Any
from rest_framework import serializers

from apps.platform.artifacts.models import CaseArtifact, FieldVisibilityRule
from apps.platform.cases.models import CaseMembership
from apps.platform.authorization.capabilities import allowed_field_actions


def _user_role_for_case(user, case_id: str | None) -> str | None:
    try:
        if not case_id:
            return None
        m = CaseMembership.objects.filter(user=user, case_id=case_id).first()
        return m.role if m else None
    except Exception:
        return None


class FieldPermissionSerializerMixin:
    def _prune_fields(self, instance: CaseArtifact, data: dict[str, Any]) -> dict[str, Any]:
        user = getattr(getattr(self, "context", None), "get", lambda *_: None)("request")
        if user:
            user = getattr(self.context.get("request"), "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return data
        role = _user_role_for_case(user, getattr(instance, 'case_fk_id', None) or instance.case_id)
        if not role:
            return data
        rules = {
            r.field_name: set(r.allowed_roles or [])
            for r in FieldVisibilityRule.objects.filter(
                resource=FieldVisibilityRule.Resource.ARTIFACT,
                type=instance.type,
            )
        }
        # FieldVisibilityRule: if rule exists and role not allowed, drop the field
        org_id = getattr(instance, "organization_id", None)
        for fname in list(data.keys()):
            allowed_roles = rules.get(fname)
            if allowed_roles is not None and role not in allowed_roles:
                data.pop(fname, None)
                continue
            # Preset policies: require 'view' action when policies exist
            acts = allowed_field_actions(
                role,
                instance.type,
                fname,
                organization_id=org_id,
                resource=FieldVisibilityRule.Resource.ARTIFACT,
            )
            if acts and "view" not in acts:
                data.pop(fname, None)
        return data


class CaseArtifactSerializer(FieldPermissionSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = CaseArtifact
        fields = [
            "id",
            "case_id",
            "job_id",
            "type",
            "title",
            "path",
            "checksum",
            "schema_version",
            "created_at",
            "metadata",
        ]

    def to_representation(self, instance):  # type: ignore[override]
        raw = super().to_representation(instance)
        return self._prune_fields(instance, raw)
