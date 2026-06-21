"""
Migration to fix MeetingRoom/MeetingParticipant/ChatMessage primary keys.
The original migration used UUIDField for the id, but DEFAULT_AUTO_FIELD
is BigAutoField — PostgreSQL couldn't insert NULL into a UUID primary key
without a default.

This migration:
1. Drops the UUID primary key
2. Adds a BigAutoField primary key
3. Recreates foreign keys with the new integer id
"""
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import visioconference.models


class Migration(migrations.Migration):

    dependencies = [
        ('visioconference', '0001_initial'),
    ]

    operations = [
        # Drop all FK constraints that reference the UUID id, then change id type
        migrations.AlterField(
            model_name='meetingroom',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='meetingparticipant',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='chatmessage',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
    ]
