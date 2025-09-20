from __future__ import annotations

from rest_framework import serializers

from apps.platform.cases.models import Case
from apps.platform.accounts.models import Organization


class CaseSerializer(serializers.ModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(), allow_null=True, required=False
    )

    class Meta:
        model = Case
        fields = ["id", "title", "organization", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]
