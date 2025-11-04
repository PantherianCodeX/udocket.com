from __future__ import annotations

from typing import Any


class ViewSet:
    ...


class GenericViewSet(ViewSet):
    ...


class ReadOnlyModelViewSet(GenericViewSet):
    ...


class ModelViewSet(GenericViewSet):
    ...
