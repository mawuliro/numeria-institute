# admissions/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
import uuid


def validate_file_size(value):
    """Valide que le fichier ne dépasse pas 2MB"""
    filesize = value.size
    if filesize > 2 * 1024 * 1024:  # 2MB
        raise ValidationError("Le fichier ne doit pas dépasser 2 Mo.")


class CampagneRecrutement(models.Model):
    """
    Une campagne de recrutement pour une filière.
    Permet de définir le prix, la date limite, et le nombre de places.
    """
    nom = models.CharField(max_length=100, verbose_name="Nom de la campagne")
    filiere = models.CharField(max_length=100, verbose_name="Filière")
    description = models.TextField(verbose_name="Description")
    
    # Dates
    date_debut = models.DateField(verbose_name="Date de début")
    date_limite = models.DateField(verbose_name="Date limite de candidature")
    
    # Capacité et prix
    capacite_max = models.IntegerField(
        default=20, 
        verbose_name="Nombre maximum d'étudiants",
        help_text="Laisser vide si illimité"
    )
    frais_candidature = models.DecimalField(
        max_digits=10, 
        decimal_places=0, 
        default=0,
        verbose_name="Frais de candidature (FCFA)",
        help_text="0 = gratuit"
    )
    
    # Statut
    est_active = models.BooleanField(default=True, verbose_name="Campagne active")
    
    # Prérequis (texte libre)
    prerequis = models.TextField(
        blank=True,
        verbose_name="Prérequis",
        help_text="Diplômes requis, expérience, etc."
    )
    
    date_creation = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.nom} ({self.filiere}) - {self.date_limite}"
    
    def est_ouverte(self):
        """Vérifie si la campagne est encore ouverte"""
        return self.est_active and self.date_limite >= timezone.now().date()
    
    class Meta:
        verbose_name = "Campagne de recrutement"
        verbose_name_plural = "Campagnes de recrutement"
        ordering = ['-date_creation']


class Candidature(models.Model):
    """Candidature d'un étudiant"""
    
    # Statuts possibles
    STATUTS = [
        ('brouillon', '📝 Brouillon'),
        ('soumise', '📤 Soumise'),
        ('en_revue', '🔍 En revue'),
        ('acceptee', '✅ Acceptée'),
        ('liste_attente', '⏳ Liste d\'attente'),
        ('refusee', '❌ Refusée'),
    ]
    
    SEXES = [
        ('M', 'Masculin'),
        ('F', 'Féminin'),
    ]
    
    # Lien vers l'utilisateur et la campagne
    utilisateur = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='candidatures'
    )
    campagne = models.ForeignKey(
        CampagneRecrutement, 
        on_delete=models.CASCADE, 
        related_name='candidatures'
    )
    
    # Statut
    statut = models.CharField(max_length=20, choices=STATUTS, default='brouillon')
    
    # ─── INFORMATIONS PERSONNELLES ─────────────────────────────────────────
    nom = models.CharField(max_length=100, verbose_name="Nom")
    prenom = models.CharField(max_length=100, verbose_name="Prénom")
    sexe = models.CharField(max_length=1, choices=SEXES, verbose_name="Sexe")
    date_naissance = models.DateField(verbose_name="Date de naissance")
    lieu_naissance = models.CharField(max_length=200, verbose_name="Lieu de naissance")
    nationalite = models.CharField(max_length=100, default='Togolaise', verbose_name="Nationalité")
    
    # Contact
    telephone = models.CharField(max_length=20, verbose_name="Téléphone")
    email_personnel = models.EmailField(verbose_name="Email personnel")
    adresse = models.TextField(verbose_name="Adresse complète")
    pays = models.CharField(max_length=100, verbose_name="Pays de résidence")
    ville = models.CharField(max_length=100, verbose_name="Ville")
    
    # ─── PARCOURS ACADÉMIQUE ───────────────────────────────────────────────
    dernier_etablissement = models.CharField(max_length=200, verbose_name="Dernier établissement fréquenté")
    niveau_etudes = models.CharField(max_length=100, verbose_name="Niveau d'études atteint")
    diplome_obtenu = models.CharField(max_length=200, blank=True, verbose_name="Diplôme obtenu")
    annee_obtention = models.IntegerField(null=True, blank=True, verbose_name="Année d'obtention")
    moyenne_generale = models.DecimalField(
        max_digits=4, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="Moyenne générale (/20)"
    )
    
    # ─── DOCUMENTS (Cloudinary) ────────────────────────────────────────────
    cv = models.FileField(
        upload_to='candidatures/cv/',
        validators=[FileExtensionValidator(['pdf']), validate_file_size],
        verbose_name="CV (PDF)",
        help_text="Format PDF, max 2MB"
    )
    lettre_motivation = models.FileField(
        upload_to='candidatures/lettres/',
        validators=[FileExtensionValidator(['pdf']), validate_file_size],
        verbose_name="Lettre de motivation (PDF)",
        help_text="Format PDF, max 2MB"
    )
    releves_notes = models.FileField(
        upload_to='candidatures/releves/',
        validators=[FileExtensionValidator(['pdf']), validate_file_size],
        verbose_name="Relevés de notes (PDF)",
        help_text="Format PDF, max 2MB"
    )
    autres_documents = models.FileField(
        upload_to='candidatures/autres/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['pdf']), validate_file_size],
        verbose_name="Autres documents (optionnel)",
        help_text="Certificats, attestations, etc. (PDF, max 2MB)"
    )
    
    # ─── QUESTIONS SPÉCIFIQUES ─────────────────────────────────────────────
    motivation = models.TextField(
        verbose_name="Pourquoi souhaitez-vous intégrer cette formation ?"
    )
    experiences = models.TextField(
        blank=True,
        verbose_name="Expériences professionnelles ou associatives"
    )
    competences = models.TextField(
        blank=True,
        verbose_name="Compétences particulières"
    )
    
    # Comment as-tu connu Numeria ?
    SOURCE_CHOICES = [
        ('google', 'Google / Recherche internet'),
        ('facebook', 'Facebook'),
        ('linkedin', 'LinkedIn'),
        ('instagram', 'Instagram'),
        ('bouche_oreille', 'Bouche à oreille'),
        ('presse', 'Presse / Média'),
        ('partenaire', 'Partenaire'),
        ('autre', 'Autre'),
    ]
    source = models.CharField(
        max_length=30, 
        choices=SOURCE_CHOICES, 
        blank=True,
        verbose_name="Comment avez-vous connu Numeria ?"
    )
    
    # ─── MÉTADONNÉES ──────────────────────────────────────────────────────
    reference = models.CharField(max_length=20, unique=True, blank=True)
    date_soumission = models.DateTimeField(auto_now_add=True)
    date_decision = models.DateTimeField(null=True, blank=True)
    commentaire_admin = models.TextField(blank=True, verbose_name="Commentaire interne")
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_candidatures', verbose_name="Traité par",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="Traité le")
    rejection_reason = models.TextField(blank=True, verbose_name="Raison de refus")

    # Paiement
    paiement = models.OneToOneField(
        'paiements.Paiement',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='candidature'
    )
    paiement_effectue = models.BooleanField(default=False, verbose_name="Paiement effectué")
    
    def save(self, *args, **kwargs):
        if not self.reference:
            # Générer une référence unique
            import random
            import string
            lettres = ''.join(random.choices(string.ascii_uppercase, k=3))
            chiffres = ''.join(random.choices(string.digits, k=6))
            self.reference = f"NUM-{lettres}-{chiffres}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.reference} - {self.prenom} {self.nom} - {self.campagne.filiere}"
    
    class Meta:
        verbose_name = "Candidature"
        verbose_name_plural = "Candidatures"
        ordering = ['-date_soumission']