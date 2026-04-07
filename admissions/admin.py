# admissions/admin.py
from django.contrib import admin
from .models import CampagneRecrutement, Candidature


@admin.register(CampagneRecrutement)
class CampagneRecrutementAdmin(admin.ModelAdmin):
    list_display = ['nom', 'filiere', 'date_limite', 'capacite_max', 'frais_candidature', 'est_active']
    list_filter = ['est_active', 'filiere']
    search_fields = ['nom', 'filiere']
    list_editable = ['est_active']
    fieldsets = (
        ('Informations générales', {
            'fields': ('nom', 'filiere', 'description')
        }),
        ('Dates', {
            'fields': ('date_debut', 'date_limite')
        }),
        ('Capacité et prix', {
            'fields': ('capacite_max', 'frais_candidature')
        }),
        ('Prérequis et statut', {
            'fields': ('prerequis', 'est_active')
        }),
    )


@admin.register(Candidature)
class CandidatureAdmin(admin.ModelAdmin):
    list_display = ['reference', 'nom', 'prenom', 'campagne', 'statut', 'date_soumission']
    list_filter = ['statut', 'campagne', 'source']
    search_fields = ['reference', 'nom', 'prenom', 'email_personnel']
    readonly_fields = ['reference', 'date_soumission']
    fieldsets = (
        ('Identifiants', {
            'fields': ('reference', 'utilisateur', 'campagne', 'statut')
        }),
        ('Informations personnelles', {
            'fields': ('nom', 'prenom', 'sexe', 'date_naissance', 'lieu_naissance', 
                      'nationalite', 'telephone', 'email_personnel', 'adresse', 'pays', 'ville')
        }),
        ('Parcours académique', {
            'fields': ('dernier_etablissement', 'niveau_etudes', 'diplome_obtenu', 
                      'annee_obtention', 'moyenne_generale')
        }),
        ('Documents', {
            'fields': ('cv', 'lettre_motivation', 'releves_notes', 'autres_documents')
        }),
        ('Questions', {
            'fields': ('motivation', 'experiences', 'competences', 'source')
        }),
        ('Administration', {
            'fields': ('date_decision', 'commentaire_admin', 'paiement_effectue')
        }),
    )