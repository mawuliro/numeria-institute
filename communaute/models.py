from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse

class Categorie(models.Model):
    nom = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    ordre = models.PositiveIntegerField(default=0)
    est_active = models.BooleanField(default=True)
    date_creation = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"
        ordering = ['ordre', 'nom']

    def __str__(self):
        return self.nom

    def get_absolute_url(self):
        return reverse('communaute:categorie_detail', kwargs={'pk': self.pk})

class Sujet(models.Model):
    titre = models.CharField(max_length=200)
    categorie = models.ForeignKey(Categorie, on_delete=models.CASCADE, related_name='sujets')
    auteur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sujets')
    contenu = models.TextField()
    date_creation = models.DateTimeField(default=timezone.now)
    date_modification = models.DateTimeField(auto_now=True)
    est_epingle = models.BooleanField(default=False)
    est_ferme = models.BooleanField(default=False)
    vues = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Sujet"
        verbose_name_plural = "Sujets"
        ordering = ['-est_epingle', '-date_modification']

    def __str__(self):
        return self.titre

    def get_absolute_url(self):
        return reverse('communaute:sujet_detail', kwargs={'pk': self.pk})

    @property
    def nombre_reponses(self):
        return self.messages.count() - 1  # -1 pour exclure le message initial

    @property
    def dernier_message(self):
        return self.messages.order_by('-date_creation').first()

class Message(models.Model):
    sujet = models.ForeignKey(Sujet, on_delete=models.CASCADE, related_name='messages')
    auteur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages')
    contenu = models.TextField()
    date_creation = models.DateTimeField(default=timezone.now)
    date_modification = models.DateTimeField(auto_now=True)
    est_edite = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        ordering = ['date_creation']

    def __str__(self):
        return f"Message de {self.auteur} dans {self.sujet}"

    def get_absolute_url(self):
        return f"{self.sujet.get_absolute_url()}#message-{self.pk}"

class ProfilUtilisateur(models.Model):
    utilisateur = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profil_communaute')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(blank=True, max_length=500)
    specialisation = models.CharField(max_length=100, blank=True)
    niveau_etudes = models.CharField(max_length=50, blank=True)
    site_web = models.URLField(blank=True)
    date_inscription = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Profil utilisateur"
        verbose_name_plural = "Profils utilisateurs"

    def __str__(self):
        return f"Profil de {self.utilisateur.username}"
