from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Formation, SessionFormation, InscriptionFormation,
    LeconFormation, ProgressionLecon, CertificatFormation
)


class LeconFormationInline(admin.StackedInline):
    model = LeconFormation
    extra = 1
    fields = ['ordre', 'titre', 'duree_minutes', 'contenu_html', 'video_youtube']


@admin.register(Formation)
class FormationAdmin(admin.ModelAdmin):
    inlines = [LeconFormationInline]
    list_display = [
        'titre', 'type_formation', 'niveau', 'duree_heures',
        'nombre_sessions', 'est_publiee', 'nombre_etudiants_total'
    ]
    list_filter = ['type_formation', 'niveau', 'est_publiee', 'date_creation']
    search_fields = ['titre', 'description_courte']
    list_editable = ['est_publiee']
    filter_horizontal = ['instructeurs']

    fieldsets = (
        ('Informations principales', {
            'fields': ('titre', 'slug', 'type_formation', 'niveau')
        }),
        ('Description', {
            'fields': ('description_courte', 'description_longue', 'prerequis')
        }),
        ('Détails', {
            'fields': ('duree_heures', 'image_couverture', 'competences_visees', 'instructeurs')
        }),
        ('Statut', {
            'fields': ('est_publiee', 'est_archivee'),
            'classes': ('collapse',)
        }),
    )

    def nombre_sessions(self, obj):
        return obj.sessions.count()
    nombre_sessions.short_description = 'Sessions'


@admin.register(SessionFormation)
class SessionFormationAdmin(admin.ModelAdmin):
    list_display = [
        'nom', 'formation', 'statut', 'date_debut', 'places_disponibles',
        'prix_fcfa', 'nombre_inscrits'
    ]
    list_filter = ['statut', 'formation', 'date_debut', 'modalite']
    search_fields = ['nom', 'formation__titre']
    list_editable = ['statut']
    filter_horizontal = ['instructeurs_session']

    fieldsets = (
        ('Formation & Session', {
            'fields': ('formation', 'nom', 'slug')
        }),
        ('Dates', {
            'fields': ('date_debut', 'date_fin', 'date_debut_inscriptions', 'date_fin_inscriptions')
        }),
        ('Capacité & Prix', {
            'fields': ('places_totales', 'prix_fcfa', 'prix_reduit_fcfa')
        }),
        ('Format', {
            'fields': ('modalite', 'lieu', 'instructeurs_session')
        }),
        ('Statut', {
            'fields': ('statut',)
        }),
    )

    def nombre_inscrits(self, obj):
        return obj.inscriptions.filter(statut__in=['confirmee', 'en_cours', 'terminee']).count()
    nombre_inscrits.short_description = 'Inscrits'

    readonly_fields = ['date_creation', 'date_modification']


@admin.register(InscriptionFormation)
class InscriptionFormationAdmin(admin.ModelAdmin):
    list_display = ['get_etudiant', 'get_session', 'statut', 'progression', 'prix_paye_fcfa', 'date_inscription']
    list_filter = ['statut', 'session__formation', 'date_inscription']
    search_fields = ['etudiant__username', 'etudiant__email', 'session__nom']
    list_editable = ['statut', 'progression']
    readonly_fields = ['date_inscription', 'date_confirmation_paiement']

    def get_etudiant(self, obj):
        return obj.etudiant.get_full_name() or obj.etudiant.username
    get_etudiant.short_description = 'Étudiant'

    def get_session(self, obj):
        return f"{obj.session.formation.titre} — {obj.session.nom}"
    get_session.short_description = 'Session'


@admin.register(LeconFormation)
class LeconFormationAdmin(admin.ModelAdmin):
    list_display = ['titre', 'formation', 'ordre', 'duree_minutes']
    list_filter = ['formation', 'ordre']
    search_fields = ['titre', 'formation__titre']
    list_editable = ['ordre']
    filter_horizontal = []

    fieldsets = (
        ('Identité', {
            'fields': ('formation', 'titre', 'ordre', 'description')
        }),
        ('Contenu', {
            'fields': ('contenu_html', 'video_youtube', 'ressources_telechargeables')
        }),
        ('Exercice (optionnel)', {
            'fields': ('exercice_code_html',),
            'classes': ('collapse',)
        }),
        ('Details', {
            'fields': ('duree_minutes',)
        }),
    )


@admin.register(CertificatFormation)
class CertificatFormationAdmin(admin.ModelAdmin):
    list_display = [
        'get_etudiant', 'get_formation', 'note_finale',
        'date_obtention', 'est_valide_badge'
    ]
    list_filter = ['inscription__session__formation', 'date_obtention']
    search_fields = ['inscription__etudiant__username', 'token_verification']
    readonly_fields = ['token_verification', 'date_obtention']

    def get_etudiant(self, obj):
        return obj.inscription.etudiant.get_full_name() or obj.inscription.etudiant.username
    get_etudiant.short_description = 'Étudiant'

    def get_formation(self, obj):
        return obj.inscription.session.formation.titre
    get_formation.short_description = 'Formation'

    def est_valide_badge(self, obj):
        if obj.est_valide():
            return format_html('<span style="color:green">✅ Valide</span>')
        return format_html('<span style="color:red">❌ Expiré</span>')
    est_valide_badge.short_description = 'Validité'
