from __future__ import annotations

from typing import Any, ClassVar, Dict, Type

from . import BaseSettings


class PydanticBaseSettingsSource:
    def __init__(self, settings_cls: Type[BaseSettings], **kwargs: Any) -> None:
        self._settings_cls = settings_cls
        self._kwargs = kwargs

    def __call__(self) -> Dict[str, Any]:
        return {}


class EnvSettingsSource(PydanticBaseSettingsSource):
    STR_LIST_FIELDS: ClassVar[set[str]] = set()
    INT_LIST_FIELDS: ClassVar[set[str]] = set()

    def decode_complex_value(self, field_name: str, field: Any, value: Any) -> Any:
        return value


class DotEnvSettingsSource(PydanticBaseSettingsSource):
    STR_LIST_FIELDS: ClassVar[set[str]] = set()
    INT_LIST_FIELDS: ClassVar[set[str]] = set()

    def decode_complex_value(self, field_name: str, field: Any, value: Any) -> Any:
        return value
