from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()


class Paiement(models.Model):
    """
    Paiements — rebuilt compatibility layer for Course/Formation purchases.

    IMPORTANT: per spec Step 18, the FK to Course must be named `cours`
    and reference 'cours.Course'.
    """

    STATUTS = [
        ('en_attente', 'En attente'),
        ('en_cours', 'En cours'),
        ('reussi', 'Réussi'),
        ('echoue', 'Échoué'),
        ('annule', 'Annulé'),
        ('rembourse', 'Remboursé'),
    ]

    METHOD_CHOICES = [
        ('mixx', 'Mixx by Yas (T-Money)'),
        ('moov', 'Moov Money (Flooz)'),
        ('card', 'Carte bancaire / VISA'),
    ]

    PROVIDERS = [
        ('sandbox', 'Sandbox (test)'),
        ('paygate', 'PayGate Global'),
        ('stripe', 'Stripe'),
        ('mixx', 'Mixx by YAS'),
        ('moov', 'Moov Money'),
        ('fedapay', 'FedaPay'),
        ('cinetpay', 'CinetPay'),
    ]

    DEVISES = [
        ('XOF', 'Franc CFA (XOF)'),
        ('EUR', 'Euro (EUR)'),
        ('USD', 'Dollar US (USD)'),
        ('GHS', 'Cedi ghaneen (GHS)'),
    ]

    etudiant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='paiements')

    cours = models.ForeignKey(
        'cours.Course',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paiements',
    )

    # Formation payment (simplified in rebuild): link directly to Formation.
    formation = models.ForeignKey(
        'formation.Formation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paiements',
    )

    method = models.CharField(max_length=20, choices=METHOD_CHOICES, blank=True, null=True)
    provider = models.CharField(max_length=20, choices=PROVIDERS, default='sandbox')
    devise = models.CharField(max_length=10, choices=DEVISES, default='XOF')

    reference_numeria = models.CharField(max_length=200, unique=True)
    external_id = models.CharField(max_length=200, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)

    montant_initial = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    montant_final = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    frais_plateforme = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    statut = models.CharField(max_length=20, choices=STATUTS, default='en_attente')
    reference_provider = models.CharField(max_length=200, blank=True, null=True)

    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, null=True)

    ip_adresse = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    def __str__(self):
        return f"{self.reference_numeria} — {self.etudiant_id} — {self.statut}"

    class Meta:
        verbose_name = 'Paiement'
        verbose_name_plural = 'Paiements'
        ordering = ['-date_creation']


class RemboursementDemande(models.Model):
    STATUTS = [
        ('en_attente', 'En attente'),
        ('approuve', 'Approuve'),
        ('refuse', 'Refuse'),
        ('traite', 'Traite'),
    ]

    paiement = models.OneToOneField(Paiement, on_delete=models.CASCADE, related_name='remboursement')
    raison = models.TextField(verbose_name='Raison du remboursement')
    statut = models.CharField(max_length=20, choices=STATUTS, default='en_attente')
    date_demande = models.DateTimeField(auto_now_add=True)
    date_traitement = models.DateTimeField(null=True, blank=True)
    notes_admin = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = "Demande de remboursement"
        verbose_name_plural = "Demandes de remboursement"
        ordering = ['-date_demande']

