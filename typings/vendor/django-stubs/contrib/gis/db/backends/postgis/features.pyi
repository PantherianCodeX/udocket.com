# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from django.contrib.gis.db.backends.base.features import BaseSpatialFeatures
from django.db.backends.postgresql.features import DatabaseFeatures as Psycopg2DatabaseFeatures

class DatabaseFeatures(BaseSpatialFeatures, Psycopg2DatabaseFeatures):
    supports_3d_storage: bool
    supports_3d_functions: bool
    supports_left_right_lookups: bool
    supports_raster: bool
    supports_empty_geometries: bool
