from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Data Tambahan", {"fields": ("role", "phone")}),
    )
    list_display = ("username", "get_full_name", "role", "email", "is_active")
    list_filter = ("role", "is_staff", "is_active")
    list_editable = ("role", "is_active")
