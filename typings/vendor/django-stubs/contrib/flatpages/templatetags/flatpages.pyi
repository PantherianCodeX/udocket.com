# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from typing import Any

from django import template
from django.template.base import Parser, Token
from django.template.context import Context

register: Any

class FlatpageNode(template.Node):
    context_name: str
    starts_with: None
    user: None
    def __init__(self, context_name: str, starts_with: str | None = ..., user: str | None = ...) -> None: ...
    def render(self, context: Context) -> str: ...

def get_flatpages(parser: Parser, token: Token) -> FlatpageNode: ...
