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
        ('payدunya', 'PayDunya'),
    ]

    # ── DEVISES ────────────────────────────────────────────────────
    DEVISES = [
        ('XOF', 'Franc CFA (XOF)'),
        ('EUR', 'Euro (EUR)'),
        ('USD', 'Dollar US (USD)'),
        ('GHS', 'Cedi ghanéen (GHS)'),
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

    # ── INFORMATIONS DU PAIEMENT ───────────────────────────────────
    montant = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Montant'
    )
    devise = models.CharField(
        max_length=3,
        choices=DEVISES,
        default='XOF',
        verbose_name='Devise'
    )
    statut = models.CharField(
        max_length=20,
        choices=STATUTS,
        default='en_attente',
        verbose_name='Statut'
    )

    # ── PROVIDER ───────────────────────────────────────────────────
    provider = models.CharField(
        max_length=20,
        choices=PROVIDERS,
        default='sandbox',
        verbose_name='Provider de paiement'
    )

    # Identifiant unique du paiement chez le provider
    # Ex: ch_3OxK2L2eZvKYlo2C pour Stripe
    reference_provider = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='Référence provider'
    )

    # Référence interne Numeria
    reference_numeria = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Référence Numeria'
    )

    # ── MÉTADONNÉES ────────────────────────────────────────────────
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    # Notes internes (pour le support)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        cours_titre = self.cours.titre if self.cours else 'Frais candidature'
        return f"{self.reference_numeria} — {self.etudiant.username} — {cours_titre} — {self.statut}"

    def est_reussi(self):
        return self.statut == 'reussi'

    class Meta:
        verbose_name = 'Paiement'
        verbose_name_plural = 'Paiements'
        ordering = ['-date_creation']


class RemboursementDemande(models.Model):
    """
    Demande de remboursement d'un étudiant.
    """

    STATUTS = [
        ('en_attente', 'En attente'),
        ('approuve',   'Approuvé'),
        ('refuse',     'Refusé'),
        ('traite',     'Traité'),
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
    notes_admin = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Remboursement — {self.paiement.reference_numeria}"

    class Meta:
        verbose_name = 'Demande de remboursement'
        verbose_name_plural = 'Demandes de remboursement'
        ordering = ['-date_demande']