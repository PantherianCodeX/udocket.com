from __future__ import annotations

from typing import Any
from django.http import HttpResponse, HttpResponseRedirect

def redirect(to: Any, *args: Any, permanent: bool = ..., preserve_request: bool = ...) -> HttpResponseRedirect: ...
def render(request: Any, template_name: str, context: Any | None = ..., *, content_type: str | None = ..., status: int | None = ..., using: str | None = ...) -> HttpResponse: ...

__all__ = ["redirect"]
