# pyright: reportUnusedImport=false, reportUnusedClass=false, reportUnusedFunction=false, reportUnusedVariable=false
# mypy: ignore-errors

"""Overlay package for django."""

from .http.request import HttpRequest

__all__ = ["HttpRequest"]

