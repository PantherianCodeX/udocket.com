from django.contrib import admin
from apps.platform.authorization.models import Role, RoleCapability


class RoleCapabilityInline(admin.TabularInline):
    model = RoleCapability
    extra = 1


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("slug", "name", "system", "created_at")
    search_fields = ("slug", "name")
    inlines = [RoleCapabilityInline]
