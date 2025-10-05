# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from django.http import HttpRequest, HttpResponse

def kml(
    request: HttpRequest,
    label: str,
    model: str,
    field_name: str | None = ...,
    compress: bool = ...,
    using: str = ...,
) -> HttpResponse: ...
def kmz(
    request: HttpRequest, label: str, model: str, field_name: str | None = ..., using: str = ...
) -> HttpResponse: ...
