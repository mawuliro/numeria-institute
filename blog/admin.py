from django.contrib import admin
from .models import Article, Categorie


class ArticleAdmin(admin.ModelAdmin):

    # Colonnes dans la liste des articles
    list_display = [
        'titre',
        'auteur',
        'categorie',
        'est_publie',
        'nombre_vues',
        'date_creation',
    ]

    # Filtres à droite
    list_filter = [
        'est_publie',
        'categorie',
        'auteur',
    ]

    # Barre de recherche
    search_fields = [
        'titre',
        'resume',
        'contenu',
    ]

    # Champs éditables dans la liste
    list_editable = [
        'est_publie',
    ]

    # Remplissage automatique du slug depuis le titre
    # Quand tu tapes le titre, le slug se remplit automatiquement
    prepopulated_fields = {'slug': ('titre',)}


class CategorieAdmin(admin.ModelAdmin):

    list_display = ['nom', 'slug']

    # Slug auto-rempli depuis le nom
    prepopulated_fields = {'slug': ('nom',)}


admin.site.register(Article, ArticleAdmin)
admin.site.register(Categorie, CategorieAdmin)