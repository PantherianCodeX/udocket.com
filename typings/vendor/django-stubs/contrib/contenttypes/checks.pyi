# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from collections.abc import Sequence
from typing import Any

from django.apps.config import AppConfig
from django.core.checks.messages import CheckMessage

def check_generic_foreign_keys(
    app_configs: Sequence[AppConfig] | None = None, **kwargs: Any
) -> Sequence[CheckMessage]: ...
def check_model_name_lengths(
    app_configs: Sequence[AppConfig] | None = None, **kwargs: Any
) -> Sequence[CheckMessage]: ...
