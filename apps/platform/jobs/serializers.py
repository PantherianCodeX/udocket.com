from __future__ import annotations

from django.conf import settings
from rest_framework import serializers

from apps.platform.authorization.capabilities import has_capability
from apps.platform.jobs.models import Job


class JobCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = [
            "case",
            "audio_input",
            "mode",
            "diarization",
            "language",
        ]


class JobSerializer(serializers.ModelSerializer):
    case_id = serializers.CharField(read_only=True)

    class Meta:
        model = Job
        fields = [
            "id",
            "case",
            "case_id",
            "audio_input",
            "mode",
            "diarization",
            "language",
            "status",
            "error_message",
            "transcript_path",
            "duration_s",
            "created_at",
            "started_at",
            "finished_at",
        ]
        read_only_fields = [
            "status",
            "error_message",
            "transcript_path",
            "duration_s",
            "created_at",
            "started_at",
            "finished_at",
        ]

    def to_representation(self, instance):  # type: ignore[override]
        data = super().to_representation(instance)
        request = self.context.get("request") if hasattr(self, "context") else None
        user = getattr(request, "user", None)
        dev_open = bool(getattr(settings, "PLATFORM_DEV_OPEN", True))

        if not user or not getattr(user, "is_authenticated", False):
            if not dev_open:
                data.pop("audio_input", None)
                data.pop("transcript_path", None)
            return data

        case_id = str(getattr(instance, "case_id", ""))
        if case_id:
            if not has_capability(user, case_id, "artifact.download"):
                data.pop("audio_input", None)
            if not has_capability(user, case_id, "artifact.field.path.view"):
                data.pop("transcript_path", None)
        else:
            data.pop("audio_input", None)
            data.pop("transcript_path", None)
        return data
