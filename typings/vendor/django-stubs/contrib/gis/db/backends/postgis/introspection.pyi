# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from typing import Any

from django.db.backends.postgresql.introspection import DatabaseIntrospection

class PostGISIntrospection(DatabaseIntrospection):
    postgis_oid_lookup: Any
    ignored_tables: Any
    def get_field_type(self, data_type: Any, description: Any) -> Any: ...
    def get_geometry_type(self, table_name: Any, description: Any) -> Any: ...
