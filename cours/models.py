from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
import uuid

# =============================================================================
# FONCTIONS UTILITAIRES VIDÉO
# Importées par templatetags/video_tags.py
# RÈGLE : On stocke TOUJOURS l'URL originale en base de données.
#         La conversion en embed se fait uniquement à l'affichage.
# =============================================================================

def extraire_id_youtube(url):
    """
    Extrait l'ID YouTube (11 caractères) depuis n'importe quel format d'URL.

    Formats supportés :
      - https://www.youtube.com/watch?v=ABC123xyz12
      - https://youtu.be/ABC123xyz12
      - https://youtube.com/shorts/ABC123xyz12
      - https://www.youtube.com/embed/ABC123xyz12
      - https://www.youtube-nocookie.com/embed/ABC123xyz12   ← CORRIGÉ
      - https://m.youtube.com/watch?v=ABC123xyz12

    Retourne l'ID (str) ou None si ce n'est pas une URL YouTube.
    """
    if not url or 'vimeo' in url:
        return None

    url = url.strip()

    # Format court : youtu.be/ID
    if 'youtu.be/' in url:
        return url.split('youtu.be/')[-1].split('?')[0].strip('/')

    # Format Shorts : /shorts/ID
    if '/shorts/' in url:
        return url.split('/shorts/')[-1].split('?')[0].strip('/')

    # Format embed : /embed/ID  (youtube.com ET youtube-nocookie.com)
    if '/embed/' in url:
        return url.split('/embed/')[-1].split('?')[0].strip('/')

    # Format normal : ?v=ID ou &v=ID
    if 'v=' in url:
        return url.split('v=')[-1].split('&')[0].strip()

    return None


def convertir_url_youtube(url):
    """
    Convertit une URL YouTube ou Vimeo en URL embed optimisée.
    Utilise youtube-nocookie.com pour éviter les blocages de confidentialité.

    Formats YouTube supportés :
      - https://www.youtube.com/watch?v=ABC123
      - https://youtu.be/ABC123
      - https://youtube.com/shorts/ABC123
      - https://www.youtube.com/embed/ABC123   (déjà embed, on normalise)
      - https://www.youtube-nocookie.com/embed/ABC123  (déjà bon, on laisse)

    Format Vimeo supporté :
      - https://vimeo.com/123456789
      - https://player.vimeo.com/video/123456789

    Retourne l'URL embed (str) ou l'URL originale si format inconnu.
    """
    if not url:
        return url

    url = url.strip()

    # ── VIMEO ──────────────────────────────────────────────────────────────
    if 'vimeo.com' in url:
        if '/video/' in url:
            video_id = url.split('/video/')[-1].split('?')[0].split('/')[0]
        else:
            video_id = url.split('vimeo.com/')[-1].split('?')[0].split('/')[0]
        if video_id.isdigit():
            return f'https://player.vimeo.com/video/{video_id}?color=E8A020&title=0&byline=0'
        return url

    # ── YOUTUBE ────────────────────────────────────────────────────────────

    # Déjà au format nocookie — on ne retouche pas
    if 'youtube-nocookie.com/embed/' in url:
        return url

    # Déjà au format embed normal — on bascule vers nocookie
    if 'youtube.com/embed/' in url:
        video_id = url.split('/embed/')[-1].split('?')[0].strip('/')
        return f'https://www.youtube-nocookie.com/embed/{video_id}?rel=0&modestbranding=1'

    # Format court : youtu.be/ID
    if 'youtu.be/' in url:
        video_id = url.split('youtu.be/')[-1].split('?')[0].strip('/')
        return f'https://www.youtube-nocookie.com/embed/{video_id}?rel=0&modestbranding=1'

    # Format Shorts : /shorts/ID
    if '/shorts/' in url:
        video_id = url.split('/shorts/')[-1].split('?')[0].strip('/')
        return f'https://www.youtube-nocookie.com/embed/{video_id}?rel=0&modestbranding=1'

    # Format normal : watch?v=ID
    if 'youtube.com' in url and 'v=' in url:
        video_id = url.split('v=')[-1].split('&')[0].strip()
        return f'https://www.youtube-nocookie.com/embed/{video_id}?rel=0&modestbranding=1'

    # Format inconnu — on retourne tel quel
    return url


# =============================================================================
# MODÈLES
# =============================================================================

class Tag(models.Model):
    """Tags pour catégoriser les cours."""
    nom = models.CharField(max_length=50, unique=True, verbose_name='Nom du tag')
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    couleur = models.CharField(max_length=7, default='#2DD4BF', verbose_name='Couleur (hex)')
    
    def __str__(self):
        return self.nom
    
    class Meta:
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'
        ordering = ['nom']


class Course(models.Model):
    """
    Représente un cours sur Numeria Institute.
    Peut être un cours général (adultes/étudiants) ou scolaire (élèves).
    """

    # ── TYPE DE COURS ──────────────────────────────────────────────────────
    TYPE_COURS = [
        ('general', 'Cours général'),
        ('scolaire', 'Cours scolaire'),
    ]
    type_cours = models.CharField(
        max_length=20, choices=TYPE_COURS, default='general',
        verbose_name='Type de cours'
    )

    # ── CYCLE SCOLAIRE ─────────────────────────────────────────────────────
    CYCLES = [
        ('primaire', 'Primaire'),
        ('college', 'Collège'),
        ('lycee', 'Lycée'),
    ]
    cycle = models.CharField(
        max_length=20, choices=CYCLES, blank=True, null=True,
        verbose_name='Cycle scolaire'
    )

    # ── CLASSES TOGOLAISES ────────────────────────────────────────────────
    CLASSES = [
        # Primaire
        ('CP',     'CP  Cours Préparatoire'),
        ('CE1',    'CE1  Cours Élémentaire 1'),
        ('CE2',    'CE2  Cours Élémentaire 2'),
        ('CM1',    'CM1  Cours Moyen 1'),
        ('CM2',    'CM2  Cours Moyen 2'),
        # Collège
        ('6eme',   '6ème'),
        ('5eme',   '5ème'),
        ('4eme',   '4ème'),
        ('3eme',   '3ème'),
        # Lycée
        ('2nde',   'Seconde'),
        ('1ere_A', 'Première A'),
        ('1ere_C', 'Première C'),
        ('1ere_D', 'Première D'),
        ('1ere_E', 'Première E'),
        ('1ere_F', 'Première F'),
        ('1ere_G', 'Première G'),
        ('Tle_A',  'Terminale A'),
        ('Tle_C',  'Terminale C'),
        ('Tle_D',  'Terminale D'),
        ('Tle_E',  'Terminale E'),
        ('Tle_F',  'Terminale F'),
        ('Tle_G',  'Terminale G'),
    ]
    classe = models.CharField(
        max_length=20, choices=CLASSES, blank=True, null=True,
        verbose_name='Classe'
    )

    # ── MATIÈRES ──────────────────────────────────────────────────────────
    MATIERES = [
        # Cours généraux
        ('python_scientifique',  'Python Scientifique'),
        ('fortran',              'Fortran & Calcul Haute Performance'),
        ('mathematica',          'Calcul Formel & Mathematica'),
        ('methodes_numeriques',  'Méthodes Numériques'),
        ('data_science',         'Data Science'),
        ('machine_learning',     'Machine Learning'),
        ('deep_learning',        'Deep Learning'),
        ('nlp',                  'NLP & IA pour Langues Africaines'),
        ('ia_deploiement',       'IA Appliquée & Déploiement'),
        # Cours scolaires
        ('maths',                'Mathématiques'),
        ('physique_chimie',      'Physique-Chimie'),
        ('svt',                  'SVT — Sciences de la Vie et de la Terre'),
        ('francais',             'Français'),
        ('anglais',              'Anglais'),
        ('histoire_geo',         'Histoire-Géographie'),
        ('philosophie',          'Philosophie'),
        ('informatique',         'Informatique'),
        ('economie',             'Économie'),
        ('autre',                'Autre'),
    ]
    matiere = models.CharField(
        max_length=30, choices=MATIERES,
        verbose_name='Matière'
    )

    # ── NIVEAUX ───────────────────────────────────────────────────────────
    NIVEAUX = [
        ('debutant',      'Débutant'),
        ('intermediaire', 'Intermédiaire'),
        ('avance',        'Avancé'),
        ('expert',        'Expert'),
    ]
    niveau = models.CharField(
        max_length=20, choices=NIVEAUX,
        verbose_name='Niveau'
    )

    # ── INFORMATIONS PRINCIPALES ──────────────────────────────────────────
    titre       = models.CharField(max_length=200, verbose_name='Titre')
    resume      = models.CharField(max_length=300, verbose_name='Résumé court')
    description = models.TextField(verbose_name='Description complète')

    # ── CONTENU ───────────────────────────────────────────────────────────
    nombre_lecons = models.IntegerField(default=0, verbose_name='Nombre de leçons')

    # URL originale (YouTube ou Vimeo) — jamais convertie en base
    video_youtube = models.URLField(
        blank=True, null=True,
        verbose_name='Vidéo YouTube / Vimeo principale',
        help_text='Collez l\'URL YouTube ou Vimeo normale. Ex : https://youtu.be/ABC123'
    )

    # ── PRIX ──────────────────────────────────────────────────────────────
    est_gratuit = models.BooleanField(default=True, verbose_name='Gratuit')
    prix = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Prix (FCFA)'
    )

    # ── STATUT ────────────────────────────────────────────────────────────
    est_publie        = models.BooleanField(default=False, verbose_name='Publié')
    date_creation     = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    # SUPPRIMÉ : le save() ne convertit plus l'URL automatiquement.
    # La conversion se fait à l'affichage dans video_tags.py.
    # Cela évite le double-encodage et le bug d'extraire_id_youtube.

    # ── PRÉALABLES ET PROGRESSION ──────────────────────────────────────
    cours_prerequises = models.ManyToManyField(
        'self', blank=True, symmetrical=False,
        related_name='cours_suivants',
        verbose_name='Cours préalables'
    )
    
    # ── TAGS ET MÉTADONNÉES AVANCÉES ──────────────────────────────────────
    tags = models.ManyToManyField(
        Tag, blank=True,
        related_name='cours',
        verbose_name='Tags'
    )
    
    duree_estimee_heures = models.IntegerField(
        default=10, verbose_name='Durée estimée (heures)'
    )
    
    competences_visees = models.TextField(
        blank=True, verbose_name='Compétences visées',
        help_text='Listez les compétences que les étudiants acquerront (séparées par des virgules)'
    )
    
    ressources_externes = models.TextField(
        blank=True, verbose_name='Ressources externes',
        help_text='Liens vers des ressources complémentaires (un par ligne)'
    )
    
    langue = models.CharField(
        max_length=10, default='fr',
        choices=[('fr', 'Français'), ('en', 'English'), ('other', 'Autre')],
        verbose_name='Langue'
    )
    
    # ── STATISTIQUES ───────────────────────────────────────────────────────
    nombre_etudiants_inscrits = models.IntegerField(default=0, editable=False)
    note_moyenne = models.DecimalField(
        max_digits=3, decimal_places=2, default=0, editable=False,
        verbose_name='Note moyenne'
    )
    taux_completion = models.IntegerField(
        default=0, editable=False,
        verbose_name='Taux de complétion (%)'
    )
    
    # ── INFORMATIONS SEO ───────────────────────────────────────────────────
    slug = models.SlugField(
        unique=True, blank=True,
        verbose_name='URL slug'
    )
    meta_keywords = models.CharField(
        max_length=200, blank=True,
        verbose_name='Mots-clés SEO'
    )

    # ── CHAMPS CMS (ajoutés pour le panneau admin custom) ──────────────────
    STATUS_COURS = [
        ('brouillon', 'Brouillon'),
        ('revision',  'En révision'),
        ('publie',    'Publié'),
        ('archive',   'Archivé'),
    ]
    status = models.CharField(
        max_length=20, choices=STATUS_COURS, default='brouillon',
        verbose_name='Statut CMS',
    )
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_courses', verbose_name='Créé par',
    )
    published_at = models.DateTimeField(
        null=True, blank=True, verbose_name='Publié le',
    )
    meta_description = models.CharField(
        max_length=160, blank=True, verbose_name='Meta description SEO',
        help_text='160 caractères max',
    )
    prerequisites = models.TextField(
        blank=True, verbose_name='Prérequis',
        help_text='Un prérequis par ligne',
    )
    thumbnail = models.ImageField(
        upload_to='courses/thumbnails/', blank=True, null=True,
        verbose_name='Miniature',
    )

    def get_video_embed_url(self):
        """Retourne l'URL embed prête pour l'<iframe>."""
        return convertir_url_youtube(self.video_youtube)
    
    def get_note_moyenne(self):
        """Calcule la note moyenne du cours."""
        evals = self.evaluations.all()
        if evals.exists():
            return sum(e.note for e in evals) / evals.count()
        return 0
    
    def get_taux_completion(self):
        """Calcule le taux de complétion moyen."""
        inscriptions = self.inscriptions.all()
        if inscriptions.exists():
            termines = inscriptions.filter(est_termine=True).count()
            return (termines / inscriptions.count()) * 100
        return 0
    
    def save(self, *args, **kwargs):
        """Génère automatiquement le slug et met à jour les stats."""
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.titre)

        # Synchronise est_publie avec status pour la compatibilité
        self.est_publie = (self.status == 'publie')

        # These queries require a primary key — skip on initial create()
        if self.pk:
            self.nombre_etudiants_inscrits = self.inscriptions.count()
            self.note_moyenne = self.get_note_moyenne()
            self.taux_completion = int(self.get_taux_completion())

        super().save(*args, **kwargs)

    def __str__(self):
        if self.type_cours == 'scolaire' and self.classe:
            return f'[{self.get_classe_display()}] {self.titre}'
        return self.titre

    class Meta:
        verbose_name = 'Cours'
        verbose_name_plural = 'Cours'
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['est_publie', '-date_creation']),
        ]


# Simple Python alias — NOT a proxy model (avoids proxy registration issues).
# Allows legacy imports like `from cours.models import Cours` to still work.
Cours = Course


class CourseModule(models.Model):
    """Regroupe des leçons dans un cours — couche facultative."""
    course      = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    titre       = models.CharField(max_length=300, verbose_name='Titre')
    description = models.TextField(blank=True, verbose_name='Description')
    ordre       = models.IntegerField(default=0, verbose_name='Ordre')
    est_actif   = models.BooleanField(default=True, verbose_name='Actif')

    class Meta:
        ordering = ['ordre']
        verbose_name = 'Module'
        verbose_name_plural = 'Modules'

    def __str__(self):
        return f'[{self.course.titre}] {self.titre}'


class CourseLesson(models.Model):
    """Une leçon dans un cours."""

    CONTENT_TYPE_CHOICES = [
        ('text',     'Texte / Article'),
        ('video',    'Vidéo'),
        ('mixed',    'Mixte (Texte + Vidéo)'),
        ('exercise', 'Exercice pratique'),
    ]

    course  = models.ForeignKey(Course,  on_delete=models.CASCADE, related_name='lessons')
    module = models.ForeignKey(
        'CourseModule', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='lessons', verbose_name='Module',
    )
    titre   = models.CharField(max_length=200, verbose_name='Titre')
    slug    = models.SlugField(blank=True, max_length=300, verbose_name='Slug')
    contenu = models.TextField(
        blank=True, verbose_name='Contenu',
        help_text='Supporte le LaTeX ($...$) et le code (<pre><code>...)'
    )
    content_type = models.CharField(
        max_length=20, choices=CONTENT_TYPE_CHOICES, default='text',
        verbose_name='Type de contenu',
    )
    ordre         = models.IntegerField(default=1, verbose_name='Ordre')
    duree_minutes = models.IntegerField(default=10, verbose_name='Durée (minutes)')
    is_free_preview = models.BooleanField(
        default=False, verbose_name='Aperçu gratuit',
        help_text='Accessible sans inscription ni paiement',
    )

    # URL originale de la leçon — jamais convertie en base
    video_youtube = models.URLField(
        blank=True, null=True,
        verbose_name='Vidéo YouTube / Vimeo',
        help_text='URL YouTube ou Vimeo normale. Ex : https://youtu.be/ABC123'
    )
    est_publiee = models.BooleanField(default=True, verbose_name='Publiée')

    def get_video_embed_url(self):
        return convertir_url_youtube(self.video_youtube)

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.titre)[:300]
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.course.titre} — Leçon {self.ordre} : {self.titre}'

    class Meta:
        verbose_name = 'Leçon'
        verbose_name_plural = 'Leçons'
        ordering = ['course', 'ordre']


class ProgressionLecon(models.Model):
    """Suit la progression d'un étudiant sur une leçon."""

    etudiant = models.ForeignKey(
        'auth.User', on_delete=models.CASCADE,
        related_name='progressions_lecons'
    )
    course_lesson = models.ForeignKey(
        'CourseLesson', on_delete=models.CASCADE, related_name='progressions'
    )
    date_completion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.etudiant.username} → {self.course_lesson.titre}'

    class Meta:
        verbose_name = 'Progression leçon'
        verbose_name_plural = 'Progressions leçons'
        unique_together = ['etudiant', 'course_lesson']


class InscriptionCours(models.Model):
    """Inscription d'un étudiant à un cours."""

    etudiant = models.ForeignKey(
        'auth.User', on_delete=models.CASCADE, related_name='inscriptions'
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name='inscriptions'
    )
    date_inscription = models.DateTimeField(auto_now_add=True)
    progression      = models.IntegerField(default=0)
    est_termine      = models.BooleanField(default=False)
    date_fin         = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.etudiant.username} → {self.course.titre}'

    class Meta:
        verbose_name = 'Inscription'
        verbose_name_plural = 'Inscriptions'
        ordering = ['-date_inscription']
        unique_together = ['etudiant', 'course']

class EvaluationCours(models.Model):
    """Évaluations et notes des cours par les étudiants."""
    
    etudiant = models.ForeignKey(
        'auth.User', on_delete=models.CASCADE,
        related_name='evaluations_cours'
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE,
        related_name='evaluations'
    )
    note = models.IntegerField(
        choices=[(i, f'{i}/5 ⭐') for i in range(1, 6)],
        verbose_name='Note'
    )
    commentaire = models.TextField(blank=True, max_length=500, verbose_name='Commentaire')
    date_creation = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f'{self.etudiant.username} → {self.course.titre} ({self.note}/5)'
    
    class Meta:
        verbose_name = 'Évaluation'
        verbose_name_plural = 'Évaluations'
        unique_together = ['etudiant', 'course']
        ordering = ['-date_creation']


class CertificatCours(models.Model):
    """Certificat d'achèvement pour un cours."""
    
    STATUTS = [
        ('en_cours', 'En cours'),
        ('gagne', 'Gagné'),
        ('expire', 'Expiré'),
    ]
    
    etudiant = models.ForeignKey(
        'auth.User', on_delete=models.CASCADE,
        related_name='certificats'
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE,
        related_name='certificats'
    )
    date_obtention = models.DateTimeField(auto_now_add=True)
    date_expiration = models.DateTimeField(blank=True, null=True, verbose_name='Date d\'expiration')
    statut = models.CharField(
        max_length=20, choices=STATUTS, default='gagne',
        verbose_name='Statut'
    )
    numero_certificat = models.CharField(
        max_length=50, unique=True,
        verbose_name='Numéro de certificat'
    )
    score_final = models.IntegerField(default=100, verbose_name='Score final (%)')
    
    def __str__(self):
        return f'Certificat {self.numero_certificat} - {self.etudiant.username}'
    
    class Meta:
        verbose_name = 'Certificat'
        verbose_name_plural = 'Certificats'
        ordering = ['-date_obtention']
        unique_together = ['etudiant', 'course']


class QuestionFAQ(models.Model):
    """Questions fréquemment posées par les étudiants dans un cours."""
    
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE,
        related_name='faq'
    )
    auteur = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL,
        null=True, related_name='questions_faq'
    )
    question = models.CharField(max_length=300, verbose_name='Question')
    reponse = models.TextField(verbose_name='Réponse')
    date_creation = models.DateTimeField(auto_now_add=True)
    approuvee_par_admin = models.BooleanField(default=False)
    votes_positifs = models.IntegerField(default=0)
    
    def __str__(self):
        return f'{self.course.titre} - {self.question[:50]}...'
    
    class Meta:
        verbose_name = 'Question FAQ'
        verbose_name_plural = 'Questions FAQ'
        ordering = ['-votes_positifs', '-date_creation']


class Exercice(models.Model):
    """
    Un exercice QCM attaché à une leçon.
    Le corrigé n'est visible qu'après une bonne réponse.
    """

    # La leçon à laquelle appartient cet exercice
    course_lesson = models.ForeignKey(
        'CourseLesson',
        on_delete=models.CASCADE,
        related_name='exercices'
    )

    # La question — supporte le LaTeX
    question = models.TextField(
        verbose_name='Question',
        help_text='Supporte le LaTeX. Ex: Calculer $x^2 + 2x + 1$'
    )

    # Les 4 choix de réponse
    choix_a = models.CharField(max_length=500, verbose_name='Choix A')
    choix_b = models.CharField(max_length=500, verbose_name='Choix B')
    choix_c = models.CharField(max_length=500, verbose_name='Choix C')
    choix_d = models.CharField(max_length=500, verbose_name='Choix D')

    # La bonne réponse
    REPONSES = [
        ('A', 'Choix A'),
        ('B', 'Choix B'),
        ('C', 'Choix C'),
        ('D', 'Choix D'),
    ]
    bonne_reponse = models.CharField(
        max_length=1,
        choices=REPONSES,
        verbose_name='Bonne réponse'
    )

    # Le corrigé détaillé — visible seulement après bonne réponse
    # Supporte le LaTeX et le code
    corrige = models.TextField(
        verbose_name='Corrigé détaillé',
        help_text='Explication complète. Supporte le LaTeX et le code HTML.'
    )

    # Ordre d'affichage dans la leçon
    ordre = models.IntegerField(default=1, verbose_name='Ordre')

    # Points accordés si bonne réponse
    points = models.IntegerField(default=1, verbose_name='Points')

    # Est-ce que l'exercice est actif ?
    est_actif = models.BooleanField(default=True, verbose_name='Actif')

    def get_bonne_reponse_texte(self):
        """Retourne le texte de la bonne réponse."""
        mapping = {
            'A': self.choix_a,
            'B': self.choix_b,
            'C': self.choix_c,
            'D': self.choix_d,
        }
        return mapping.get(self.bonne_reponse, '')

    def __str__(self):
        return f"[{self.course_lesson.titre}] Exercice {self.ordre} : {self.question[:50]}..."

    class Meta:
        verbose_name = 'Exercice'
        verbose_name_plural = 'Exercices'
        ordering = ['course_lesson', 'ordre']


class TentativeExercice(models.Model):
    """
    Enregistre chaque tentative d'un étudiant sur un exercice.
    Permet de savoir si l'étudiant a déjà réussi l'exercice.
    """

    etudiant = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='tentatives'
    )

    exercice = models.ForeignKey(
        Exercice,
        on_delete=models.CASCADE,
        related_name='tentatives'
    )

    # La réponse choisie par l'étudiant
    reponse_choisie = models.CharField(max_length=1)

    # Est-ce que c'était la bonne réponse ?
    est_correcte = models.BooleanField(default=False)

    # Date de la tentative
    date_tentative = models.DateTimeField(auto_now_add=True)

    # Nombre de tentatives pour cet exercice
    numero_tentative = models.IntegerField(default=1)

    def __str__(self):
        statut = "✅" if self.est_correcte else "❌"
        return f"{statut} {self.etudiant.username} → {self.exercice}"

    class Meta:
        verbose_name = 'Tentative'
        verbose_name_plural = 'Tentatives'
        ordering = ['-date_tentative']

class Certificat(models.Model):
    """
    Certificat de réussite généré automatiquement quand un étudiant
    termine un cours payant.
    """

    inscription = models.OneToOneField(
        InscriptionCours,
        on_delete=models.CASCADE,
        related_name='certificat'
    )

    # Date de génération du certificat
    date_emission = models.DateTimeField(auto_now_add=True)

    # Code unique de vérification (pour le QR code)
    code_verification = models.CharField(
        max_length=32,
        unique=True,
        verbose_name='Code de vérification'
    )

    def __str__(self):
        return (
            f"Certificat — {self.inscription.etudiant.username} "
            f"— {self.inscription.course.titre}"
        )

    def get_nom_fichier(self):
        """Nom du fichier PDF téléchargeable."""
        prenom = self.inscription.etudiant.first_name or self.inscription.etudiant.username
        nom    = self.inscription.etudiant.last_name or ''
        cours  = self.inscription.course.titre[:30].replace(' ', '_')
        return f"Certificat_Numeria_{prenom}_{nom}_{cours}.pdf"

    class Meta:
        verbose_name = 'Certificat'
        verbose_name_plural = 'Certificats'
        ordering = ['-date_emission']


# =============================================================================
# EXERCICES DE CODE (Pyodide — exécution dans le navigateur)
# =============================================================================

class CodeExercise(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy',   _('Facile')),
        ('medium', _('Moyen')),
        ('hard',   _('Difficile')),
    ]
    EVAL_MODES = [
        ('exact',    _('Output exact')),
        ('contains', _('Output contient')),
        ('tests',    _('Tests unitaires')),
    ]

    course_lesson = models.ForeignKey(
        'CourseLesson', on_delete=models.CASCADE,
        related_name='code_exercises', verbose_name=_('Leçon'),
        null=True, blank=True,
    )
    formation_lesson = models.ForeignKey(
        'formation.FormationLesson', on_delete=models.CASCADE,
        related_name='code_exercises', verbose_name=_('Leçon de formation'),
        null=True, blank=True,
    )
    title = models.CharField(max_length=300, verbose_name=_('Titre'))
    instructions = models.TextField(
        verbose_name=_('Instructions'),
        help_text=_('Instructions en Markdown'),
    )
    starter_code = models.TextField(
        verbose_name=_('Code de départ'),
        help_text=_('Code affiché à l\'étudiant'),
    )
    solution_code = models.TextField(
        verbose_name=_('Solution'),
        help_text=_('Jamais montrée à l\'étudiant'),
    )
    expected_output = models.TextField(
        blank=True, verbose_name=_('Output attendu'),
        help_text=_('Pour comparaison exacte ou contient'),
    )
    test_code = models.TextField(
        blank=True, verbose_name=_('Code de tests'),
        help_text=_('Assertions cachées (mode tests unitaires)'),
    )
    evaluation_mode = models.CharField(
        max_length=20, choices=EVAL_MODES, default='exact',
        verbose_name=_('Mode d\'évaluation'),
    )
    difficulty = models.CharField(
        max_length=10, choices=DIFFICULTY_CHOICES, default='easy',
        verbose_name=_('Difficulté'),
    )
    hint = models.TextField(
        blank=True, verbose_name=_('Indice'),
        help_text=_('Affiché après 3 tentatives échouées'),
    )
    max_attempts = models.IntegerField(
        default=0, verbose_name=_('Tentatives max'),
        help_text=_('0 = illimité'),
    )
    points = models.IntegerField(default=10, verbose_name=_('Points'))
    order = models.IntegerField(default=0, verbose_name=_('Ordre'))
    is_active = models.BooleanField(default=True, verbose_name=_('Actif'))
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_code_exercises', verbose_name=_('Créé par'),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Créé le'), null=True)

    class Meta:
        ordering = ['order']
        verbose_name = _('Exercice de code')
        verbose_name_plural = _('Exercices de code')

    def __str__(self):
        return self.title


class StudentCodeSubmission(models.Model):
    student = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='code_submissions', verbose_name=_('Étudiant'),
    )
    exercise = models.ForeignKey(
        CodeExercise, on_delete=models.CASCADE,
        related_name='submissions', verbose_name=_('Exercice'),
    )
    code_submitted = models.TextField(verbose_name=_('Code soumis'))
    output_received = models.TextField(blank=True, verbose_name=_('Output reçu'))
    is_correct = models.BooleanField(default=False, verbose_name=_('Correct'))
    attempt_number = models.IntegerField(default=1, verbose_name=_('Tentative n°'))
    time_spent_seconds = models.IntegerField(default=0, verbose_name=_('Temps (s)'))
    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Soumis le'))

    class Meta:
        ordering = ['-submitted_at']
        verbose_name = _('Soumission de code')
        verbose_name_plural = _('Soumissions de code')

    def __str__(self):
        status = '✅' if self.is_correct else '❌'
        return f"{status} {self.student.username} — {self.exercise.title} (#{self.attempt_number})"


# =============================================================================
# SANDBOX — Scripts sauvegardés par les utilisateurs
# =============================================================================

class UserScript(models.Model):
    """Script Python personnel sauvegardé dans le sandbox utilisateur."""
    user  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_scripts')
    titre = models.CharField(max_length=200, default='Sans titre', verbose_name='Titre')
    code  = models.TextField(default='', verbose_name='Code')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Créé le')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Modifié le')

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Script utilisateur'
        verbose_name_plural = 'Scripts utilisateurs'

    def __str__(self):
        return f"{self.user.username} — {self.titre}"

# =============================================================================
# LESSON BLOCKS — Système de blocs ordonnés pour les leçons
# =============================================================================

class LessonBlock(models.Model):
    """Ordered content block inside a Course Lesson or Formation Lesson."""
    BLOCK_TYPES = [
        ('text',         _('Texte / Markdown / LaTeX')),
        ('video',        _('Vidéo')),
        ('sandbox',      _('Sandbox Python libre')),
        ('exercise',     _('Exercice de code Python')),
        ('mcq',          _('Question à choix multiples')),
        ('fill_blank',   _('Texte à trous')),
        ('true_false',   _('Vrai ou Faux')),
        ('code_order',   _('Ordonner le code')),
        ('matching',     _('Associations')),
        ('short_answer', _('Réponse courte')),
        ('grouped_exercise', _('Exercice groupé')),
    ]

    # Belongs to one of these two (exactly one must be set)
    course_lesson = models.ForeignKey(
        'CourseLesson', on_delete=models.CASCADE,
        related_name='blocks', null=True, blank=True,
        verbose_name=_('Leçon de cours'),
    )
    formation_lesson = models.ForeignKey(
        'formation.FormationLesson', on_delete=models.CASCADE,
        related_name='blocks', null=True, blank=True,
        verbose_name=_('Leçon de formation'),
    )

    block_type = models.CharField(max_length=20, choices=BLOCK_TYPES, verbose_name=_('Type'))
    order      = models.IntegerField(default=0, verbose_name=_('Ordre'))

    # ── TEXT block ────────────────────────────────────────────────────────
    text_content = models.TextField(blank=True, verbose_name=_('Contenu Markdown / LaTeX'))

    # ── VIDEO block ───────────────────────────────────────────────────────
    video_url     = models.URLField(blank=True, null=True, verbose_name=_('URL vidéo'))
    video_caption = models.CharField(max_length=300, blank=True, verbose_name=_('Légende'))

    # ── SANDBOX block ─────────────────────────────────────────────────────
    sandbox_title        = models.CharField(max_length=300, blank=True, default='Essaie toi-même')
    sandbox_initial_code = models.TextField(blank=True, default='# Écris ton code ici\n')

    # ── EXERCISE block ────────────────────────────────────────────────────
    code_exercise = models.ForeignKey(
        'CodeExercise', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='lesson_blocks',
        verbose_name=_('Exercice de code'),
    )

    # ── MCQ block ─────────────────────────────────────────────────────────
    mcq_exercise = models.ForeignKey(
        'MCQExercise', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='lesson_blocks',
        verbose_name=_('QCM'),
    )

    # ── NEW EXERCISE TYPES ────────────────────────────────────────────────
    fill_blank_exercise = models.ForeignKey(
        'FillBlankExercise', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='lesson_blocks',
    )
    true_false_exercise = models.ForeignKey(
        'TrueFalseExercise', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='lesson_blocks',
    )
    code_order_exercise = models.ForeignKey(
        'CodeOrderExercise', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='lesson_blocks',
    )
    matching_exercise = models.ForeignKey(
        'MatchingExercise', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='lesson_blocks',
    )
    short_answer_exercise = models.ForeignKey(
        'ShortAnswerExercise', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='lesson_blocks',
    )
    grouped_exercise = models.ForeignKey(
        'GroupedExercise', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='lesson_blocks',
        verbose_name=_('Exercice groupé'),
    )

    class Meta:
        ordering = ['order']
        verbose_name = _('Bloc de leçon')
        verbose_name_plural = _('Blocs de leçon')

    def __str__(self):
        parent = self.course_lesson or self.formation_lesson
        return f'[{self.block_type}] {parent}'

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.course_lesson and not self.formation_lesson:
            raise ValidationError(
                'Un bloc doit appartenir à une leçon de cours ou de formation.'
            )


# =============================================================================
# MCQ EXERCISES — Questions à Choix Multiples
# =============================================================================

class MCQExercise(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy',   _('Facile')),
        ('medium', _('Moyen')),
        ('hard',   _('Difficile')),
    ]

    course_lesson = models.ForeignKey(
        'CourseLesson', on_delete=models.CASCADE,
        related_name='mcq_exercises', null=True, blank=True,
        verbose_name=_('Leçon de cours'),
    )
    formation_lesson = models.ForeignKey(
        'formation.FormationLesson', on_delete=models.CASCADE,
        related_name='mcq_exercises', null=True, blank=True,
        verbose_name=_('Leçon de formation'),
    )
    title      = models.CharField(max_length=300, verbose_name=_('Titre'))
    question   = models.TextField(verbose_name=_('Question'))
    explanation = models.TextField(blank=True, verbose_name=_('Explication'))
    hint       = models.TextField(blank=True, verbose_name=_('Indice'))
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='easy')
    points     = models.IntegerField(default=5, verbose_name=_('Points'))
    max_attempts = models.IntegerField(default=0, verbose_name=_('Tentatives max (0=illimité)'))
    allow_multiple_correct = models.BooleanField(
        default=False,
        verbose_name=_('Plusieurs bonnes réponses possibles'),
    )
    shuffle_choices = models.BooleanField(default=True, verbose_name=_('Mélanger les choix'))
    show_explanation_on_wrong = models.BooleanField(default=True)
    order      = models.IntegerField(default=0)
    is_active  = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_mcq_exercises',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']
        verbose_name = _('Exercice QCM')
        verbose_name_plural = _('Exercices QCM')

    def __str__(self):
        return self.title

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.course_lesson and not self.formation_lesson:
            raise ValidationError(
                'Un QCM doit être lié à une leçon de cours ou de formation.'
            )


class MCQChoice(models.Model):
    exercise   = models.ForeignKey(MCQExercise, on_delete=models.CASCADE, related_name='choices')
    text       = models.TextField(verbose_name=_('Texte du choix'))
    is_correct = models.BooleanField(default=False, verbose_name=_('Bonne réponse'))
    order      = models.IntegerField(default=0)
    feedback   = models.TextField(blank=True, verbose_name=_('Feedback spécifique'))

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{'✓' if self.is_correct else '○'} {self.text[:60]}"


class MCQSubmission(models.Model):
    student    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mcq_submissions')
    exercise   = models.ForeignKey(MCQExercise, on_delete=models.CASCADE, related_name='submissions')
    selected_choices = models.ManyToManyField(MCQChoice, related_name='submissions', blank=True)
    is_correct = models.BooleanField(default=False)
    attempt_number = models.IntegerField(default=1)
    points_earned  = models.IntegerField(default=0)
    submitted_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']


class MCQGrade(models.Model):
    """Tracks a student's best result on a specific MCQExercise."""
    student       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mcq_grades')
    exercise      = models.ForeignKey(MCQExercise, on_delete=models.CASCADE, related_name='grades')
    is_solved     = models.BooleanField(default=False)
    points_earned = models.IntegerField(default=0)
    attempts_count = models.IntegerField(default=0)
    solved_at     = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('student', 'exercise')


# =============================================================================
# EXERCISE GRADE — Code exercises (parallel to MCQGrade)
# =============================================================================

class ExerciseGrade(models.Model):
    """Tracks a student's best result on a CodeExercise."""
    student        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='exercise_grades')
    exercise       = models.ForeignKey('CodeExercise', on_delete=models.CASCADE, related_name='grades')
    is_solved      = models.BooleanField(default=False)
    points_earned  = models.IntegerField(default=0)
    attempts_count = models.IntegerField(default=0)
    time_spent_seconds = models.IntegerField(default=0)
    solved_at      = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('student', 'exercise')
        verbose_name = _('Note exercice code')


# =============================================================================
# 5 NEW EXERCISE TYPES
# All server-evaluated (no Pyodide needed for evaluation)
# =============================================================================

_DIFF = [('easy','Facile'),('medium','Moyen'),('hard','Difficile')]


class FillBlankExercise(models.Model):
    """Texte à trous — blanks marked {{blank_1}}, {{blank_2}} in text."""
    course_lesson    = models.ForeignKey('CourseLesson', on_delete=models.CASCADE, null=True, blank=True, related_name='fill_blank_exercises')
    formation_lesson = models.ForeignKey('formation.FormationLesson', on_delete=models.CASCADE, null=True, blank=True, related_name='fill_blank_exercises')
    title            = models.CharField(max_length=300)
    instructions     = models.TextField(blank=True)
    text_with_blanks = models.TextField(help_text='Use {{blank_1}}, {{blank_2}}, … markers')
    # JSON: {"blank_1": ["nx", "n*x"], "blank_2": ["n-1"]}
    answers          = models.JSONField(default=dict)
    case_sensitive   = models.BooleanField(default=False)
    difficulty       = models.CharField(max_length=10, choices=_DIFF, default='easy')
    points           = models.IntegerField(default=5)
    hint             = models.TextField(blank=True)
    explanation      = models.TextField(blank=True)
    max_attempts     = models.IntegerField(default=0)
    is_active        = models.BooleanField(default=True)
    order            = models.IntegerField(default=0)
    class Meta: ordering = ['order']
    def __str__(self): return self.title


class FillBlankGrade(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fill_blank_grades')
    exercise = models.ForeignKey(FillBlankExercise, on_delete=models.CASCADE, related_name='grades')
    is_solved = models.BooleanField(default=False)
    points_earned = models.IntegerField(default=0)
    attempts_count = models.IntegerField(default=0)
    solved_at = models.DateTimeField(null=True, blank=True)
    class Meta: unique_together = ('student', 'exercise')


class TrueFalseExercise(models.Model):
    """Vrai ou Faux — list of statements each marked true/false."""
    course_lesson    = models.ForeignKey('CourseLesson', on_delete=models.CASCADE, null=True, blank=True, related_name='true_false_exercises')
    formation_lesson = models.ForeignKey('formation.FormationLesson', on_delete=models.CASCADE, null=True, blank=True, related_name='true_false_exercises')
    title            = models.CharField(max_length=300)
    # JSON: [{"statement": "...", "is_true": true, "explanation": "..."}, ...]
    statements       = models.JSONField(default=list)
    points_per_statement = models.IntegerField(default=2)
    difficulty       = models.CharField(max_length=10, choices=_DIFF, default='easy')
    hint             = models.TextField(blank=True)
    is_active        = models.BooleanField(default=True)
    order            = models.IntegerField(default=0)
    class Meta: ordering = ['order']
    def __str__(self): return self.title


class TrueFalseGrade(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='true_false_grades')
    exercise = models.ForeignKey(TrueFalseExercise, on_delete=models.CASCADE, related_name='grades')
    is_solved = models.BooleanField(default=False)
    points_earned = models.IntegerField(default=0)
    attempts_count = models.IntegerField(default=0)
    solved_at = models.DateTimeField(null=True, blank=True)
    class Meta: unique_together = ('student', 'exercise')


class CodeOrderExercise(models.Model):
    """Ordonner le code — drag code lines into correct order."""
    course_lesson    = models.ForeignKey('CourseLesson', on_delete=models.CASCADE, null=True, blank=True, related_name='code_order_exercises')
    formation_lesson = models.ForeignKey('formation.FormationLesson', on_delete=models.CASCADE, null=True, blank=True, related_name='code_order_exercises')
    title            = models.CharField(max_length=300)
    instructions     = models.TextField(blank=True)
    # JSON array of code lines IN CORRECT ORDER
    correct_order    = models.JSONField(default=list)
    # JSON array of distractor lines (wrong lines)
    distractor_lines = models.JSONField(default=list, blank=True)
    difficulty       = models.CharField(max_length=10, choices=_DIFF, default='easy')
    points           = models.IntegerField(default=10)
    hint             = models.TextField(blank=True)
    explanation      = models.TextField(blank=True)
    max_attempts     = models.IntegerField(default=0)
    is_active        = models.BooleanField(default=True)
    order            = models.IntegerField(default=0)
    class Meta: ordering = ['order']
    def __str__(self): return self.title


class CodeOrderGrade(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='code_order_grades')
    exercise = models.ForeignKey(CodeOrderExercise, on_delete=models.CASCADE, related_name='grades')
    is_solved = models.BooleanField(default=False)
    points_earned = models.IntegerField(default=0)
    attempts_count = models.IntegerField(default=0)
    solved_at = models.DateTimeField(null=True, blank=True)
    class Meta: unique_together = ('student', 'exercise')


class MatchingExercise(models.Model):
    """Associations — match left items to right items."""
    course_lesson    = models.ForeignKey('CourseLesson', on_delete=models.CASCADE, null=True, blank=True, related_name='matching_exercises')
    formation_lesson = models.ForeignKey('formation.FormationLesson', on_delete=models.CASCADE, null=True, blank=True, related_name='matching_exercises')
    title            = models.CharField(max_length=300)
    instructions     = models.TextField(blank=True)
    # JSON: [{"left": "Dérivée", "right": "Taux de variation"}, ...]
    pairs            = models.JSONField(default=list)
    difficulty       = models.CharField(max_length=10, choices=_DIFF, default='easy')
    points           = models.IntegerField(default=8)
    hint             = models.TextField(blank=True)
    explanation      = models.TextField(blank=True)
    is_active        = models.BooleanField(default=True)
    order            = models.IntegerField(default=0)
    class Meta: ordering = ['order']
    def __str__(self): return self.title


class MatchingGrade(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='matching_grades')
    exercise = models.ForeignKey(MatchingExercise, on_delete=models.CASCADE, related_name='grades')
    is_solved = models.BooleanField(default=False)
    points_earned = models.IntegerField(default=0)
    attempts_count = models.IntegerField(default=0)
    solved_at = models.DateTimeField(null=True, blank=True)
    class Meta: unique_together = ('student', 'exercise')


class ShortAnswerExercise(models.Model):
    """Réponse courte — student types a short text answer."""
    course_lesson    = models.ForeignKey('CourseLesson', on_delete=models.CASCADE, null=True, blank=True, related_name='short_answer_exercises')
    formation_lesson = models.ForeignKey('formation.FormationLesson', on_delete=models.CASCADE, null=True, blank=True, related_name='short_answer_exercises')
    title            = models.CharField(max_length=300)
    question         = models.TextField()
    # JSON list of accepted answers after normalization
    accepted_answers = models.JSONField(default=list)
    case_sensitive   = models.BooleanField(default=False)
    strip_whitespace = models.BooleanField(default=True)
    difficulty       = models.CharField(max_length=10, choices=_DIFF, default='easy')
    points           = models.IntegerField(default=5)
    hint             = models.TextField(blank=True)
    explanation      = models.TextField(blank=True)
    max_attempts     = models.IntegerField(default=3)
    is_code_answer   = models.BooleanField(default=False)
    is_active        = models.BooleanField(default=True)
    order            = models.IntegerField(default=0)
    class Meta: ordering = ['order']
    def __str__(self): return self.title


class GroupedExercise(models.Model):
    QUESTION_TYPES = [
        ('qcm', _('QCM')),
        ('fill_blank', _('Texte à trous')),
        ('true_false', _('Vrai ou Faux')),
        ('short_answer', _('Réponse courte')),
    ]

    course_lesson    = models.ForeignKey('CourseLesson', on_delete=models.CASCADE, null=True, blank=True, related_name='grouped_exercises')
    formation_lesson = models.ForeignKey('formation.FormationLesson', on_delete=models.CASCADE, null=True, blank=True, related_name='grouped_exercises')
    title            = models.CharField(max_length=300)
    instructions     = models.TextField(blank=True)
    question_type    = models.CharField(max_length=20, choices=QUESTION_TYPES, default='qcm')
    questions        = models.JSONField(default=list)
    created_by       = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_grouped_exercises', verbose_name=_('Créé par'),
    )
    created_at       = models.DateTimeField(auto_now_add=True, verbose_name=_('Créé le'))
    is_active        = models.BooleanField(default=True)

    class Meta:
        verbose_name = _('Exercice groupé')
        verbose_name_plural = _('Exercices groupés')

    def __str__(self):
        return self.title


class ShortAnswerGrade(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='short_answer_grades')
    exercise = models.ForeignKey(ShortAnswerExercise, on_delete=models.CASCADE, related_name='grades')
    is_solved = models.BooleanField(default=False)
    points_earned = models.IntegerField(default=0)
    attempts_count = models.IntegerField(default=0)
    solved_at = models.DateTimeField(null=True, blank=True)
    class Meta: unique_together = ('student', 'exercise')


# =============================================================================
# UNIFIED PROGRESS TRACKING (all exercise types)
# =============================================================================

class ExerciseAttempt(models.Model):
    """Records every attempt by a student on any exercise type."""
    EXERCISE_TYPES = [
        ('code',         _('Code')),
        ('mcq',          _('QCM')),
        ('fill_blank',   _('Texte à trous')),
        ('true_false',   _('Vrai/Faux')),
        ('code_order',   _('Ordre code')),
        ('matching',     _('Associations')),
        ('short_answer', _('Réponse courte')),
    ]
    student = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='exercise_attempts',
        verbose_name=_('Étudiant'),
    )
    exercise_type = models.CharField(max_length=20, choices=EXERCISE_TYPES)
    exercise_id = models.PositiveIntegerField()
    attempt_number = models.PositiveIntegerField(default=1)
    is_correct = models.BooleanField(default=False)
    points_earned = models.IntegerField(default=0)
    answer_data = models.JSONField(default=dict, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']
        verbose_name = _('Tentative exercice')
        verbose_name_plural = _('Tentatives exercices')
        indexes = [
            models.Index(fields=['student', 'exercise_type', 'exercise_id']),
        ]

    def __str__(self):
        status = '✅' if self.is_correct else '❌'
        return f'{status} {self.student.username} — {self.exercise_type} #{self.exercise_id}'


class StudentProgress(models.Model):
    """Best result per student per exercise (unified across all types)."""
    student = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='student_progress',
        verbose_name=_('Étudiant'),
    )
    exercise_type = models.CharField(max_length=20)
    exercise_id = models.PositiveIntegerField()
    is_solved = models.BooleanField(default=False)
    points_earned = models.IntegerField(default=0)
    attempts = models.PositiveIntegerField(default=0)
    solved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('student', 'exercise_type', 'exercise_id')
        verbose_name = _('Progression étudiant')
        verbose_name_plural = _('Progressions étudiants')
        indexes = [
            models.Index(fields=['student', 'exercise_type']),
        ]

    def __str__(self):
        status = '✅' if self.is_solved else '○'
        return f'{status} {self.student.username} — {self.exercise_type} #{self.exercise_id}'


# ── Backward-compatible aliases (deprecated — use English names) ─────────────
Cours = Course
Module = CourseModule
Lecon = CourseLesson
