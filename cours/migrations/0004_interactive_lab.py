# Generated for the QM-LAB-FRAMEWORK task — InteractiveLab + LabProgress models
# and the new 'interactive_lab' LessonBlock type.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cours', '0003_fix_exercise_schema'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. Create the InteractiveLab model (inherits from BaseExercise which
        #    is abstract — the inherited fields are inlined into the new table).
        migrations.CreateModel(
            name='InteractiveLab',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                # Inherited BaseExercise fields (abstract base — inlined here)
                ('title', models.CharField(max_length=200)),
                ('instructions', models.TextField(blank=True, help_text='Markdown + LaTeX + HTML')),
                ('difficulty', models.CharField(max_length=20, default='medium')),
                ('points', models.IntegerField(default=20)),
                ('max_attempts', models.IntegerField(default=0, help_text='0 = illimité')),
                ('hint', models.TextField(blank=True)),
                ('explanation', models.TextField(blank=True)),
                ('order', models.IntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                # InteractiveLab-specific fields
                ('simulation_code', models.TextField(help_text='Code Python (Pyodide) qui définit une fonction simulate(params) retournant un dict de résultats')),
                ('slider_config', models.JSONField(default=list, help_text='Liste de sliders [{name, label, min, max, step, default, unit}]')),
                ('challenges', models.JSONField(default=list, help_text='Liste ordonnée de challenges adaptatifs')),
                # Inherited FKs
                ('course_lesson', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(class)s_set', to='cours.courselesson')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created', to=settings.AUTH_USER_MODEL)),
                ('formation_lesson', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(class)s_set', to='formation.formationlesson')),
            ],
            options={
                'verbose_name': 'Lab interactif',
                'verbose_name_plural': 'Labs interactifs',
            },
        ),

        # 2. Create the LabProgress model.
        migrations.CreateModel(
            name='LabProgress',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('current_challenge_id', models.CharField(default='', max_length=50)),
                ('challenges_solved', models.JSONField(default=list)),
                ('attempts', models.IntegerField(default=0)),
                ('is_completed', models.BooleanField(default=False)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lab_progress', to=settings.AUTH_USER_MODEL)),
                ('lab', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='progress', to='cours.interactivelab')),
            ],
            options={
                'verbose_name': 'Progression de lab',
                'verbose_name_plural': 'Progressions de lab',
                'unique_together': {('student', 'lab')},
                'ordering': ['-updated_at'],
            },
        ),

        # 3. Add the new block_type choice + interactive_lab FK on LessonBlock.
        migrations.AlterField(
            model_name='lessonblock',
            name='block_type',
            field=models.CharField(
                choices=[
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
                    ('interactive_lab', 'Lab interactif'),
                ],
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name='lessonblock',
            name='interactive_lab',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='blocks',
                to='cours.interactivelab',
            ),
        ),
    ]
