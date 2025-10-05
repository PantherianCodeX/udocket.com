# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from typing import Any

from django.template import Node
from django.template.base import Parser, Token

register: Any

def localize(value: Any) -> str: ...
def unlocalize(value: Any) -> str: ...

class LocalizeNode(Node):
    nodelist: list[Node]
    use_l10n: bool
    def __init__(self, nodelist: list[Node], use_l10n: bool) -> None: ...

def localize_tag(parser: Parser, token: Token) -> LocalizeNode: ...
