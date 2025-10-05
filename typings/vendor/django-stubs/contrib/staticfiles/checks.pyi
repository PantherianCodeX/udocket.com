# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from collections.abc import Sequence
from typing import Any

from django.apps.config import AppConfig
from django.core.checks.messages import CheckMessage, Error

E005: Error

def check_finders(app_configs: Sequence[AppConfig] | None = None, **kwargs: Any) -> list[CheckMessage]: ...
def check_storages(app_configs: Sequence[AppConfig] | None = None, **kwargs: Any) -> list[CheckMessage]: ...
