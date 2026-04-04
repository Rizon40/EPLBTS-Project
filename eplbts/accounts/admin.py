from django.contrib import admin

# Register your models here.

# accounts/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'role', 'hospital', 'is_active']
    fieldsets = UserAdmin.fieldsets + (
        ('Role Info', {'fields': ('role', 'phone_number', 'hospital')}),
    )

admin.site.register(CustomUser, CustomUserAdmin)