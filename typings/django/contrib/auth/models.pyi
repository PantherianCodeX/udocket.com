from __future__ import annotations

from typing import Any, Iterable, Protocol


class _SupportsStr(Protocol):
    def __str__(self) -> str: ...


class Permission:
    id: int
    codename: str
    name: str


class Group:
    id: int
    name: str


class AbstractBaseUser:
    pk: Any
    is_active: bool
    is_superuser: bool
    is_staff: bool
    username: str
    email: str

    def get_username(self) -> str: ...
    def set_password(self, raw_password: str) -> None: ...
    def check_password(self, raw_password: str) -> bool: ...


class AnonymousUser:
    is_authenticated: bool
    is_anonymous: bool


class User(AbstractBaseUser):
    first_name: str
    last_name: str
    groups: Iterable[Group]


def get_user_model() -> type[AbstractBaseUser]: ...


__all__ = [
    "AbstractBaseUser",
    "AnonymousUser",
    "Group",
    "Permission",
    "User",
    "get_user_model",
]

