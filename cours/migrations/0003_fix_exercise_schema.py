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

# Build the ADD COLUMN IF NOT EXISTS statements for BaseExercise inherited fields
_ADD_BASE_FIELDS = '\n'.join(
    f"""
    ALTER TABLE {t} ADD COLUMN IF NOT EXISTS instructions      TEXT    NOT NULL DEFAULT '';
    ALTER TABLE {t} ADD COLUMN IF NOT EXISTS max_attempts      INTEGER NOT NULL DEFAULT 0;
    ALTER TABLE {t} ADD COLUMN IF NOT EXISTS hint              TEXT    NOT NULL DEFAULT '';
    ALTER TABLE {t} ADD COLUMN IF NOT EXISTS explanation       TEXT    NOT NULL DEFAULT '';
    ALTER TABLE {t} ADD COLUMN IF NOT EXISTS formation_lesson_id BIGINT
        REFERENCES formation_formationlesson(id) ON DELETE CASCADE;
    """
    for t in _EXERCISE_TABLES
)

# Rename LessonBlock FKs using a PL/pgSQL DO block (safe even if already renamed)
_RENAME_LESSON_BLOCK_FKS = """
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'cours_lessonblock'
          AND column_name = 'fill_blank_exercise_id'
    ) THEN
        ALTER TABLE cours_lessonblock
            RENAME COLUMN fill_blank_exercise_id TO fill_blank_id;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'cours_lessonblock'
          AND column_name = 'true_false_exercise_id'
    ) THEN
        ALTER TABLE cours_lessonblock
            RENAME COLUMN true_false_exercise_id TO true_false_id;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'cours_lessonblock'
          AND column_name = 'code_order_exercise_id'
    ) THEN
        ALTER TABLE cours_lessonblock
            RENAME COLUMN code_order_exercise_id TO code_order_id;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'cours_lessonblock'
          AND column_name = 'matching_exercise_id'
    ) THEN
        ALTER TABLE cours_lessonblock
            RENAME COLUMN matching_exercise_id TO matching_id;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'cours_lessonblock'
          AND column_name = 'short_answer_exercise_id'
    ) THEN
        ALTER TABLE cours_lessonblock
            RENAME COLUMN short_answer_exercise_id TO short_answer_id;
    END IF;
END $$;
"""

# MCQChoice extra columns
_MCQCHOICE_FIELDS = """
    ALTER TABLE cours_mcqchoice ADD COLUMN IF NOT EXISTS feedback TEXT    NOT NULL DEFAULT '';
    ALTER TABLE cours_mcqchoice ADD COLUMN IF NOT EXISTS "order"  INTEGER NOT NULL DEFAULT 0;
"""

# Extra fields that might be missing from specific exercise tables
_SPECIFIC_FIELDS = """
    ALTER TABLE cours_fillblankexercise
        ADD COLUMN IF NOT EXISTS case_sensitive BOOLEAN NOT NULL DEFAULT FALSE;

    ALTER TABLE cours_shortanswerexercise
        ADD COLUMN IF NOT EXISTS is_code_answer BOOLEAN NOT NULL DEFAULT FALSE;

    ALTER TABLE cours_mcqexercise
        ADD COLUMN IF NOT EXISTS shuffle_choices BOOLEAN NOT NULL DEFAULT TRUE;
"""


class Migration(migrations.Migration):

    dependencies = [
        ('cours', '0002_rename_fields'),
        ('formation', '0002_recreate_tables'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[],
            database_operations=[
                migrations.RunSQL(
                    sql=_ADD_BASE_FIELDS + _RENAME_LESSON_BLOCK_FKS + _MCQCHOICE_FIELDS + _SPECIFIC_FIELDS,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
        ),
    ]
