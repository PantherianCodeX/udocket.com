from __future__ import annotations

from typing import Any

class ViewSet:
    pass

class GenericViewSet(ViewSet):
    pass

class ModelViewSet(GenericViewSet):
    pass

__all__ = ["ViewSet", "GenericViewSet", "ModelViewSet"]

