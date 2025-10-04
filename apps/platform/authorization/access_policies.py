from __future__ import annotations

try:
    from drf_access_policy import AccessPolicy  # type: ignore
except Exception:  # Fallback when dependency unavailable (dev bootstrap)
    from rest_framework.permissions import BasePermission

    class AccessPolicy(BasePermission):  # type: ignore
        statements: list = []

        def _is_open(self, request) -> bool:
            from django.conf import settings

            return bool(getattr(settings, "PLATFORM_DEV_OPEN", True))

        def _resolve_action(self, request, view) -> str:
            action = getattr(view, "action", None)
            if action:
                return str(action)
            return request.method.lower()

        def _actions_match(self, action: str, statement_actions) -> bool:
            if statement_actions == "*":
                return True
            if isinstance(statement_actions, (list, tuple, set)):
                return action in statement_actions
            return action == statement_actions

        def _check_condition(self, condition, request, view, action) -> bool:
            if not condition:
                return True
            method = getattr(self, condition, None)
            if not callable(method):
                return False
            return bool(method(request, view, action))

        def _evaluate(self, request, view, action: str) -> bool:
            decision: bool | None = None
            for stmt in self.statements or []:
                stmt_actions = stmt.get("action")
                if stmt_actions is None:
                    continue
                if not self._actions_match(action, stmt_actions):
                    continue
                if not self._check_condition(stmt.get("condition"), request, view, action):
                    continue
                effect = (stmt.get("effect") or "").lower()
                if effect == "deny":
                    return False
                if effect == "allow":
                    decision = True
            return bool(decision)

        def has_permission(self, request, view):
            if self._is_open(request):
                return True
            action = self._resolve_action(request, view)
            return self._evaluate(request, view, action)

        def has_object_permission(self, request, view, obj):
            if self._is_open(request):
                return True
            action = self._resolve_action(request, view)
            setattr(request, "_access_policy_obj", obj)
            try:
                return self._evaluate(request, view, action)
            finally:
                if hasattr(request, "_access_policy_obj"):
                    delattr(request, "_access_policy_obj")

from django.conf import settings
from apps.platform.cases.models import Case, CaseMembership
from apps.platform.authorization.capabilities import has_capability


class _MembershipMixin:
    def _is_dev_open(self) -> bool:
        return bool(getattr(settings, "PLATFORM_DEV_OPEN", True))

    def _resolve_case_id(self, request, view) -> str | None:
        obj = getattr(request, "_access_policy_obj", None)
        if obj is not None:
            case_id = getattr(obj, "case_id", None)
            if case_id:
                return str(case_id)
            case = getattr(obj, "case", None)
            if case is not None:
                cid = getattr(case, "id", None)
                if cid:
                    return str(cid)
            if obj.__class__.__name__ == "Case":
                cid = getattr(obj, "id", None)
                if cid:
                    return str(cid)

        # Fall back to request payload
        data = getattr(request, "data", None)
        if data:
            case_id = data.get("case") or data.get("case_id")
            if case_id:
                return str(case_id)

        # Query params (e.g., list filtering)
        params = getattr(request, "query_params", None)
        if params:
            case_id = params.get("case") or params.get("case_id")
            if case_id:
                return str(case_id)

        # URL kwargs (nested routes)
        kwargs = getattr(view, "kwargs", {}) or {}
        for key in ("case_pk", "case_id"):
            case_id = kwargs.get(key)
            if case_id:
                return str(case_id)
        pk = kwargs.get("pk")
        if pk and view.__class__.__name__.lower().startswith("case"):
            return str(pk)

        return None

    def _membership_role(self, user, case_id: str | None) -> str | None:
        if not case_id:
            return None
        try:
            membership = CaseMembership.objects.filter(case_id=case_id, user=user).first()
            return membership.role if membership else None
        except Exception:
            return None

    def _has_cap(self, request, view, capability: str) -> bool:
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return self._is_dev_open()
        case_id = self._resolve_case_id(request, view)
        if not case_id:
            return True
        try:
            return has_capability(user, case_id, capability)
        except Exception:
            return False

    def is_case_member(self, request, view, action) -> bool:
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return self._is_dev_open()
        case_id = self._resolve_case_id(request, view)
        if case_id is None:
            return True
        return CaseMembership.objects.filter(case_id=case_id, user=user).exists()

    def can_manage_case(self, request, view, action) -> bool:
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return self._is_dev_open()
        case_id = self._resolve_case_id(request, view)
        if not case_id:
            return False
        if self._has_cap(request, view, "case.update"):
            return True
        role = self._membership_role(user, case_id)
        return role in {
            CaseMembership.Role.OWNER,
            CaseMembership.Role.ADMIN,
            CaseMembership.Role.SUPERUSER,
        }

    def can_manage_jobs(self, request, view, action) -> bool:
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return self._is_dev_open()
        case_id = self._resolve_case_id(request, view)
        if not case_id:
            return True
        if self._has_cap(request, view, "job.create"):
            return True
        role = self._membership_role(user, case_id)
        return role in {
            CaseMembership.Role.OWNER,
            CaseMembership.Role.CONTRIBUTOR,
            CaseMembership.Role.ADMIN,
            CaseMembership.Role.SUPERUSER,
        }

    def can_review_job(self, request, view, action) -> bool:
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return self._is_dev_open()
        case_id = self._resolve_case_id(request, view)
        if not case_id:
            # Allow the request to proceed so object-level evaluation can enforce membership.
            return True
        if self._has_cap(request, view, "case.update"):
            return True
        if CaseMembership.objects.filter(case_id=case_id, user=user, role=CaseMembership.Role.REVIEWER).exists():
            return True
        try:
            case = Case.objects.get(pk=case_id)
            if case.reviewer_id and str(case.reviewer_id) == str(user.id):
                return True
        except Case.DoesNotExist:
            return False
        return False

    def can_download_artifacts(self, request, view, action) -> bool:
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return self._is_dev_open()
        case_id = self._resolve_case_id(request, view)
        if not case_id:
            return True
        return self._has_cap(request, view, "artifact.download")

    def can_view_artifacts(self, request, view, action) -> bool:
        case_id = self._resolve_case_id(request, view)
        if case_id is None:
            return self.is_case_member(request, view, action)
        return self._has_cap(request, view, "artifact.view")

    def can_create_case(self, request, view, action) -> bool:
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return self._is_dev_open()
        return True


class CaseAccessPolicy(_MembershipMixin, AccessPolicy):
    statements = [
        {"action": ["list", "retrieve", "jobs_summary", "jobs_detail"], "principal": "*", "effect": "allow", "condition": "is_case_member"},
        {"action": ["create"], "principal": "*", "effect": "allow", "condition": "can_create_case"},
        {"action": ["update", "partial_update"], "principal": "*", "effect": "allow", "condition": "can_manage_case"},
        {"action": ["destroy"], "principal": "*", "effect": "deny"},
    ]


class JobAccessPolicy(_MembershipMixin, AccessPolicy):
    statements = [
        {"action": ["list", "retrieve", "telemetry"], "principal": "*", "effect": "allow", "condition": "is_case_member"},
        {"action": ["create", "upload", "analyze_summary", "analyze_timeline", "analyze_graph"], "principal": "*", "effect": "allow", "condition": "can_manage_jobs"},
        {"action": ["status", "bulk_status"], "principal": "*", "effect": "allow", "condition": "is_case_member"},
        {"action": ["notes"], "principal": "*", "effect": "allow", "condition": "can_review_job"},
        {"action": ["download", "logs"], "principal": "*", "effect": "allow", "condition": "can_download_artifacts"},
        {"action": ["approve", "reject"], "principal": "*", "effect": "allow", "condition": "is_case_member"},
        {"action": ["destroy", "update", "partial_update"], "principal": "*", "effect": "deny"},
    ]


class ArtifactAccessPolicy(_MembershipMixin, AccessPolicy):
    statements = [
        {"action": ["list", "retrieve"], "principal": "*", "effect": "allow", "condition": "can_view_artifacts"},
    ]
