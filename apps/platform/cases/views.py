from __future__ import annotations

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import PermissionDenied
from apps.platform.authorization.access_policies import CaseAccessPolicy
from django.conf import settings

from apps.platform.cases.models import Case
from apps.platform.cases.serializers import CaseSerializer
from apps.platform.cases.models import CaseMembership
from apps.platform.authorization.capabilities import role_capabilities
from apps.platform.operations.audit import emit as audit_emit
from apps.platform.tenancy import scope_cases, scope_jobs
from apps.platform.accounts.models import OrganizationMembership
from apps.platform.accounts.utils import resolve_request_organization
from apps.platform.jobs.models import Job
from apps.platform.jobs.serializers import JobTelemetrySerializer
from apps.platform.jobs.telemetry import summarize_jobs


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
            m = CaseMembership.objects.filter(case=case, user=user).select_related("case__organization").first()
            role = m.role if m else None
            org_id = m.case.organization_id if m and m.case_id else None
        else:
            role = None
            org_id = None
        caps = sorted(list(role_capabilities(role, organization_id=org_id))) if role else []
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
        try:
            organization = resolve_request_organization(self.request, required=True)
        except PermissionDenied as exc:
            raise PermissionDenied(str(exc))
        if not user or not getattr(user, "is_authenticated", False):
            if getattr(settings, "PLATFORM_DEV_OPEN", False):
                serializer.save(organization=organization)
                return
            raise PermissionDenied("Authentication required to create cases.")
        if not OrganizationMembership.objects.filter(user=user, organization=organization).exists():
            raise PermissionDenied("User is not a member of the selected organization.")
        serializer.save(organization=organization)

    @action(detail=True, methods=["get"], url_path="jobs/summary")
    def jobs_summary(self, request, pk=None):
        case = self.get_object()
        jobs = scope_jobs(
            Job.objects.filter(case=case).select_related("case", "case__organization").order_by("-created_at"),
            getattr(request, "user", None),
        )
        summary = summarize_jobs(jobs)
        last_update = summary.get("last_update")
        summary["last_update"] = last_update.isoformat() if last_update else None
        return Response(summary)

    @action(detail=True, methods=["get"], url_path="jobs/detail")
    def jobs_detail(self, request, pk=None):
        case = self.get_object()
        jobs = scope_jobs(
            Job.objects.filter(case=case).select_related("case", "case__organization").order_by("-created_at"),
            getattr(request, "user", None),
        )
        serializer = JobTelemetrySerializer(jobs, many=True, context={"request": request})
        return Response({"jobs": serializer.data})
