from __future__ import annotations

from collections.abc import Iterator

# pyright: strict
from typing import Any, Protocol, TypeVar, cast, overload

T_co = TypeVar("T_co", covariant=True)


class QuerySetProtocol(Protocol[T_co]):
    """Minimal protocol capturing the queryset surface our code relies on."""

    def __iter__(self) -> Iterator[T_co]: ...

    @overload
    def __getitem__(self, key: int) -> T_co: ...

    @overload
    def __getitem__(self, key: slice) -> QuerySetProtocol[T_co]: ...

    def all(self) -> QuerySetProtocol[T_co]: ...

    def filter(self, *args: Any, **kwargs: Any) -> QuerySetProtocol[T_co]: ...

    def exclude(self, *args: Any, **kwargs: Any) -> QuerySetProtocol[T_co]: ...

    def select_related(self, *fields: str) -> QuerySetProtocol[T_co]: ...

    def prefetch_related(self, *fields: str) -> QuerySetProtocol[T_co]: ...

    def order_by(self, *fields: str) -> QuerySetProtocol[T_co]: ...

    def values(self, *fields: str) -> QuerySetProtocol[dict[str, Any]]: ...

    def values_list(self, *fields: str, flat: bool = ...) -> QuerySetProtocol[Any]: ...

    def annotate(self, **kwargs: Any) -> QuerySetProtocol[T_co]: ...

    def none(self) -> QuerySetProtocol[T_co]: ...

    def iterator(self, chunk_size: int | None = ...) -> Iterator[T_co]: ...

    def get(self, *args: Any, **kwargs: Any) -> T_co: ...

    def get_or_create(
        self, defaults: dict[str, Any] | None = ..., **kwargs: Any
    ) -> tuple[T_co, bool]: ...

    def create(self, **kwargs: Any) -> T_co: ...

    def first(self) -> T_co | None: ...

    def last(self) -> T_co | None: ...

    def exists(self) -> bool: ...

    def count(self) -> int: ...

    def update(self, **kwargs: Any) -> int: ...

    def delete(self) -> tuple[int, dict[str, int]]: ...


class ManagerProtocol(QuerySetProtocol[T_co], Protocol[T_co]):
    """Django manager surface built on top of QuerySetProtocol."""

    def get_queryset(self) -> QuerySetProtocol[T_co]: ...


TypedManager = ManagerProtocol[T_co]
TypedQuerySet = QuerySetProtocol[T_co]


def get_typed_manager(model: type[T_co]) -> TypedManager[T_co]:
    """Cast Django's ``objects`` attribute to a typed manager."""

    manager_obj = getattr(model, "objects", None)
    if manager_obj is None:
        raise AttributeError(f"{model!r} does not expose an 'objects' manager")
    return cast(TypedManager[T_co], manager_obj)


__all__ = [
    "TypedManager",
    "TypedQuerySet",
    "ManagerProtocol",
    "QuerySetProtocol",
    "get_typed_manager",
]
