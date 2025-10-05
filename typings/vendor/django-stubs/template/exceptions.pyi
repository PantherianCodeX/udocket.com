# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from django.template.backends.base import BaseEngine
from django.template.base import Origin

class TemplateDoesNotExist(Exception):
    backend: BaseEngine | None
    tried: list[tuple[Origin, str]]
    chain: list[TemplateDoesNotExist]
    def __init__(
        self,
        msg: Origin | str,
        tried: list[tuple[Origin, str]] | None = None,
        backend: BaseEngine | None = None,
        chain: list[TemplateDoesNotExist] | None = None,
    ) -> None: ...

class TemplateSyntaxError(Exception): ...
