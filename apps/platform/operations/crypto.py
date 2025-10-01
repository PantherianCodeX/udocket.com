from __future__ import annotations

"""Lightweight helpers for encrypting secrets tied to the Django SECRET_KEY."""

import base64
import hashlib
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _fernet() -> Fernet:
    secret_key = settings.SECRET_KEY.encode("utf-8")
    digest = hashlib.sha256(secret_key).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_secret(value: Optional[str]) -> str:
    if value in (None, ""):
        return ""
    token = _fernet().encrypt(value.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_secret(token: Optional[str]) -> str:
    if not token:
        return ""
    try:
        value = _fernet().decrypt(token.encode("utf-8"))
        return value.decode("utf-8")
    except (InvalidToken, ValueError):  # pragma: no cover - defensive guard
        return ""


__all__ = ["encrypt_secret", "decrypt_secret"]
