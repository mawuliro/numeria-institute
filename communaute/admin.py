from django.contrib import admin
from .models import Categorie, Sujet, Message, ProfilUtilisateur

@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display = ['nom', 'description', 'ordre', 'est_active', 'date_creation']
    list_filter = ['est_active', 'date_creation']
    search_fields = ['nom', 'description']
    ordering = ['ordre', 'nom']

@admin.register(Sujet)
class SujetAdmin(admin.ModelAdmin):
    list_display = ['titre', 'categorie', 'auteur', 'date_creation', 'est_epingle', 'est_ferme', 'vues']
    list_filter = ['categorie', 'est_epingle', 'est_ferme', 'date_creation']
    search_fields = ['titre', 'contenu', 'auteur__username']
    readonly_fields = ['vues']
    ordering = ['-date_creation']

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['sujet', 'auteur', 'date_creation', 'est_edite']
    list_filter = ['date_creation', 'est_edite']
    search_fields = ['contenu', 'auteur__username', 'sujet__titre']
    ordering = ['-date_creation']

@admin.register(ProfilUtilisateur)
class ProfilUtilisateurAdmin(admin.ModelAdmin):
    list_display = ['utilisateur', 'specialisation', 'niveau_etudes', 'date_inscription']
    list_filter = ['niveau_etudes', 'date_inscription']
    search_fields = ['utilisateur__username', 'specialisation', 'bio']
    ordering = ['-date_inscription']
