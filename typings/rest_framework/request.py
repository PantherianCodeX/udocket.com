from __future__ import annotations

from typing import Any, Mapping


class Request:
    user: Any
    data: Mapping[str, Any]
