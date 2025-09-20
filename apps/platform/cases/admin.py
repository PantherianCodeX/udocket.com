from django.contrib import admin
from apps.platform.cases.models import Case


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "created_at", "updated_at")
    search_fields = ("id", "title")

