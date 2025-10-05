# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from collections.abc import Awaitable, Callable, Iterable
from typing import TypeVar

from redis.backoff import AbstractBackoff
from redis.exceptions import RedisError

_T = TypeVar("_T")

class Retry:
    def __init__(self, backoff: AbstractBackoff, retries: int, supported_errors: tuple[type[RedisError], ...] = ...) -> None: ...
    def update_supported_errors(self, specified_errors: Iterable[type[RedisError]]) -> None: ...
    async def call_with_retry(self, do: Callable[[], Awaitable[_T]], fail: Callable[[RedisError], Awaitable[object]]) -> _T: ...
