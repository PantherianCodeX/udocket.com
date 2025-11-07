from __future__ import annotations

from typing import Any, Callable, ClassVar, Mapping, Tuple, Type, TypeVar, TypeAlias

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
        cls: Type["BaseSettings"],
        settings_cls: Type["BaseSettings"],
        init_settings: Callable[..., Any],
        env_settings: Callable[..., Any],
        dotenv_settings: Callable[..., Any],
        file_secret_settings: Callable[..., Any],
    ) -> Tuple[Callable[..., Any], ...]: ...


from . import sources

__all__ = ["BaseSettings", "SettingsConfigDict", "sources"]
