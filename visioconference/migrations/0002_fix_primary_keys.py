"""
Migration to fix visioconference primary keys from UUID to BigAutoField.

PostgreSQL cannot cast UUID to bigint directly, so we:
1. Drop the old tables (they contain no important data — visio meetings are ephemeral)
2. Recreate them with BigAutoField primary keys

This is safe because MeetingRoom/MeetingParticipant/ChatMessage are ephemeral —
meetings are created and deleted, not long-term data.
"""
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import visioconference.models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('visioconference', '0001_initial'),
    ]

    operations = [
        # Drop all existing tables (ephemeral data — safe to lose)
        migrations.DeleteModel('MeetingRoom'),
        migrations.DeleteModel('MeetingParticipant'),
        migrations.DeleteModel('ChatMessage'),

        # Recreate with BigAutoField (the Django DEFAULT_AUTO_FIELD)
        migrations.CreateModel(
            name='MeetingRoom',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('host', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='visio_rooms', to=settings.AUTH_USER_MODEL)),
                ('title', models.CharField(max_length=120)),
                ('room_code', models.CharField(default=visioconference.models.generate_room_code, max_length=9, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_active', models.BooleanField(default=True)),
                ('max_participants', models.PositiveSmallIntegerField(default=10)),
                ('password', models.CharField(blank=True, max_length=128, null=True)),
                ('waiting_room', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='MeetingParticipant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('room', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='participants', to='visioconference.meetingroom')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='visio_participations', to=settings.AUTH_USER_MODEL)),
                ('joined_at', models.DateTimeField(auto_now_add=True)),
                ('left_at', models.DateTimeField(blank=True, null=True)),
                ('is_host', models.BooleanField(default=False)),
                ('is_approved', models.BooleanField(default=False)),
                ('is_muted', models.BooleanField(default=False)),
                ('camera_on', models.BooleanField(default=True)),
                ('hand_raised', models.BooleanField(default=False)),
                ('peer_id', models.CharField(blank=True, max_length=64)),
                ('display_name', models.CharField(blank=True, max_length=150)),
            ],
            options={
                'ordering': ['joined_at'],
                'unique_together': {('room', 'user', 'peer_id')},
            },
        ),
        migrations.CreateModel(
            name='ChatMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('room', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='visioconference.meetingroom')),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='visio_chat_messages', to=settings.AUTH_USER_MODEL)),
                ('content', models.TextField()),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['timestamp'],
            },
        ),
    ]
