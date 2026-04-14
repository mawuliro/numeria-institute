from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from cloudinary.models import CloudinaryField


class Profil(models.Model):
    """Extension du modèle User de Django."""

    utilisateur = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profil'
    )

    # --- PHOTO DE PROFIL ---
    # CORRIGÉ : CloudinaryField avec les bons paramètres
    photo = CloudinaryField(
        'photo',  # Le premier argument est le nom du champ
        blank=True,
        null=True,
        folder="photos_profil/"  # Optionnel : organise dans un dossier
    )

    # --- INFORMATIONS PERSONNELLES ---
    bio = models.TextField(
        blank=True,
        null=True,
        max_length=500,
        help_text="Parlez-nous de vous en quelques mots"
    )
    pays = models.CharField(max_length=100, blank=True, null=True, default='Togo')
    ville = models.CharField(max_length=100, blank=True, null=True)

    NIVEAUX_ETUDES = [
        ('lycee', _('Lycée')),
        ('licence', _('Licence')),
        ('master', _('Master')),
        ('doctorat', _('Doctorat')),
        ('professionnel', _('Professionnel')),
        ('autre', _('Autre')),
    ]
    niveau_etudes = models.CharField(
        max_length=20,
        choices=NIVEAUX_ETUDES,
        blank=True,
        null=True
    )
    domaine = models.CharField(max_length=100, blank=True, null=True)

    # --- RÉSEAUX SOCIAUX ---
    linkedin = models.URLField(blank=True, null=True)
    github = models.URLField(blank=True, null=True)

    # --- MÉTADONNÉES SOCIALES ---
    nombre_abonnes = models.IntegerField(default=0, verbose_name='Nombre d\'abonnés')
    nombre_abonnements = models.IntegerField(default=0, verbose_name='Nombre d\'abonnements')
    nombre_messages_prives = models.IntegerField(default=0)
    est_verifiee = models.BooleanField(default=False, verbose_name='Compte vérifié')
    est_menteur = models.BooleanField(
        default=False,
        verbose_name='Accès mentor activé',
        help_text='Peut répondre aux questions des étudiants'
    )
    
    # --- PRÉFÉRENCES ---
    notifications_activees = models.BooleanField(
        default=True,
        verbose_name='Notifications activées'
    )
    theme_preference = models.CharField(
        max_length=10,
        choices=[('light', 'Clair'), ('dark', 'Sombre'), ('auto', 'Auto')],
        default='auto',
        verbose_name='Préférence thème'
    )
    langue_preference = models.CharField(
        max_length=10,
        choices=[('fr', 'Français'), ('en', 'English')],
        default='fr',
        verbose_name='Langue préférée'
    )

    # --- MÉTADONNÉES ---
    date_inscription = models.DateTimeField(auto_now_add=True)
    est_actif = models.BooleanField(default=True)

    def __str__(self):
        return f"Profil de {self.utilisateur.username}"

    def get_photo_url(self):
        """
        Retourne l'URL de la photo ou None si pas de photo.
        """
        if self.photo:
            return self.photo.url
        return None

    class Meta:
        verbose_name = _('Profil')
        verbose_name_plural = _('Profils')
        ordering = ['-date_inscription']