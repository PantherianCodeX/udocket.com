from __future__ import annotations

import importlib
import importlib.util
from types import SimpleNamespace
from typing import Any, Mapping, MutableMapping, Protocol, Sequence, TypedDict, cast

django_conf_spec = importlib.util.find_spec("django.conf")
if django_conf_spec is not None:
    settings = importlib.import_module("django.conf").settings  # type: ignore[attr-defined]
else:  # pragma: no cover - lightweight typing stub when Django is unavailable
    settings = SimpleNamespace(PLATFORM_DEV_OPEN=True)
from apps.platform.cases.models import Case, CaseMembership
from apps.platform.authorization.capabilities import has_capability


def _case_membership_manager() -> Any:
    case_membership_model = cast(Any, CaseMembership)
    return case_membership_model.objects


def _case_manager() -> Any:
    case_model = cast(Any, Case)
    return case_model.objects


class RequestLike(Protocol):
    method: str
    user: Any
    data: Mapping[str, Any] | MutableMapping[str, Any] | None
    query_params: Mapping[str, Any] | MutableMapping[str, Any] | None


class ViewLike(Protocol):
    action: str | None
    kwargs: Mapping[str, Any]


class PolicyStatement(TypedDict, total=False):
    action: str | Sequence[str]
    principal: str | Sequence[str]
    effect: str
    condition: str


class _BasePermission(Protocol):
    def has_permission(self, request: Any, view: Any) -> bool:
        ...

    def has_object_permission(self, request: Any, view: Any, obj: Any) -> bool:
        ...


def _load_base_permission() -> type[_BasePermission]:
    permissions_spec = importlib.util.find_spec("rest_framework.permissions")
    if permissions_spec is None:
        class _FallbackBasePermission:  # pragma: no cover - simple runtime shim
            def has_permission(self, request: Any, view: Any) -> bool:
                return True

            def has_object_permission(self, request: Any, view: Any, obj: Any) -> bool:
                return True

        return _FallbackBasePermission

    module = importlib.import_module("rest_framework.permissions")
    base = getattr(module, "BasePermission")
    return cast("type[_BasePermission]", base)


BasePermission = _load_base_permission()


class AccessPolicy(BasePermission):
    statements: Sequence[PolicyStatement] = ()

    def _is_open(self, request: RequestLike) -> bool:
        return bool(getattr(settings, "PLATFORM_DEV_OPEN", True))

    def _resolve_action(self, request: RequestLike, view: ViewLike) -> str:
        action = getattr(view, "action", None)
        if action:
            return str(action)
        return request.method.lower()

    def _actions_match(self, action: str, statement_actions: str | Sequence[str]) -> bool:
        if statement_actions == "*":
            return True
        if isinstance(statement_actions, str):
            return action == statement_actions
        if isinstance(statement_actions, (list, tuple, set)):
            return action in statement_actions
        return action == statement_actions

    def _check_condition(
        self,
        condition: str | None,
        request: RequestLike,
        view: ViewLike,
        action: str,
    ) -> bool:
        if not condition:
            return True
        method = getattr(self, condition, None)
        if not callable(method):
            return False
        return bool(method(request, view, action))

    def _evaluate(self, request: RequestLike, view: ViewLike, action: str) -> bool:
        decision: bool | None = None
        for stmt in self.statements or ():
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

    def has_permission(self, request: RequestLike, view: ViewLike) -> bool:
        if self._is_open(request):
            return True
        action = self._resolve_action(request, view)
        return self._evaluate(request, view, action)

    def has_object_permission(self, request: RequestLike, view: ViewLike, obj: Any) -> bool:
        if self._is_open(request):
            return True
        action = self._resolve_action(request, view)
        setattr(request, "_access_policy_obj", obj)
        try:
            return self._evaluate(request, view, action)
        finally:
            if hasattr(request, "_access_policy_obj"):
                delattr(request, "_access_policy_obj")


class _MembershipMixin:
    def _is_dev_open(self) -> bool:
        return bool(getattr(settings, "PLATFORM_DEV_OPEN", True))

    def _resolve_case_id(self, request: RequestLike, view: ViewLike) -> str | None:
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
        if isinstance(data, Mapping):
            data_mapping = cast(Mapping[str, Any], data)
            case_id = data_mapping.get("case") or data_mapping.get("case_id")
            if case_id:
                return str(case_id)

        # Query params (e.g., list filtering)
        params = getattr(request, "query_params", None)
        if isinstance(params, Mapping):
            params_mapping = cast(Mapping[str, Any], params)
            case_id = params_mapping.get("case") or params_mapping.get("case_id")
            if case_id:
                return str(case_id)

        # URL kwargs (nested routes)
        kwargs_obj = getattr(view, "kwargs", None)
        kwargs: Mapping[str, Any]
        if isinstance(kwargs_obj, Mapping):
            kwargs = cast(Mapping[str, Any], kwargs_obj)
        else:
            kwargs = cast(Mapping[str, Any], {})
        for key in ("case_pk", "case_id"):
            case_id = kwargs.get(key)
            if case_id:
                return str(case_id)
        pk = kwargs.get("pk")
        if pk and view.__class__.__name__.lower().startswith("case"):
            return str(pk)

        return None

    def _membership_role(self, user: Any, case_id: str | None) -> str | None:
        if not case_id:
            return None
        try:
            membership = cast(
                CaseMembership | None,
                _case_membership_manager().filter(case_id=case_id, user=user).first(),
            )
            if membership is None:
                return None
            membership_role = cast(Any, membership).role
            return cast(str, membership_role)
        except Exception:
            return None

    def _has_cap(self, request: RequestLike, view: ViewLike, capability: str) -> bool:
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

    def is_case_member(self, request: RequestLike, view: ViewLike, action: str) -> bool:
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return self._is_dev_open()
        case_id = self._resolve_case_id(request, view)
        if case_id is None:
            return True
        memberships = _case_membership_manager()
        return bool(memberships.filter(case_id=case_id, user=user).exists())

    def can_manage_case(self, request: RequestLike, view: ViewLike, action: str) -> bool:
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return self._is_dev_open()
        case_id = self._resolve_case_id(request, view)
        if not case_id:
            return False
        if self._has_cap(request, view, "case.update"):
            return True
        role: str | None = self._membership_role(user, case_id)
        owner_role = cast(str, CaseMembership.Role.OWNER)
        admin_role = cast(str, CaseMembership.Role.ADMIN)
        superuser_role = cast(str, CaseMembership.Role.SUPERUSER)
        return role in {owner_role, admin_role, superuser_role}

    def can_manage_jobs(self, request: RequestLike, view: ViewLike, action: str) -> bool:
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return self._is_dev_open()
        case_id = self._resolve_case_id(request, view)
        if not case_id:
            return True
        if self._has_cap(request, view, "job.create"):
            return True
        role: str | None = self._membership_role(user, case_id)
        owner_role = cast(str, CaseMembership.Role.OWNER)
        contributor_role = cast(str, CaseMembership.Role.CONTRIBUTOR)
        admin_role = cast(str, CaseMembership.Role.ADMIN)
        superuser_role = cast(str, CaseMembership.Role.SUPERUSER)
        return role in {owner_role, contributor_role, admin_role, superuser_role}

    def can_review_job(self, request: RequestLike, view: ViewLike, action: str) -> bool:
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return self._is_dev_open()
        case_id = self._resolve_case_id(request, view)
        if not case_id:
            # Allow the request to proceed so object-level evaluation can enforce membership.
            return True
        if self._has_cap(request, view, "case.update"):
            return True
        memberships = _case_membership_manager()
        reviewer_role = cast(str, CaseMembership.Role.REVIEWER)
        if memberships.filter(case_id=case_id, user=user, role=reviewer_role).exists():
            return True
        case_manager = _case_manager()
        try:
            case = cast(Case, case_manager.get(pk=case_id))
            if case.reviewer_id and str(case.reviewer_id) == str(user.id):
                return True
        except case_manager.model.DoesNotExist:  # type: ignore[attr-defined]
            return False
        return False

    def can_download_artifacts(self, request: RequestLike, view: ViewLike, action: str) -> bool:
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return self._is_dev_open()
        case_id = self._resolve_case_id(request, view)
        if not case_id:
            return True
        return self._has_cap(request, view, "artifact.download")

    def can_view_artifacts(self, request: RequestLike, view: ViewLike, action: str) -> bool:
        case_id = self._resolve_case_id(request, view)
        if case_id is None:
            return self.is_case_member(request, view, action)
        return self._has_cap(request, view, "artifact.view")

    def can_create_case(self, request: RequestLike, view: ViewLike, action: str) -> bool:
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
        {"action": ["status"], "principal": "*", "effect": "allow", "condition": "is_case_member"},
        {"action": ["notes"], "principal": "*", "effect": "allow", "condition": "can_review_job"},
        {"action": ["download", "logs"], "principal": "*", "effect": "allow", "condition": "can_download_artifacts"},
        {"action": ["approve", "reject"], "principal": "*", "effect": "allow", "condition": "is_case_member"},
        {"action": ["destroy", "update", "partial_update"], "principal": "*", "effect": "deny"},
    ]


class ArtifactAccessPolicy(_MembershipMixin, AccessPolicy):
    statements = [
        {"action": ["list", "retrieve"], "principal": "*", "effect": "allow", "condition": "can_view_artifacts"},
    ]
