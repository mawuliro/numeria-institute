"""Student grades / progress pages — /mes-notes/"""
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, render

from cours.models import (
    Course, InscriptionCours, CourseLesson, StudentProgress,
    CodeExercise, MCQExercise, FillBlankExercise,
    TrueFalseExercise, CodeOrderExercise, MatchingExercise, ShortAnswerExercise,
)
from formation.models import Formation, InscriptionFormation, FormationLesson

EXERCISE_MODELS = {
    'code': CodeExercise,
    'mcq': MCQExercise,
    'fill_blank': FillBlankExercise,
    'true_false': TrueFalseExercise,
    'code_order': CodeOrderExercise,
    'matching': MatchingExercise,
    'short_answer': ShortAnswerExercise,
}

TYPE_ICONS = {
    'code': '💻', 'mcq': '🔘', 'fill_blank': '✏️',
    'true_false': '✅', 'code_order': '🧩', 'matching': '🔗', 'short_answer': '💬',
}


def _exercise_title(ex_type, ex_id):
    model = EXERCISE_MODELS.get(ex_type)
    if not model:
        return f'Exercice #{ex_id}'
    ex = model.objects.filter(pk=ex_id).first()
    return ex.title if ex else f'Exercice #{ex_id}'


def _exercise_points(ex_type, ex_id):
    model = EXERCISE_MODELS.get(ex_type)
    if not model:
        return 0
    ex = model.objects.filter(pk=ex_id).first()
    if not ex:
        return 0
    if hasattr(ex, 'points'):
        return ex.points
    if hasattr(ex, 'points_per_statement') and ex.statements:
        return ex.points_per_statement * len(ex.statements)
    return 0


@login_required
def mes_notes(request):
    """Overview of all courses/formations with grade summary."""
    user = request.user
    cours_rows = []
    for ins in InscriptionCours.objects.filter(etudiant=user).select_related('course'):
        c = ins.course
        lesson_ids = list(c.lessons.values_list('id', flat=True))
        progress = StudentProgress.objects.filter(student=user)
        # Points from exercises linked to course lessons
        earned = 0
        possible = 0
        for ex_type, model in EXERCISE_MODELS.items():
            qs = model.objects.filter(is_active=True, course_lesson_id__in=lesson_ids)
            if ex_type == 'mcq':
                qs = model.objects.filter(is_active=True, course_lesson_id__in=lesson_ids)
            for ex in qs:
                pts = _exercise_points(ex_type, ex.pk)
                possible += pts
                prog = progress.filter(exercise_type=ex_type, exercise_id=ex.pk, is_solved=True).first()
                if prog:
                    earned += prog.points_earned
        cours_rows.append({
            'obj': c,
            'kind': 'cours',
            'title': c.titre,
            'slug': c.slug,
            'earned': earned,
            'possible': possible,
            'progression': ins.progression,
        })

    formation_rows = []
    for ins in InscriptionFormation.objects.filter(etudiant=user).select_related('session__formation'):
        f = ins.session.formation
        lesson_ids = list(f.formation_lessons.values_list('id', flat=True))
        progress = StudentProgress.objects.filter(student=user)
        earned = possible = 0
        for ex_type, model in EXERCISE_MODELS.items():
            qs = model.objects.filter(is_active=True, formation_lesson_id__in=lesson_ids)
            for ex in qs:
                pts = _exercise_points(ex_type, ex.pk)
                possible += pts
                prog = progress.filter(exercise_type=ex_type, exercise_id=ex.pk, is_solved=True).first()
                if prog:
                    earned += prog.points_earned
        formation_rows.append({
            'obj': f,
            'kind': 'formation',
            'title': f.titre,
            'slug': f.slug,
            'earned': earned,
            'possible': possible,
            'progression': ins.progression,
        })

    total_earned = sum(r['earned'] for r in cours_rows + formation_rows)

    return render(request, 'cours/mes_notes.html', {
        'cours_rows': cours_rows,
        'formation_rows': formation_rows,
        'total_earned': total_earned,
    })


@login_required
def mes_notes_cours(request, slug):
    """Lesson-by-lesson breakdown for one course."""
    cours = get_object_or_404(Course, slug=slug)
    user = request.user
    lessons = cours.lessons.filter(est_publiee=True).order_by('ordre')
    lesson_data = []

    for lecon in lessons:
        exercises = []
        for ex_type, model in EXERCISE_MODELS.items():
            if ex_type == 'mcq':
                qs = model.objects.filter(is_active=True, course_lesson=lecon)
            else:
                qs = model.objects.filter(is_active=True, course_lesson=lecon)
            for ex in qs:
                prog = StudentProgress.objects.filter(
                    student=user, exercise_type=ex_type, exercise_id=ex.pk,
                ).first()
                max_pts = _exercise_points(ex_type, ex.pk)
                exercises.append({
                    'type': ex_type,
                    'icon': TYPE_ICONS.get(ex_type, '📝'),
                    'title': ex.title,
                    'max_points': max_pts,
                    'earned': prog.points_earned if prog and prog.is_solved else 0,
                    'attempts': prog.attempts if prog else 0,
                    'status': 'solved' if prog and prog.is_solved else (
                        'failed' if prog and prog.attempts > 0 else 'none'
                    ),
                })
        lesson_data.append({'lecon': lecon, 'exercises': exercises})

    return render(request, 'cours/mes_notes_detail.html', {
        'parent': cours,
        'parent_kind': 'cours',
        'parent_title': cours.titre,
        'lessons': lesson_data,
    })


@login_required
def mes_notes_formation(request, slug):
    """Lesson-by-lesson breakdown for one formation."""
    formation = get_object_or_404(Formation, slug=slug)
    user = request.user
    lessons = formation.formation_lessons.filter(est_active=True).order_by('ordre')
    lesson_data = []

    for lecon in lessons:
        exercises = []
        for ex_type, model in EXERCISE_MODELS.items():
            qs = model.objects.filter(is_active=True, formation_lesson=lecon)
            for ex in qs:
                prog = StudentProgress.objects.filter(
                    student=user, exercise_type=ex_type, exercise_id=ex.pk,
                ).first()
                max_pts = _exercise_points(ex_type, ex.pk)
                exercises.append({
                    'type': ex_type,
                    'icon': TYPE_ICONS.get(ex_type, '📝'),
                    'title': ex.title,
                    'max_points': max_pts,
                    'earned': prog.points_earned if prog and prog.is_solved else 0,
                    'attempts': prog.attempts if prog else 0,
                    'status': 'solved' if prog and prog.is_solved else (
                        'failed' if prog and prog.attempts > 0 else 'none'
                    ),
                })
        lesson_data.append({'lecon': lecon, 'exercises': exercises})

    return render(request, 'cours/mes_notes_detail.html', {
        'parent': formation,
        'parent_kind': 'formation',
        'parent_title': formation.titre,
        'lessons': lesson_data,
    })
