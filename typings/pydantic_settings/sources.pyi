from __future__ import annotations

from typing import Any, ClassVar, Dict, Type

from . import BaseSettings


class PydanticBaseSettingsSource:
    def __init__(self, settings_cls: Type[BaseSettings], **kwargs: Any) -> None: ...
    def __call__(self) -> Dict[str, Any]: ...


class EnvSettingsSource(PydanticBaseSettingsSource):
    STR_LIST_FIELDS: ClassVar[set[str]]
    INT_LIST_FIELDS: ClassVar[set[str]]

    def __init__(self, settings_cls: Type[BaseSettings], **kwargs: Any) -> None: ...

    def decode_complex_value(self, field_name: str, field: Any, value: Any) -> Any: ...


class DotEnvSettingsSource(PydanticBaseSettingsSource):
    STR_LIST_FIELDS: ClassVar[set[str]]
    INT_LIST_FIELDS: ClassVar[set[str]]

    def __init__(self, settings_cls: Type[BaseSettings], **kwargs: Any) -> None: ...

    def decode_complex_value(self, field_name: str, field: Any, value: Any) -> Any: ...
