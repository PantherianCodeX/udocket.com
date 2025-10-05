# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from django.contrib.flatpages.models import FlatPage
from django.http.request import HttpRequest
from django.http.response import HttpResponse

DEFAULT_TEMPLATE: str

def flatpage(request: HttpRequest, url: str) -> HttpResponse: ...
def render_flatpage(request: HttpRequest, f: FlatPage) -> HttpResponse: ...
