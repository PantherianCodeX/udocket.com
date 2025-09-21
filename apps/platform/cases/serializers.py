from __future__ import annotations

from rest_framework import serializers

from apps.platform.cases.models import Case


class CaseSerializer(serializers.ModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Case
        fields = [
            "id",
            "title",
            "organization",
            "client_name",
            "opposing_party",
            "client_position",
            "court_location",
            "court_level",
            "court_division",
            "court_case_number",
            "representation",
            "legal_aid",
            "pro_bono",
            "court_date",
            "filing_deadline",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["organization", "created_at", "updated_at"]

    # Field-level filtering is now enforced by capability checks on the views.
