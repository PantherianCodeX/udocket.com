# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from typing import Any

from django.db.backends.sqlite3.introspection import DatabaseIntrospection, FlexibleFieldLookupDict

class GeoFlexibleFieldLookupDict(FlexibleFieldLookupDict):
    base_data_types_reverse: Any

class SpatiaLiteIntrospection(DatabaseIntrospection):
    data_types_reverse: Any
    def get_geometry_type(self, table_name: Any, description: Any) -> Any: ...
    def get_constraints(self, cursor: Any, table_name: Any) -> Any: ...
