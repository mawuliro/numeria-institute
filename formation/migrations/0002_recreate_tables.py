"""
Drop old formation tables (UUID PK, old field names) and recreate them
with the new schema defined in 0001_initial.

The rebuild commit (d96080f) reset 0001_initial but the DB kept the old
schema, so this migration actually applies those CREATE TABLE statements.
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('formation', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Step 1: Drop everything from the old schema (order matters for FKs)
        migrations.RunSQL(
            sql="""
                DROP TABLE IF EXISTS formation_progressionformationlesson CASCADE;
                DROP TABLE IF EXISTS formation_progressionlecon CASCADE;
                DROP TABLE IF EXISTS formation_certificatformation CASCADE;
                DROP TABLE IF EXISTS formation_inscriptionformation CASCADE;
                DROP TABLE IF EXISTS formation_formationlesson CASCADE;
                DROP TABLE IF EXISTS formation_formationmodule CASCADE;
                DROP TABLE IF EXISTS formation_leconformation CASCADE;
                DROP TABLE IF EXISTS formation_sessionformation CASCADE;
                DROP TABLE IF EXISTS formation_formation_instructeurs CASCADE;
                DROP TABLE IF EXISTS formation_formation CASCADE;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),

        # Step 2: Recreate with the new schema (mirrors 0001_initial operations,
        # but runs DB SQL only — state is already set by 0001_initial).
        migrations.SeparateDatabaseAndState(
            state_operations=[],
            database_operations=[
                migrations.CreateModel(
                    name='Formation',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('title', models.CharField(max_length=300)),
                        ('slug', models.SlugField(blank=True, unique=True)),
                        ('description', models.TextField(blank=True)),
                        ('short_description', models.CharField(blank=True, max_length=300)),
                        ('category', models.CharField(choices=[('mathematiques', 'Mathématiques'), ('physique', 'Physique'), ('informatique', 'Informatique'), ('python', 'Python'), ('ia', 'Intelligence Artificielle'), ('data', 'Data Science'), ('autre', 'Autre')], default='autre', max_length=50)),
                        ('level', models.CharField(choices=[('debutant', 'Débutant'), ('intermediaire', 'Intermédiaire'), ('avance', 'Avancé')], default='debutant', max_length=20)),
                        ('language', models.CharField(choices=[('fr', 'Français'), ('en', 'English')], default='fr', max_length=10)),
                        ('price', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                        ('is_free', models.BooleanField(default=True)),
                        ('thumbnail', models.ImageField(blank=True, null=True, upload_to='formations/thumbnails/')),
                        ('status', models.CharField(choices=[('draft', 'Brouillon'), ('published', 'Publié'), ('archived', 'Archivé')], default='draft', max_length=20)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('updated_at', models.DateTimeField(auto_now=True)),
                        ('objectives', models.TextField(blank=True)),
                        ('prerequisites', models.TextField(blank=True)),
                        ('estimated_hours', models.DecimalField(decimal_places=1, default=0, max_digits=5)),
                        ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_formations', to=settings.AUTH_USER_MODEL)),
                    ],
                    options={'verbose_name': 'Formation', 'verbose_name_plural': 'Formations'},
                ),
                migrations.CreateModel(
                    name='FormationModule',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('title', models.CharField(max_length=300)),
                        ('description', models.TextField(blank=True)),
                        ('order', models.PositiveIntegerField(default=0)),
                        ('is_active', models.BooleanField(default=True)),
                        ('formation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='modules', to='formation.formation')),
                    ],
                    options={'ordering': ['order']},
                ),
                migrations.CreateModel(
                    name='FormationLesson',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('title', models.CharField(max_length=300)),
                        ('slug', models.SlugField(blank=True)),
                        ('order', models.PositiveIntegerField(default=0)),
                        ('is_free_preview', models.BooleanField(default=False)),
                        ('is_active', models.BooleanField(default=True)),
                        ('estimated_minutes', models.PositiveIntegerField(default=10)),
                        ('formation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lessons', to='formation.formation')),
                        ('module', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lessons', to='formation.formationmodule')),
                    ],
                    options={'ordering': ['order']},
                ),
                migrations.CreateModel(
                    name='InscriptionFormation',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('statut', models.CharField(choices=[('en_attente', 'En attente'), ('confirmee', 'Confirmée'), ('en_cours', 'En cours'), ('terminee', 'Terminée'), ('annulee', 'Annulée')], default='en_attente', max_length=20)),
                        ('progression', models.IntegerField(default=0)),
                        ('date_inscription', models.DateTimeField(auto_now_add=True)),
                        ('etudiant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='inscriptions_formations', to=settings.AUTH_USER_MODEL)),
                        ('formation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='inscriptions', to='formation.formation')),
                    ],
                    options={'ordering': ['-date_inscription'], 'unique_together': {('formation', 'etudiant')}},
                ),
            ],
        ),
    ]
