from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cours', '0011_rename_questionfaq_course_field'),
    ]

    operations = [
        migrations.AddField(
            model_name='codeexercise',
            name='explanation',
            field=models.TextField(blank=True, default='', verbose_name='Explication'),
            preserve_default=False,
        ),
    ]
