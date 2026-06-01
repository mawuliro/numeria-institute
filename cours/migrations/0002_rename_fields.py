"""
Rename DB columns to match the rebuilt model field names (d96080f).

0001_initial was reset with new field names already in its state, so
RenameField would fail (state has 'title', not 'titre').
We use SeparateDatabaseAndState with RunSQL so only the DB is touched.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cours', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[],   # state is already correct from 0001_initial
            database_operations=[
                migrations.RunSQL(sql="""
                    -- Course
                    ALTER TABLE cours_course RENAME COLUMN titre              TO title;
                    ALTER TABLE cours_course RENAME COLUMN resume             TO short_description;
                    ALTER TABLE cours_course RENAME COLUMN matiere            TO category;
                    ALTER TABLE cours_course RENAME COLUMN niveau             TO level;
                    ALTER TABLE cours_course RENAME COLUMN est_gratuit        TO is_free;
                    ALTER TABLE cours_course RENAME COLUMN prix               TO price;
                    ALTER TABLE cours_course RENAME COLUMN date_creation      TO created_at;
                    ALTER TABLE cours_course RENAME COLUMN date_modification  TO updated_at;
                    ALTER TABLE cours_course RENAME COLUMN duree_estimee_heures TO estimated_hours;

                    -- Add genuinely new columns (did not exist before the rebuild)
                    ALTER TABLE cours_course
                        ADD COLUMN IF NOT EXISTS language    VARCHAR(10) NOT NULL DEFAULT 'fr',
                        ADD COLUMN IF NOT EXISTS objectives  TEXT        NOT NULL DEFAULT '';

                    -- CourseModule
                    ALTER TABLE cours_coursemodule RENAME COLUMN titre TO title;
                    ALTER TABLE cours_coursemodule RENAME COLUMN ordre TO "order";

                    -- CourseLesson
                    ALTER TABLE cours_courselesson RENAME COLUMN titre        TO title;
                    ALTER TABLE cours_courselesson RENAME COLUMN ordre        TO "order";
                    ALTER TABLE cours_courselesson RENAME COLUMN est_publiee  TO is_active;
                    ALTER TABLE cours_courselesson RENAME COLUMN duree_minutes TO estimated_minutes;
                """,
                reverse_sql=migrations.RunSQL.noop),
            ],
        ),
    ]
