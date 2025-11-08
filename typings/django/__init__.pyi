# pyright: reportUnusedImport=false, reportUnusedClass=false, reportUnusedFunction=false, reportUnusedVariable=false
# mypy: ignore-errors

"""Overlay package for django."""

from .http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse, Http404, QueryDict
# Re-export commonly imported submodules to satisfy "from django import template/shortcuts"
from . import template, shortcuts, utils

__all__ = [
    "HttpRequest",
    "HttpResponse",
    "HttpResponseRedirect",
    "JsonResponse",
    "Http404",
    "QueryDict",
    "template",
    "shortcuts",
    "utils",
]
