from typing import Any

class BasePlugin:
    config: dict[str, Any]

    def __getattr__(self, name: str) -> Any: ...
