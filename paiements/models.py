from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from cours.models import Cours


class Paiement(models.Model):
    """
    Enregistre chaque transaction de paiement.
    Conçu pour supporter plusieurs providers (Stripe, FedaPay, CinetPay, etc.)
    """

    # ── STATUTS ────────────────────────────────────────────────────
    STATUTS = [
        ('en_attente', 'En attente'),
        ('en_cours',   'En cours'),
        ('reussi',     'Réussi'),
        ('echoue',     'Échoué'),
        ('annule',     'Annulé'),
        ('rembourse',  'Remboursé'),
    ]

    # ── MÉTHODES DE PAIEMENT ────────────────────────────────────────
    METHOD_CHOICES = [
        ('mixx', 'Mixx by Yas (T-Money)'),
        ('moov', 'Moov Money (Flooz)'),
        ('card', 'Carte bancaire / VISA'),
    ]

    # ── PROVIDERS INTERNES ─────────────────────────────────────────
    PROVIDERS = [
        ('sandbox', 'Sandbox (test)'),
        ('paygate', 'PayGate Global'),
        ('stripe',  'Stripe'),
        ('mixx',    'Mixx by YAS'),
        ('moov',    'Moov Money'),
        ('fedapay', 'FedaPay'),
        ('cinetpay','CinetPay'),
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
    formation_inscription = models.ForeignKey(
        'formation.InscriptionFormation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paiements'
    )
    
    # ── MÉTHODE / PROVIDER ─────────────────────────────────────────
    method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
        blank=True,
        null=True,
        verbose_name='Méthode de paiement'
    )
    provider = models.CharField(
        max_length=20,
        choices=PROVIDERS,
        default='sandbox',
        verbose_name='Provider de paiement'
    )

    # ── DEVISE & RÉFÉRENCES ─────────────────────────────────────────
    devise = models.CharField(
        max_length=10,
        choices=DEVISES,
        default='XOF',
        verbose_name='Devise'
    )
    reference_numeria = models.CharField(
        max_length=200,
        unique=True,
        verbose_name='Référence Numeria'
    )
    external_id = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='ID externe'
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='Numéro de téléphone'
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Métadonnées'
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
    
    # ── STATUT ──────────────────────────────────────────────────────
    statut = models.CharField(
        max_length=20,
        choices=STATUTS,
        default='en_attente',
        verbose_name='Statut'
    )

    # Identifiant unique du paiement chez le provider
    reference_provider = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='Reference provider'
    )

    # ── METADONNEES ────────────────────────────────────────────────
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, null=True)
    
    # ── TRACE POUR SECURITE ────────────────────────────────────────
    ip_adresse = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    def __str__(self):
        if self.cours:
            item_titre = self.cours.titre
        elif self.formation_inscription:
            item_titre = f"{self.formation_inscription.session.formation.titre} — {self.formation_inscription.session.nom}"
        else:
            paiement_seance = None
            try:
                paiement_seance = self.paiement_seance
            except ObjectDoesNotExist:
                pass
            if paiement_seance:
                item_titre = f"Séance {paiement_seance.seance.titre}"
            else:
                item_titre = 'Paiement'
        return f"{self.reference} — {self.etudiant.username} — {item_titre} — {self.status}"

    @property
    def reference(self):
        return self.reference_numeria

    @property
    def currency(self):
        return self.devise

    @property
    def status(self):
        return self.statut

    @property
    def amount(self):
        return self.montant_final

    @property
    def user(self):
        return self.etudiant

    @property
    def course(self):
        return self.cours

    @property
    def montant(self):
        return self.montant_final

    @property
    def objet(self):
        if self.cours:
            return self.cours
        if self.formation_inscription:
            return self.formation_inscription
        try:
            return self.paiement_seance
        except ObjectDoesNotExist:
            return None

    @property
    def objet_type(self):
        if self.cours:
            return 'cours'
        if self.formation_inscription:
            return 'formation'
        try:
            if self.paiement_seance:
                return 'mentorat'
        except ObjectDoesNotExist:
            pass
        return None

    def est_reussi(self):
        return self.statut == 'reussi'

    class Meta:
        verbose_name = 'Paiement'
        verbose_name_plural = 'Paiements'
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['etudiant', '-date_creation']),
            models.Index(fields=['statut']),
            models.Index(fields=['provider']),
            models.Index(fields=['reference_provider']),
            models.Index(fields=['etudiant', 'statut', '-date_creation']),
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
