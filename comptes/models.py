from django.db import models
from django.contrib.auth.models import User


def chemin_photo_profil(instance, filename):
    """
    Définit le chemin de stockage de la photo.
    La photo sera stockée dans : media/photos_profil/username/photo.jpg
    Cela évite les conflits entre utilisateurs.
    """
    # On récupère l'extension du fichier original
    extension = filename.split('.')[-1]
    # On crée un nom de fichier propre
    return f'photos_profil/{instance.utilisateur.username}/photo.{extension}'


class Profil(models.Model):
    """Extension du modèle User de Django."""

    utilisateur = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profil'
    )

    # --- PHOTO DE PROFIL ---
    # ImageField stocke le fichier et sauvegarde le chemin en base de données
    # blank=True, null=True → la photo est optionnelle
    # upload_to → utilise notre fonction pour définir le chemin
    photo = models.ImageField(
        upload_to=chemin_photo_profil,
        blank=True,
        null=True,
        verbose_name="Photo de profil"
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
        ('lycee', 'Lycée'),
        ('licence', 'Licence'),
        ('master', 'Master'),
        ('doctorat', 'Doctorat'),
        ('professionnel', 'Professionnel'),
        ('autre', 'Autre'),
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

    # --- MÉTADONNÉES ---
    date_inscription = models.DateTimeField(auto_now_add=True)
    est_actif = models.BooleanField(default=True)

    def __str__(self):
        return f"Profil de {self.utilisateur.username}"

    def get_photo_url(self):
        """
        Retourne l'URL de la photo ou None si pas de photo.
        On utilisera cette méthode dans les templates.
        """
        if self.photo:
            return self.photo.url
        return None

    class Meta:
        verbose_name = 'Profil'
        verbose_name_plural = 'Profils'
        ordering = ['-date_inscription']