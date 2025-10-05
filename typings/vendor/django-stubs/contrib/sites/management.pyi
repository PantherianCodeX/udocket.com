# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from typing import Any

from django.apps.config import AppConfig
from django.apps.registry import Apps

def create_default_site(
    app_config: AppConfig,
    verbosity: int = 2,
    interactive: bool = True,
    using: str = "default",
    apps: Apps = ...,
    **kwargs: Any,
) -> None: ...
