# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from typing import Any

from django.contrib.admin import ModelAdmin
from django.contrib.gis.forms import BaseGeometryWidget

class GISModelAdmin(ModelAdmin):
    gis_widget: BaseGeometryWidget
    gis_widget_kwargs: dict[str, Any]
