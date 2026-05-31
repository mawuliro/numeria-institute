# Phase A — rename Cours/Module/Lecon models and unify course_lesson FKs

import django.db.models.deletion
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cours', '0009_exerciseattempt_studentprogress'),
    ]

    operations = [
        # ── Model renames ────────────────────────────────────────────────────
        migrations.RenameModel(old_name='Cours', new_name='Course'),
        migrations.RenameModel(old_name='Module', new_name='CourseModule'),
        migrations.RenameModel(old_name='Lecon', new_name='CourseLesson'),

        # ── CourseModule / CourseLesson FK renames ───────────────────────────
        migrations.RenameField(model_name='coursemodule', old_name='cours', new_name='course'),
        migrations.RenameField(model_name='courselesson', old_name='cours', new_name='course'),

        # ── Inscription / evaluation / certificate FK renames ────────────────
        migrations.RenameField(model_name='inscriptioncours', old_name='cours', new_name='course'),
        migrations.RenameField(model_name='evaluationcours', old_name='cours', new_name='course'),
        migrations.RenameField(model_name='certificatcours', old_name='cours', new_name='course'),

        # ── lecon → course_lesson ────────────────────────────────────────────
        migrations.RenameField(model_name='progressionlecon', old_name='lecon', new_name='course_lesson'),
        migrations.RenameField(model_name='exercice', old_name='lecon', new_name='course_lesson'),
        migrations.RenameField(model_name='codeexercise', old_name='lecon', new_name='course_lesson'),

        # ── lesson → course_lesson (newer exercise models) ───────────────────
        migrations.RenameField(model_name='lessonblock', old_name='lesson', new_name='course_lesson'),
        migrations.RenameField(model_name='mcqexercise', old_name='lesson', new_name='course_lesson'),
        migrations.RenameField(model_name='fillblankexercise', old_name='lesson', new_name='course_lesson'),
        migrations.RenameField(model_name='truefalseexercise', old_name='lesson', new_name='course_lesson'),
        migrations.RenameField(model_name='codeorderexercise', old_name='lesson', new_name='course_lesson'),
        migrations.RenameField(model_name='matchingexercise', old_name='lesson', new_name='course_lesson'),
        migrations.RenameField(model_name='shortanswerexercise', old_name='lesson', new_name='course_lesson'),

        # ── LessonBlock exercise → code_exercise ─────────────────────────────
        migrations.RenameField(model_name='lessonblock', old_name='exercise', new_name='code_exercise'),

        # ── unique_together updates ──────────────────────────────────────────
        migrations.AlterUniqueTogether(
            name='inscriptioncours',
            unique_together={('etudiant', 'course')},
        ),
        migrations.AlterUniqueTogether(
            name='evaluationcours',
            unique_together={('etudiant', 'course')},
        ),
        migrations.AlterUniqueTogether(
            name='certificatcours',
            unique_together={('etudiant', 'course')},
        ),
        migrations.AlterUniqueTogether(
            name='progressionlecon',
            unique_together={('etudiant', 'course_lesson')},
        ),
    ]
