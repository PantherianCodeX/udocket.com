# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from django.contrib.gis.sitemaps.kml import KMLSitemap as KMLSitemap
from django.contrib.gis.sitemaps.kml import KMZSitemap as KMZSitemap

__all__ = ["KMLSitemap", "KMZSitemap"]
