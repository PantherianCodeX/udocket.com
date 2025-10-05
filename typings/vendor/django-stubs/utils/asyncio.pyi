# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from collections.abc import Callable
from typing import TypeVar, overload

_C = TypeVar("_C", bound=Callable)

@overload
def async_unsafe(message: str) -> Callable[[_C], _C]: ...
@overload
def async_unsafe(message: _C) -> _C: ...
