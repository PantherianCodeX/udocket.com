# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from collections.abc import Sequence
from typing import Any

from django.apps.config import AppConfig

from . import Error

E001: Error
E002: Error
E003: Error
E004: Error

def check_setting_language_code(app_configs: Sequence[AppConfig] | None, **kwargs: Any) -> Sequence[Error]: ...
def check_setting_languages(app_configs: Sequence[AppConfig] | None, **kwargs: Any) -> Sequence[Error]: ...
def check_setting_languages_bidi(app_configs: Sequence[AppConfig] | None, **kwargs: Any) -> Sequence[Error]: ...
def check_language_settings_consistent(app_configs: Sequence[AppConfig] | None, **kwargs: Any) -> Sequence[Error]: ...
