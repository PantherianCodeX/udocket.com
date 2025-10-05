# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from collections.abc import Callable
from typing import TypeVar, overload

from django.utils.functional import _StrOrPromise

_C = TypeVar("_C", bound=Callable)

@overload
def staff_member_required(
    view_func: _C = ..., redirect_field_name: str | None = ..., login_url: _StrOrPromise = ...
) -> _C: ...
@overload
def staff_member_required(
    view_func: None = None, redirect_field_name: str | None = ..., login_url: _StrOrPromise = ...
) -> Callable: ...
