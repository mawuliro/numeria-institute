"""
Rename DB columns to match the rebuilt model field names (d96080f).

0001_initial was reset with new field names, but the DB still has the old schema.
This migration runs the actual ALTER TABLE RENAME COLUMN statements.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cours', '0001_initial'),
    ]

    operations = [
        # ── Course ────────────────────────────────────────────────────────────
        migrations.RenameField('Course', 'titre',              'title'),
        migrations.RenameField('Course', 'resume',             'short_description'),
        migrations.RenameField('Course', 'matiere',            'category'),
        migrations.RenameField('Course', 'niveau',             'level'),
        migrations.RenameField('Course', 'est_gratuit',        'is_free'),
        migrations.RenameField('Course', 'prix',               'price'),
        migrations.RenameField('Course', 'date_creation',      'created_at'),
        migrations.RenameField('Course', 'date_modification',  'updated_at'),
        migrations.RenameField('Course', 'duree_estimee_heures', 'estimated_hours'),
        # Add fields that are genuinely new (didn't exist before the rebuild)
        migrations.AddField(
            model_name='course',
            name='language',
            field=models.CharField(
                choices=[('fr', 'Français'), ('en', 'English')],
                default='fr',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='course',
            name='objectives',
            field=models.TextField(blank=True, default=''),
            preserve_default=False,
        ),

        # ── CourseModule ──────────────────────────────────────────────────────
        migrations.RenameField('CourseModule', 'titre', 'title'),
        migrations.RenameField('CourseModule', 'ordre', 'order'),

        # ── CourseLesson ──────────────────────────────────────────────────────
        migrations.RenameField('CourseLesson', 'titre',        'title'),
        migrations.RenameField('CourseLesson', 'ordre',        'order'),
        migrations.RenameField('CourseLesson', 'est_publiee',  'is_active'),
        migrations.RenameField('CourseLesson', 'duree_minutes', 'estimated_minutes'),
    ]
