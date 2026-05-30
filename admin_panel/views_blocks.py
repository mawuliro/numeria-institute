"""
Block CRUD AJAX endpoints for the admin panel lesson block builder.
Used by both Course lessons (Lecon) and Formation lessons (FormationLesson).
"""
import json
import logging
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST, require_GET

from .utils import staff_only

logger = logging.getLogger(__name__)


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _render_block_card(request, block):
    """Render a single block card as HTML string."""
    from cours.models import CodeExercise
    all_exercises = CodeExercise.objects.select_related('lecon', 'formation_lesson').order_by('title')
    return render_to_string('admin_panel/blocks/block_card.html', {
        'block': block,
        'all_exercises': all_exercises,
    }, request=request)


def _render_block_list(request, blocks, lesson_id, lesson_type):
    """Render the full block list HTML."""
    from cours.models import CodeExercise
    all_exercises = CodeExercise.objects.select_related('lecon', 'formation_lesson').order_by('title')
    return render_to_string('admin_panel/blocks/block_list.html', {
        'blocks': blocks,
        'lesson_id': lesson_id,
        'lesson_type': lesson_type,
        'all_exercises': all_exercises,
    }, request=request)


# ─── COURSE LESSON BLOCKS ─────────────────────────────────────────────────────

@staff_only
def get_lesson_blocks(request, lesson_id):
    from cours.models import Lecon, LessonBlock
    lecon  = get_object_or_404(Lecon, id=lesson_id)
    blocks = LessonBlock.objects.filter(lesson=lecon).order_by('order')
    html   = _render_block_list(request, blocks, lesson_id, 'cours')
    return JsonResponse({'html': html})


@staff_only
@require_POST
def add_lesson_block(request, lesson_id):
    from cours.models import Lecon, LessonBlock
    lecon = get_object_or_404(Lecon, id=lesson_id)
    try:
        data       = json.loads(request.body)
        block_type = data.get('block_type', 'text')
        position   = data.get('position')
    except Exception:
        block_type, position = 'text', None

    existing = LessonBlock.objects.filter(lesson=lecon)
    if position is not None:
        existing.filter(order__gte=position).update(order=F('order') + 1)
        order = int(position)
    else:
        order = existing.count()

    block = LessonBlock.objects.create(
        lesson=lecon, block_type=block_type, order=order,
    )
    html = _render_block_card(request, block)
    return JsonResponse({'block_id': block.id, 'html': html, 'order': block.order})


@staff_only
@require_POST
def reorder_lesson_blocks(request, lesson_id):
    from cours.models import Lecon, LessonBlock
    lecon = get_object_or_404(Lecon, id=lesson_id)
    try:
        order_list = json.loads(request.body).get('order', [])
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    for idx, block_id in enumerate(order_list):
        LessonBlock.objects.filter(id=block_id, lesson=lecon).update(order=idx)
    return JsonResponse({'success': True})


# ─── FORMATION LESSON BLOCKS ──────────────────────────────────────────────────

@staff_only
def get_formation_lesson_blocks(request, lesson_id):
    from formation.models import FormationLesson
    from cours.models import LessonBlock
    fl     = get_object_or_404(FormationLesson, id=lesson_id)
    blocks = LessonBlock.objects.filter(formation_lesson=fl).order_by('order')
    html   = _render_block_list(request, blocks, lesson_id, 'formation')
    return JsonResponse({'html': html})


@staff_only
@require_POST
def add_formation_lesson_block(request, lesson_id):
    from formation.models import FormationLesson
    from cours.models import LessonBlock
    fl = get_object_or_404(FormationLesson, id=lesson_id)
    try:
        data       = json.loads(request.body)
        block_type = data.get('block_type', 'text')
        position   = data.get('position')
    except Exception:
        block_type, position = 'text', None

    existing = LessonBlock.objects.filter(formation_lesson=fl)
    if position is not None:
        existing.filter(order__gte=position).update(order=F('order') + 1)
        order = int(position)
    else:
        order = existing.count()

    block = LessonBlock.objects.create(
        formation_lesson=fl, block_type=block_type, order=order,
    )
    html = _render_block_card(request, block)
    return JsonResponse({'block_id': block.id, 'html': html, 'order': block.order})


@staff_only
@require_POST
def reorder_formation_lesson_blocks(request, lesson_id):
    from formation.models import FormationLesson
    from cours.models import LessonBlock
    fl = get_object_or_404(FormationLesson, id=lesson_id)
    try:
        order_list = json.loads(request.body).get('order', [])
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    for idx, block_id in enumerate(order_list):
        LessonBlock.objects.filter(id=block_id, formation_lesson=fl).update(order=idx)
    return JsonResponse({'success': True})


# ─── SHARED: UPDATE + DELETE BLOCK ────────────────────────────────────────────

@staff_only
@require_POST
def update_block(request, block_id):
    from cours.models import LessonBlock
    block = get_object_or_404(LessonBlock, id=block_id)
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST.dict()

    # Update only the fields that are present in the request
    allowed = {
        'text_content', 'video_url', 'video_caption',
        'sandbox_title', 'sandbox_initial_code',
    }
    for field in allowed:
        if field in data:
            setattr(block, field, data[field])

    if 'exercise_id' in data:
        from cours.models import CodeExercise
        ex_id = data['exercise_id']
        block.exercise = CodeExercise.objects.filter(id=ex_id).first() if ex_id else None

    block.save()
    return JsonResponse({'success': True})


@staff_only
@require_POST
def delete_block(request, block_id):
    from cours.models import LessonBlock
    block = get_object_or_404(LessonBlock, id=block_id)
    block.delete()
    return JsonResponse({'success': True})
