from __future__ import annotations

from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from apps.platform.authorization.access_policies import ArtifactAccessPolicy
from django.conf import settings

from apps.platform.artifacts.models import CaseArtifact
from django.db.models import Q
from apps.platform.artifacts.serializers import CaseArtifactSerializer
from apps.platform.operations.audit import emit as audit_emit


class ArtifactViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CaseArtifact.objects.all()
    serializer_class = CaseArtifactSerializer
    permission_classes = [ArtifactAccessPolicy]

    def get_queryset(self):  # type: ignore[override]
        qs = super().get_queryset()
        user = getattr(self.request, "user", None)
        # Filter by case when provided
        case_id = self.request.query_params.get("case")
        if case_id:
            qs = qs.filter(Q(case_id=case_id) | Q(case_fk__id=case_id))
        if user and getattr(user, "is_authenticated", False):
            return qs
        return qs if getattr(settings, "PLATFORM_DEV_OPEN", True) else qs.none()

    def retrieve(self, request, *args, **kwargs):  # type: ignore[override]
        resp = super().retrieve(request, *args, **kwargs)
        try:
            obj = self.get_object()
            audit_emit(request, case_id=obj.case_id, event="artifact.retrieve", data={"artifact_id": obj.id, "type": obj.type})
        except Exception:
            pass
        return resp

    def list(self, request, *args, **kwargs):  # type: ignore[override]
        resp = super().list(request, *args, **kwargs)
        try:
            case_id = request.query_params.get("case")
            audit_emit(request, case_id=case_id, event="artifact.list", data={"count": len(resp.data) if hasattr(resp, 'data') else None})
        except Exception:
            pass
        return resp
