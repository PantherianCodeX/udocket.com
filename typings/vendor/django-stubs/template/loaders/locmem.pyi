# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from django.template.base import Origin
from django.template.engine import Engine

from .base import Loader as BaseLoader

class Loader(BaseLoader):
    templates_dict: dict[str, str]
    def __init__(self, engine: Engine, templates_dict: dict[str, str]) -> None: ...
    def get_contents(self, origin: Origin) -> str: ...
