from django.contrib import admin
from .models import Cours, InscriptionCours, Lecon, ProgressionLecon, Exercice, TentativeExercice, Certificat



class ExerciceInline(admin.StackedInline):
    """Exercices intégrés dans la page leçon."""
    model = Exercice
    extra = 1
    fields = [
        'ordre', 'question',
        'choix_a', 'choix_b', 'choix_c', 'choix_d',
        'bonne_reponse', 'corrige', 'points', 'est_actif'
    ]


class LeconInline(admin.StackedInline):
    """Leçons intégrées dans la page cours."""
    model = Lecon
    extra = 1
    fields = ['ordre', 'titre', 'contenu', 'video_youtube', 'duree_minutes', 'est_publiee']
    show_change_link = True


class CoursAdmin(admin.ModelAdmin):
    inlines = [LeconInline]

    list_display = [
        'titre', 'type_cours', 'cycle', 'classe',
        'matiere', 'niveau', 'est_gratuit', 'est_publie',
    ]
    list_filter = [
        'type_cours', 'cycle', 'classe',
        'matiere', 'niveau', 'est_gratuit', 'est_publie',
    ]
    search_fields = ['titre', 'resume', 'description']
    list_editable = ['est_publie', 'est_gratuit']

    fieldsets = [
        ('Informations principales', {
            'fields': ['titre', 'resume', 'description']
        }),
        ('Type de cours', {
            'fields': ['type_cours', 'cycle', 'classe'],
        }),
        ('Classification', {
            'fields': ['matiere', 'niveau', 'nombre_lecons']
        }),
        ('Vidéo principale', {
            'fields': ['video_youtube'],
        }),
        ('Prix et publication', {
            'fields': ['est_gratuit', 'prix', 'est_publie']
        }),
    ]


class LeconAdmin(admin.ModelAdmin):
    """Admin pour les leçons avec exercices intégrés."""
    inlines = [ExerciceInline]

    list_display = ['cours', 'ordre', 'titre', 'duree_minutes', 'est_publiee']
    list_filter = ['cours__type_cours', 'cours', 'est_publiee']
    search_fields = ['titre', 'contenu']
    list_editable = ['ordre', 'est_publiee']


class ExerciceAdmin(admin.ModelAdmin):
    list_display = [
        'lecon', 'ordre', 'question_courte',
        'bonne_reponse', 'points', 'est_actif'
    ]
    list_filter = ['est_actif', 'bonne_reponse', 'lecon__cours']
    search_fields = ['question', 'corrige']
    list_editable = ['est_actif', 'points']

    def question_courte(self, obj):
        """Affiche les 60 premiers caractères de la question."""
        return obj.question[:60] + '...' if len(obj.question) > 60 else obj.question
    question_courte.short_description = 'Question'


class TentativeAdmin(admin.ModelAdmin):
    list_display = [
        'etudiant', 'exercice', 'reponse_choisie',
        'est_correcte', 'numero_tentative', 'date_tentative'
    ]
    list_filter = ['est_correcte', 'reponse_choisie']
    search_fields = ['etudiant__username']
    readonly_fields = ['date_tentative']


class InscriptionAdmin(admin.ModelAdmin):
    list_display = ['etudiant', 'cours', 'progression', 'est_termine', 'date_inscription']
    list_filter = ['est_termine', 'cours__type_cours', 'cours']
    search_fields = ['etudiant__username', 'cours__titre']
    list_editable = ['progression', 'est_termine']


admin.site.register(Cours, CoursAdmin)
admin.site.register(Lecon, LeconAdmin)
admin.site.register(Exercice, ExerciceAdmin)
admin.site.register(TentativeExercice, TentativeAdmin)
admin.site.register(InscriptionCours, InscriptionAdmin)
admin.site.register(ProgressionLecon)

admin.site.site_header = 'Numeria Institute — Administration'
admin.site.site_title = 'Numeria Admin'

class CertificatAdmin(admin.ModelAdmin):
    list_display = [
        'get_etudiant',
        'get_cours',
        'date_emission',
        'code_verification',
    ]
    list_filter  = ['date_emission', 'inscription__cours']
    search_fields = [
        'inscription__etudiant__username',
        'inscription__etudiant__first_name',
        'inscription__etudiant__last_name',
        'inscription__cours__titre',
        'code_verification',
    ]
    readonly_fields = ['code_verification', 'date_emission']

    def get_etudiant(self, obj):
        u = obj.inscription.etudiant
        return f"{u.first_name} {u.last_name} ({u.username})"
    get_etudiant.short_description = 'Étudiant'

    def get_cours(self, obj):
        return obj.inscription.cours.titre
    get_cours.short_description = 'Cours'


admin.site.register(Certificat, CertificatAdmin)