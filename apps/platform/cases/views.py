from __future__ import annotations

from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from apps.platform.cases.models import Case
from apps.platform.cases.serializers import CaseSerializer


class CaseViewSet(viewsets.ModelViewSet):
    queryset = Case.objects.all()
    serializer_class = CaseSerializer
    permission_classes = [AllowAny]  # TODO: replace with auth/policy

