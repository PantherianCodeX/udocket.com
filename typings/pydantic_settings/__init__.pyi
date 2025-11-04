from __future__ import annotations

from typing import Any, ClassVar, Mapping, Tuple, Type, TypeVar, TypeAlias

T = TypeVar("T", bound="BaseSettings")

SettingsConfigDict: TypeAlias = dict[str, Any]


class BaseSettings:
    model_config: ClassVar[Any]
    model_fields: ClassVar[Mapping[str, Any]]

    def __init__(self, **data: Any) -> None: ...

    @classmethod
    def model_validate(cls: Type[T], obj: Any) -> T: ...

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type["BaseSettings"],
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ) -> Tuple[Any, ...]: ...


from . import sources

__all__ = ["BaseSettings", "SettingsConfigDict", "sources"]
