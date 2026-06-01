from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cours', '0010_rename_course_schema'),
    ]

    operations = [
        migrations.RenameField(
            model_name='questionfaq',
            old_name='cours',
            new_name='course',
        ),
    ]
