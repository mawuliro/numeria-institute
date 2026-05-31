from django.contrib import admin
from .models import Paiement, RemboursementDemande


class PaiementAdmin(admin.ModelAdmin):
    list_display = [
        'reference_numeria',
        'etudiant',
        'cours',
        'montant_initial',
        'devise',
        'provider',
        'method',
        'statut',
        'date_creation',
    ]
    list_filter = ['statut', 'provider', 'method', 'devise']
    search_fields = [
        'reference_numeria',
        'etudiant__username',
        'course__titre',
        'reference_provider',
    ]
    readonly_fields = [
        'reference_numeria',
        'date_creation',
        'date_modification',
    ]
    list_editable = ['statut']

    fieldsets = [
        ('Informations principales', {
            'fields': [
                'etudiant', 'cours',
                'montant_initial', 'montant_final', 'frais_plateforme', 'devise',
                'statut',
            ]
        }),
        ('Provider', {
            'fields': [
                'provider',
                'method',
                'reference_numeria',
                'reference_provider',
            ]
        }),
        ('Métadonnées', {
            'fields': ['notes', 'date_creation', 'date_modification'],
            'classes': ['collapse'],
        }),
    ]


class RemboursementAdmin(admin.ModelAdmin):
    list_display = ['paiement', 'statut', 'date_demande']
    list_filter = ['statut']
    list_editable = ['statut']


admin.site.register(Paiement, PaiementAdmin)
admin.site.register(RemboursementDemande, RemboursementAdmin)