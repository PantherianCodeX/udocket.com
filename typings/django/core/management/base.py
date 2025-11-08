from __future__ import annotations

from typing import Any, Protocol


class CommandParser:
    def add_argument(self, *args: Any, **kwargs: Any) -> None: ...


class Style(Protocol):
    def SUCCESS(self, message: str) -> str: ...

    def WARNING(self, message: str) -> str: ...

    def ERROR(self, message: str) -> str: ...


class OutputWrapper:
    def write(self, msg: str) -> None: ...


class BaseCommand:
    help: str
    stdout: OutputWrapper
    style: Style

    def add_arguments(self, parser: CommandParser) -> None: ...

    def handle(self, *args: Any, **options: Any) -> Any: ...
__all__ = ['BaseCommand', 'CommandParser', 'OutputWrapper', 'Style']
