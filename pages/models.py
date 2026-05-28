from django.db import models
from django.core.exceptions import ValidationError


class HomePage(models.Model):
    """Contenu dynamique de la page d'accueil"""

    # Section héros
    hero_badge = models.CharField(max_length=100, default="Scientific Computing & AI", verbose_name="Badge héros")
    hero_title = models.TextField(default="La science accessible à tous les esprits curieux", verbose_name="Titre héros")
    hero_description = models.TextField(default="Des cours scientifiques de qualité...", verbose_name="Description héros")
    hero_cta_primary_text = models.CharField(max_length=50, default="Découvrir les cours", verbose_name="Texte bouton principal")
    hero_cta_primary_url = models.CharField(max_length=200, default="{% url 'cours:catalogue' %}", verbose_name="URL bouton principal")
    hero_cta_secondary_text = models.CharField(max_length=50, default="Créer un compte", verbose_name="Texte bouton secondaire")
    hero_cta_secondary_url = models.CharField(max_length=200, default="{% url 'comptes:inscription' %}", verbose_name="URL bouton secondaire")

    # Statistiques
    stats_students = models.IntegerField(default=1500, verbose_name="Nombre d'étudiants")
    stats_courses = models.IntegerField(default=25, verbose_name="Nombre de cours")
    stats_countries = models.IntegerField(default=15, verbose_name="Nombre de pays")

    # Section fonctionnalités
    features_title = models.CharField(max_length=200, default="Pourquoi choisir Numeria ?", verbose_name="Titre fonctionnalités")
    features = models.JSONField(default=list, verbose_name="Fonctionnalités (JSON)")

    # Témoignages
    testimonials = models.JSONField(default=list, verbose_name="Témoignages (JSON)")

    # Métadonnées
    meta_title = models.CharField(max_length=60, default="Accueil - Numeria Institute", verbose_name="Meta title")
    meta_description = models.TextField(max_length=160, default="...", verbose_name="Meta description")

    class Meta:
        verbose_name = "Page d'accueil"
        verbose_name_plural = "Page d'accueil"

    def __str__(self):
        return "Contenu page d'accueil"

    def clean(self):
        if HomePage.objects.exclude(pk=self.pk).exists():
            raise ValidationError("Il ne peut y avoir qu'une seule page d'accueil.")


class AboutPage(models.Model):
    """Contenu dynamique de la page À propos"""

    title = models.CharField(max_length=200, default="À propos de Numeria Institute", verbose_name="Titre")
    content = models.TextField(default="Numeria Institute est...", verbose_name="Contenu")
    mission_title = models.CharField(max_length=200, default="Notre mission", verbose_name="Titre mission")
    mission_content = models.TextField(default="...", verbose_name="Contenu mission")
    vision_title = models.CharField(max_length=200, default="Notre vision", verbose_name="Titre vision")
    vision_content = models.TextField(default="...", verbose_name="Contenu vision")

    # Équipe (JSON pour simplicité)
    team = models.JSONField(default=list, verbose_name="Équipe (JSON)")

    meta_title = models.CharField(max_length=60, default="À propos - Numeria Institute", verbose_name="Meta title")
    meta_description = models.TextField(max_length=160, default="...", verbose_name="Meta description")

    class Meta:
        verbose_name = "Page À propos"
        verbose_name_plural = "Page À propos"

    def __str__(self):
        return "Contenu page À propos"

    def clean(self):
        if AboutPage.objects.exclude(pk=self.pk).exists():
            raise ValidationError("Il ne peut y avoir qu'une seule page À propos.")


class ContactPage(models.Model):
    """Contenu dynamique de la page Contact"""

    title = models.CharField(max_length=200, default="Contactez-nous", verbose_name="Titre")
    intro = models.TextField(default="Nous sommes là pour vous aider.", verbose_name="Introduction")
    address = models.TextField(default="Lomé, Togo", verbose_name="Adresse")
    phone = models.CharField(max_length=20, default="+228 XX XX XX XX", verbose_name="Téléphone")
    email = models.EmailField(default="numeriainstitude@gmail.com", verbose_name="Email")
    hours = models.TextField(default="Lundi-Vendredi: 9h-18h", verbose_name="Horaires")

    meta_title = models.CharField(max_length=60, default="Contact - Numeria Institute", verbose_name="Meta title")
    meta_description = models.TextField(max_length=160, default="...", verbose_name="Meta description")

    class Meta:
        verbose_name = "Page Contact"
        verbose_name_plural = "Page Contact"

    def __str__(self):
        return "Contenu page Contact"

    def clean(self):
        if ContactPage.objects.exclude(pk=self.pk).exists():
            raise ValidationError("Il ne peut y avoir qu'une seule page Contact.")
