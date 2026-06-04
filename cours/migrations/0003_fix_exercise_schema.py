"""
Fix exercise table schema mismatches caused by the d96080f migration reset.

Three classes of problems:
1. BaseExercise gained fields (instructions, max_attempts, hint, explanation,
   formation_lesson) after the original 0001_initial — those migrations were
   squashed, leaving the columns absent.
2. LessonBlock FK names shortened: fill_blank_exercise→fill_blank, etc.
3. MCQChoice gained feedback + order columns.

All operations use IF NOT EXISTS / DO-block guards so this is idempotent.
"""
from django.db import migrations

_EXERCISE_TABLES = [
    'cours_codeexercise',
    'cours_mcqexercise',
    'cours_fillblankexercise',
    'cours_truefalseexercise',
    'cours_codeorderexercise',
    'cours_matchingexercise',
    'cours_shortanswerexercise',
]


def apply_exercise_schema_fixes(apps, schema_editor):
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

    def add_column(table_name, column_name, column_sql):
        if not has_column(table_name, column_name):
            execute(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}")

    def rename_column(table_name, old_name, new_name):
        if has_column(table_name, old_name) and not has_column(table_name, new_name):
            execute(f"ALTER TABLE {table_name} RENAME COLUMN {old_name} TO {new_name}")

    for table in _EXERCISE_TABLES:
        add_column(table, 'instructions', "instructions TEXT NOT NULL DEFAULT ''")
        add_column(table, 'max_attempts', 'max_attempts INTEGER NOT NULL DEFAULT 0')
        add_column(table, 'hint', "hint TEXT NOT NULL DEFAULT ''")
        add_column(table, 'explanation', "explanation TEXT NOT NULL DEFAULT ''")
        add_column(
            table,
            'formation_lesson_id',
            'formation_lesson_id BIGINT REFERENCES formation_formationlesson(id) ON DELETE CASCADE',
        )

    rename_column('cours_lessonblock', 'fill_blank_exercise_id', 'fill_blank_id')
    rename_column('cours_lessonblock', 'true_false_exercise_id', 'true_false_id')
    rename_column('cours_lessonblock', 'code_order_exercise_id', 'code_order_id')
    rename_column('cours_lessonblock', 'matching_exercise_id', 'matching_id')
    rename_column('cours_lessonblock', 'short_answer_exercise_id', 'short_answer_id')

    add_column('cours_mcqchoice', 'feedback', "feedback TEXT NOT NULL DEFAULT ''")
    add_column('cours_mcqchoice', 'order', '"order" INTEGER NOT NULL DEFAULT 0')

    add_column('cours_fillblankexercise', 'case_sensitive', 'case_sensitive BOOLEAN NOT NULL DEFAULT FALSE')
    add_column('cours_shortanswerexercise', 'is_code_answer', 'is_code_answer BOOLEAN NOT NULL DEFAULT FALSE')
    add_column('cours_mcqexercise', 'shuffle_choices', 'shuffle_choices BOOLEAN NOT NULL DEFAULT TRUE')


class Migration(migrations.Migration):

    dependencies = [
        ('cours', '0002_rename_fields'),
        ('formation', '0002_recreate_tables'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[],
            database_operations=[
                migrations.RunPython(apply_exercise_schema_fixes, reverse_code=migrations.RunPython.noop),
            ],
        ),
    ]
