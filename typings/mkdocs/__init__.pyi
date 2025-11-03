from typing import Any

class Config(dict[str, Any]): ...

class _ConfigOptionsModule:
    def Type(self, value: type[Any], default: Any | None = ...) -> Any: ...

config_options: _ConfigOptionsModule

class BasePlugin:
    config: dict[str, Any]

    def __getattr__(self, name: str) -> Any: ...
