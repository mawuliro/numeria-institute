from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class StaffActivityLog(models.Model):
    ACTION_TYPES = [
        ('contact_replied',      _('Réponse contact')),
        ('candidacy_accepted',   _('Candidature acceptée')),
        ('candidacy_rejected',   _('Candidature rejetée')),
        ('candidacy_waitlisted', _('Candidature en attente')),
        ('candidacy_reviewing',  _('Candidature en revue')),
        ('mentorship_accepted',  _('Mentorat accepté')),
        ('mentorship_rejected',  _('Mentorat rejeté')),
        ('user_activated',       _('Utilisateur activé')),
        ('user_deactivated',     _('Utilisateur désactivé')),
        ('notification_sent',    _('Notification envoyée')),
    ]

    performed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='staff_actions', verbose_name=_('Effectué par'),
    )
    action_type = models.CharField(
        max_length=50, choices=ACTION_TYPES, verbose_name=_('Type d\'action'),
    )
    description = models.TextField(verbose_name=_('Description'))
    target_user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='activity_logs', verbose_name=_('Utilisateur concerné'),
    )
    performed_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Date'))

    class Meta:
        ordering = ['-performed_at']
        verbose_name = _('Journal d\'activité')
        verbose_name_plural = _('Journal d\'activités')

    def __str__(self):
        by = self.performed_by.username if self.performed_by else '?'
        return f"[{self.action_type}] {by} — {self.performed_at:%Y-%m-%d %H:%M}"


class ContactReply(models.Model):
    contact_message = models.ForeignKey(
        'pages.ContactMessage', on_delete=models.CASCADE,
        related_name='replies', verbose_name=_('Message de contact'),
    )
    replied_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        verbose_name=_('Répondu par'),
    )
    subject = models.CharField(max_length=300, verbose_name=_('Sujet'))
    message = models.TextField(verbose_name=_('Message'))
    replied_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Envoyé le'))

    class Meta:
        ordering = ['replied_at']
        verbose_name = _('Réponse contact')
        verbose_name_plural = _('Réponses contact')

    def __str__(self):
        by = self.replied_by.get_full_name() if self.replied_by else '?'
        return f"Réponse de {by} à #{self.contact_message_id}"


class UploadedMedia(models.Model):
    MEDIA_TYPES = [
        ('image', _('Image')),
        ('pdf',   _('PDF')),
        ('other', _('Autre')),
    ]
    file        = models.FileField(upload_to='uploads/media/', verbose_name=_('Fichier'))
    name        = models.CharField(max_length=200, verbose_name=_('Nom'))
    media_type  = models.CharField(max_length=20, choices=MEDIA_TYPES, default='image')
    uploaded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name=_('Uploadé par'),
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Uploadé le'))
    file_size   = models.BigIntegerField(default=0, verbose_name=_('Taille (octets)'))

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = _('Média uploadé')
        verbose_name_plural = _('Médias uploadés')

    def __str__(self):
        return self.name

    @property
    def url(self):
        return self.file.url if self.file else ''


class ContentVersion(models.Model):
    """Snapshot pour la récupération de brouillon (auto-save)."""
    CONTENT_TYPES = [('cours', 'Cours'), ('article', 'Article'), ('lecon', 'Leçon')]
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES)
    object_id    = models.IntegerField()
    version_data = models.JSONField()
    created_by   = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Version de contenu'
        verbose_name_plural = 'Versions de contenu'

    def __str__(self):
        return f"{self.content_type} #{self.object_id} — {self.created_at:%Y-%m-%d %H:%M}"
