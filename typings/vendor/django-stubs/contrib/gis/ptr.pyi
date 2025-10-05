# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from typing import Any

class CPointerBase:
    ptr_type: Any
    destructor: Any
    null_ptr_exception_class: Any
    @property
    def ptr(self) -> Any: ...
    @ptr.setter
    def ptr(self, ptr: Any) -> None: ...
    def __del__(self) -> None: ...
