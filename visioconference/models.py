import uuid
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string


User = get_user_model()


def generate_room_code():
    return get_random_string(9, allowed_chars='ABCDEFGHJKLMNPQRSTUVWXYZ23456789')


class MeetingRoom(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name='visio_rooms')
    title = models.CharField(max_length=120)
    room_code = models.CharField(max_length=9, unique=True, default=generate_room_code)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    max_participants = models.PositiveSmallIntegerField(default=6)
    password = models.CharField(max_length=128, blank=True)
    waiting_room = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.room_code})"

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        if not self.password:
            return True
        return check_password(raw_password, self.password)

    def active_participants(self):
        return self.participants.filter(left_at__isnull=True, is_approved=True)

    def pending_participants(self):
        return self.participants.filter(left_at__isnull=True, is_approved=False)

    def participant_count(self):
        return self.active_participants().count()

    def has_capacity(self):
        return self.participant_count() < self.max_participants

    @property
    def room_url(self):
        return f'/visio/room/{self.room_code}/'


class MeetingParticipant(models.Model):
    room = models.ForeignKey(MeetingRoom, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='visio_participations')
    display_name = models.CharField(max_length=150)
    peer_id = models.CharField(max_length=64, blank=True)
    joined_at = models.DateTimeField(default=timezone.now)
    left_at = models.DateTimeField(blank=True, null=True)
    is_host = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    is_muted = models.BooleanField(default=False)
    camera_on = models.BooleanField(default=True)
    hand_raised = models.BooleanField(default=False)

    class Meta:
        ordering = ['joined_at']
        unique_together = [['room', 'user', 'peer_id']]

    def __str__(self):
        return f"{self.display_name} ({self.room.room_code})"

    @property
    def active(self):
        return self.left_at is None and self.is_approved


class ChatMessage(models.Model):
    room = models.ForeignKey(MeetingRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='visio_chat_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Message de {self.sender.username} à {self.timestamp:%Y-%m-%d %H:%M}"
