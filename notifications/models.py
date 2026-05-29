from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
    TYPES = [
        ('info',        _('Information')),
        ('success',     _('Succès')),
        ('warning',     _('Avertissement')),
        ('alert',       _('Alerte')),
        ('course',      _('Cours')),
        ('payment',     _('Paiement')),
        ('mentorship',  _('Mentorat')),
        ('candidacy',   _('Candidature')),
        ('broadcast',   _('Annonce générale')),
    ]

    # null recipient = broadcast to all users
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,
        blank=True,
        verbose_name=_('Destinataire'),
    )
    notification_type = models.CharField(
        max_length=50,
        choices=TYPES,
        default='info',
        verbose_name=_('Type'),
    )
    title = models.CharField(max_length=300, verbose_name=_('Titre'))
    message = models.TextField(verbose_name=_('Message'))
    link = models.CharField(max_length=500, blank=True, null=True, verbose_name=_('Lien (CTA)'))
    is_read = models.BooleanField(default=False, verbose_name=_('Lu'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Date'))
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_notifications',
        verbose_name=_('Envoyé par'),
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')

    def __str__(self):
        dest = self.recipient.username if self.recipient else 'broadcast'
        return f"[{self.notification_type}] {self.title} → {dest}"
