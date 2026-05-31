# Generated manually for ExerciseAttempt + StudentProgress

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cours', '0008_codeexercise_created_at_codeexercise_created_by_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExerciseAttempt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('exercise_type', models.CharField(choices=[('code', 'Code'), ('mcq', 'QCM'), ('fill_blank', 'Texte à trous'), ('true_false', 'Vrai/Faux'), ('code_order', 'Ordre code'), ('matching', 'Associations'), ('short_answer', 'Réponse courte')], max_length=20)),
                ('exercise_id', models.PositiveIntegerField()),
                ('attempt_number', models.PositiveIntegerField(default=1)),
                ('is_correct', models.BooleanField(default=False)),
                ('points_earned', models.IntegerField(default=0)),
                ('answer_data', models.JSONField(blank=True, default=dict)),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='exercise_attempts', to=settings.AUTH_USER_MODEL, verbose_name='Étudiant')),
            ],
            options={
                'verbose_name': 'Tentative exercice',
                'verbose_name_plural': 'Tentatives exercices',
                'ordering': ['-submitted_at'],
            },
        ),
        migrations.CreateModel(
            name='StudentProgress',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('exercise_type', models.CharField(max_length=20)),
                ('exercise_id', models.PositiveIntegerField()),
                ('is_solved', models.BooleanField(default=False)),
                ('points_earned', models.IntegerField(default=0)),
                ('attempts', models.PositiveIntegerField(default=0)),
                ('solved_at', models.DateTimeField(blank=True, null=True)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='student_progress', to=settings.AUTH_USER_MODEL, verbose_name='Étudiant')),
            ],
            options={
                'verbose_name': 'Progression étudiant',
                'verbose_name_plural': 'Progressions étudiants',
                'unique_together': {('student', 'exercise_type', 'exercise_id')},
            },
        ),
        migrations.AddIndex(
            model_name='exerciseattempt',
            index=models.Index(fields=['student', 'exercise_type', 'exercise_id'], name='cours_exerc_student_8a1f2d_idx'),
        ),
        migrations.AddIndex(
            model_name='studentprogress',
            index=models.Index(fields=['student', 'exercise_type'], name='cours_stude_student_3c4e5f_idx'),
        ),
    ]
