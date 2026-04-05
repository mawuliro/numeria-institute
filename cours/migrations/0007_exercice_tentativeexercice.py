# Migration générée manuellement pour les modèles Exercice et TentativeExercice
# Dépend de la migration 0006 (alter_cours_classe)

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cours', '0006_alter_cours_classe'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Exercice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name='ID')),
                ('question', models.TextField(
                    help_text='Supporte le LaTeX. Ex: Calculer $x^2 + 2x + 1$',
                    verbose_name='Question'
                )),
                ('choix_a', models.CharField(max_length=500, verbose_name='Choix A')),
                ('choix_b', models.CharField(max_length=500, verbose_name='Choix B')),
                ('choix_c', models.CharField(max_length=500, verbose_name='Choix C')),
                ('choix_d', models.CharField(max_length=500, verbose_name='Choix D')),
                ('bonne_reponse', models.CharField(
                    choices=[('A', 'Choix A'), ('B', 'Choix B'),
                             ('C', 'Choix C'), ('D', 'Choix D')],
                    max_length=1,
                    verbose_name='Bonne réponse'
                )),
                ('corrige', models.TextField(
                    help_text='Explication complète. Supporte le LaTeX et le code HTML.',
                    verbose_name='Corrigé détaillé'
                )),
                ('ordre',  models.IntegerField(default=1, verbose_name='Ordre')),
                ('points', models.IntegerField(default=1, verbose_name='Points')),
                ('est_actif', models.BooleanField(default=True, verbose_name='Actif')),
                ('lecon', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='exercices',
                    to='cours.lecon'
                )),
            ],
            options={
                'verbose_name': 'Exercice',
                'verbose_name_plural': 'Exercices',
                'ordering': ['lecon', 'ordre'],
            },
        ),
        migrations.CreateModel(
            name='TentativeExercice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name='ID')),
                ('reponse_choisie', models.CharField(max_length=1)),
                ('est_correcte',    models.BooleanField(default=False)),
                ('date_tentative',  models.DateTimeField(auto_now_add=True)),
                ('numero_tentative', models.IntegerField(default=1)),
                ('etudiant', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='tentatives',
                    to=settings.AUTH_USER_MODEL
                )),
                ('exercice', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='tentatives',
                    to='cours.exercice'
                )),
            ],
            options={
                'verbose_name': 'Tentative',
                'verbose_name_plural': 'Tentatives',
                'ordering': ['-date_tentative'],
            },
        ),
    ]