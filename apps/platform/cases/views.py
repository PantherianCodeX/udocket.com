from __future__ import annotations

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from apps.platform.authorization.access_policies import CaseAccessPolicy
from django.conf import settings

from apps.platform.cases.models import Case
from apps.platform.cases.serializers import CaseSerializer
from apps.platform.cases.models import CaseMembership
from apps.platform.authorization.capabilities import role_capabilities
from apps.platform.operations.audit import emit as audit_emit


class CaseViewSet(viewsets.ModelViewSet):
    queryset = Case.objects.all()
    serializer_class = CaseSerializer
    permission_classes = [CaseAccessPolicy]

    def get_queryset(self):  # type: ignore[override]
        qs = super().get_queryset()
        user = getattr(self.request, "user", None)
        if user and user.is_authenticated:
            return qs.filter(memberships__user=user).distinct()
        # Anonymous users only see data when PLATFORM_DEV_OPEN is enabled
        return qs if getattr(settings, "PLATFORM_DEV_OPEN", True) else qs.none()

    @action(detail=True, methods=["get"], url_path="capabilities")
    def capabilities(self, request, pk=None):
        """Return the effective capabilities for the current user on this case.

        Useful for UI gating without exposing sensitive fields.
        """
        case = self.get_object()
        user = getattr(request, "user", None)
        role = None
        if user and getattr(user, "is_authenticated", False):
            m = CaseMembership.objects.filter(case=case, user=user).first()
            role = m.role if m else None
        caps = sorted(list(role_capabilities(role))) if role else []
        return Response({"case": str(case.id), "role": role, "capabilities": caps})

    def retrieve(self, request, *args, **kwargs):  # type: ignore[override]
        resp = super().retrieve(request, *args, **kwargs)
        try:
            obj = self.get_object()
            audit_emit(request, case_id=str(obj.id), event="case.retrieve", data={})
        except Exception:
            pass
        return resp

    def list(self, request, *args, **kwargs):  # type: ignore[override]
        resp = super().list(request, *args, **kwargs)
        try:
            audit_emit(request, case_id=None, event="case.list", data={"count": len(resp.data) if hasattr(resp, 'data') else None})
        except Exception:
            pass
        return resp
