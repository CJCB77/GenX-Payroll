"""
Django admin customization for user model
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


class UserAdmin(BaseUserAdmin):
    ordering = ["id"]
    list_display = ["username", "odoo_user_id", "is_staff"]
    fieldsets = (
        (None, {"fields": ("username", "password", "odoo_user_id")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "email")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    readonly_fields = ["last_login", "date_joined", "odoo_user_id"]
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username", 
                    "password1", 
                    "password2",
                    "name",
                    "odoo_user_id",
                    "email",
                    "first_name",
                    "last_name",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )

    search_fields = ["username", "odoo_user_id"]

admin.site.register(User, UserAdmin)
