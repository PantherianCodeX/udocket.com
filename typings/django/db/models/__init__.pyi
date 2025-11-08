from __future__ import annotations

from typing import Any, Generic, Iterable, Iterator, Optional, Type, TypeVar, overload

_ModelT = TypeVar("_ModelT", bound="Model")
_StoredT = TypeVar("_StoredT")
_ReturnT = TypeVar("_ReturnT")


class QuerySet(Generic[_ModelT], Iterable[_ModelT]):
    def __iter__(self) -> Iterator[_ModelT]: ...

    @overload
    def __getitem__(self, key: int) -> _ModelT: ...

    @overload
    def __getitem__(self, key: slice) -> QuerySet[_ModelT]: ...

    def __len__(self) -> int: ...

    def all(self) -> QuerySet[_ModelT]: ...

    def filter(self, *args: Any, **kwargs: Any) -> QuerySet[_ModelT]: ...

    def exclude(self, *args: Any, **kwargs: Any) -> QuerySet[_ModelT]: ...

    def select_related(self, *fields: str) -> QuerySet[_ModelT]: ...

    def prefetch_related(self, *fields: str) -> QuerySet[_ModelT]: ...

    def order_by(self, *fields: str) -> QuerySet[_ModelT]: ...

    def values_list(self, *fields: str, flat: bool = ...) -> QuerySet[Any]: ...

    def values(self, *fields: str) -> QuerySet[Any]: ...

    def none(self) -> QuerySet[_ModelT]: ...

    def annotate(self, **kwargs: Any) -> QuerySet[_ModelT]: ...

    def iterator(self, chunk_size: int | None = ...) -> Iterator[_ModelT]: ...

    def get(self, *args: Any, **kwargs: Any) -> _ModelT: ...

    def first(self) -> Optional[_ModelT]: ...

    def last(self) -> Optional[_ModelT]: ...

    def exists(self) -> bool: ...

    def count(self) -> int: ...

    def update(self, **kwargs: Any) -> int: ...

    def delete(self) -> tuple[int, dict[str, int]]: ...

    def create(self, **kwargs: Any) -> _ModelT: ...

    def get_or_create(
        self,
        defaults: dict[str, Any] | None = ...,
        **kwargs: Any,
    ) -> tuple[_ModelT, bool]: ...


class Manager(QuerySet[_ModelT], Generic[_ModelT]):
    model: Type[_ModelT]

    def get_queryset(self) -> QuerySet[_ModelT]: ...


class Model:
    objects: Manager["Model"]
    pk: Any

    class DoesNotExist(Exception): ...

    class MultipleObjectsReturned(Exception): ...

    def save(self, *args: Any, **kwargs: Any) -> None: ...

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]: ...


class Field(Generic[_StoredT, _ReturnT]):
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

    def __get__(self, instance: Any, owner: Type[Any]) -> _ReturnT: ...

    def __set__(self, instance: Any, value: _StoredT) -> None: ...


class ForeignKey(Field[_StoredT, _ReturnT], Generic[_StoredT, _ReturnT]): ...


class ManyToManyField(Field[_StoredT, _ReturnT], Generic[_StoredT, _ReturnT]): ...


class OneToOneField(Field[_StoredT, _ReturnT], Generic[_StoredT, _ReturnT]): ...


class IntegerField(Field[_StoredT, _ReturnT], Generic[_StoredT, _ReturnT]): ...


class FloatField(Field[_StoredT, _ReturnT], Generic[_StoredT, _ReturnT]): ...


class BooleanField(Field[_StoredT, _ReturnT], Generic[_StoredT, _ReturnT]): ...


class CharField(Field[_StoredT, _ReturnT], Generic[_StoredT, _ReturnT]): ...


class DateTimeField(Field[_StoredT, _ReturnT], Generic[_StoredT, _ReturnT]): ...


class JSONField(Field[_StoredT, _ReturnT], Generic[_StoredT, _ReturnT]): ...


class EmailField(CharField[_StoredT, _ReturnT], Generic[_StoredT, _ReturnT]): ...


class TextField(Field[_StoredT, _ReturnT], Generic[_StoredT, _ReturnT]): ...


class UUIDField(Field[_StoredT, _ReturnT], Generic[_StoredT, _ReturnT]): ...


class AutoField(Field[_StoredT, _ReturnT], Generic[_StoredT, _ReturnT]): ...


class BigAutoField(Field[_StoredT, _ReturnT], Generic[_StoredT, _ReturnT]): ...


def ModelChoiceField(*args: Any, **kwargs: Any) -> Any: ...


CASCADE: Any
PROTECT: Any
SET_NULL: Any
SET_DEFAULT: Any
DO_NOTHING: Any


__all__ = [
    "Model",
    "Manager",
    "QuerySet",
    "Field",
    "ForeignKey",
    "ManyToManyField",
    "OneToOneField",
    "IntegerField",
    "FloatField",
    "BooleanField",
    "CharField",
    "DateTimeField",
    "JSONField",
    "EmailField",
    "TextField",
    "UUIDField",
    "AutoField",
    "BigAutoField",
    "ModelChoiceField",
    "CASCADE",
    "PROTECT",
    "SET_NULL",
    "SET_DEFAULT",
    "DO_NOTHING",
]
