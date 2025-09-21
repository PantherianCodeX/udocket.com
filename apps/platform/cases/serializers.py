from __future__ import annotations

from rest_framework import serializers

from apps.platform.artifacts.models import FieldVisibilityRule
from apps.platform.authorization.capabilities import allowed_field_actions
from apps.platform.cases.models import Case, CaseMembership


class CaseSerializer(serializers.ModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Case
        fields = ["id", "title", "organization", "created_at", "updated_at"]
        read_only_fields = ["organization", "created_at", "updated_at"]

    def to_representation(self, instance):  # type: ignore[override]
        data = super().to_representation(instance)
        request = self.context.get("request") if hasattr(self, "context") else None
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return data
        membership = (
            CaseMembership.objects.filter(case=instance, user=user)
            .only("role")
            .first()
        )
        if not membership:
            return data
        role = membership.role
        rules = {
            r.field_name: set(r.allowed_roles or [])
            for r in FieldVisibilityRule.objects.filter(
                resource=FieldVisibilityRule.Resource.CASE,
                type="CASE",
            )
        }
        for field in list(data.keys()):
            allowed_roles = rules.get(field)
            if allowed_roles is not None and role not in allowed_roles:
                data.pop(field, None)
                continue
            acts = allowed_field_actions(
                role,
                "CASE",
                field,
                organization_id=getattr(instance, "organization_id", None),
                resource=FieldVisibilityRule.Resource.CASE,
            )
            if acts and "view" not in acts:
                data.pop(field, None)
        return data
