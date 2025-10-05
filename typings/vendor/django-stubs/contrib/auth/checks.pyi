# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from collections.abc import Sequence
from typing import Any

from django.apps.config import AppConfig
from django.core.checks.messages import CheckMessage

def check_user_model(app_configs: Sequence[AppConfig] | None = ..., **kwargs: Any) -> Sequence[CheckMessage]: ...
def check_models_permissions(
    app_configs: Sequence[AppConfig] | None = ..., **kwargs: Any
) -> Sequence[CheckMessage]: ...
def check_middleware(app_configs: Sequence[AppConfig] | None, **kwargs: Any) -> Sequence[CheckMessage]: ...
