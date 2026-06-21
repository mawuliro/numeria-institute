"""
blog/admin.py — Articles are managed at /fr/admin-panel/blog/.
Only Categorie is kept here for quick management.
"""
from django.contrib import admin
from .models import Categorie


@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display       = ['nom', 'slug']
    prepopulated_fields = {'slug': ('nom',)}