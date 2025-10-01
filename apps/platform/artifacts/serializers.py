from __future__ import annotations

from rest_framework import serializers

from apps.platform.artifacts.models import CaseArtifact


class CaseArtifactSerializer(serializers.ModelSerializer):
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
