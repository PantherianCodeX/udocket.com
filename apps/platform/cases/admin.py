from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from apps.platform.cases.models import Case, CaseMembership
from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

class CaseMembershipInline(admin.TabularInline):
    model = CaseMembership
    extra = 1


@admin.register(Case)
class CaseAdmin(SimpleHistoryAdmin):
    list_display = ("id", "title", "created_at", "updated_at")
    search_fields = ("id", "title")
    inlines = [CaseMembershipInline]
