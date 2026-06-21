"""
Management command: fix_mecanique_math_inline

In-place fix for the math escape bug in the Mécanique Classique course.

PROBLEM:
  When the course was originally seeded, the seed file used `\\\\vec{F}`
  (4 backslashes in Python source) instead of `\\vec{F}` (2 backslashes).
  After Python parsed the source, the DB stored `\\vec{F}` (2 backslashes),
  which MathJax interprets as LaTeX line-break + literal text "vec{F}"
  instead of the vector symbol.

FIX:
  This command reads every LessonBlock.text_content, MCQExercise.question,
  MCQExercise.explanation, FillBlankExercise.text_with_blanks,
  TrueFalseExercise.statements (JSON), CodeExercise.* fields, and replaces
  every 2-backslash-run-followed-by-a-letter with a 1-backslash run.
  This matches what MathJax expects.

  Effect: `\\vec{F}` → `\vec{F}`, `\\frac{a}{b}` → `\frac{a}{b}`, etc.

  The 2-backslash runs that are NOT followed by a letter (e.g., `\\n` in
  matplotlib titles inside sandbox code) are left alone.

USAGE:
  python manage.py fix_mecanique_math_inline           # dry-run, show stats
  python manage.py fix_mecanique_math_inline --apply    # actually patch DB

Safe to run multiple times — once the DB is fixed, subsequent runs are no-ops.
"""
import json
import re
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from cours.models import (
    Course, CourseModule, CourseLesson, LessonBlock,
    MCQExercise, MCQChoice, FillBlankExercise, TrueFalseExercise,
    CodeExercise,
)

# Match exactly 2 backslashes (not 1, not 3+) followed by a letter.
# In DB-stored strings, "\\vec" should become "\vec".
DB_LATEX_BUG = re.compile(r'(?<!\\)\\\\(?=[a-zA-Z])')

def fix_string(s: str) -> tuple:
    """Replace `\\X` (2 backslashes + letter) with `\\X` (1 backslash + letter).
    Returns (fixed_string, num_replacements)."""
    if not s:
        return s, 0
    new, n = DB_LATEX_BUG.subn(r'\\', s)
    return new, n

class Command(BaseCommand):
    help = "Fix LaTeX double-backslash bug in Mécanique Classique course content (in-place)."

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true',
                            help='Actually write the fixes to the DB (default: dry-run).')
        parser.add_argument('--course-slug', default='mecanique-classique',
                            help='Course slug to fix (default: mecanique-classique).')

    @transaction.atomic
    def handle(self, *args, **opts):
        apply = opts['apply']
        slug = opts['course_slug']

        try:
            course = Course.objects.get(slug=slug)
        except Course.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Course '{slug}' not found."))
            return

        self.stdout.write(self.style.SUCCESS(f"Course: {course.title} (id={course.id})"))
        self.stdout.write(f"Mode: {'APPLY' if apply else 'DRY-RUN (use --apply to write)'}")
        self.stdout.write("")

        total_replacements = 0
        blocks_touched = 0

        # 1. LessonBlock.text_content
        for blk in LessonBlock.objects.filter(course_lesson__course=course):
            if not blk.text_content:
                continue
            new, n = fix_string(blk.text_content)
            if n > 0:
                blocks_touched += 1
                total_replacements += n
                if apply:
                    blk.text_content = new
                    blk.save(update_fields=['text_content'])
                self.stdout.write(f"  Block #{blk.id} ({blk.block_type}): {n} fixes")

        # 2. MCQExercise.question + explanation
        for ex in MCQExercise.objects.filter(course_lesson__course=course):
            touched = False
            new_q, n_q = fix_string(ex.question or '')
            new_e, n_e = fix_string(ex.explanation or '')
            new_inst, n_inst = fix_string(ex.instructions or '')
            new_hint, n_hint = fix_string(ex.hint or '')
            if n_q + n_e + n_inst + n_hint > 0:
                blocks_touched += 1
                total_replacements += n_q + n_e + n_inst + n_hint
                if apply:
                    ex.question = new_q
                    ex.explanation = new_e
                    ex.instructions = new_inst
                    ex.hint = new_hint
                    ex.save(update_fields=['question', 'explanation', 'instructions', 'hint'])
                self.stdout.write(f"  MCQ #{ex.id} '{ex.title[:40]}': q={n_q} exp={n_e} inst={n_inst} hint={n_hint}")
            # MCQChoice.text
            for ch in MCQChoice.objects.filter(exercise=ex):
                new_t, n_t = fix_string(ch.text or '')
                new_f, n_f = fix_string(ch.feedback or '')
                if n_t + n_f > 0:
                    blocks_touched += 1
                    total_replacements += n_t + n_f
                    if apply:
                        ch.text = new_t
                        ch.feedback = new_f
                        ch.save(update_fields=['text', 'feedback'])

        # 3. FillBlankExercise
        for ex in FillBlankExercise.objects.filter(course_lesson__course=course):
            new_t, n_t = fix_string(ex.text_with_blanks or '')
            new_inst, n_inst = fix_string(ex.instructions or '')
            new_exp, n_exp = fix_string(ex.explanation or '')
            new_hint, n_hint = fix_string(ex.hint or '')
            if n_t + n_inst + n_exp + n_hint > 0:
                blocks_touched += 1
                total_replacements += n_t + n_inst + n_exp + n_hint
                if apply:
                    ex.text_with_blanks = new_t
                    ex.instructions = new_inst
                    ex.explanation = new_exp
                    ex.hint = new_hint
                    ex.save(update_fields=['text_with_blanks', 'instructions', 'explanation', 'hint'])

        # 4. TrueFalseExercise.statements (JSON list)
        for ex in TrueFalseExercise.objects.filter(course_lesson__course=course):
            statements = ex.statements or []
            touched = False
            new_statements = []
            for s in statements:
                new_s_text, n_s = fix_string(s.get('statement', ''))
                if n_s > 0:
                    touched = True
                    total_replacements += n_s
                    s2 = dict(s)
                    s2['statement'] = new_s_text
                    new_statements.append(s2)
                else:
                    new_statements.append(s)
            if touched:
                blocks_touched += 1
                if apply:
                    ex.statements = new_statements
                    ex.save(update_fields=['statements'])

        # 5. CodeExercise (starter_code, expected_output, test_code, title, instructions)
        for ex in CodeExercise.objects.filter(course_lesson__course=course):
            fields = ['title', 'instructions', 'starter_code', 'expected_output',
                      'test_code', 'hint', 'solution', 'explanation']
            updates = {}
            for f in fields:
                v = getattr(ex, f, None)
                if v:
                    new_v, n_v = fix_string(v)
                    if n_v > 0:
                        total_replacements += n_v
                        updates[f] = new_v
            if updates:
                blocks_touched += 1
                if apply:
                    for f, v in updates.items():
                        setattr(ex, f, v)
                    ex.save(update_fields=list(updates.keys()))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Done. {total_replacements} LaTeX commands {'fixed' if apply else 'would be fixed'} "
            f"across {blocks_touched} records."
        ))
        if not apply and total_replacements > 0:
            self.stdout.write(self.style.WARNING(
                "Re-run with --apply to actually update the database."
            ))
        elif apply and total_replacements > 0:
            self.stdout.write(self.style.SUCCESS(
                "✓ Database updated. Refresh the lesson page — math should now render correctly."
            ))
        elif total_replacements == 0:
            self.stdout.write(self.style.SUCCESS(
                "✓ No bugs found — content is already correctly escaped."
            ))
