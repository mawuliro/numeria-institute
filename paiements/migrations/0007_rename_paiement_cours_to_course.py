from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('paiements', '0006_add_missing_indexes'),
    ]

    operations = [
        migrations.RenameField(
            model_name='paiement',
            old_name='cours',
            new_name='course',
        ),
        migrations.AlterField(
            model_name='paiement',
            name='course',
            field=models.ForeignKey(
                'cours.Course',
                on_delete=django.db.models.deletion.SET_NULL,
                null=True,
                blank=True,
                related_name='paiements',
                db_column='cours_id',
            ),
        ),
    ]
