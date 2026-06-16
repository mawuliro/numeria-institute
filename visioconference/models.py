import string
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string


def generate_room_code():
    return get_random_string(length=9, allowed_chars='ABCDEFGHJKLMNPQRSTUVWXYZ23456789')


class MeetingRoom(models.Model):
    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='visio_rooms')
    title = models.CharField(max_length=120)
    room_code = models.CharField(max_length=9, unique=True, default=generate_room_code)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    max_participants = models.PositiveSmallIntegerField(default=10)
    password = models.CharField(max_length=128, blank=True, null=True)
    waiting_room = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.room_code})"

    def get_absolute_url(self):
        return reverse('visioconference:meeting_room', kwargs={'room_code': self.room_code})

    @staticmethod
    def generate_room_code():
        return generate_room_code()

    def has_capacity(self):
        return self.participants.filter(left_at__isnull=True, is_approved=True).count() < self.max_participants


class MeetingParticipant(models.Model):
    room = models.ForeignKey(MeetingRoom, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='visio_participations')
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(blank=True, null=True)
    is_host = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    is_muted = models.BooleanField(default=False)
    camera_on = models.BooleanField(default=True)
    hand_raised = models.BooleanField(default=False)
    peer_id = models.CharField(max_length=64, blank=True)
    display_name = models.CharField(max_length=150, blank=True)

    class Meta:
        ordering = ['joined_at']
        unique_together = [['room', 'user', 'peer_id']]

    def __str__(self):
        return f"{self.display_name or self.user.get_full_name() or self.user.username} ({self.room.room_code})"

    @property
    def active(self):
        return self.left_at is None


class ChatMessage(models.Model):
    room = models.ForeignKey(MeetingRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='visio_chat_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Message de {self.sender.username} à {self.timestamp:%Y-%m-%d %H:%M}"
