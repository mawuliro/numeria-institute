# ProgressionFormationLesson for CMS formation lessons

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('formation', '0003_formationmodule_formationlesson'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProgressionFormationLesson',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('est_commencee', models.BooleanField(default=False)),
                ('est_terminee', models.BooleanField(default=False)),
                ('date_premiere_visite', models.DateTimeField(auto_now_add=True)),
                ('date_completion', models.DateTimeField(blank=True, null=True)),
                ('formation_lesson', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='progressions', to='formation.formationlesson')),
                ('inscription', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='progressions_cms', to='formation.inscriptionformation')),
            ],
            options={
                'verbose_name': 'Progression leçon CMS',
                'verbose_name_plural': 'Progressions leçons CMS',
                'unique_together': {('inscription', 'formation_lesson')},
            },
        ),
    ]
