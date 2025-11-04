from __future__ import annotations


class DjangoException(Exception): ...


class ImproperlyConfigured(DjangoException): ...


class PermissionDenied(DjangoException): ...


class ObjectDoesNotExist(DjangoException): ...


class ValidationError(DjangoException): ...


__all__ = [
    "DjangoException",
    "ImproperlyConfigured",
    "PermissionDenied",
    "ObjectDoesNotExist",
    "ValidationError",
]

