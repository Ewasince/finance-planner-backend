from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = [
        "username",
        "email",
        "first_name",
        "last_name",
        "created_at",
        "is_staff",
    ]
    list_filter = ["is_staff", "is_superuser", "created_at"]
    readonly_fields = ["created_at"]
    fieldsets = list(UserAdmin.fieldsets or []) + [
        ("Дополнительная информация", {"fields": ("created_at",)})
    ]
