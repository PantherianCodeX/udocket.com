from __future__ import annotations

try:
    from drf_access_policy import AccessPolicy  # type: ignore
except Exception:  # Fallback when dependency unavailable (dev bootstrap)
    from rest_framework.permissions import BasePermission

    class AccessPolicy(BasePermission):  # type: ignore
        statements: list = []
        def has_permission(self, request, view):
            from django.conf import settings
            return bool(getattr(settings, "PLATFORM_DEV_OPEN", True)) or (getattr(request, "user", None) and getattr(request.user, "is_authenticated", False))
        def has_object_permission(self, request, view, obj):
            return self.has_permission(request, view)

from django.conf import settings
from apps.platform.cases.models import CaseMembership
from apps.platform.authorization.capabilities import has_capability


class _MembershipMixin:
    def is_case_member(self, request, view, action) -> bool:
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return bool(getattr(settings, "PLATFORM_DEV_OPEN", True))
        obj = None
        try:
            if hasattr(view, "get_object"):
                obj = view.get_object()
        except Exception:
            obj = None
        case_id = None
        if obj is not None:
            case_id = getattr(obj, "case_id", None)
            if case_id is None:
                case = getattr(obj, "case", None)
                case_id = getattr(case, "id", None)
        if case_id is None:
            return True
        return CaseMembership.objects.filter(case_id=case_id, user=user).exists()

    def can_contribute(self, request, view, action) -> bool:
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return bool(getattr(settings, "PLATFORM_DEV_OPEN", True))
        obj = None
        try:
            if hasattr(view, "get_object"):
                obj = view.get_object()
        except Exception:
            obj = None
        case_id = None
        if obj is not None:
            case_id = getattr(obj, "case_id", None)
            if case_id is None:
                case = getattr(obj, "case", None)
                case_id = getattr(case, "id", None)
        if case_id is None:
            return True
        try:
            if has_capability(user, case_id, "case.update"):
                return True
        except Exception:
            pass
        return CaseMembership.objects.filter(case_id=case_id, user=user, role__in=[
            CaseMembership.Role.OWNER, CaseMembership.Role.CONTRIBUTOR
        ]).exists()


class CaseAccessPolicy(_MembershipMixin, AccessPolicy):
    statements = [
        {"action": ["list", "retrieve"], "principal": "*", "effect": "allow", "condition": "is_case_member"},
        {"action": ["create", "update", "partial_update"], "principal": "*", "effect": "allow", "condition": "can_contribute"},
        {"action": ["destroy"], "principal": "*", "effect": "deny"},
    ]


class JobAccessPolicy(_MembershipMixin, AccessPolicy):
    statements = [
        {"action": ["list", "retrieve"], "principal": "*", "effect": "allow", "condition": "is_case_member"},
        {"action": ["create"], "principal": "*", "effect": "allow", "condition": "can_contribute"},
        {"action": ["status", "download", "logs"], "principal": "*", "effect": "allow", "condition": "is_case_member"},
        {"action": ["destroy", "update", "partial_update"], "principal": "*", "effect": "deny"},
    ]


class ArtifactAccessPolicy(_MembershipMixin, AccessPolicy):
    statements = [
        {"action": ["list", "retrieve"], "principal": "*", "effect": "allow", "condition": "is_case_member"},
    ]
