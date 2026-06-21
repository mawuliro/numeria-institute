"""
Numeria Institute — Formations (REBUILT CLEAN).

This app mirrors the Course structure (Formation / Module / Lesson)
as specified in the rebuild spec.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Formation(models.Model):
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
    thumbnail = models.ImageField(upload_to='formations/thumbnails/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS, default='draft')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_formations',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objectives = models.TextField(blank=True)
    prerequisites = models.TextField(blank=True)
    estimated_hours = models.DecimalField(max_digits=5, decimal_places=1, default=0)

    class Meta:
        verbose_name = 'Formation'
        verbose_name_plural = 'Formations'

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)
            slug = base
            n = 1
            while Formation.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{n}'
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)


class FormationModule(models.Model):
    formation = models.ForeignKey(Formation, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.formation.title} — {self.title}'


class FormationLesson(models.Model):
    formation = models.ForeignKey(Formation, on_delete=models.CASCADE, related_name='lessons')
    module = models.ForeignKey(
        FormationModule,
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

    def __str__(self):
        return f'{self.formation.title} — {self.title}'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


# =============================================================================
# Enrollment (kept for compatibility; used by /mes-notes/ and existing pages)
# =============================================================================

class InscriptionFormation(models.Model):
    STATUTS = [
        ('en_attente', 'En attente'),
        ('confirmee', 'Confirmée'),
        ('en_cours', 'En cours'),
        ('terminee', 'Terminée'),
        ('annulee', 'Annulée'),
    ]

    formation = models.ForeignKey(Formation, on_delete=models.CASCADE, related_name='inscriptions')
    etudiant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='inscriptions_formations')
    statut = models.CharField(max_length=20, choices=STATUTS, default='en_attente')
    progression = models.IntegerField(default=0)
    date_inscription = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('formation', 'etudiant')
        ordering = ['-date_inscription']

