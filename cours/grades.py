"""
Grade computation helpers for all exercise types.
"""
from django.db.models import Sum


def _get_exercises_for_block_context(course_lesson=None, formation_lesson=None):
    """
    Returns a flat dict mapping exercise_type → list of exercise objects
    for a given lesson (course or formation).
    Used to compute total_points_possible.
    """
    from .models import (
        CodeExercise, MCQExercise,
        FillBlankExercise, TrueFalseExercise,
        CodeOrderExercise, MatchingExercise, ShortAnswerExercise,
    )
    result = {}
    kw = {'course_lesson': course_lesson} if course_lesson else {'formation_lesson': formation_lesson}
    result['code']         = list(CodeExercise.objects.filter(is_active=True, **kw))
    result['mcq']          = list(MCQExercise.objects.filter(is_active=True, **kw))
    result['fill_blank']   = list(FillBlankExercise.objects.filter(is_active=True, **kw))
    result['true_false']   = list(TrueFalseExercise.objects.filter(is_active=True, **kw))
    result['code_order']   = list(CodeOrderExercise.objects.filter(is_active=True, **kw))
    result['matching']     = list(MatchingExercise.objects.filter(is_active=True, **kw))
    result['short_answer'] = list(ShortAnswerExercise.objects.filter(is_active=True, **kw))
    return result


def get_lesson_total_points(course_lesson=None, formation_lesson=None):
    """Return the maximum points achievable for a lesson across all exercise types."""
    exercises = _get_exercises_for_block_context(course_lesson, formation_lesson)
    total = 0
    for exs in exercises.values():
        for ex in exs:
            if hasattr(ex, 'points'):
                total += ex.points
            elif hasattr(ex, 'points_per_statement'):
                total += ex.points_per_statement * len(ex.statements)
    return total


def get_student_lesson_points(student, course_lesson=None, formation_lesson=None):
    """Return points earned by student on all exercise types in a lesson."""
    from .models import (
        CodeExercise, MCQExercise,
        FillBlankExercise, TrueFalseExercise,
        CodeOrderExercise, MatchingExercise, ShortAnswerExercise,
        StudentProgress,
    )

    filter_kw = {'course_lesson': course_lesson} if course_lesson else {'formation_lesson': formation_lesson}
    exercise_models = {
        'code':         CodeExercise,
        'mcq':          MCQExercise,
        'fill_blank':   FillBlankExercise,
        'true_false':   TrueFalseExercise,
        'code_order':   CodeOrderExercise,
        'matching':     MatchingExercise,
        'short_answer': ShortAnswerExercise,
    }

    total = 0
    for ex_type, model in exercise_models.items():
        exercise_ids = list(model.objects.filter(is_active=True, **filter_kw).values_list('id', flat=True))
        if not exercise_ids:
            continue
        agg = StudentProgress.objects.filter(
            student=student,
            exercise_type=ex_type,
            exercise_id__in=exercise_ids,
            is_solved=True,
        ).aggregate(t=Sum('points_earned'))
        total += agg['t'] or 0

    return total


def award_exercise_points(student, grade_model, exercise, points):
    """Mark an exercise grade as solved and award points. Idempotent."""
    from django.utils import timezone
    if not grade_model.is_solved:
        grade_model.is_solved = True
        grade_model.points_earned = points
        grade_model.solved_at = timezone.now()
        grade_model.save()
    return grade_model.is_solved


def notify_exercise_solved(student, title, points):
    """Send in-app success notification."""
    try:
        from notifications.notifications import notify_user
        from django.utils.translation import gettext as _
        notify_user(
            student,
            title=_("Exercice réussi ! 🎉"),
            message=_(f"Tu as répondu correctement à '{title}' (+{points} pts)"),
            notification_type='success',
        )
    except Exception:
        pass
