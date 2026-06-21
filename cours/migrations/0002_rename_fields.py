"""
Rename DB columns to match the rebuilt model field names (d96080f).

0001_initial was reset with new field names already in its state, so
RenameField would fail (state has 'title', not 'titre').
We use SeparateDatabaseAndState with RunSQL so only the DB is touched.
"""
from django.db import migrations


def rename_old_cours_columns(apps, schema_editor):
    connection = schema_editor.connection

    def has_column(table_name, column_name):
        cursor = connection.cursor()
        if connection.vendor == 'sqlite':
            cursor.execute(f"PRAGMA table_info({table_name})")
            return any(row[1] == column_name for row in cursor.fetchall())

        cursor.execute(
            "SELECT 1 FROM information_schema.columns WHERE table_name=%s AND column_name=%s",
            [table_name, column_name],
        )
        return cursor.fetchone() is not None

    def execute(sql, params=None):
        cursor = connection.cursor()
        cursor.execute(sql, params or [])

    def rename_column(table, old_name, new_name):
        if has_column(table, old_name) and not has_column(table, new_name):
            execute(f"ALTER TABLE {table} RENAME COLUMN {old_name} TO {new_name}")

    def add_column_if_missing(table, column_name, column_sql):
        if not has_column(table, column_name):
            execute(f"ALTER TABLE {table} ADD COLUMN {column_sql}")

    rename_column('cours_course', 'titre', 'title')
    rename_column('cours_course', 'resume', 'short_description')
    rename_column('cours_course', 'matiere', 'category')
    rename_column('cours_course', 'niveau', 'level')
    rename_column('cours_course', 'est_gratuit', 'is_free')
    rename_column('cours_course', 'prix', 'price')
    rename_column('cours_course', 'date_creation', 'created_at')
    rename_column('cours_course', 'date_modification', 'updated_at')
    rename_column('cours_course', 'duree_estimee_heures', 'estimated_hours')
    add_column_if_missing('cours_course', 'language', "language VARCHAR(10) NOT NULL DEFAULT 'fr'")
    add_column_if_missing('cours_course', 'objectives', "objectives TEXT NOT NULL DEFAULT ''")

    rename_column('cours_coursemodule', 'titre', 'title')
    rename_column('cours_coursemodule', 'ordre', '"order"')

    rename_column('cours_courselesson', 'titre', 'title')
    rename_column('cours_courselesson', 'ordre', '"order"')
    rename_column('cours_courselesson', 'est_publiee', 'is_active')
    rename_column('cours_courselesson', 'duree_minutes', 'estimated_minutes')


class Migration(migrations.Migration):

    dependencies = [
        ('cours', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[],   # state is already correct from 0001_initial
            database_operations=[
                migrations.RunPython(rename_old_cours_columns, reverse_code=migrations.RunPython.noop),
            ],
        ),
    ]
