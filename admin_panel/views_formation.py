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
        .order_by('order')
    )
    standalone = list(
        FormationLesson.objects.filter(formation=formation, module__isnull=True).order_by('order')
    )
    return {'modules': modules, 'standalone_lecons': standalone}


# ─── LIST ─────────────────────────────────────────────────────────────────────

@staff_only
def formation_list(request):
    from formation.models import Formation
    qs = Formation.objects.annotate(
        nb_modules=Count('modules', distinct=True),
        nb_lessons=Count('lessons', distinct=True),
        nb_inscrits=Count('inscriptions__etudiant', distinct=True),
    )

    status_f = request.GET.get('status', '')
    q        = request.GET.get('q', '').strip()
    mine     = request.GET.get('mine', '')

    if status_f == 'publie':
        qs = qs.filter(status='published')
    elif status_f == 'brouillon':
        qs = qs.filter(status='draft')
    elif status_f == 'archive':
        qs = qs.filter(status='archived')
    if mine:
        qs = qs.filter(created_by=request.user)
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(short_description__icontains=q))

    sort = request.GET.get('sort', '-created_at')
    sort_map = {'-created_at': '-created_at', 'title': 'title', '-nb_inscrits': '-nb_inscrits'}
    qs = qs.order_by(sort_map.get(sort, '-created_at'))

    draft_count = Formation.objects.filter(status='draft').count()

    paginator = Paginator(qs, 12)
    page_obj  = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin_panel/formation_list.html', {
        'page_obj':    page_obj,
        'status_f':    status_f,
        'q':           q,
        'mine':        mine,
        'sort':        sort,
        'draft_count': draft_count,
        'types':       Formation.CATEGORIES,
        'niveaux':     Formation.LEVELS,
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
            title=titre,
            slug=slug,
            short_description=request.POST.get('description_courte', ''),
            description='',
            category=request.POST.get('type_formation', 'autre'),
            level=request.POST.get('niveau', 'debutant'),
            estimated_hours=int(request.POST.get('duree_heures', 0) or 0),
            prerequisites='',
            objectives='',
            created_by=request.user,
        )
        log_staff_action(request.user, 'notification_sent', f"Formation créée : «{formation.title}»")
        return redirect('admin_panel:formation_edit', slug=formation.slug)

    from formation.models import Formation as F
    return render(request, 'admin_panel/formation_create.html', {
        'types':   F.CATEGORIES,
        'niveaux': F.LEVELS,
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
        'types':             Formation.CATEGORIES,
        'niveaux':           Formation.LEVELS,
    })


@staff_only
@require_POST
def formation_delete(request, slug):
    from formation.models import Formation
    f = get_object_or_404(Formation, slug=slug)
    titre = f.title
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
        lecon_active = formation.lessons.filter(is_active=True).first()

    # Build LessonBlock data for the active lesson (staff preview — no grade gating)
    lesson_blocks_data = []
    if lecon_active:
        blocks_qs = LessonBlock.objects.filter(formation_lesson=lecon_active).order_by('order')
        for block in blocks_qs:
            lesson_blocks_data.append(block.get_payload())

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
    from formation.models import Formation, InscriptionFormation
    from paiements.models import Paiement
    from datetime import timedelta

    formation = get_object_or_404(Formation, slug=slug)
    total_inscrits = InscriptionFormation.objects.filter(formation=formation).count()
    total_termines = InscriptionFormation.objects.filter(
        formation=formation, progression=100
    ).count()
    completion_rate = round(total_termines / total_inscrits * 100, 1) if total_inscrits else 0

    revenus = Paiement.objects.filter(
        formation=formation, statut='reussi'
    ).aggregate(t=Sum('montant_final'))['t'] or 0

    now = timezone.now()
    weeks_data = []
    for i in range(11, -1, -1):
        week_start = now - timedelta(weeks=i+1)
        week_end   = now - timedelta(weeks=i)
        count = InscriptionFormation.objects.filter(
            formation=formation,
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

    field_map = {
        'titre': 'title',
        'description_courte': 'short_description',
        'description_longue': 'description',
        'type_formation': 'category',
        'niveau': 'level',
        'duree_heures': 'estimated_hours',
        'prerequis': 'prerequisites',
        'competences_visees': 'objectives',
    }
    for old_key, new_key in field_map.items():
        if old_key in data:
            setattr(formation, new_key, data[old_key])
        elif new_key in data:
            setattr(formation, new_key, data[new_key])

    if 'statut' in data:
        s = data['statut']
        if s == 'publie':
            formation.status = 'published'
        elif s == 'archive':
            formation.status = 'archived'
        else:
            formation.status = 'draft'
    elif 'status' in data:
        formation.status = data['status']

    if 'image_couverture' in request.FILES:
        formation.thumbnail = request.FILES['image_couverture']
    elif 'thumbnail' in request.FILES:
        formation.thumbnail = request.FILES['thumbnail']

    formation.save()
    return JsonResponse({'ok': True, 'slug': formation.slug, 'title': formation.title})


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
    module = FormationModule.objects.create(formation=formation, title=titre, order=ordre)
    return JsonResponse({'id': module.id, 'title': module.title, 'order': module.order})


@staff_only
@require_POST
def ajax_fmodule_update(request, module_id):
    from formation.models import FormationModule
    module = get_object_or_404(FormationModule, id=module_id)
    try:
        titre = json.loads(request.body).get('titre', module.title).strip()
    except Exception:
        titre = request.POST.get('titre', module.title).strip()
    if titre:
        module.title = titre
        module.save(update_fields=['title'])
    return JsonResponse({'ok': True, 'title': module.title})


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
        formation=formation, module=module, title=titre, order=ordre,
    )
    return JsonResponse({'id': lesson.id, 'title': lesson.title,
                         'module_id': module.id if module else None, 'order': lesson.order})


@staff_only
def ajax_flesson_get(request, lesson_id):
    from formation.models import FormationLesson
    lesson = get_object_or_404(FormationLesson, id=lesson_id)
    return JsonResponse({
        'id': lesson.id, 'title': lesson.title,
        'estimated_minutes': lesson.estimated_minutes,
        'is_free_preview': lesson.is_free_preview,
        'is_active': lesson.is_active, 'order': lesson.order,
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
    lesson.title           = (data.get('titre') or data.get('title') or lesson.title).strip() or lesson.title
    lesson.estimated_minutes = int(data.get('duree_minutes') or data.get('estimated_minutes') or lesson.estimated_minutes or 10)
    lesson.is_free_preview = data.get('is_free_preview') in (True, 'true', '1', 'on')
    lesson.is_active       = data.get('est_active', data.get('is_active', True)) not in (False, 'false', '0')
    lesson.save()
    return JsonResponse({'ok': True, 'id': lesson.id, 'title': lesson.title})


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
            FormationModule.objects.filter(id=pk, formation=formation).update(order=o)
        elif t == 'lecon':
            qs = FormationLesson.objects.filter(id=pk, formation=formation)
            qs.update(order=o, module_id=mid) if mid else qs.update(order=o, module=None)
    return JsonResponse({'ok': True})
