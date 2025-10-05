# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from pathlib import Path

from django.http.request import HttpRequest
from django.http.response import HttpResponseForbidden

CSRF_FAILURE_TEMPLATE_NAME: str

def builtin_template_path(name: str) -> Path: ...
def csrf_failure(request: HttpRequest, reason: str = ..., template_name: str = ...) -> HttpResponseForbidden: ...
