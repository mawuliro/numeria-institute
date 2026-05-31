from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('paiements', '0001_initial'),
        ('cours', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paiement',
            name='cours',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='paiements',
                to='cours.Cours',
            ),
        ),
    ]