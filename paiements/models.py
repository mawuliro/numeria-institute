from django.db import models
from django.contrib.auth.models import User
from cours.models import Cours


class Paiement(models.Model):
    """
    Enregistre chaque transaction de paiement.
    Conçu pour supporter plusieurs providers (Stripe, FedaPay, CinetPay, etc.)
    """

    # ── STATUTS ────────────────────────────────────────────────────
    STATUTS = [
        ('en_attente', 'En attente'),
        ('reussi',     'Réussi'),
        ('echoue',     'Échoué'),
        ('rembourse',  'Remboursé'),
        ('annule',     'Annulé'),
    ]

    # ── PROVIDERS ──────────────────────────────────────────────────
    PROVIDERS = [
        ('sandbox',  'Sandbox (test)'),
        ('stripe',   'Stripe'),
        ('fedapay',  'FedaPay'),
        ('cinetpay', 'CinetPay'),
        ('mixx',     'Mixx by YAS'),
        ('paydunya', 'PayDunya'),
    ]

    # ── DEVISES ────────────────────────────────────────────────────
    DEVISES = [
        ('XOF', 'Franc CFA (XOF)'),
        ('EUR', 'Euro (EUR)'),
        ('USD', 'Dollar US (USD)'),
        ('GHS', 'Cedi ghaneen (GHS)'),
    ]

    # ── RELATIONS ──────────────────────────────────────────────────
    etudiant = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='paiements'
    )
    
    cours = models.ForeignKey(
        Cours,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paiements'
    )
    
    # ── MONTANT ────────────────────┬────────────────────────────────
    devise = models.CharField(
        max_length=3, choices=DEVISES, default='XOF',
        verbose_name='Devise'
    )
    montant_initial = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Montant initial'
    )
    montant_final = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Montant final (apres frais)'
    )
    frais_plateforme = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Frais plateforme'
    )
    
    # ── STATUT et PROVIDER ─────────────────────────────────────────
    statut = models.CharField(
        max_length=20,
        choices=STATUTS,
        default='en_attente',
        verbose_name='Statut'
    )
    
    provider = models.CharField(
        max_length=20,
        choices=PROVIDERS,
        default='sandbox',
        verbose_name='Provider de paiement'
    )

    # Identifiant unique du paiement chez le provider
    reference_provider = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='Reference provider'
    )

    # Reference interne Numeria
    reference_numeria = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Reference Numeria'
    )

    # ── METADONNEES ────────────────────────────────────────────────
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, null=True)
    
    # ── TRACE POUR SECURITE ────────────────────────────────────────
    ip_adresse = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    def __str__(self):
        cours_titre = self.cours.titre if self.cours else 'Frais candidature'
        return f"{self.reference_numeria} — {self.etudiant.username} — {cours_titre} — {self.statut}"

    def est_reussi(self):
        return self.statut == 'reussi'

    class Meta:
        verbose_name = 'Paiement'
        verbose_name_plural = 'Paiements'
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['etudiant', '-date_creation']),
            models.Index(fields=['statut']),
        ]


class RemboursementDemande(models.Model):
    """
    Demande de remboursement d'un etudiant.
    """

    STATUTS = [
        ('en_attente', 'En attente'),
        ('approuve',   'Approuve'),
        ('refuse',     'Refuse'),
        ('traite',     'Traite'),
    ]

    paiement = models.OneToOneField(
        Paiement,
        on_delete=models.CASCADE,
        related_name='remboursement'
    )
    raison = models.TextField(verbose_name='Raison du remboursement')
    statut = models.CharField(
        max_length=20,
        choices=STATUTS,
        default='en_attente'
    )
    date_demande = models.DateTimeField(auto_now_add=True)
    date_traitement = models.DateTimeField(null=True, blank=True)
    notes_admin = models.TextField(blank=True, default='')

    def __str__(self):
        return f"Remboursement {self.paiement.reference_numeria}"

    class Meta:
        verbose_name = "Demande de remboursement"
        verbose_name_plural = "Demandes de remboursement"
        ordering = ['-date_demande']
