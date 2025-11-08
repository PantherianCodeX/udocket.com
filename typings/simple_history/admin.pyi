from typing import Any, Type

from django.contrib.admin import ModelAdmin
from django.db.models import Model

class SimpleHistoryAdmin(ModelAdmin[Model]):
    history_list_display: tuple[str, ...]
    def __init__(self, model: Type[Model], admin_site: Any | None = ...) -> None: ...
