# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from collections.abc import Callable
from typing import Any, Literal, TypeVar

_F = TypeVar("_F", bound=Callable[..., Any])

coroutine_functions_to_sensitive_variables: dict[int, Literal["__ALL__"] | tuple[str, ...]]

def sensitive_variables(*variables: str) -> Callable[[_F], _F]: ...
def sensitive_post_parameters(*parameters: str) -> Callable[[_F], _F]: ...
