from django.db import models
from django.contrib.auth.models import User
from cours.models import Cours
from django.db.models import Q


class StatistiquesGlobales(models.Model):
    """Statistiques globales du site pour le dashboard."""
    
    date = models.DateField(auto_now_add=True, unique=True)
    nombre_utilisateurs_actifs = models.IntegerField(default=0)
    nombre_etudiants_inscrits = models.IntegerField(default=0)
    nombre_cours_suivis = models.IntegerField(default=0)
    nombre_certificats_gagnes = models.IntegerField(default=0)
    nombre_paiements_jour = models.IntegerField(default=0)
    revenus_jour = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    nombre_sessions_jour = models.IntegerField(default=0)
    taux_engagement = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name='Taux d\'engagement (%)'
    )
    
    def __str__(self):
        return f'Stats {self.date}'
    
    class Meta:
        verbose_name = 'Statistique globale'
        verbose_name_plural = 'Statistiques globales'
        ordering = ['-date']


class AnalytiquesCours(models.Model):
    """Analytics détaillées par cours."""
    
    cours = models.OneToOneField(
        Cours, on_delete=models.CASCADE,
        related_name='analytics'
    )
    
    # Performance
    nombre_consultations = models.IntegerField(default=0)
    nombre_inscriptions = models.IntegerField(default=0)
    nombre_completions = models.IntegerField(default=0)
    taux_completion = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Engagement
    temps_moyen_par_etudiant = models.IntegerField(default=0, help_text='En minutes')
    nombre_questions_posees = models.IntegerField(default=0)
    nombre_discussions = models.IntegerField(default=0)
    
    # Finance
    revenus_totaux = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    nombre_transactions = models.IntegerField(default=0)
    
    # Données mise à jour
    derniere_mise_a_jour = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f'Analytics {self.cours.titre}'
    
    class Meta:
        verbose_name = 'Analytique cours'
        verbose_name_plural = 'Analytiques cours'


class AnalytiquesUtilisateur(models.Model):
    """Comportement et engagement de chaque utilisateur."""
    
    utilisateur = models.OneToOneField(
        User, on_delete=models.CASCADE,
        related_name='analytics'
    )
    
    # Activité
    nombre_connexions = models.IntegerField(default=0)
    derniere_connexion = models.DateTimeField(null=True, blank=True)
    premiere_connexion = models.DateTimeField(null=True, blank=True)
    
    # Apprentissage
    nombre_cours_suivis = models.IntegerField(default=0)
    nombre_lecons_completees = models.IntegerField(default=0)
    nombre_exercices_termines = models.IntegerField(default=0)
    nombre_certificats = models.IntegerField(default=0)
    
    # Engagement
    temps_total_apprentissage = models.IntegerField(default=0, help_text='En minutes')
    score_engagement = models.IntegerField(default=0, help_text='Score 0-100')
    
    # Préférences
    matieres_favorites = models.CharField(max_length=200, blank=True)
    niveau_prefere = models.CharField(max_length=50, blank=True)
    
    derniere_mise_a_jour = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f'Analytics {self.utilisateur.username}'
    
    class Meta:
        verbose_name = 'Analytique utilisateur'
        verbose_name_plural = 'Analytiques utilisateurs'


class EveneementUtilisateur(models.Model):
    """Enregistre chaque action de l'utilisateur pour l'analyse."""
    
    TYPES_EVENEMENTS = [
        ('connexion', 'Connexion'),
        ('lecture_cours', 'Lecture de cours'),
        ('completion_lecon', 'Complétion de leçon'),
        ('reponse_exercice', 'Réponse exercice'),
        ('achat_cours', 'Achat de cours'),
        ('telechargement_certificat', 'Téléchargement certificat'),
        ('publication_discussion', 'Publication discussion'),
        ('download_ressource', 'Téléchargement ressource'),
        ('interaction_forum', 'Interaction forum'),
        ('autre', 'Autre'),
    ]
    
    utilisateur = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='evenements'
    )
    
    type_evenement = models.CharField(
        max_length=50, choices=TYPES_EVENEMENTS,
        verbose_name='Type d\'\u00e9vénement'
    )
    
    # Contexte de l'événement
    cours = models.ForeignKey(
        Cours, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='evenements'
    )
    
    description = models.TextField(blank=True)
    metadonnees = models.JSONField(default=dict, blank=True)
    
    date_creation = models.DateTimeField(auto_now_add=True)
    ip_adresse = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    def __str__(self):
        return f'{self.utilisateur.username} - {self.get_type_evenement_display()}'
    
    class Meta:
        verbose_name = 'Événement utilisateur'
        verbose_name_plural = 'Événements utilisateurs'
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['utilisateur', '-date_creation']),
            models.Index(fields=['type_evenement']),
        ]
