"""Unified exercise attempt and progress tracking."""
from django.utils import timezone

EXERCISE_TYPE_MAP = {
    'CodeExercise': 'code',
    'MCQExercise': 'mcq',
    'FillBlankExercise': 'fill_blank',
    'TrueFalseExercise': 'true_false',
    'CodeOrderExercise': 'code_order',
    'MatchingExercise': 'matching',
    'ShortAnswerExercise': 'short_answer',
}


def exercise_type_for(exercise):
    return EXERCISE_TYPE_MAP.get(exercise.__class__.__name__, 'code')


def record_submission(student, exercise, is_correct, points_earned=0, answer_data=None):
    """
    Record one submission: ExerciseAttempt row + StudentProgress update.
    Returns (progress, newly_solved).
    """
    from .models import ExerciseAttempt, StudentProgress

    ex_type = exercise_type_for(exercise)
    ex_id = exercise.pk

    progress, _ = StudentProgress.objects.get_or_create(
        student=student,
        exercise_type=ex_type,
        exercise_id=ex_id,
        defaults={'attempts': 0},
    )
    progress.attempts += 1
    newly_solved = False

    if is_correct and not progress.is_solved:
        progress.is_solved = True
        progress.points_earned = points_earned
        progress.solved_at = timezone.now()
        newly_solved = True

    progress.save()

    ExerciseAttempt.objects.create(
        student=student,
        exercise_type=ex_type,
        exercise_id=ex_id,
        attempt_number=progress.attempts,
        is_correct=is_correct,
        points_earned=points_earned if is_correct else 0,
        answer_data=answer_data or {},
    )

    return progress, newly_solved
