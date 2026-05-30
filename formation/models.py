# formation/models.py
"""
APP FORMATION — Formations payantes avec sessions et accès conditionnel

Structure:
  Formation
    ├─ Session 1 (Janvier)
    │   ├─ Inscription (paiement)
    │   ├─ Leçon 1
    │   └─ Leçon 2
    ├─ Session 2 (Mars)
    └─ ...

Logique commerciale:
  - Formation définie une fois (contenu réutilisable)
  - Sessions = groupes avec places limitées + prix fixe
  - Paiement = accès à UNE session + ses leçons
  - Certificat SEULEMENT si 100% complété
  - Accès limité dans le temps (3 ans après fin session)
"""

import os

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta
import uuid


class Formation(models.Model):
    """
    Modèle représentant une formation générale (bootcamp, workshop, etc).
    Peut avoir plusieurs sessions.
    """
    # Identité
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    titre = models.CharField(max_length=200, verbose_name='Titre')
    slug = models.SlugField(unique=True, verbose_name='Slug URL')
    
    # Description
    description_courte = models.CharField(
        max_length=300,
        verbose_name='Description courte',
        help_text='Brève accroche (ex: "Bootcamp Python 8 semaines")'
    )
    description_longue = models.TextField(verbose_name='Description complète')
    
    # Métadonnées
    TYPES_FORMATION = [
        ('bootcamp', 'Bootcamp (intense)'),
        ('workshop', 'Workshop (court)'),
        ('course', 'Cours (long)'),
        ('masterclass', 'Masterclass'),
        ('certification', 'Certification professionnelle'),
    ]
    type_formation = models.CharField(
        max_length=20,
        choices=TYPES_FORMATION,
        verbose_name='Type'
    )
    
    NIVEAUX = [
        ('debutant', 'Débutant'),
        ('intermediaire', 'Intermédiaire'),
        ('avance', 'Avancé'),
        ('expert', 'Expert'),
    ]
    niveau = models.CharField(max_length=20, choices=NIVEAUX, default='debutant')
    
    # Durée typique (en heures)
    duree_heures = models.IntegerField(
        verbose_name='Durée estimée (heures)',
        help_text='ex: 40 heures pour un bootcamp'
    )
    
    # Instructeur(s)
    instructeurs = models.ManyToManyField(
        User,
        related_name='formations_enseignees',
        verbose_name='Instructeurs'
    )
    
    # Image
    image_couverture = models.ImageField(
        upload_to='formations/covers/',
        verbose_name='Image de couverture',
        help_text='1200x630px recommandé',
        blank=True,
        null=True
    )
    
    # Compétences enseignées
    competences_visees = models.TextField(
        verbose_name='Compétences visées',
        help_text='Une par ligne'
    )
    
    # Prérequis
    prerequis = models.TextField(
        blank=True,
        verbose_name='Prérequis',
        help_text='Connaissances nécessaires avant de s\'inscrire'
    )
    
    # Statut
    est_publiee = models.BooleanField(
        default=False,
        verbose_name='Publiée (visible publiquement)'
    )
    est_archivee = models.BooleanField(
        default=False,
        verbose_name='Archivée (plus d\'inscriptions)'
    )
    
    # Statistiques
    nombre_etudiants_total = models.IntegerField(default=0, editable=False)
    nombre_certifies = models.IntegerField(default=0, editable=False)
    note_moyenne = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        default=0,
        editable=False,
        verbose_name='Note moyenne'
    )
    
    # Dates
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Formation'
        verbose_name_plural = 'Formations'
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['est_publiee']),
        ]
    
    def __str__(self):
        return self.titre
    
    def get_absolute_url(self):
        return reverse('formation:detail', kwargs={'slug': self.slug})
    
    def sessions_actives(self):
        """Sessions ouvertes aux inscriptions."""
        return self.sessions.filter(
            statut__in=['planifiee', 'ouverture', 'en_cours'],
            date_debut_inscriptions__lte=timezone.now().date(),
            date_fin_inscriptions__gte=timezone.now().date()
        ).order_by('date_debut')
    
    def prochaine_session(self):
        """La prochaine session à démarrer ou ouverte."""
        return self.sessions.filter(
            statut__in=['planifiee', 'ouverture', 'en_cours'],
            date_fin_inscriptions__gte=timezone.now().date()
        ).order_by('date_debut').first()
    
    @property
    def image_couverture_url(self):
        """URL de l'image de couverture, ou None si elle n'existe pas."""
        if self.image_couverture:
            try:
                return self.image_couverture.url
            except (ValueError, AttributeError):
                return None
        return None


class SessionFormation(models.Model):
    """
    Une session = groupe/cohorte d'étudiants pour UNE formation.
    
    Exemple:
      Formation "Python Bootcamp"
        ├─ Session Janvier 2026 (30 places)
        ├─ Session Mars 2026 (30 places)
        └─ Session Mai 2026 (30 places)
    """
    formation = models.ForeignKey(
        Formation,
        on_delete=models.CASCADE,
        related_name='sessions',
        verbose_name='Formation'
    )
    
    # Identité
    nom = models.CharField(
        max_length=200,
        verbose_name='Nom de la session',
        help_text='ex: "Cohort Jan 2026"'
    )
    slug = models.SlugField(verbose_name='Slug')
    
    # Dates
    date_debut = models.DateField(verbose_name='Date de début du cours')
    date_fin = models.DateField(verbose_name='Date de fin du cours')
    date_debut_inscriptions = models.DateField(verbose_name='Ouverture des inscriptions')
    date_fin_inscriptions = models.DateField(verbose_name='Fermeture des inscriptions')
    
    # Capacité et prix
    places_totales = models.IntegerField(
        verbose_name='Places disponibles',
        default=30
    )
    prix_fcfa = models.IntegerField(
        verbose_name='Prix (FCFA)',
        help_text='ex: 150000 pour bootcamp 8 semaines'
    )
    
    # Réduction possible
    prix_reduit_fcfa = models.IntegerField(
        blank=True,
        null=True,
        verbose_name='Prix réduit (FCFA)',
        help_text='Si vide, pas de réduction'
    )
    
    # Modalité
    MODALITES = [
        ('presentiel', 'Présentiel'),
        ('visio', 'Visioconférence'),
        ('hybride', 'Hybride'),
    ]
    modalite = models.CharField(
        max_length=20,
        choices=MODALITES,
        default='visio',
        verbose_name='Format'
    )
    
    # Lieu si présentiel
    lieu = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Lieu'
    )
    
    # Statut
    STATUTS = [
        ('planifiee', 'Planifiée (pas encore inscriptions)'),
        ('ouverture', 'Ouverture (inscriptions en cours)'),
        ('fermee', 'Fermée (plus d\'inscriptions)'),
        ('en_cours', 'En cours de formation'),
        ('terminee', 'Terminée'),
        ('annulee', 'Annulée'),
    ]
    statut = models.CharField(
        max_length=20,
        choices=STATUTS,
        default='planifiee',
        verbose_name='Statut'
    )
    
    # Instructeurs spécifiques (vide = utiliser ceux de la formation)
    instructeurs_session = models.ManyToManyField(
        User,
        blank=True,
        related_name='sessions_enseignees',
        verbose_name='Instructeurs (si différent de la formation)'
    )
    
    # Dates
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Session de formation'
        verbose_name_plural = 'Sessions de formation'
        ordering = ['date_debut']
        unique_together = ['formation', 'slug']
        indexes = [
            models.Index(fields=['formation', 'statut']),
            models.Index(fields=['date_fin_inscriptions']),
        ]
    
    def __str__(self):
        return f"{self.formation.titre} — {self.nom}"
    
    def places_disponibles(self):
        """Nombre de places restantes."""
        nb_inscrits = self.inscriptions.filter(
            statut__in=['en_attente', 'confirmee', 'en_cours', 'terminee']
        ).count()
        return max(0, self.places_totales - nb_inscrits)
    
    def places_occupees(self):
        """Nombre de places déjà réservées."""
        return self.places_totales - self.places_disponibles()
    
    def taux_remplissage(self):
        """Pourcentage de places occupées."""
        if self.places_totales <= 0:
            return 0
        return min(100, int((self.places_occupees() / self.places_totales) * 100))
    
    def est_ouverte_aux_inscriptions(self):
        """Session accepte des inscriptions."""
        now = timezone.now().date()
        if self.statut in ['fermee', 'annulee', 'terminee']:
            return False
        return (
            self.date_debut_inscriptions <= now <= self.date_fin_inscriptions and
            self.places_disponibles() > 0
        )
    
    def clean(self):
        """Valider la cohérence des dates de session et d'inscription."""
        super().clean()
        erreurs = {}

        if self.date_fin_inscriptions < self.date_debut_inscriptions:
            erreurs['date_fin_inscriptions'] = ValidationError(
                "La date de fin des inscriptions doit être postérieure ou égale à la date de début."
            )

        if self.date_fin < self.date_debut:
            erreurs['date_fin'] = ValidationError(
                "La date de fin de la session doit être postérieure ou égale à la date de début."
            )

        if erreurs:
            raise ValidationError(erreurs)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def get_instructeurs(self):
        """Retourne les instructeurs (de session ou de formation)."""
        if self.instructeurs_session.exists():
            return self.instructeurs_session.all()
        return self.formation.instructeurs.all()


class InscriptionFormation(models.Model):
    """
    Inscription d'un étudiant à UNE session.
    Paiement OBLIGATOIRE pour confirmer.
    """
    # Relations
    session = models.ForeignKey(
        SessionFormation,
        on_delete=models.CASCADE,
        related_name='inscriptions'
    )
    etudiant = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='inscriptions_formations'
    )
    
    # Prix payé (peut être différent du prix session si réduction)
    prix_paye_fcfa = models.IntegerField(verbose_name='Prix payé (FCFA)')
    
    # Statut
    STATUTS = [
        ('en_attente', 'En attente de paiement'),
        ('confirmee', 'Confirmée (payée)'),
        ('en_cours', 'En cours'),
        ('terminee', 'Terminée'),
        ('annulee', 'Annulée'),
    ]
    statut = models.CharField(
        max_length=20,
        choices=STATUTS,
        default='en_attente',
        verbose_name='Statut'
    )
    
    # Progression
    progression = models.IntegerField(
        default=0,
        verbose_name='Progression (%)'
    )
    
    # Dates
    date_inscription = models.DateTimeField(auto_now_add=True)
    date_confirmation_paiement = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        verbose_name = 'Inscription formation'
        verbose_name_plural = 'Inscriptions formations'
        ordering = ['-date_inscription']
        unique_together = ['session', 'etudiant']  # Une seule inscription par session
        indexes = [
            models.Index(fields=['session', 'statut']),
            models.Index(fields=['etudiant']),
        ]
    
    def __str__(self):
        return f"{self.etudiant.username} → {self.session.nom}"
    
    def a_acces(self):
        """Étudiant peut accéder au contenu."""
        return self.statut in ['confirmee', 'en_cours', 'terminee']
    
    def acces_expire(self):
        """L'accès au contenu expirera à cette date."""
        # 3 ans après la fin de la session
        return self.session.date_fin + timedelta(days=3*365)
    
    def est_acces_expire(self):
        """L'accès a-t-il expiré?"""
        return timezone.now().date() > self.acces_expire()

    @property
    def progression_pct(self):
        return self.progression or 0

    @property
    def session_formation(self):
        return self.session

    @property
    def date_completion(self):
        if self.statut == 'terminee':
            return self.session.date_fin
        return None

    @property
    def prochaine_lecon(self):
        """Retourne la prochaine leçon à faire (non terminée)."""
        if not self.session_id:
            return None
        progressions = self.progressions_lecons.all()
        lecons_terminees = set(p.lecon_id for p in progressions if p.est_terminees)

        for lecon in self.session.formation.lecons.order_by('ordre'):
            if lecon.id not in lecons_terminees:
                return lecon

        return None  # Toutes les leçons sont terminées


class LeconFormation(models.Model):
    """
    Une leçon/module d'une formation.
    Accès conditionnel = inscription confirmée + pas d'accès expiré.
    """
    formation = models.ForeignKey(
        Formation,
        on_delete=models.CASCADE,
        related_name='lecons'
    )
    
    # Metadata
    titre = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Ordre
    ordre = models.IntegerField(default=1, verbose_name='Ordre d\'affichage')
    
    # Contenu
    contenu_html = models.TextField(verbose_name='Contenu (HTML)')
    video_youtube = models.URLField(
        blank=True,
        verbose_name='Vidéo YouTube/Vimeo'
    )
    ressources_telechargeables = models.FileField(
        upload_to='formations/resources/',
        blank=True,
        verbose_name='Ressource téléchargeable (PDF, ZIP, etc)'
    )
    
    # Durée estimée
    duree_minutes = models.IntegerField(default=30, verbose_name='Durée (minutes)')
    
    # Exercice optionnel
    exercice_code_html = models.TextField(
        blank=True,
        verbose_name='HTML de l\'exercice (si s/o)',
        help_text='HTML personnalisé pour un exercice'
    )
    
    # Dates
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Leçon formation'
        verbose_name_plural = 'Leçons formation'
        ordering = ['formation', 'ordre']
        indexes = [
            models.Index(fields=['formation', 'ordre']),
        ]
    
    def __str__(self):
        return f"{self.formation.titre} > {self.titre}"

    @property
    def url_video(self):
        return self.video_youtube

    @property
    def ressources(self):
        if not self.ressources_telechargeables:
            return []
        return [{
            'url': self.ressources_telechargeables.url,
            'nom': os.path.basename(self.ressources_telechargeables.name)
        }]

    @property
    def exercice_code(self):
        return self.exercice_code_html

    @property
    def duree_estimee(self):
        return self.duree_minutes
    
    def get_next(self):
        """Leçon suivante."""
        return self.formation.lecons.filter(ordre__gt=self.ordre).order_by('ordre').first()
    
    def get_previous(self):
        """Leçon précédente."""
        return self.formation.lecons.filter(ordre__lt=self.ordre).order_by('-ordre').first()


class ProgressionLecon(models.Model):
    """
    Progression d'un étudiant dans une leçon.
    """
    inscription = models.ForeignKey(
        InscriptionFormation,
        on_delete=models.CASCADE,
        related_name='progressions_lecons'
    )
    lecon = models.ForeignKey(LeconFormation, on_delete=models.CASCADE)
    
    # States
    est_commencee = models.BooleanField(default=False)
    est_terminees = models.BooleanField(default=False)
    
    # Dates
    date_premiere_visite = models.DateTimeField(auto_now_add=True)
    date_completion = models.DateTimeField(blank=True, null=True)
    temps_passe_minutes = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = 'Progression leçon'
        verbose_name_plural = 'Progressions leçons'
        unique_together = ['inscription', 'lecon']
    
    def __str__(self):
        return f"{self.inscription.etudiant.username} > {self.lecon.titre}"


class CertificatFormation(models.Model):
    """
    Certificat décerné après completion 100% d'une session.
    """
    inscription = models.OneToOneField(
        InscriptionFormation,
        on_delete=models.CASCADE,
        related_name='certificat'
    )
    
    # Token de vérification publique
    token_verification = models.CharField(
        max_length=64,
        unique=True,
        verbose_name='Token (URL vérification)',
        help_text='Permet vérifier le certificat sans compte'
    )
    
    # Dates
    date_obtention = models.DateTimeField(auto_now_add=True)
    date_expiration = models.DateField(
        blank=True,
        null=True,
        verbose_name='Expiration (vide = pas d\'expiration)'
    )
    
    # Note
    note_finale = models.IntegerField(verbose_name='Note finale (%)')
    
    class Meta:
        verbose_name = 'Certificat formation'
        verbose_name_plural = 'Certificats formations'
        ordering = ['-date_obtention']
    
    def __str__(self):
        return f"Certificat {self.inscription.etudiant.username}"
    
    def est_valide(self):
        """Certificat toujours valide?"""
        if not self.date_expiration:
            return True
        return timezone.now().date() <= self.date_expiration


# =============================================================================
# FORMATION CMS — Structure Module → Leçon (ajoutée pour le panneau admin)
# Séparée de LeconFormation existante pour éviter tout conflit.
# =============================================================================

class FormationModule(models.Model):
    """Regroupe des leçons dans une formation — couche facultative."""
    formation   = models.ForeignKey(Formation, on_delete=models.CASCADE, related_name='modules')
    titre       = models.CharField(max_length=300, verbose_name='Titre')
    description = models.TextField(blank=True, verbose_name='Description')
    ordre       = models.IntegerField(default=0, verbose_name='Ordre')
    est_actif   = models.BooleanField(default=True, verbose_name='Actif')

    class Meta:
        ordering = ['ordre']
        verbose_name = 'Module de formation'
        verbose_name_plural = 'Modules de formation'

    def __str__(self):
        return f'[{self.formation.titre}] {self.titre}'


class FormationLesson(models.Model):
    """Leçon CMS dans un module de formation — supporte EasyMDE, LaTeX, code."""
    CONTENT_TYPE_CHOICES = [
        ('text',     'Texte / Article'),
        ('video',    'Vidéo'),
        ('mixed',    'Mixte (Texte + Vidéo)'),
        ('exercise', 'Exercice pratique'),
    ]

    module      = models.ForeignKey(FormationModule, on_delete=models.CASCADE, related_name='lessons')
    formation   = models.ForeignKey(Formation, on_delete=models.CASCADE, related_name='formation_lessons')
    titre       = models.CharField(max_length=300, verbose_name='Titre')
    slug        = models.SlugField(blank=True, max_length=300)
    contenu     = models.TextField(blank=True, verbose_name='Contenu',
                                   help_text='Supporte HTML, LaTeX, Markdown.')
    video_url   = models.URLField(blank=True, null=True, verbose_name='URL vidéo')
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES,
                                    default='text', verbose_name='Type de contenu')
    ordre       = models.IntegerField(default=0, verbose_name='Ordre')
    is_free_preview = models.BooleanField(default=False, verbose_name='Aperçu gratuit')
    duree_minutes = models.IntegerField(default=10, verbose_name='Durée (minutes)')
    est_active  = models.BooleanField(default=True, verbose_name='Active')

    class Meta:
        ordering = ['ordre']
        verbose_name = 'Leçon de formation'
        verbose_name_plural = 'Leçons de formation'

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.titre)[:300]
        super().save(*args, **kwargs)

    def __str__(self):
        return f'[{self.formation.titre}] {self.titre}'
