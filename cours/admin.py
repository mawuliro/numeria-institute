"""
cours/admin.py — Keeps only the models NOT managed by the custom staff panel.
Course content (Cours, CourseLesson, Exercice, CodeExercise, etc.) is managed at
/fr/admin-panel/cours/ — no need to register them here.

Kept: InscriptionCours (student enrollment emergency view), Certificat,
      InteractiveLab + LabProgress (complex JSONField editing benefits from
      Django admin's raw JSON widget and is not yet wired into the staff panel).
"""
from django.contrib import admin
from .models import InscriptionCours, Certificat, InteractiveLab, LabProgress

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


@admin.register(InteractiveLab)
class InteractiveLabAdmin(admin.ModelAdmin):
    """Full admin for the interactive lab framework.

    The `simulation_code`, `slider_config` and `challenges` fields hold
    rich JSON / Python payloads — admin is the quickest way to seed a new
    lab while the staff panel form is not yet wired up.
    """
    list_display    = ['title', 'difficulty', 'points', 'is_active', 'created_at']
    list_filter     = ['difficulty', 'is_active', 'course_lesson', 'formation_lesson']
    search_fields   = ['title', 'instructions', 'simulation_code']
    list_editable   = ['is_active', 'difficulty', 'points']
    list_per_page   = 25
    date_hierarchy  = 'created_at'
    ordering        = ['-created_at']
    raw_id_fields   = ['course_lesson', 'formation_lesson', 'created_by']
    filter_horizontal = []  # no M2M yet — placeholder per spec
    readonly_fields = ['created_at']
    fieldsets = (
        (None, {
            'fields': ('title', 'instructions', 'is_active'),
        }),
        ('Simulation Pyodide', {
            'description': 'Le code Python doit définir une fonction simulate(params) '
                           'qui retourne une figure matplotlib.',
            'fields': ('simulation_code', 'slider_config'),
        }),
        ('Challenges adaptatifs', {
            'description': 'Liste ordonnée de challenges. Chaque challenge porte les '
                           'clés id, question, expected_value, tolerance, unit, hint, '
                           'explanation, next_on_correct, next_on_wrong.',
            'fields': ('challenges', 'points', 'difficulty'),
        }),
        ('Rattachement à une leçon', {
            'classes': ('collapse',),
            'fields': ('course_lesson', 'formation_lesson', 'created_by', 'created_at'),
        }),
    )


@admin.register(LabProgress)
class LabProgressAdmin(admin.ModelAdmin):
    """Read-mostly admin view of student progress through labs."""
    list_display    = ['student', 'lab', 'attempts', 'is_completed', 'updated_at']
    list_filter     = ['is_completed', 'lab']
    search_fields   = ['student__username', 'lab__title']
    raw_id_fields   = ['student', 'lab']
    readonly_fields = ['created_at', 'updated_at', 'completed_at']
    list_per_page   = 50
    ordering        = ['-updated_at']