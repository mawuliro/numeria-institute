"""
cours/admin.py — Keeps only the models NOT managed by the custom staff panel.
Course content (Cours, CourseLesson, Exercice, CodeExercise, etc.) is managed at
/fr/admin-panel/cours/ — no need to register them here.

Kept: InscriptionCours (student enrollment emergency view), Certificat.
"""
from django.contrib import admin
from .models import InscriptionCours, Certificat

admin.site.site_header = 'Numeria Institute — Administration'
admin.site.site_title  = 'Numeria Admin'


@admin.register(InscriptionCours)
class InscriptionAdmin(admin.ModelAdmin):
    list_display    = ['etudiant', 'course', 'progression', 'est_termine', 'date_inscription']
    list_filter     = ['est_termine', 'course']
    search_fields   = ['etudiant__username', 'course__titre']
    raw_id_fields   = ['etudiant', 'course']


@admin.register(Certificat)
class CertificatAdmin(admin.ModelAdmin):
    list_display    = ['__str__', 'date_emission', 'code_verification']
    readonly_fields = ['code_verification', 'date_emission']
    raw_id_fields   = ['inscription']