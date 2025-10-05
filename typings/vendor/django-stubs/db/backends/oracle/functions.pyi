# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from typing import Any

from django.db.models import Func

class IntervalToSeconds(Func):
    function: str
    template: str
    def __init__(self, expression: Any, *, output_field: Any | None = None, **extra: Any) -> None: ...

class SecondsToInterval(Func):
    function: str
    template: str
    def __init__(self, expression: Any, *, output_field: Any | None = None, **extra: Any) -> None: ...
