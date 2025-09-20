from __future__ import annotations

from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from django.conf import settings

from apps.platform.artifacts.models import CaseArtifact
from apps.platform.artifacts.serializers import CaseArtifactSerializer


class ArtifactViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CaseArtifact.objects.all()
    serializer_class = CaseArtifactSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):  # type: ignore[override]
        qs = super().get_queryset()
        user = getattr(self.request, "user", None)
        # Filter by case when provided
        case_id = self.request.query_params.get("case")
        if case_id:
            qs = qs.filter(case_id=case_id)
        if user and getattr(user, "is_authenticated", False):
            return qs
        return qs if getattr(settings, "PLATFORM_DEV_OPEN", True) else qs.none()

