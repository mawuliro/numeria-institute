from django.contrib import admin

from .models import Formation, FormationModule, FormationLesson, InscriptionFormation


@admin.register(Formation)
class FormationAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'level', 'category', 'language', 'price', 'is_free', 'created_at']
    list_filter = ['status', 'level', 'category', 'language', 'is_free']
    search_fields = ['title', 'slug']


@admin.register(FormationModule)
class FormationModuleAdmin(admin.ModelAdmin):
    list_display = ['formation', 'title', 'order', 'is_active']
    list_filter = ['is_active', 'formation']
    search_fields = ['title', 'formation__title']


@admin.register(FormationLesson)
class FormationLessonAdmin(admin.ModelAdmin):
    list_display = ['formation', 'module', 'title', 'order', 'is_active', 'is_free_preview']
    list_filter = ['is_active', 'is_free_preview', 'formation']
    search_fields = ['title', 'formation__title']


@admin.register(InscriptionFormation)
class InscriptionFormationAdmin(admin.ModelAdmin):
    list_display = ['formation', 'etudiant', 'statut', 'progression', 'date_inscription']
    list_filter = ['statut', 'formation']
    search_fields = ['formation__title', 'etudiant__username', 'etudiant__email']

