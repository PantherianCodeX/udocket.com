# pyright: strict

from __future__ import annotations

"""Lightweight helpers for encrypting secrets tied to the Django SECRET_KEY."""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _fernet() -> Fernet:
    secret_raw = getattr(settings, "SECRET_KEY", None)
    if not isinstance(secret_raw, str) or not secret_raw:
        raise RuntimeError("SECRET_KEY must be configured for encryption helpers")
    secret_key = secret_raw.encode("utf-8")
    digest = hashlib.sha256(secret_key).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_secret(value: str | None) -> str:
    if value is None or value == "":
        return ""
    token: bytes = _fernet().encrypt(value.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_secret(token: str | None) -> str:
    if token is None or token == "":
        return ""
    try:
        value: bytes = _fernet().decrypt(token.encode("utf-8"))
        return value.decode("utf-8")
    except (InvalidToken, ValueError):  # pragma: no cover - defensive guard
        return ""


__all__ = ["encrypt_secret", "decrypt_secret"]
