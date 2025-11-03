from typing import Any

class Config(dict[str, Any]):
    config_file_path: str

class _ConfigOptionsModule:
    def Type(self, value: type[Any], default: Any | None = ...) -> Any: ...

config_options: _ConfigOptionsModule
