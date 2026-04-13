from django.contrib import admin
from .models import Mentor, Mentee, DemandeMentorat, RelationMentorat, SeanceMentorat, PaiementSeance


@admin.register(Mentor)
class MentorAdmin(admin.ModelAdmin):
    list_display = ['profil', 'domaines_expertise', 'niveau_experience', 'est_actif', 'nombre_mentees_actuels']
    list_filter = ['domaines_expertise', 'niveau_experience', 'est_actif', 'disponibilite']
    search_fields = ['profil__utilisateur__username', 'profil__utilisateur__first_name', 'profil__utilisateur__last_name']
    readonly_fields = ['date_inscription', 'nombre_mentees_actuels', 'nombre_mentees_total']


@admin.register(Mentee)
class MenteeAdmin(admin.ModelAdmin):
    list_display = ['profil', 'objectifs', 'niveau_etudes', 'est_actif', 'a_mentor_actuel']
    list_filter = ['objectifs', 'niveau_etudes', 'est_actif', 'a_mentor_actuel']
    search_fields = ['profil__utilisateur__username', 'profil__utilisateur__first_name', 'profil__utilisateur__last_name']
    readonly_fields = ['date_inscription']


@admin.register(DemandeMentorat)
class DemandeMentoratAdmin(admin.ModelAdmin):
    list_display = ['mentee', 'mentor', 'statut', 'date_creation', 'date_reponse']
    list_filter = ['statut', 'date_creation']
    search_fields = ['mentee__profil__utilisateur__username', 'mentor__profil__utilisateur__username']
    readonly_fields = ['date_creation', 'date_reponse']
    actions = ['accepter_demandes', 'refuser_demandes']

    def accepter_demandes(self, request, queryset):
        for demande in queryset.filter(statut='en_attente'):
            demande.accepter()
        self.message_user(request, f"{queryset.filter(statut='en_attente').count()} demandes acceptées.")
    accepter_demandes.short_description = "Accepter les demandes sélectionnées"

    def refuser_demandes(self, request, queryset):
        for demande in queryset.filter(statut='en_attente'):
            demande.refuser()
        self.message_user(request, f"{queryset.filter(statut='en_attente').count()} demandes refusées.")
    refuser_demandes.short_description = "Refuser les demandes sélectionnées"


@admin.register(RelationMentorat)
class RelationMentoratAdmin(admin.ModelAdmin):
    list_display = ['mentor', 'mentee', 'date_debut', 'est_active']
    list_filter = ['est_active', 'date_debut']
    search_fields = ['mentor__profil__utilisateur__username', 'mentee__profil__utilisateur__username']
    readonly_fields = ['date_debut', 'date_fin']


@admin.register(SeanceMentorat)
class SeanceMentoratAdmin(admin.ModelAdmin):
    list_display = ['relation', 'titre', 'date_heure', 'statut', 'modalite']
    list_filter = ['statut', 'modalite', 'date_heure']
    search_fields = ['relation__mentor__profil__utilisateur__username', 'relation__mentee__profil__utilisateur__username', 'titre']
    readonly_fields = ['date_creation', 'date_modification']


@admin.register(PaiementSeance)
class PaiementSeanceAdmin(admin.ModelAdmin):
    list_display = ['seance', 'montant_total', 'commission_numeria', 'montant_mentor', 'statut', 'date_creation']
    list_filter = ['statut', 'date_creation']
    search_fields = ['seance__relation__mentor__profil__utilisateur__username', 'seance__relation__mentee__profil__utilisateur__username', 'reference_mobile_money']
    readonly_fields = ['montant_total', 'commission_numeria', 'montant_mentor', 'date_creation', 'date_confirmation']
    actions = ['confirmer_paiements']

    def confirmer_paiements(self, request, queryset):
        count = 0
        for p in queryset.filter(statut='preuve_soumise'):
            p.confirmer()
            count += 1
        self.message_user(request, f"{count} paiement(s) confirmé(s).")
    confirmer_paiements.short_description = "Confirmer les paiements sélectionnés"
