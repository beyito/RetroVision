from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "username",
        "email",
        "role",
        "tenant",
        "store",
        "is_staff",
        "is_active",
    )
    list_filter = ("role", "tenant", "store", "is_staff", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "RetroVision Scope",
            {
                "fields": ("role", "tenant", "store"),
            },
        ),
    )
