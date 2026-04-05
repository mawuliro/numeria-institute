from django.db import models
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

class Cours(models.Model):
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

    def get_video_embed_url(self):
        """Retourne l'URL embed prête pour l'<iframe>."""
        return convertir_url_youtube(self.video_youtube)

    def __str__(self):
        if self.type_cours == 'scolaire' and self.classe:
            return f'[{self.get_classe_display()}] {self.titre}'
        return self.titre

    class Meta:
        verbose_name = 'Cours'
        verbose_name_plural = 'Cours'
        ordering = ['-date_creation']


class Lecon(models.Model):
    """Une leçon dans un cours."""

    cours = models.ForeignKey(
        Cours, on_delete=models.CASCADE, related_name='lecons'
    )
    titre   = models.CharField(max_length=200, verbose_name='Titre')
    contenu = models.TextField(
        blank=True, verbose_name='Contenu',
        help_text='Supporte le LaTeX ($...$) et le code (<pre><code>...)'
    )
    ordre         = models.IntegerField(default=1, verbose_name='Ordre')
    duree_minutes = models.IntegerField(default=10, verbose_name='Durée (minutes)')

    # URL originale de la leçon — jamais convertie en base
    video_youtube = models.URLField(
        blank=True, null=True,
        verbose_name='Vidéo YouTube / Vimeo',
        help_text='URL YouTube ou Vimeo normale. Ex : https://youtu.be/ABC123'
    )
    est_publiee = models.BooleanField(default=True, verbose_name='Publiée')

    # SUPPRIMÉ : le save() ne convertit plus l'URL automatiquement.

    def get_video_embed_url(self):
        return convertir_url_youtube(self.video_youtube)

    def __str__(self):
        return f'{self.cours.titre} — Leçon {self.ordre} : {self.titre}'

    class Meta:
        verbose_name = 'Leçon'
        verbose_name_plural = 'Leçons'
        ordering = ['cours', 'ordre']


class ProgressionLecon(models.Model):
    """Suit la progression d'un étudiant sur une leçon."""

    etudiant = models.ForeignKey(
        'auth.User', on_delete=models.CASCADE,
        related_name='progressions_lecons'
    )
    lecon = models.ForeignKey(
        Lecon, on_delete=models.CASCADE, related_name='progressions'
    )
    date_completion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.etudiant.username} → {self.lecon.titre}'

    class Meta:
        verbose_name = 'Progression leçon'
        verbose_name_plural = 'Progressions leçons'
        unique_together = ['etudiant', 'lecon']


class InscriptionCours(models.Model):
    """Inscription d'un étudiant à un cours."""

    etudiant = models.ForeignKey(
        'auth.User', on_delete=models.CASCADE, related_name='inscriptions'
    )
    cours = models.ForeignKey(
        Cours, on_delete=models.CASCADE, related_name='inscriptions'
    )
    date_inscription = models.DateTimeField(auto_now_add=True)
    progression      = models.IntegerField(default=0)
    est_termine      = models.BooleanField(default=False)
    date_fin         = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.etudiant.username} → {self.cours.titre}'

    class Meta:
        verbose_name = 'Inscription'
        verbose_name_plural = 'Inscriptions'
        ordering = ['-date_inscription']
        unique_together = ['etudiant', 'cours']

class Exercice(models.Model):
    """
    Un exercice QCM attaché à une leçon.
    Le corrigé n'est visible qu'après une bonne réponse.
    """

    # La leçon à laquelle appartient cet exercice
    lecon = models.ForeignKey(
        Lecon,
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
        return f"[{self.lecon.titre}] Exercice {self.ordre} : {self.question[:50]}..."

    class Meta:
        verbose_name = 'Exercice'
        verbose_name_plural = 'Exercices'
        ordering = ['lecon', 'ordre']


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
            f"— {self.inscription.cours.titre}"
        )

    def get_nom_fichier(self):
        """Nom du fichier PDF téléchargeable."""
        prenom = self.inscription.etudiant.first_name or self.inscription.etudiant.username
        nom    = self.inscription.etudiant.last_name or ''
        cours  = self.inscription.cours.titre[:30].replace(' ', '_')
        return f"Certificat_Numeria_{prenom}_{nom}_{cours}.pdf"

    class Meta:
        verbose_name = 'Certificat'
        verbose_name_plural = 'Certificats'
        ordering = ['-date_emission']