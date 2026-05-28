from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
from comptes.models import Profil


class Mentor(models.Model):
    """
    Modèle représentant un mentor dans le système de mentorat.
    """
    profil = models.OneToOneField(
        Profil,
        on_delete=models.CASCADE,
        related_name='mentorat_mentor'
    )

    # Domaines d'expertise
    DOMAINES = [
        ('informatique', 'Informatique'),
        ('mathematiques', 'Mathématiques'),
        ('physique', 'Physique'),
        ('chimie', 'Chimie'),
        ('biologie', 'Biologie'),
        ('ingenierie', 'Ingénierie'),
        ('data_science', 'Data Science'),
        ('intelligence_artificielle', 'Intelligence Artificielle'),
        ('entrepreneuriat', 'Entrepreneuriat'),
        ('autre', 'Autre'),
    ]
    domaines_expertise = models.CharField(
        max_length=50,
        choices=DOMAINES,
        verbose_name='Domaine d\'expertise'
    )

    # Niveau d'expérience
    NIVEAUX_EXPERIENCE = [
        ('debutant', 'Débutant (1-2 ans)'),
        ('intermediaire', 'Intermédiaire (3-5 ans)'),
        ('avance', 'Avancé (6-10 ans)'),
        ('expert', 'Expert (+10 ans)'),
    ]
    niveau_experience = models.CharField(
        max_length=20,
        choices=NIVEAUX_EXPERIENCE,
        verbose_name='Niveau d\'expérience'
    )

    # Disponibilité
    DISPONIBILITES = [
        ('hebdomadaire', '1-2 heures par semaine'),
        ('bimensuel', '3-4 heures par semaine'),
        ('quotidien', 'Plus de 5 heures par semaine'),
    ]
    disponibilite = models.CharField(
        max_length=20,
        choices=DISPONIBILITES,
        verbose_name='Disponibilité'
    )

    # Description et motivations
    bio_mentorat = models.TextField(
        max_length=1000,
        verbose_name='Biographie de mentor',
        help_text='Décrivez votre parcours, vos motivations à devenir mentor...'
    )

    titre_professionnel = models.CharField(
        max_length=120,
        blank=True,
        verbose_name='Titre professionnel',
        help_text='Ex: Coach en Data Science, Ingénieur logiciel senior...'
    )
    categories = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Catégories de mentorat',
        help_text='Liste courte des sujets séparés par des virgules.'
    )
    langues = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Langues parlées',
        help_text='Ex: Français, Anglais.'
    )

    # Tarification
    TAUX_COMMISSION = 20  # Numeria prélève 20% sur chaque séance payante
    tarif_par_seance = models.PositiveIntegerField(
        default=0,
        verbose_name='Tarif par séance (FCFA)',
        help_text='0 = mentorat gratuit. Numeria prélevé 20% de commission.'
    )

    # Statut
    est_actif = models.BooleanField(default=True, verbose_name='Actif comme mentor')
    date_inscription = models.DateTimeField(auto_now_add=True)

    # Statistiques
    nombre_mentees_actuels = models.PositiveIntegerField(default=0)
    nombre_mentees_total = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Mentor'
        verbose_name_plural = 'Mentors'
        ordering = ['-date_inscription']

    def __str__(self):
        return f"Mentor: {self.profil.utilisateur.get_full_name() or self.profil.utilisateur.username}"

    def get_absolute_url(self):
        return reverse('mentorat:mentor_detail', kwargs={'pk': self.pk})


class MentorApplication(models.Model):
    """
    Application d'un utilisateur pour devenir mentor.
    """
    STATUTS = [
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('rejected', 'Rejeté'),
    ]

    profil = models.OneToOneField(
        Profil,
        on_delete=models.CASCADE,
        related_name='application_mentor'
    )
    full_name = models.CharField(max_length=150, verbose_name='Nom complet')
    professional_title = models.CharField(
        max_length=120,
        verbose_name='Titre professionnel'
    )
    bio = models.TextField(
        max_length=1200,
        verbose_name='Biographie professionnelle'
    )
    expertise_categories = models.TextField(
        verbose_name='Expertise / catégories',
        help_text='Séparez les thèmes par des virgules.'
    )
    cv = models.FileField(
        upload_to='mentor_applications/cvs/',
        verbose_name='CV',
        help_text='PDF, JPG, PNG, DOCX. Taille max 5MB.'
    )
    certificate = models.FileField(
        upload_to='mentor_applications/certificats/',
        verbose_name='Certificat',
        help_text='Un document de certification est requis.',
    )
    linkedin = models.URLField(blank=True, null=True, verbose_name='Profil LinkedIn')
    portfolio = models.URLField(blank=True, null=True, verbose_name='Site portfolio')
    github = models.URLField(blank=True, null=True, verbose_name='Profil GitHub')
    recommendation_letter = models.FileField(
        upload_to='mentor_applications/recommendations/',
        blank=True,
        null=True,
        verbose_name='Lettre de recommandation',
        help_text='Optionnel',
    )
    additional_documents = models.FileField(
        upload_to='mentor_applications/documents/',
        blank=True,
        null=True,
        verbose_name='Documents supplémentaires',
        help_text='Optionnel',
    )
    social_profiles = models.TextField(
        blank=True,
        verbose_name='Réseaux sociaux',
        help_text='Liens vers d’autres profils sociaux, séparés par des virgules.',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUTS,
        default='pending',
        verbose_name='Statut de la candidature'
    )
    rejection_notes = models.TextField(blank=True, verbose_name='Notes de rejet')
    approved_at = models.DateTimeField(blank=True, null=True)
    rejected_at = models.DateTimeField(blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Candidature Mentor'
        verbose_name_plural = 'Candidatures Mentors'
        ordering = ['-date_created']

    def __str__(self):
        return f"Candidature Mentor: {self.full_name} ({self.get_status_display()})"

    def approve(self):
        """Approuve la candidature et active l'accès mentor."""
        if self.status != 'pending':
            return
        mentor, created = Mentor.objects.get_or_create(
            profil=self.profil,
            defaults={
                'titre_professionnel': self.professional_title,
                'bio_mentorat': self.bio,
                'domaines_expertise': self._best_matching_expertise(),
                'categories': self.expertise_categories,
                'niveau_experience': 'intermediaire',
                'disponibilite': 'hebdomadaire',
                'tarif_par_seance': 0,
            }
        )
        if not created:
            mentor.titre_professionnel = self.professional_title
            mentor.bio_mentorat = self.bio
            mentor.categories = self.expertise_categories
            mentor.save()

        self.profil.est_menteur = True
        self.profil.role = 'mentor'
        self.profil.save()

        self.status = 'approved'
        self.approved_at = timezone.now()
        self.rejection_notes = ''
        self.save()

    def reject(self, notes=''):  # pragma: no cover
        self.status = 'rejected'
        self.rejection_notes = notes
        self.rejected_at = timezone.now()
        self.save()

    def _best_matching_expertise(self):
        """Retourne une valeur de domaines_expertise si possible."""
        lower = self.expertise_categories.lower()
        for key, label in Mentor.DOMAINES:
            if key in lower or label.lower() in lower:
                return key
        return 'autre'


class Mentee(models.Model):
    """
    Modèle représentant un mentoré dans le système de mentorat.
    """
    profil = models.OneToOneField(
        Profil,
        on_delete=models.CASCADE,
        related_name='mentorat_mentee'
    )

    # Objectifs
    OBJECTIFS = [
        ('orientation', 'Orientation professionnelle'),
        ('competences', 'Développement de compétences'),
        ('carriere', 'Conseils carrière'),
        ('projet', 'Accompagnement projet'),
        ('autre', 'Autre'),
    ]
    objectifs = models.CharField(
        max_length=50,
        choices=OBJECTIFS,
        verbose_name='Objectifs principaux'
    )

    # Niveau actuel
    NIVEAUX_ETUDES = [
        ('lycee', 'Lycée'),
        ('licence', 'Licence/Bachelor'),
        ('master', 'Master'),
        ('doctorat', 'Doctorat'),
        ('professionnel', 'Professionnel'),
    ]
    niveau_etudes = models.CharField(
        max_length=20,
        choices=NIVEAUX_ETUDES,
        verbose_name='Niveau d\'études'
    )

    # Description des besoins
    besoins = models.TextField(
        max_length=1000,
        verbose_name='Besoins spécifiques',
        help_text='Décrivez ce que vous attendez de votre mentor...'
    )

    # Statut
    est_actif = models.BooleanField(default=True, verbose_name='Recherche un mentor')
    date_inscription = models.DateTimeField(auto_now_add=True)

    # Statistiques
    a_mentor_actuel = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Mentoré'
        verbose_name_plural = 'Mentorés'
        ordering = ['-date_inscription']

    def __str__(self):
        return f"Mentoré: {self.profil.utilisateur.get_full_name() or self.profil.utilisateur.username}"


class DemandeMentorat(models.Model):
    """
    Modèle représentant une demande de mentorat.
    """
    mentee = models.ForeignKey(
        Mentee,
        on_delete=models.CASCADE,
        related_name='demandes'
    )
    mentor = models.ForeignKey(
        Mentor,
        on_delete=models.CASCADE,
        related_name='demandes_recues'
    )

    # Statut de la demande
    STATUTS = [
        ('en_attente', 'En attente'),
        ('acceptee', 'Acceptée'),
        ('refusee', 'Refusée'),
        ('terminee', 'Terminée'),
    ]
    statut = models.CharField(
        max_length=20,
        choices=STATUTS,
        default='en_attente',
        verbose_name='Statut'
    )

    # Message d'accompagnement
    message = models.TextField(
        max_length=500,
        verbose_name='Message au mentor',
        help_text='Présentez-vous et expliquez pourquoi vous souhaitez ce mentor...'
    )

    # Dates
    date_creation = models.DateTimeField(auto_now_add=True)
    date_reponse = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = 'Demande de mentorat'
        verbose_name_plural = 'Demandes de mentorat'
        ordering = ['-date_creation']
        unique_together = ['mentee', 'mentor']  # Une demande par paire mentee-mentor

    def __str__(self):
        return f"Demande de {self.mentee} à {self.mentor}"

    def accepter(self):
        """Accepte la demande et crée une relation de mentorat."""
        self.statut = 'acceptee'
        self.date_reponse = timezone.now()
        self.save()

        # Créer la relation de mentorat
        RelationMentorat.objects.create(
            mentor=self.mentor,
            mentee=self.mentee
        )

        # Mettre à jour les statistiques
        self.mentor.nombre_mentees_actuels += 1
        self.mentor.nombre_mentees_total += 1
        self.mentor.save()

        self.mentee.a_mentor_actuel = True
        self.mentee.save()

    def refuser(self):
        """Refuse la demande."""
        self.statut = 'refusee'
        self.date_reponse = timezone.now()
        self.save()


class RelationMentorat(models.Model):
    """
    Modèle représentant une relation active de mentorat.
    """
    mentor = models.ForeignKey(
        Mentor,
        on_delete=models.CASCADE,
        related_name='relations_actives'
    )
    mentee = models.ForeignKey(
        Mentee,
        on_delete=models.CASCADE,
        related_name='relations_actives'
    )

    # Dates
    date_debut = models.DateTimeField(auto_now_add=True)
    date_fin = models.DateTimeField(blank=True, null=True)

    # Statut
    est_active = models.BooleanField(default=True)

    # Objectifs de la relation
    objectifs = models.TextField(
        max_length=1000,
        blank=True,
        verbose_name='Objectifs de la relation'
    )

    class Meta:
        verbose_name = 'Relation de mentorat'
        verbose_name_plural = 'Relations de mentorat'
        ordering = ['-date_debut']
        unique_together = ['mentor', 'mentee']  # Une relation active par paire

    def __str__(self):
        return f"Relation: {self.mentor} ↔ {self.mentee}"

    def terminer(self):
        """Termine la relation de mentorat."""
        self.est_active = False
        self.date_fin = timezone.now()
        self.save()

        # Mettre à jour les statistiques
        self.mentor.nombre_mentees_actuels -= 1
        self.mentor.save()

        self.mentee.a_mentor_actuel = False
        self.mentee.save()


class SeanceMentorat(models.Model):
    """
    Modèle représentant une séance de mentorat.
    """
    relation = models.ForeignKey(
        RelationMentorat,
        on_delete=models.CASCADE,
        related_name='seances'
    )

    # Informations de la séance
    titre = models.CharField(max_length=200, verbose_name='Titre de la séance')
    description = models.TextField(
        max_length=500,
        blank=True,
        verbose_name='Description'
    )

    # Date et heure
    date_heure = models.DateTimeField(verbose_name='Date et heure')
    duree_minutes = models.PositiveIntegerField(
        default=60,
        verbose_name='Durée (minutes)'
    )

    # Statut
    STATUTS = [
        ('planifiee', 'Planifiée'),
        ('en_cours', 'En cours'),
        ('terminee', 'Terminée'),
        ('annulee', 'Annulée'),
    ]
    statut = models.CharField(
        max_length=20,
        choices=STATUTS,
        default='planifiee',
        verbose_name='Statut'
    )

    # Lieu/modalité
    MODALITES = [
        ('presentiel', 'Présentiel'),
        ('visio', 'Visioconférence'),
        ('telephone', 'Téléphone'),
        ('email', 'Email'),
    ]
    modalite = models.CharField(
        max_length=20,
        choices=MODALITES,
        default='visio',
        verbose_name='Modalité'
    )

    # Notes et compte-rendu
    notes_mentor = models.TextField(
        blank=True,
        verbose_name='Notes du mentor'
    )
    notes_mentee = models.TextField(
        blank=True,
        verbose_name='Notes du mentoré'
    )

    # Dates
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Séance de mentorat'
        verbose_name_plural = 'Séances de mentorat'
        ordering = ['-date_heure']

    def __str__(self):
        return f"Séance: {self.titre} ({self.date_heure.strftime('%d/%m/%Y %H:%M')})"

    def tarif(self):
        """Retourne le tarif de la séance (selon le mentor)."""
        return self.relation.mentor.tarif_par_seance

    def est_payante(self):
        return self.tarif() > 0

    def terminer_seance(self, notes_mentor='', notes_mentee=''):
        """Termine la séance avec des notes."""
        self.statut = 'terminee'
        self.notes_mentor = notes_mentor
        self.notes_mentee = notes_mentee
        self.save()


class PaiementSeance(models.Model):
    """
    Paiement d'une séance de mentorat.
    Numeria prélève TAUX_COMMISSION% du montant comme commission de mise en relation.
    """
    TAUX_COMMISSION = 20  # %

    seance = models.OneToOneField(
        SeanceMentorat,
        on_delete=models.CASCADE,
        related_name='paiement'
    )
    paiement = models.OneToOneField(
        'paiements.Paiement',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paiement_seance'
    )

    # Montants
    montant_total = models.PositiveIntegerField(verbose_name='Montant total (FCFA)')
    commission_numeria = models.PositiveIntegerField(verbose_name='Commission Numeria (FCFA)')
    montant_mentor = models.PositiveIntegerField(verbose_name='Part mentor (FCFA)')

    # Statut
    STATUTS = [
        ('en_attente', 'En attente de paiement'),
        ('preuve_soumise', 'Preuve soumise'),
        ('confirme', 'Confirmé'),
        ('echec', 'Échec / Annulé'),
    ]
    statut = models.CharField(max_length=20, choices=STATUTS, default='en_attente')

    # Preuve de paiement (capture mobile money)
    reference_mobile_money = models.CharField(
        max_length=100, blank=True,
        verbose_name='Référence mobile money',
        help_text='Numéro de transaction TMoney / Flooz / autre'
    )
    preuve_paiement = models.ImageField(
        upload_to='paiements_mentorat/',
        blank=True, null=True,
        verbose_name='Capture d\'écran du paiement'
    )

    # ── ESCROW ET SÉCURITÉ ────────────────────────────────────────
    est_suspect = models.BooleanField(
        default=False,
        verbose_name='Paiement flaggé comme suspect',
        help_text='En escrow pour vérification admin'
    )
    raisons_suspect = models.TextField(
        blank=True,
        verbose_name='Raisons du flagging',
        help_text='Séparées par |'
    )
    date_deblocage = models.DateTimeField(
        blank=True, null=True,
        verbose_name='Date de déblocage (escrow)',
        help_text='Après cette date, si pas de contestation, débloquer'
    )
    date_submission = models.DateTimeField(
        blank=True, null=True,
        verbose_name='Date de soumission de preuve'
    )
    raison_echec = models.TextField(
        blank=True,
        verbose_name='Raison de l\'échec/contestation'
    )
    signature_mentoré = models.CharField(
        max_length=64, blank=True,
        verbose_name='Signature HMAC du mentoré',
        help_text='Empêche modification du montant'
    )

    # ── AUDIT ──────────────────────────────────────────────────────
    adresse_ip_mentoré = models.GenericIPAddressField(
        blank=True, null=True,
        verbose_name='IP du mentoré (audit)'
    )
    user_agent = models.CharField(
        max_length=255, blank=True,
        verbose_name='User-Agent (audit)'
    )

    # Dates
    date_creation = models.DateTimeField(auto_now_add=True)
    date_confirmation = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = 'Paiement de séance'
        verbose_name_plural = 'Paiements de séances'
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['statut', 'date_creation']),
            models.Index(fields=['est_suspect']),
            models.Index(fields=['reference_mobile_money']),
        ]

    def __str__(self):
        return f"Paiement {self.montant_total} FCFA — {self.seance}"

    @classmethod
    def creer_pour_seance(cls, seance, ip_mentoré=None, user_agent=None):
        """Crée automatiquement un paiement pour une séance payante."""
        tarif = seance.relation.mentor.tarif_par_seance
        commission = round(tarif * cls.TAUX_COMMISSION / 100)
        return cls.objects.create(
            seance=seance,
            montant_total=tarif,
            commission_numeria=commission,
            montant_mentor=tarif - commission,
            adresse_ip_mentoré=ip_mentoré,
            user_agent=user_agent or '',
        )

    def lier_paiement(self, paiement):
        """Lie un paiement provider à cette séance."""
        self.paiement = paiement
        self.save()

    def confirmer(self):
        """Admin confirme le paiement."""
        self.statut = 'confirme'
        self.date_confirmation = timezone.now()
        self.save()
    
    def est_pas_encore_débloqué(self):
        """Retourne True si toujours en escrow."""
        if not self.date_deblocage:
            return False
        return timezone.now() < self.date_deblocage
