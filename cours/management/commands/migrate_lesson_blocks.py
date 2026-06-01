"""
Management command: migrate_lesson_blocks

Converts existing lesson content (text + video_url) and linked
CodeExercise objects into ordered LessonBlock records.

Run after the 0006_lessonblock migration:
    python manage.py migrate_lesson_blocks

Idempotent: skips lessons that already have blocks.
"""
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'Convert existing lesson content and exercises into LessonBlock records.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Show what would be done without actually creating blocks.',
        )
        parser.add_argument(
            '--formation-lessons', action='store_true',
            help='Also migrate FormationLesson objects.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        do_formations = options['formation_lessons']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no changes will be saved.\n'))

        total_lessons  = 0
        total_blocks   = 0
        skipped        = 0

        # ── COURSE LESSONS (Lecon) ─────────────────────────────────────────
        from cours.models import CourseLesson, LessonBlock, CodeExercise

        self.stdout.write('Migrating Course lessons (Lecon)…')
        for lecon in CourseLesson.objects.all():
            # Skip if already has blocks
            if LessonBlock.objects.filter(course_lesson=lecon).exists():
                skipped += 1
                continue

            has_content = bool(lecon.contenu and lecon.contenu.strip())
            has_video   = bool(lecon.video_youtube)
            exercises   = CodeExercise.objects.filter(
                course_lesson=lecon, is_active=True
            ).order_by('order')

            if not has_content and not has_video and not exercises.exists():
                skipped += 1
                continue

            blocks_for_lesson = []
            order = 0

            if has_video and not has_content:
                # Video-only lesson
                blocks_for_lesson.append(dict(
                    course_lesson=lecon, block_type='video',
                    order=order, video_url=lecon.video_youtube,
                ))
                order += 1
            elif has_content and has_video:
                # Text first, then video
                blocks_for_lesson.append(dict(
                    course_lesson=lecon, block_type='text',
                    order=order, text_content=lecon.contenu,
                ))
                order += 1
                blocks_for_lesson.append(dict(
                    course_lesson=lecon, block_type='video',
                    order=order, video_url=lecon.video_youtube,
                ))
                order += 1
            elif has_content:
                blocks_for_lesson.append(dict(
                    course_lesson=lecon, block_type='text',
                    order=order, text_content=lecon.contenu,
                ))
                order += 1

            # Exercises → exercise blocks
            for ex in exercises:
                blocks_for_lesson.append(dict(
                    course_lesson=lecon, block_type='exercise',
                    order=order, exercise=ex,
                ))
                order += 1

            if not dry_run:
                for bd in blocks_for_lesson:
                    LessonBlock.objects.create(**bd)

            total_lessons += 1
            total_blocks  += len(blocks_for_lesson)
            self.stdout.write(
                f'  [{lecon.course.title}] {lecon.title} → '
                f'{len(blocks_for_lesson)} bloc(s)'
            )

        # ── FORMATION LESSONS (FormationLesson) ───────────────────────────
        if do_formations:
            from formation.models import FormationLesson

            self.stdout.write('\nMigrating Formation lessons (FormationLesson)…')
            for fl in FormationLesson.objects.all():
                if LessonBlock.objects.filter(formation_lesson=fl).exists():
                    skipped += 1
                    continue

                has_content = bool(fl.contenu and fl.contenu.strip())
                has_video   = bool(fl.video_url)
                exercises   = CodeExercise.objects.filter(
                    formation_lesson=fl, is_active=True
                ).order_by('order')

                if not has_content and not has_video and not exercises.exists():
                    skipped += 1
                    continue

                blocks_for_lesson = []
                order = 0

                if has_video and not has_content:
                    blocks_for_lesson.append(dict(
                        formation_lesson=fl, block_type='video',
                        order=order, video_url=fl.video_url,
                    ))
                    order += 1
                elif has_content and has_video:
                    blocks_for_lesson.append(dict(
                        formation_lesson=fl, block_type='text',
                        order=order, text_content=fl.contenu,
                    ))
                    order += 1
                    blocks_for_lesson.append(dict(
                        formation_lesson=fl, block_type='video',
                        order=order, video_url=fl.video_url,
                    ))
                    order += 1
                elif has_content:
                    blocks_for_lesson.append(dict(
                        formation_lesson=fl, block_type='text',
                        order=order, text_content=fl.contenu,
                    ))
                    order += 1

                for ex in exercises:
                    blocks_for_lesson.append(dict(
                        formation_lesson=fl, block_type='exercise',
                        order=order, exercise=ex,
                    ))
                    order += 1

                if not dry_run:
                    for bd in blocks_for_lesson:
                        LessonBlock.objects.create(**bd)

                total_lessons += 1
                total_blocks  += len(blocks_for_lesson)
                self.stdout.write(
                    f'  [{fl.formation.title}] {fl.title} → '
                    f'{len(blocks_for_lesson)} bloc(s)'
                )

        # ── SUMMARY ───────────────────────────────────────────────────────
        self.stdout.write('')
        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'DRY RUN — would create {total_blocks} bloc(s) '
                f'across {total_lessons} leçon(s). '
                f'{skipped} skipped (already have blocks or no content).'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'✓ {total_blocks} bloc(s) créé(s) '
                f'dans {total_lessons} leçon(s). '
                f'{skipped} ignoré(s).'
            ))
