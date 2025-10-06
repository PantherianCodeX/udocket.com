from __future__ import annotations

from typing import Any

class BaseAuthentication:
    def authenticate(self, request: Any) -> Any: ...
    def authenticate_header(self, request: Any) -> str: ...

def get_authorization_header(request: Any) -> bytes: ...

__all__ = ["BaseAuthentication", "get_authorization_header"]

