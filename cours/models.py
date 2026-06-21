"""
Numeria Institute — Courses, Lessons, Blocks, Exercises (REBUILT CLEAN).

This module defines ONLY the new clean system (schema + validation rules)
as specified in the rebuild spec.

Golden rules:
- Never store Django template tags in DB fields.
- Lesson foreign keys use exactly: course_lesson / formation_lesson.
- Exactly one of course_lesson or formation_lesson must be set (never both).
"""

from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify


# =============================================================================
# Video helpers (used by templatetags + templates)
# =============================================================================

def extraire_id_youtube(url: str | None):
    """Extract YouTube video ID from common URL formats."""
    if not url or 'vimeo' in (url or '').lower():
        return None
    url = url.strip()
    if 'youtu.be/' in url:
        return url.split('youtu.be/')[-1].split('?')[0].strip('/')
    if '/shorts/' in url:
        return url.split('/shorts/')[-1].split('?')[0].strip('/')
    if '/embed/' in url:
        return url.split('/embed/')[-1].split('?')[0].strip('/')
    if 'v=' in url:
        return url.split('v=')[-1].split('&')[0].strip()
    return None


def convertir_url_youtube(url: str | None):
    """Convert YouTube/Vimeo URL to embed URL (display-time only)."""
    if not url:
        return url

    url = url.strip()
    u = url.lower()

    # Vimeo
    if 'vimeo.com' in u:
        if '/video/' in u:
            video_id = url.split('/video/')[-1].split('?')[0].split('/')[0]
        else:
            video_id = url.split('vimeo.com/')[-1].split('?')[0].split('/')[0]
        if video_id.isdigit():
            return f'https://player.vimeo.com/video/{video_id}?color=E8A020&title=0&byline=0'
        return url

    # YouTube
    if 'youtube-nocookie.com/embed/' in u:
        return url
    if 'youtube.com/embed/' in u:
        video_id = url.split('/embed/')[-1].split('?')[0].strip('/')
        return f'https://www.youtube-nocookie.com/embed/{video_id}?rel=0&modestbranding=1'
    if 'youtu.be/' in u:
        video_id = url.split('youtu.be/')[-1].split('?')[0].strip('/')
        return f'https://www.youtube-nocookie.com/embed/{video_id}?rel=0&modestbranding=1'
    if '/shorts/' in u:
        video_id = url.split('/shorts/')[-1].split('?')[0].strip('/')
        return f'https://www.youtube-nocookie.com/embed/{video_id}?rel=0&modestbranding=1'
    if 'youtube.com' in u and 'v=' in url:
        video_id = url.split('v=')[-1].split('&')[0].strip()
        return f'https://www.youtube-nocookie.com/embed/{video_id}?rel=0&modestbranding=1'
    return url


# =============================================================================
# Course models (SPEC)
# =============================================================================

class Course(models.Model):
    STATUS = [
        ('draft', 'Brouillon'),
        ('published', 'Publié'),
        ('archived', 'Archivé'),
    ]
    LEVELS = [
        ('debutant', 'Débutant'),
        ('intermediaire', 'Intermédiaire'),
        ('avance', 'Avancé'),
    ]
    CATEGORIES = [
        ('mathematiques', 'Mathématiques'),
        ('physique', 'Physique'),
        ('informatique', 'Informatique'),
        ('python', 'Python'),
        ('ia', 'Intelligence Artificielle'),
        ('data', 'Data Science'),
        ('autre', 'Autre'),
    ]

    title = models.CharField(max_length=300)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    short_description = models.CharField(max_length=300, blank=True)
    category = models.CharField(max_length=50, choices=CATEGORIES, default='autre')
    level = models.CharField(max_length=20, choices=LEVELS, default='debutant')
    language = models.CharField(
        max_length=10,
        choices=[('fr', 'Français'), ('en', 'English')],
        default='fr',
    )
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_free = models.BooleanField(default=True)
    thumbnail = models.ImageField(upload_to='courses/thumbnails/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS, default='draft')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_courses',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objectives = models.TextField(blank=True)
    prerequisites = models.TextField(blank=True)
    estimated_hours = models.DecimalField(max_digits=5, decimal_places=1, default=0)

    class Meta:
        verbose_name = 'Cours'
        verbose_name_plural = 'Cours'

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)
            slug = base
            n = 1
            while Course.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{n}'
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)


class CourseModule(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']
        verbose_name = 'Module'
        verbose_name_plural = 'Modules'

    def __str__(self):
        return f'{self.course.title} — {self.title}'


class CourseLesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons')
    module = models.ForeignKey(
        CourseModule,
        on_delete=models.SET_NULL,
        related_name='lessons',
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=300)
    slug = models.SlugField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_free_preview = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    estimated_minutes = models.PositiveIntegerField(default=10)

    class Meta:
        ordering = ['order']
        verbose_name = 'Leçon'
        verbose_name_plural = 'Leçons'

    def __str__(self):
        return f'{self.course.title} — {self.title}'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


# =============================================================================
# Enrollment + lesson completion (kept for platform compatibility)
# =============================================================================

class InscriptionCours(models.Model):
    """Course enrollment (legacy-compatible name used across the app)."""
    etudiant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='inscriptions',
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='inscriptions',
    )
    date_inscription = models.DateTimeField(auto_now_add=True)
    progression = models.IntegerField(default=0)
    est_termine = models.BooleanField(default=False)
    date_fin = models.DateTimeField(null=True, blank=True)

    @property
    def cours(self):  # backward-compatible template usage
        return self.course

    class Meta:
        unique_together = ('etudiant', 'course')
        ordering = ['-date_inscription']


class ProgressionLecon(models.Model):
    """Tracks completion of a CourseLesson by a student."""
    etudiant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='progressions_lecons',
    )
    course_lesson = models.ForeignKey(
        CourseLesson,
        on_delete=models.CASCADE,
        related_name='progressions',
    )
    date_completion = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('etudiant', 'course_lesson')


class Certificat(models.Model):
    """Legacy-compatible certificate model (used by Django admin + PDF generator)."""
    inscription = models.OneToOneField(
        InscriptionCours,
        on_delete=models.CASCADE,
        related_name='certificat',
    )
    date_emission = models.DateTimeField(auto_now_add=True)
    code_verification = models.CharField(max_length=64, unique=True)

    def save(self, *args, **kwargs):
        if not self.code_verification:
            # short deterministic-ish token without pulling in extra deps
            self.code_verification = slugify(f'{self.inscription_id}-{self.date_emission}')[:64] or 'cert'
        super().save(*args, **kwargs)

    def get_nom_fichier(self):
        """Return a safe filename for the PDF certificate download."""
        nom = slugify(self.inscription.etudiant.get_full_name() or self.inscription.etudiant.username)
        cours = slugify(self.inscription.course.title)
        return f'certificat-{nom}-{cours}.pdf'

    class Meta:
        ordering = ['-date_emission']


# Backward-compatible aliases (used across templates/views while rebuilding)
Cours = Course
Module = CourseModule
Lecon = CourseLesson


# =============================================================================
# Lesson blocks (SPEC)
# =============================================================================

class LessonBlock(models.Model):
    BLOCK_TYPES = [
        ('text', 'Texte'),
        ('video', 'Vidéo'),
        ('sandbox', 'Sandbox Python'),
        ('code_exercise', 'Exercice code'),
        ('mcq', 'QCM'),
        ('fill_blank', 'Texte à trous'),
        ('true_false', 'Vrai ou Faux'),
        ('code_order', 'Ordonner le code'),
        ('matching', 'Associations'),
        ('short_answer', 'Réponse courte'),
    ]

    # Exactly one of these is set (Rule 5)
    course_lesson = models.ForeignKey(
        'CourseLesson',
        on_delete=models.CASCADE,
        related_name='blocks',
        null=True,
        blank=True,
    )
    formation_lesson = models.ForeignKey(
        'formation.FormationLesson',
        on_delete=models.CASCADE,
        related_name='blocks',
        null=True,
        blank=True,
    )
    block_type = models.CharField(max_length=30, choices=BLOCK_TYPES)
    order = models.PositiveIntegerField(default=0)

    # TEXT
    text_content = models.TextField(blank=True)

    # VIDEO
    video_url = models.URLField(blank=True, null=True)
    video_caption = models.CharField(max_length=300, blank=True)

    # SANDBOX
    sandbox_title = models.CharField(max_length=300, blank=True, default='Essaie toi-même')
    sandbox_initial_code = models.TextField(blank=True, default='# Écris ton code ici\n')

    # Exercise foreign keys — nullable, only one used
    code_exercise = models.ForeignKey(
        'CodeExercise',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lesson_blocks',
    )
    mcq_exercise = models.ForeignKey(
        'MCQExercise',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lesson_blocks',
    )
    fill_blank = models.ForeignKey(
        'FillBlankExercise',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lesson_blocks',
    )
    true_false = models.ForeignKey(
        'TrueFalseExercise',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lesson_blocks',
    )
    code_order = models.ForeignKey(
        'CodeOrderExercise',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lesson_blocks',
    )
    matching = models.ForeignKey(
        'MatchingExercise',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lesson_blocks',
    )
    short_answer = models.ForeignKey(
        'ShortAnswerExercise',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lesson_blocks',
    )

    class Meta:
        ordering = ['order']

    def clean(self):
        if self.course_lesson and self.formation_lesson:
            raise ValidationError('Set course_lesson OR formation_lesson, not both.')
        if not self.course_lesson and not self.formation_lesson:
            raise ValidationError('Must set course_lesson or formation_lesson.')

    def get_payload(self, user=None, preview=False):
        """Build a sanitised dict for the lesson_blocks_render.html template.

        Never includes solution_code or test_code in plain text —
        test_code is base64-encoded for client-side evaluation only.
        """
        import base64

        data = {
            'id': self.id,
            'type': self.block_type,
            'order': self.order,
        }

        if self.block_type == 'text':
            data['text_content'] = self.text_content or ''

        elif self.block_type == 'video':
            data['embed_url'] = self._embed_url(self.video_url)
            data['video_caption'] = self.video_caption or ''

        elif self.block_type == 'sandbox':
            data['title'] = self.sandbox_title or 'Essaie toi-même'
            data['initial_code'] = self.sandbox_initial_code or ''

        elif self.block_type == 'code_exercise':
            ex = self.code_exercise
            if ex:
                data['exercise_id'] = ex.id
                data['id'] = ex.id
                data['title'] = ex.title
                data['instructions'] = ex.instructions or ''
                data['difficulty'] = ex.difficulty
                data['points'] = ex.points
                data['hint'] = ex.hint or ''
                data['max_attempts'] = ex.max_attempts
                data['starter_code'] = ex.starter_code or ''
                data['expected_output'] = ex.expected_output or ''
                data['evaluation_mode'] = ex.evaluation_mode
                data['test_code_b64'] = base64.b64encode(
                    (ex.test_code or '').encode()
                ).decode() if ex.test_code else ''
                data['order'] = ex.order
                data['is_solved'] = False
                data['points_earned'] = 0
                data['attempts_used'] = 0
                if user and not preview:
                    from cours.models import StudentProgress, ExerciseAttempt
                    progress = StudentProgress.objects.filter(
                        student=user, exercise_type='code',
                        exercise_id=ex.id
                    ).first()
                    if progress:
                        data['is_solved'] = progress.is_solved
                        data['points_earned'] = progress.points_earned
                    data['attempts_used'] = ExerciseAttempt.objects.filter(
                        exercise_type='code', exercise_id=ex.id, student=user
                    ).count()

        elif self.block_type == 'mcq':
            ex = self.mcq_exercise
            if ex:
                data['mcq_id'] = ex.id
                data['mcq_title'] = ex.title
                data['title'] = ex.title
                data['question'] = ex.question or ''
                data['hint'] = ex.hint or ''
                data['allow_multiple'] = ex.allow_multiple_correct
                data['shuffle'] = ex.shuffle_choices
                data['max_attempts'] = ex.max_attempts
                data['points'] = ex.points
                data['difficulty'] = ex.difficulty
                data['explanation'] = ''  # hidden until solved/exhausted
                data['is_solved'] = False
                data['points_earned'] = 0
                data['attempts_used'] = 0
                data['correct_ids'] = []
                data['choices'] = [
                    {'id': c.id, 'text': c.text, 'order': c.order}
                    for c in ex.choices.all().order_by('order')
                ]
                if user and not preview:
                    from cours.models import StudentProgress, ExerciseAttempt
                    progress = StudentProgress.objects.filter(
                        student=user, exercise_type='mcq',
                        exercise_id=ex.id
                    ).first()
                    if progress:
                        data['is_solved'] = progress.is_solved
                        data['points_earned'] = progress.points_earned
                    data['attempts_used'] = ExerciseAttempt.objects.filter(
                        exercise_type='mcq', exercise_id=ex.id, student=user
                    ).count()
                    # Reveal correct answers if solved or attempts exhausted
                    if data['is_solved'] or (ex.max_attempts > 0 and data['attempts_used'] >= ex.max_attempts):
                        data['correct_ids'] = [c.id for c in ex.choices.filter(is_correct=True)]
                        data['explanation'] = ex.explanation or ''

        elif self.block_type == 'fill_blank':
            ex = self.fill_blank
            if ex:
                data['fill_blank_id'] = ex.id
                data['title'] = ex.title
                data['text_with_blanks'] = ex.text_with_blanks or ''
                data['text_rendered'] = ex.text_with_blanks or ''
                data['blank_count'] = len(ex.answers) if isinstance(ex.answers, dict) else 0
                data['points'] = ex.points
                data['difficulty'] = ex.difficulty
                data['hint'] = ex.hint or ''
                data['max_attempts'] = ex.max_attempts
                data['is_solved'] = False
                data['attempts_used'] = 0
                if user and not preview:
                    from cours.models import StudentProgress, ExerciseAttempt
                    progress = StudentProgress.objects.filter(
                        student=user, exercise_type='fill_blank',
                        exercise_id=ex.id
                    ).first()
                    if progress:
                        data['is_solved'] = progress.is_solved
                    data['attempts_used'] = ExerciseAttempt.objects.filter(
                        exercise_type='fill_blank', exercise_id=ex.id, student=user
                    ).count()

        elif self.block_type == 'true_false':
            ex = self.true_false
            if ex:
                data['true_false_id'] = ex.id
                data['title'] = ex.title
                data['statements'] = ex.statements or []
                data['points_per_statement'] = ex.points_per_statement
                data['points'] = ex.points
                data['difficulty'] = ex.difficulty
                data['hint'] = ex.hint or ''
                data['max_attempts'] = ex.max_attempts
                data['is_solved'] = False
                data['attempts_used'] = 0
                if user and not preview:
                    from cours.models import StudentProgress, ExerciseAttempt
                    progress = StudentProgress.objects.filter(
                        student=user, exercise_type='true_false',
                        exercise_id=ex.id
                    ).first()
                    if progress:
                        data['is_solved'] = progress.is_solved
                    data['attempts_used'] = ExerciseAttempt.objects.filter(
                        exercise_type='true_false', exercise_id=ex.id, student=user
                    ).count()

        elif self.block_type == 'code_order':
            ex = self.code_order
            if ex:
                data['code_order_id'] = ex.id
                data['title'] = ex.title
                data['instructions'] = ex.instructions or ''
                data['correct_order'] = ex.correct_order or []
                data['distractor_lines'] = ex.distractor_lines or []
                data['points'] = ex.points
                data['difficulty'] = ex.difficulty
                data['hint'] = ex.hint or ''
                data['is_solved'] = False
                data['attempts_used'] = 0

        elif self.block_type == 'matching':
            ex = self.matching
            if ex:
                data['matching_id'] = ex.id
                data['title'] = ex.title
                data['instructions'] = ex.instructions or ''
                data['pairs'] = ex.pairs or []
                data['points'] = ex.points
                data['difficulty'] = ex.difficulty
                data['hint'] = ex.hint or ''
                data['is_solved'] = False
                data['attempts_used'] = 0

        elif self.block_type == 'short_answer':
            ex = self.short_answer
            if ex:
                data['short_answer_id'] = ex.id
                data['title'] = ex.title
                data['instructions'] = ex.instructions or ''
                data['points'] = ex.points
                data['difficulty'] = ex.difficulty
                data['hint'] = ex.hint or ''
                data['max_attempts'] = ex.max_attempts
                data['is_solved'] = False
                data['attempts_used'] = 0

        return data

    @staticmethod
    def _embed_url(url):
        """Convert YouTube/Vimeo URLs to embeddable iframe URLs."""
        if not url:
            return ''
        u = url.strip()
        if 'youtube.com/watch' in u and 'v=' in u:
            vid = u.split('v=', 1)[1].split('&', 1)[0]
            return f'https://www.youtube.com/embed/{vid}'
        if 'youtu.be/' in u:
            vid = u.split('youtu.be/', 1)[1].split('?', 1)[0]
            return f'https://www.youtube.com/embed/{vid}'
        if 'vimeo.com/' in u and '/embed/' not in u:
            vid = u.rstrip('/').split('/')[-1]
            return f'https://player.vimeo.com/video/{vid}'
        return u


# =============================================================================
# Exercises (SPEC)
# =============================================================================

class BaseExercise(models.Model):
    DIFFICULTY = [
        ('easy', 'Facile'),
        ('medium', 'Moyen'),
        ('hard', 'Difficile'),
    ]

    # Exactly one is set (Rule 5)
    course_lesson = models.ForeignKey(
        'cours.CourseLesson',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='%(class)s_set',
    )
    formation_lesson = models.ForeignKey(
        'formation.FormationLesson',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='%(class)s_set',
    )
    title = models.CharField(max_length=300)
    instructions = models.TextField(blank=True, help_text='Markdown + LaTeX + HTML')
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY, default='easy')
    points = models.IntegerField(default=5)
    max_attempts = models.IntegerField(default=0, help_text='0 = illimité')
    hint = models.TextField(blank=True)
    explanation = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_created',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

    def clean(self):
        if self.course_lesson and self.formation_lesson:
            raise ValidationError('Set course_lesson OR formation_lesson, not both.')
        if not self.course_lesson and not self.formation_lesson:
            raise ValidationError('Must set course_lesson or formation_lesson.')

    def __str__(self):
        return self.title


class CodeExercise(BaseExercise):
    EVAL_MODES = [
        ('exact', 'Output exact'),
        ('contains', 'Output contient'),
        ('tests', 'Tests unitaires'),
    ]
    starter_code = models.TextField(default='# Écris ton code ici\n')
    solution_code = models.TextField(default='')
    expected_output = models.TextField(blank=True)
    test_code = models.TextField(blank=True, help_text='assert statements. Jamais envoyé au navigateur.')
    evaluation_mode = models.CharField(max_length=20, choices=EVAL_MODES, default='exact')

    class Meta:
        verbose_name = 'Exercice code'


class MCQExercise(BaseExercise):
    question = models.TextField(help_text='Markdown + LaTeX')
    allow_multiple_correct = models.BooleanField(default=False)
    shuffle_choices = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'QCM'


class MCQChoice(models.Model):
    exercise = models.ForeignKey(MCQExercise, on_delete=models.CASCADE, related_name='choices')
    text = models.TextField()
    is_correct = models.BooleanField(default=False)
    feedback = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']


class FillBlankExercise(BaseExercise):
    text_with_blanks = models.TextField()
    answers = models.JSONField(default=dict)
    case_sensitive = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Texte à trous'


class TrueFalseExercise(BaseExercise):
    statements = models.JSONField(default=list)
    points_per_statement = models.IntegerField(default=2)

    class Meta:
        verbose_name = 'Vrai ou Faux'


class CodeOrderExercise(BaseExercise):
    correct_order = models.JSONField(default=list)
    distractor_lines = models.JSONField(default=list, blank=True)

    class Meta:
        verbose_name = 'Ordonner le code'


class MatchingExercise(BaseExercise):
    pairs = models.JSONField(default=list)

    class Meta:
        verbose_name = 'Associations'


class ShortAnswerExercise(BaseExercise):
    question = models.TextField(help_text='Markdown + LaTeX')
    accepted_answers = models.JSONField(default=list)
    case_sensitive = models.BooleanField(default=False)
    is_code_answer = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Réponse courte'


# =============================================================================
# Student progress (SPEC)
# =============================================================================

class ExerciseAttempt(models.Model):
    EXERCISE_TYPES = [
        ('code', 'Code'),
        ('mcq', 'QCM'),
        ('fill_blank', 'Texte à trous'),
        ('true_false', 'Vrai/Faux'),
        ('code_order', 'Ordre code'),
        ('matching', 'Associations'),
        ('short_answer', 'Réponse courte'),
    ]

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='attempts')
    exercise_type = models.CharField(max_length=20, choices=EXERCISE_TYPES)
    exercise_id = models.PositiveIntegerField()
    attempt_number = models.PositiveIntegerField(default=1)
    is_correct = models.BooleanField(default=False)
    points_earned = models.IntegerField(default=0)
    answer_data = models.JSONField(default=dict)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']


class StudentProgress(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='progress')
    exercise_type = models.CharField(max_length=20)
    exercise_id = models.PositiveIntegerField()
    is_solved = models.BooleanField(default=False)
    points_earned = models.IntegerField(default=0)
    attempts = models.PositiveIntegerField(default=0)
    solved_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'exercise_type', 'exercise_id')


# =============================================================================
# Sandbox (kept — used by dashboard + admin sandbox)
# =============================================================================

class UserScript(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_scripts')
    titre = models.CharField(max_length=200, default='Sans titre')
    code = models.TextField(default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

