from django.db import migrations


def fix_typo(apps, schema_editor):
    CampagneRecrutement = apps.get_model('admissions', 'CampagneRecrutement')
    for campagne in CampagneRecrutement.objects.all():
        if campagne.description:
            updated = campagne.description.replace(
                'nos capacité', 'nos capacités'
            ).replace(
                'des problème', 'des problèmes'
            )
            if updated != campagne.description:
                campagne.description = updated
                campagne.save()


class Migration(migrations.Migration):

    dependencies = [
        ('admissions', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(fix_typo, migrations.RunPython.noop),
    ]
