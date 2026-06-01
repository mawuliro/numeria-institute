"""Shared LessonBlock serializer for student views and admin previews."""
import base64
import json
import random

from .models import (
    LessonBlock, CodeExercise, StudentCodeSubmission,
    MCQExercise, MCQGrade, MCQChoice,
    FillBlankExercise, FillBlankGrade,
    TrueFalseExercise, TrueFalseGrade,
    CodeOrderExercise, CodeOrderGrade,
    MatchingExercise, MatchingGrade,
    ShortAnswerExercise, ShortAnswerGrade,
    convertir_url_youtube,
)


def build_lesson_blocks(*, course_lesson=None, formation_lesson=None, user=None, preview=False):
    """
    Build sanitized block dicts for lesson_blocks_render.html.
    Exactly one of course_lesson or formation_lesson must be provided.
    """
    if bool(course_lesson) == bool(formation_lesson):
        return []

    filter_kw = (
        {'course_lesson': course_lesson}
        if course_lesson else
        {'formation_lesson': formation_lesson}
    )
    blocks_qs = LessonBlock.objects.filter(**filter_kw).order_by('order')
    if not blocks_qs.exists():
        return []

    result = []

    for block in blocks_qs:
        result.append(block.get_payload(user=user, preview=preview))

    return result


def build_legacy_code_exercises(*, course_lesson=None, formation_lesson=None, user=None):
    """Legacy CodeExercise list when no LessonBlocks exist."""
    filter_kw = (
        {'course_lesson': course_lesson}
        if course_lesson else
        {'formation_lesson': formation_lesson}
    )
    raw_exs = CodeExercise.objects.filter(is_active=True, **filter_kw).order_by('order')
    if not raw_exs.exists():
        return []

    solved_ids = set()
    if user:
        solved_ids = set(
            StudentCodeSubmission.objects.filter(
                student=user, is_correct=True, exercise__in=raw_exs,
            ).values_list('exercise_id', flat=True)
        )

    data = []
    for ex in raw_exs:
        payload = ex.get_payload(user=user)
        payload['id'] = ex.id
        data.append(payload)
    return data
