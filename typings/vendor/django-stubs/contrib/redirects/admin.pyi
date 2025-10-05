# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from typing import Any, ClassVar

from django.contrib import admin

class RedirectAdmin(admin.ModelAdmin):
    list_display: Any
    list_filter: ClassVar[Any]
    search_fields: ClassVar[Any]
    radio_fields: ClassVar[Any]
