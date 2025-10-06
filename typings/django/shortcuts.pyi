from __future__ import annotations

from typing import Any
from django.http import HttpResponseRedirect

def redirect(to: Any, *args: Any, permanent: bool = ..., preserve_request: bool = ...) -> HttpResponseRedirect: ...

__all__ = ["redirect"]

