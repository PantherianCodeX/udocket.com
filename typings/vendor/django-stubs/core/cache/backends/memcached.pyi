# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from collections.abc import Sequence
from types import ModuleType
from typing import Any

from django.core.cache.backends.base import BaseCache

class BaseMemcachedCache(BaseCache):
    def __init__(
        self,
        server: str | Sequence[str],
        params: dict[str, Any],
        library: ModuleType,
        value_not_found_exception: type[BaseException],
    ) -> None: ...
    @property
    def client_servers(self) -> Sequence[str]: ...

class PyLibMCCache(BaseMemcachedCache):
    def __init__(self, server: str | Sequence[str], params: dict[str, Any]) -> None: ...
    @property
    def client_servers(self) -> list[str]: ...

class PyMemcacheCache(BaseMemcachedCache):
    def __init__(self, server: str | Sequence[str], params: dict[str, Any]) -> None: ...
