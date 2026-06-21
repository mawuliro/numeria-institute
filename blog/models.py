from django.db import models

# On importe User — le modèle utilisateur intégré de Django
# Il représente l'auteur de l'article
from django.contrib.auth.models import User


class Categorie(models.Model):
    """
    Catégorie d'un article de blog.
    Ex: Mathématiques, Physique, Actualités scientifiques...
    """

    # Nom de la catégorie
    nom = models.CharField(max_length=100)

    # Le "slug" est la version URL-friendly du nom
    # Ex: "Actualités scientifiques" → "actualites-scientifiques"
    slug = models.SlugField(max_length=100, unique=True)

    def __str__(self):
        return self.nom

    class Meta:
        verbose_name = 'Catégorie'
        verbose_name_plural = 'Catégories'
        ordering = ['nom']


class Article(models.Model):
    """
    Un article de blog sur Numeria Institute.
    """

    # --- INFORMATIONS PRINCIPALES ---

    # Titre de l'article
    titre = models.CharField(max_length=200)

    # Slug pour l'URL : /blog/introduction-algebre-lineaire/
    # unique=True : deux articles ne peuvent pas avoir le même slug
    slug = models.SlugField(max_length=200, unique=True)

    # Résumé court affiché dans la liste des articles
    resume = models.CharField(max_length=300)

    # Contenu complet de l'article — texte long
    contenu = models.TextField()

    # --- RELATIONS ---

    # L'auteur de l'article — lié au modèle User de Django
    # on_delete=SET_NULL : si l'auteur est supprimé, l'article reste
    auteur = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='articles'
    )

    # La catégorie de l'article
    # on_delete=SET_NULL : si la catégorie est supprimée, l'article reste
    categorie = models.ForeignKey(
        Categorie,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='articles'
    )

    # --- MÉDIAS ---

    # Image de couverture de l'article (optionnelle)
    image_couverture = models.URLField(
        blank=True,
        null=True,
        help_text="URL d'une image de couverture"
    )

    # --- STATUT ---

    # Est-ce que l'article est publié ?
    est_publie = models.BooleanField(default=False)

    # Nombre de vues de l'article
    nombre_vues = models.IntegerField(default=0)

    # --- MÉTADONNÉES ---

    # Date de création automatique
    date_creation = models.DateTimeField(auto_now_add=True)

    # Date de modification automatique
    date_modification = models.DateTimeField(auto_now=True)

    # Date de publication choisie manuellement
    date_publication = models.DateTimeField(null=True, blank=True)

    # ── CHAMPS CMS ────────────────────────────────────────────────────────
    STATUS_ARTICLE = [
        ('brouillon', 'Brouillon'),
        ('publie',    'Publié'),
        ('archive',   'Archivé'),
    ]
    status = models.CharField(
        max_length=20, choices=STATUS_ARTICLE, default='brouillon',
        verbose_name='Statut',
    )
    meta_description = models.CharField(
        max_length=160, blank=True, verbose_name='Meta description',
    )
    reading_time_minutes = models.IntegerField(
        default=5, verbose_name='Temps de lecture (min)',
    )
    tags = models.CharField(
        max_length=500, blank=True,
        verbose_name='Tags', help_text='Tags séparés par des virgules',
    )

    def save(self, *args, **kwargs):
        # Synchronise est_publie avec status
        self.est_publie = (self.status == 'publie')
        # Auto-calculate reading time (~200 words/min)
        if self.contenu:
            words = len(self.contenu.split())
            self.reading_time_minutes = max(1, words // 200)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.titre

    class Meta:
        verbose_name = 'Article'
        verbose_name_plural = 'Articles'
        ordering = ['-date_creation']