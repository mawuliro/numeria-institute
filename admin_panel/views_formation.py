"""
Formation CMS views for the custom staff admin panel.
Mirrors admin_panel/views_cours.py but operates on Formation models.
"""
import json
import logging
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from .utils import staff_only, log_staff_action

logger = logging.getLogger(__name__)


def _get_formation_context(formation):
    """Return modules + standalone lessons tree for the formation editor."""
    from formation.models import FormationModule, FormationLesson
    modules = list(
        FormationModule.objects.filter(formation=formation)
        .prefetch_related('lessons')
        .order_by('ordre')
    )
    standalone = list(
        FormationLesson.objects.filter(formation=formation, module__isnull=True).order_by('ordre')
    )
    return {'modules': modules, 'standalone_lecons': standalone}


# ─── LIST ─────────────────────────────────────────────────────────────────────

@staff_only
def formation_list(request):
    from formation.models import Formation
    qs = Formation.objects.annotate(
        nb_modules=Count('modules', distinct=True),
        nb_lessons=Count('formation_lessons', distinct=True),
        nb_inscrits=Count('sessions__inscriptions__etudiant', distinct=True),
    )

    status_f = request.GET.get('status', '')
    q        = request.GET.get('q', '').strip()
    mine     = request.GET.get('mine', '')

    if status_f == 'publie':
        qs = qs.filter(est_publiee=True, est_archivee=False)
    elif status_f == 'brouillon':
        qs = qs.filter(est_publiee=False, est_archivee=False)
    elif status_f == 'archive':
        qs = qs.filter(est_archivee=True)
    if mine:
        qs = qs.filter(instructeurs=request.user)
    if q:
        qs = qs.filter(Q(titre__icontains=q) | Q(description_courte__icontains=q))

    sort = request.GET.get('sort', '-date_creation')
    sort_map = {'-date_creation': '-date_creation', 'titre': 'titre', '-nb_inscrits': '-nb_inscrits'}
    qs = qs.order_by(sort_map.get(sort, '-date_creation'))

    draft_count = Formation.objects.filter(est_publiee=False, est_archivee=False).count()

    paginator = Paginator(qs, 12)
    page_obj  = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin_panel/formation_list.html', {
        'page_obj':    page_obj,
        'status_f':    status_f,
        'q':           q,
        'mine':        mine,
        'sort':        sort,
        'draft_count': draft_count,
        'types':       Formation.TYPES_FORMATION,
        'niveaux':     Formation.NIVEAUX,
        'statut_choices': [
            ('', 'Toutes'),
            ('publie', 'Publiées'),
            ('brouillon', 'Brouillons'),
            ('archive', 'Archivées'),
        ],
    })


# ─── CREATE / EDIT ────────────────────────────────────────────────────────────

@staff_only
def formation_create(request):
    from formation.models import Formation
    if request.method == 'POST':
        titre = request.POST.get('titre', '').strip()
        if not titre:
            messages.error(request, 'Le titre est obligatoire.')
            return redirect('admin_panel:formation_create')
        slug = slugify(titre)
        counter, base = 1, slug
        while Formation.objects.filter(slug=slug).exists():
            slug = f'{base}-{counter}'
            counter += 1
        formation = Formation.objects.create(
            titre=titre,
            slug=slug,
            description_courte=request.POST.get('description_courte', ''),
            description_longue='',
            type_formation=request.POST.get('type_formation', 'bootcamp'),
            niveau=request.POST.get('niveau', 'debutant'),
            duree_heures=int(request.POST.get('duree_heures', 0) or 0),
            prerequis='',
            competences_visees='',
        )
        log_staff_action(request.user, 'notification_sent', f"Formation créée : «{formation.titre}»")
        return redirect('admin_panel:formation_edit', slug=formation.slug)

    from formation.models import Formation as F
    return render(request, 'admin_panel/formation_create.html', {
        'types':   F.TYPES_FORMATION,
        'niveaux': F.NIVEAUX,
    })


@staff_only
def formation_edit(request, slug):
    from formation.models import Formation
    formation = get_object_or_404(Formation, slug=slug)
    tree      = _get_formation_context(formation)
    return render(request, 'admin_panel/formation_edit.html', {
        'formation':         formation,
        'modules':           tree['modules'],
        'standalone_lecons': tree['standalone_lecons'],
        'types':             Formation.TYPES_FORMATION,
        'niveaux':           Formation.NIVEAUX,
    })


@staff_only
@require_POST
def formation_delete(request, slug):
    from formation.models import Formation
    f = get_object_or_404(Formation, slug=slug)
    titre = f.titre
    f.delete()
    messages.success(request, f'Formation «{titre}» supprimée.')
    return redirect('admin_panel:formation_list')


# ─── PREVIEW ──────────────────────────────────────────────────────────────────

@staff_only
def formation_preview(request, slug):
    import base64
    from formation.models import Formation, FormationLesson
    from cours.models import LessonBlock, MCQExercise
    from django.utils import timezone as _tz

    formation    = get_object_or_404(Formation, slug=slug)
    lesson_id    = request.GET.get('lecon')
    lecon_active = None
    if lesson_id:
        lecon_active = FormationLesson.objects.filter(id=lesson_id, formation=formation).first()
    if not lecon_active:
        lecon_active = formation.formation_lessons.filter(est_active=True).first()

    # Build LessonBlock data for the active lesson (staff preview — no grade gating)
    lesson_blocks_data = []
    if lecon_active:
        blocks_qs = LessonBlock.objects.filter(formation_lesson=lecon_active).order_by('order')
        for block in blocks_qs:
            bd = {'id': block.id, 'type': block.block_type, 'order': block.order}
            if block.block_type == 'text':
                bd['text_content'] = block.text_content
            elif block.block_type == 'video':
                bd['video_url']    = block.video_url
                bd['video_caption']= block.video_caption
                if block.video_url:
                    from formation.models import Formation as F
                    from cours.models import convertir_url_youtube
                    bd['embed_url'] = convertir_url_youtube(block.video_url)
            elif block.block_type == 'sandbox':
                bd['title']        = block.sandbox_title or 'Essaie toi-même'
                bd['initial_code'] = block.sandbox_initial_code
            elif block.block_type == 'exercise' and block.code_exercise:
                ex    = block.code_exercise
                tc_b64 = base64.b64encode(ex.test_code.encode()).decode() if ex.test_code else ''
                bd.update({
                    'exercise_id':    ex.id, 'title': ex.title,
                    'instructions':   ex.instructions, 'starter_code': ex.starter_code,
                    'expected_output':ex.expected_output, 'evaluation_mode': ex.evaluation_mode,
                    'difficulty':     ex.difficulty, 'hint': ex.hint,
                    'max_attempts':   ex.max_attempts, 'points': ex.points,
                    'test_code_b64':  tc_b64, 'is_solved': False, 'attempts_used': 0,
                })
            elif block.block_type == 'mcq' and block.mcq_exercise:
                mcq = block.mcq_exercise
                choices = list(mcq.choices.order_by('order'))
                bd.update({
                    'mcq_id': mcq.id, 'mcq_title': mcq.title, 'question': mcq.question,
                    'hint': mcq.hint, 'allow_multiple': mcq.allow_multiple_correct,
                    'shuffle': mcq.shuffle_choices, 'max_attempts': mcq.max_attempts,
                    'points': mcq.points, 'difficulty': mcq.difficulty,
                    'choices': [{'id': c.id, 'text': c.text, 'order': c.order} for c in choices],
                    'is_solved': False, 'points_earned': 0, 'attempts_used': 0,
                    'correct_ids': [], 'explanation': '',
                })
            elif block.block_type == 'fill_blank' and block.fill_blank_exercise:
                ex = block.fill_blank_exercise
                bd.update({
                    'fill_blank_id': ex.id,
                    'title': ex.title,
                    'instructions': ex.instructions,
                    'text_rendered': ex.text_with_blanks,
                    'blank_count': len(ex.answers or {}),
                    'points': ex.points,
                    'difficulty': ex.difficulty,
                    'hint': ex.hint,
                    'max_attempts': ex.max_attempts,
                    'is_solved': False,
                    'attempts_used': 0,
                })
            elif block.block_type == 'true_false' and block.true_false_exercise:
                ex = block.true_false_exercise
                stmts = [{'statement': s.get('statement', ''), 'is_true': s.get('is_true', True)} for s in (ex.statements or [])]
                bd.update({
                    'true_false_id': ex.id,
                    'title': ex.title,
                    'statements': stmts,
                    'points_per_statement': ex.points_per_statement,
                    'difficulty': ex.difficulty,
                    'hint': ex.hint,
                    'is_solved': False,
                    'attempts_used': 0,
                })
            elif block.block_type == 'code_order' and block.code_order_exercise:
                import random as _random
                ex = block.code_order_exercise
                all_lines = list(ex.correct_order) + list(ex.distractor_lines or [])
                indices = list(range(len(all_lines)))
                _random.seed(12345 + ex.id)
                _random.shuffle(indices)
                shuffled = [all_lines[i] for i in indices]
                import json as _json
                bd.update({
                    'code_order_id': ex.id,
                    'title': ex.title,
                    'instructions': ex.instructions,
                    'shuffled_lines': shuffled,
                    'shuffled_indices_json': _json.dumps(indices),
                    'points': ex.points,
                    'difficulty': ex.difficulty,
                    'hint': ex.hint,
                    'max_attempts': ex.max_attempts,
                    'is_solved': False,
                    'attempts_used': 0,
                })
            elif block.block_type == 'matching' and block.matching_exercise:
                import random as _random
                ex = block.matching_exercise
                pairs = ex.pairs or []
                left = [p.get('left', '') for p in pairs]
                right = [p.get('right', '') for p in pairs]
                indices = list(range(len(right)))
                _random.seed(12346 + ex.id)
                _random.shuffle(indices)
                shuffled_right = [right[i] for i in indices]
                bd.update({
                    'matching_id': ex.id,
                    'title': ex.title,
                    'instructions': ex.instructions,
                    'left_items': left,
                    'right_items': shuffled_right,
                    'right_indices': list(range(len(pairs))),
                    'pairs': pairs,
                    'points': ex.points,
                    'difficulty': ex.difficulty,
                    'hint': ex.hint,
                    'is_solved': False,
                    'attempts_used': 0,
                })
            elif block.block_type == 'short_answer' and block.short_answer_exercise:
                ex = block.short_answer_exercise
                bd.update({
                    'short_answer_id': ex.id,
                    'title': ex.title,
                    'question': ex.question,
                    'points': ex.points,
                    'difficulty': ex.difficulty,
                    'hint': ex.hint,
                    'max_attempts': ex.max_attempts,
                    'is_code_answer': ex.is_code_answer,
                    'is_solved': False,
                    'attempts_used': 0,
                })
            lesson_blocks_data.append(bd)

    return render(request, 'admin_panel/formation_preview.html', {
        'formation':         formation,
        'lecon_active':      lecon_active,
        'lesson_blocks':     lesson_blocks_data,
        'modules':           _get_formation_context(formation)['modules'],
        'is_preview':        True,
        'has_blocks':        bool(lesson_blocks_data),
    })


# ─── ANALYTICS ────────────────────────────────────────────────────────────────

@staff_only
def formation_analytics(request, slug):
    from formation.models import Formation, InscriptionFormation, ProgressionLecon
    from paiements.models import Paiement
    from datetime import timedelta

    formation = get_object_or_404(Formation, slug=slug)
    total_inscrits = InscriptionFormation.objects.filter(session__formation=formation).count()
    total_termines = InscriptionFormation.objects.filter(
        session__formation=formation, progression=100
    ).count()
    completion_rate = round(total_termines / total_inscrits * 100, 1) if total_inscrits else 0

    revenus = Paiement.objects.filter(
        formation_inscription__session__formation=formation, statut='reussi'
    ).aggregate(t=Sum('montant_final'))['t'] or 0

    now = timezone.now()
    weeks_data = []
    for i in range(11, -1, -1):
        week_start = now - timedelta(weeks=i+1)
        week_end   = now - timedelta(weeks=i)
        count = InscriptionFormation.objects.filter(
            session__formation=formation,
            date_inscription__gte=week_start, date_inscription__lt=week_end
        ).count()
        weeks_data.append({'label': week_start.strftime('%d/%m'), 'count': count})

    return render(request, 'admin_panel/formation_analytics.html', {
        'formation':       formation,
        'total_inscrits':  total_inscrits,
        'total_termines':  total_termines,
        'completion_rate': completion_rate,
        'revenus':         revenus,
        'weeks_data_json': json.dumps(weeks_data),
    })


# ─── AJAX — META SAVE ─────────────────────────────────────────────────────────

@staff_only
@require_POST
def ajax_formation_save(request, slug):
    from formation.models import Formation
    formation = get_object_or_404(Formation, slug=slug)
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST.dict()

    for field in ['titre', 'description_courte', 'description_longue', 'type_formation',
                  'niveau', 'duree_heures', 'prerequis', 'competences_visees']:
        if field in data:
            setattr(formation, field, data[field])

    if 'statut' in data:
        s = data['statut']
        formation.est_publiee = (s == 'publie')
        formation.est_archivee = (s == 'archive')

    if 'image_couverture' in request.FILES:
        formation.image_couverture = request.FILES['image_couverture']

    formation.save()
    return JsonResponse({'ok': True, 'slug': formation.slug, 'titre': formation.titre})


# ─── AJAX — MODULE ────────────────────────────────────────────────────────────

@staff_only
@require_POST
def ajax_fmodule_create(request, slug):
    from formation.models import Formation, FormationModule
    formation = get_object_or_404(Formation, slug=slug)
    try:
        data  = json.loads(request.body)
        titre = data.get('titre', '').strip()
    except Exception:
        titre = request.POST.get('titre', '').strip()
    if not titre:
        return JsonResponse({'error': 'Titre requis'}, status=400)
    ordre  = FormationModule.objects.filter(formation=formation).count()
    module = FormationModule.objects.create(formation=formation, titre=titre, ordre=ordre)
    return JsonResponse({'id': module.id, 'titre': module.titre, 'ordre': module.ordre})


@staff_only
@require_POST
def ajax_fmodule_update(request, module_id):
    from formation.models import FormationModule
    module = get_object_or_404(FormationModule, id=module_id)
    try:
        titre = json.loads(request.body).get('titre', module.titre).strip()
    except Exception:
        titre = request.POST.get('titre', module.titre).strip()
    if titre:
        module.titre = titre
        module.save(update_fields=['titre'])
    return JsonResponse({'ok': True, 'titre': module.titre})


@staff_only
@require_POST
def ajax_fmodule_delete(request, module_id):
    from formation.models import FormationModule
    module = get_object_or_404(FormationModule, id=module_id)
    module.lessons.update(module=None)
    module.delete()
    return JsonResponse({'ok': True})


# ─── AJAX — LESSON ────────────────────────────────────────────────────────────

@staff_only
@require_POST
def ajax_flesson_create(request, slug):
    from formation.models import Formation, FormationLesson, FormationModule
    formation = get_object_or_404(Formation, slug=slug)
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST.dict()
    titre     = data.get('titre', 'Nouvelle leçon').strip()
    module_id = data.get('module_id')
    module    = None
    if module_id:
        module = FormationModule.objects.filter(id=module_id, formation=formation).first()
    ordre = module.lessons.count() if module else FormationLesson.objects.filter(
        formation=formation, module__isnull=True).count()
    lesson = FormationLesson.objects.create(
        formation=formation, module=module, titre=titre,
        ordre=ordre, content_type=data.get('content_type', 'text'),
    )
    return JsonResponse({'id': lesson.id, 'titre': lesson.titre,
                         'module_id': module.id if module else None, 'ordre': lesson.ordre})


@staff_only
def ajax_flesson_get(request, lesson_id):
    from formation.models import FormationLesson
    lesson = get_object_or_404(FormationLesson, id=lesson_id)
    return JsonResponse({
        'id': lesson.id, 'titre': lesson.titre, 'contenu': lesson.contenu,
        'video_url': lesson.video_url or '', 'content_type': lesson.content_type,
        'duree_minutes': lesson.duree_minutes, 'is_free_preview': lesson.is_free_preview,
        'est_active': lesson.est_active, 'ordre': lesson.ordre,
    })


@staff_only
@require_POST
def ajax_flesson_save(request, lesson_id):
    from formation.models import FormationLesson
    lesson = get_object_or_404(FormationLesson, id=lesson_id)
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST.dict()
    lesson.titre          = data.get('titre', lesson.titre).strip() or lesson.titre
    lesson.contenu        = data.get('contenu', lesson.contenu)
    lesson.video_url      = data.get('video_url', lesson.video_url) or None
    lesson.content_type   = data.get('content_type', lesson.content_type)
    lesson.duree_minutes  = int(data.get('duree_minutes', lesson.duree_minutes) or 10)
    lesson.is_free_preview = data.get('is_free_preview') in (True, 'true', '1', 'on')
    lesson.est_active     = data.get('est_active', True) not in (False, 'false', '0')
    lesson.save()
    return JsonResponse({'ok': True, 'id': lesson.id, 'titre': lesson.titre})


@staff_only
@require_POST
def ajax_flesson_delete(request, lesson_id):
    from formation.models import FormationLesson
    get_object_or_404(FormationLesson, id=lesson_id).delete()
    return JsonResponse({'ok': True})


# ─── AJAX — REORDER ───────────────────────────────────────────────────────────

@staff_only
@require_POST
def ajax_freorder(request, slug):
    from formation.models import Formation, FormationModule, FormationLesson
    formation = get_object_or_404(Formation, slug=slug)
    try:
        items = json.loads(request.body).get('items', [])
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    for item in items:
        t, pk, o, mid = item.get('type'), item.get('id'), item.get('order', 0), item.get('module_id')
        if t == 'module':
            FormationModule.objects.filter(id=pk, formation=formation).update(ordre=o)
        elif t == 'lecon':
            qs = FormationLesson.objects.filter(id=pk, formation=formation)
            qs.update(ordre=o, module_id=mid) if mid else qs.update(ordre=o, module=None)
    return JsonResponse({'ok': True})
