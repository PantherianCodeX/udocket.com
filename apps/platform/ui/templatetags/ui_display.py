from __future__ import annotations

# pyright: strict
from django import template

register = template.Library()


@register.filter
def short_uuid(value: str, visible: int = 8) -> str:
    if not value:
        return ""
    text = str(value)
    if len(text) <= visible + 4:
        return text
    prefix = text[: max(1, visible)]
    suffix = text[-4:]
    return f"{prefix}…{suffix}"


@register.filter
def truncate_middle(value: str, args: str = "24,8") -> str:
    if not value:
        return ""
    try:
        front_str, back_str = args.split(",")
        front = max(1, int(front_str))
        back = max(1, int(back_str))
    except Exception:
        front, back = 24, 8
    text = str(value)
    if len(text) <= front + back + 1:
        return text
    return f"{text[:front]}…{text[-back:]}"


@register.filter(name="dict_get")
def dict_get(mapping: Any, key: str) -> Any:
    if isinstance(mapping, dict):
        return mapping.get(key, "")
    getter = getattr(mapping, "get", None)
    if callable(getter):
        try:
            return getter(key, "")
        except Exception:
            return ""
    try:
        return getattr(mapping, key)
    except Exception:
        return ""
