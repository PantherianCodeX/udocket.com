from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "email", "is_staff", "is_superuser", "last_login")
    search_fields = ("username", "email", "display_name", "kc_sub")
    ordering = ("username",)

