from __future__ import annotations

from rest_framework import serializers

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
