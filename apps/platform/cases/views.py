from __future__ import annotations

from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from django.conf import settings

from apps.platform.cases.models import Case
from apps.platform.cases.serializers import CaseSerializer


class CaseViewSet(viewsets.ModelViewSet):
    queryset = Case.objects.all()
    serializer_class = CaseSerializer
    permission_classes = [AllowAny]  # Will switch to authenticated policies when IAM is ready

    def get_queryset(self):  # type: ignore[override]
        qs = super().get_queryset()
        user = getattr(self.request, "user", None)
        if user and user.is_authenticated:
            return qs.filter(memberships__user=user).distinct()
        # Anonymous users only see data when PLATFORM_DEV_OPEN is enabled
        return qs if getattr(settings, "PLATFORM_DEV_OPEN", True) else qs.none()
