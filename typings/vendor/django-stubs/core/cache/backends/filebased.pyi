# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from typing import Any, ClassVar

from django.core.cache.backends.base import BaseCache

class FileBasedCache(BaseCache):
    cache_suffix: ClassVar[str]
    pickle_protocol: ClassVar[int]
    def __init__(self, dir: str, params: dict[str, Any]) -> None: ...
