from __future__ import annotations

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import PermissionDenied, ValidationError
from apps.platform.authorization.access_policies import CaseAccessPolicy
from django.conf import settings

from apps.platform.cases.models import Case
from apps.platform.cases.serializers import CaseSerializer
from apps.platform.cases.models import CaseMembership
from apps.platform.authorization.capabilities import role_capabilities
from apps.platform.operations.audit import emit as audit_emit
from apps.platform.tenancy import scope_cases
from apps.platform.accounts.models import OrganizationMembership


class CaseViewSet(viewsets.ModelViewSet):
    queryset = Case.objects.all()
    serializer_class = CaseSerializer
    permission_classes = [CaseAccessPolicy]

    def get_queryset(self):  # type: ignore[override]
        qs = super().get_queryset().select_related("organization")
        user = getattr(self.request, "user", None)
        return scope_cases(qs, user)

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

    def perform_create(self, serializer):  # type: ignore[override]
        user = getattr(self.request, "user", None)
        organization = serializer.validated_data.get("organization")
        if organization is None:
            raise ValidationError({"organization": "This field is required."})
        if not user or not getattr(user, "is_authenticated", False):
            if getattr(settings, "PLATFORM_DEV_OPEN", False):
                serializer.save()
                return
            raise PermissionDenied("Authentication required to create cases.")
        if not OrganizationMembership.objects.filter(user=user, organization=organization).exists():
            raise PermissionDenied("User is not a member of the selected organization.")
        serializer.save()
