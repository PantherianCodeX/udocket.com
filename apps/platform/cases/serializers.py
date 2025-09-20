from __future__ import annotations

from rest_framework import serializers

from apps.platform.cases.models import Case


class CaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Case
        fields = ["id", "title", "created_at", "updated_at"]

