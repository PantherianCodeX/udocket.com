# pyright: reportUnusedImport=false, reportUnusedClass=false, reportUnusedFunction=false, reportUnusedVariable=false
# mypy: ignore-errors

from __future__ import annotations

from typing import Any, Iterable

from django.contrib.admin import ModelAdmin


class UserAdmin(ModelAdmin):
    add_fieldsets: Iterable[Any]


__all__ = ["UserAdmin"]
