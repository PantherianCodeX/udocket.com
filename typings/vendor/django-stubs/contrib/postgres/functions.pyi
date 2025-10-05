# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from typing import ClassVar

from django.db.models import DateTimeField, Func, UUIDField

class RandomUUID(Func):
    output_field: ClassVar[UUIDField]

class TransactionNow(Func):
    output_field: ClassVar[DateTimeField]
