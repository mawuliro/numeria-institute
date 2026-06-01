"""
Course Management views for the custom staff admin panel.
All views are protected by the staff_only decorator.
"""
import json
import logging
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST, require_http_methods

from .utils import staff_only, log_staff_action

logger = logging.getLogger(__name__)


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _get_cours_context(cours):
    """Return a dict with module/lesson tree for the course editor."""
    from cours.models import CourseModule, CourseLesson
    modules = list(
        CourseModule.objects.filter(course=cours).prefetch_related('lessons').order_by('ordre')
    )
    standalone_lecons = list(
        CourseLesson.objects.filter(course=cours, module__isnull=True).order_by('ordre')
    )
    return {'modules': modules, 'standalone_lecons': standalone_lecons}


# ─── COURSE LIST ──────────────────────────────────────────────────────────────

@staff_only
def cours_list(request):
    from cours.models import Course, InscriptionCours

    qs = Course.objects.select_related('created_by').annotate(
        nb_inscrits=Count('inscriptions', distinct=True),
        nb_modules=Count('modules', distinct=True),
        nb_lecons=Count('lessons', distinct=True),
    )

    # Filters
    status_f   = request.GET.get('status', '')
    categorie_f = request.GET.get('categorie', '')
    niveau_f   = request.GET.get('niveau', '')
    langue_f   = request.GET.get('langue', '')
    mine_only  = request.GET.get('mine', '')
    q          = request.GET.get('q', '').strip()
    sort       = request.GET.get('sort', '-date_creation')

    if status_f:
        qs = qs.filter(status=status_f)
    if categorie_f:
        qs = qs.filter(matiere=categorie_f)
    if niveau_f:
        qs = qs.filter(niveau=niveau_f)
    if langue_f:
        qs = qs.filter(langue=langue_f)
    if mine_only:
        qs = qs.filter(created_by=request.user)
    if q:
        qs = qs.filter(Q(titre__icontains=q) | Q(resume__icontains=q))

    sort_map = {
        '-date_creation': '-date_creation',
        'date_creation':  'date_creation',
        'titre':          'titre',
        '-nb_inscrits':   '-nb_inscrits',
    }
    qs = qs.order_by(sort_map.get(sort, '-date_creation'))

    paginator = Paginator(qs, 12)
    page_obj  = paginator.get_page(request.GET.get('page'))

    draft_count = Course.objects.filter(status='brouillon').count()

    return render(request, 'admin_panel/cours_list.html', {
        'page_obj':    page_obj,
        'status_f':    status_f,
        'categorie_f': categorie_f,
        'niveau_f':    niveau_f,
        'langue_f':    langue_f,
        'mine_only':   mine_only,
        'q':           q,
        'sort':        sort,
        'draft_count': draft_count,
        'status_choices': Course.STATUS_COURS,
        'matieres':    Course.MATIERES,
        'niveaux':     Course.NIVEAUX,
    })


# ─── COURSE CREATE / EDIT ─────────────────────────────────────────────────────

@staff_only
def cours_create(request):
    from cours.models import Course
    if request.method == 'POST':
        titre = request.POST.get('titre', '').strip()
        if not titre:
            messages.error(request, 'Le titre est obligatoire.')
            return redirect('admin_panel:cours_create')
        slug = slugify(titre)
        counter = 1
        base_slug = slug
        while Course.objects.filter(slug=slug).exists():
            slug = f'{base_slug}-{counter}'
            counter += 1
        cours = Course.objects.create(
            titre=titre,
            slug=slug,
            resume=request.POST.get('resume', ''),
            description=request.POST.get('description', ''),
            matiere=request.POST.get('matiere', 'autre'),
            niveau=request.POST.get('niveau', 'debutant'),
            langue=request.POST.get('langue', 'fr'),
            status='brouillon',
            created_by=request.user,
        )
        log_staff_action(request.user, 'notification_sent',
                         f"Cours créé : «{cours.titre}»")
        return redirect('admin_panel:cours_edit', slug=cours.slug)

    from cours.models import Course as C
    return render(request, 'admin_panel/cours_create.html', {
        'matieres': C.MATIERES,
        'niveaux':  C.NIVEAUX,
    })


@staff_only
def cours_edit(request, slug):
    from cours.models import Course
    cours = get_object_or_404(Course, slug=slug)
    tree  = _get_cours_context(cours)

    return render(request, 'admin_panel/cours_edit.html', {
        'cours':             cours,
        'modules':           tree['modules'],
        'standalone_lecons': tree['standalone_lecons'],
        'matieres':          Course.MATIERES,
        'niveaux':           Course.NIVEAUX,
        'status_choices':    Course.STATUS_COURS,
    })


@staff_only
@require_POST
def cours_delete(request, slug):
    from cours.models import Course
    cours = get_object_or_404(Course, slug=slug)
    titre = cours.titre
    cours.delete()
    log_staff_action(request.user, 'notification_sent', f"Cours supprimé : «{titre}»")
    messages.success(request, f'Cours «{titre}» supprimé.')
    return redirect('admin_panel:cours_list')


# ─── COURSE PREVIEW ───────────────────────────────────────────────────────────

@staff_only
def cours_preview(request, slug):
    import base64
    from cours.models import Course, CourseLesson, LessonBlock
    cours = get_object_or_404(Course, slug=slug)
    lecon_id = request.GET.get('lecon')
    lecon_active = None
    if lecon_id:
        lecon_active = CourseLesson.objects.filter(id=lecon_id, course=cours).first()
    if not lecon_active:
        lecon_active = cours.lessons.filter(est_publiee=True).first()

    lesson_blocks_data = []
    if lecon_active:
        blocks_qs = LessonBlock.objects.filter(course_lesson=lecon_active).order_by('order')
        for block in blocks_qs:
            lesson_blocks_data.append(block.get_payload())

    return render(request, 'admin_panel/cours_preview.html', {
        'cours':        cours,
        'lecon_active': lecon_active,
        'modules':      _get_cours_context(cours)['modules'],
        'is_preview':   True,
        'lesson_blocks': lesson_blocks_data,
        'has_blocks': bool(lesson_blocks_data),
    })


# ─── COURSE ANALYTICS ────────────────────────────────────────────────────────

@staff_only
def cours_analytics(request, slug):
    from cours.models import Course, InscriptionCours, ProgressionLecon, CourseLesson
    from paiements.models import Paiement
    from django.db.models.functions import TruncWeek

    cours = get_object_or_404(Course, slug=slug)
    total_inscrits = InscriptionCours.objects.filter(course=cours).count()
    total_termines = InscriptionCours.objects.filter(course=cours, est_termine=True).count()
    completion_rate = round(total_termines / total_inscrits * 100, 1) if total_inscrits else 0

    revenus = Paiement.objects.filter(course=cours, statut='reussi').aggregate(
        t=Sum('montant_final')
    )['t'] or 0

    # Most dropped lesson
    total_lecons = cours.lessons.count()
    lecons_stats = []
    for l in cours.lessons.all():
        done = ProgressionLecon.objects.filter(course_lesson=l).count()
        lecons_stats.append({'lecon': l, 'done': done})
    lecons_stats.sort(key=lambda x: x['done'])
    most_dropped = lecons_stats[0] if lecons_stats else None

    # Weekly enrollments (last 12 weeks) — simple queryset
    from datetime import timedelta
    weeks_data = []
    now = timezone.now()
    for i in range(11, -1, -1):
        week_start = now - timedelta(weeks=i+1)
        week_end   = now - timedelta(weeks=i)
        count = InscriptionCours.objects.filter(
            course=course, date_inscription__gte=week_start, date_inscription__lt=week_end
        ).count()
        weeks_data.append({'label': week_start.strftime('%d/%m'), 'count': count})

    return render(request, 'admin_panel/cours_analytics.html', {
        'cours':          cours,
        'total_inscrits': total_inscrits,
        'total_termines': total_termines,
        'completion_rate': completion_rate,
        'revenus':        revenus,
        'most_dropped':   most_dropped,
        'weeks_data_json': json.dumps(weeks_data),
    })


# ─── AJAX — COURSE META SAVE (Steps 1, 3, 4) ─────────────────────────────────

@staff_only
@require_POST
def ajax_cours_save(request, slug):
    from cours.models import Course
    cours = get_object_or_404(Course, slug=slug)
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        data = request.POST.dict()

    updatable = [
        'titre', 'resume', 'description', 'matiere', 'niveau', 'langue',
        'duree_estimee_heures', 'competences_visees', 'prerequisites',
        'meta_description', 'meta_keywords', 'status', 'est_gratuit', 'prix',
        'video_youtube',
    ]
    if 'slug_new' in data:
        from django.utils.text import slugify
        new_slug = slugify(data['slug_new'].strip())[:300]
        if new_slug and new_slug != cours.slug:
            cours.slug = new_slug

    for field in updatable:
        if field in data:
            val = data[field]
            if field == 'est_gratuit':
                val = val in (True, 'true', '1', 'on')
            setattr(cours, field, val)

    if 'status' in data and data['status'] == 'publie' and not cours.published_at:
        cours.published_at = timezone.now()

    # Handle thumbnail upload
    if 'thumbnail' in request.FILES:
        cours.thumbnail = request.FILES['thumbnail']

    cours.save()

    # Save ContentVersion snapshot
    try:
        from admin_panel.models import ContentVersion
        ContentVersion.objects.create(
            content_type='cours',
            object_id=cours.id,
            version_data={'titre': cours.titre, 'resume': cours.resume, 'status': cours.status},
            created_by=request.user,
        )
        ContentVersion.objects.filter(
            content_type='cours', object_id=cours.id
        ).order_by('-created_at')[3:].delete()
    except Exception:
        pass

    return JsonResponse({'ok': True, 'slug': cours.slug, 'titre': cours.titre})


# ─── AJAX — MODULE ────────────────────────────────────────────────────────────

@staff_only
@require_POST
def ajax_module_create(request, slug):
    from cours.models import Course, CourseModule
    cours = get_object_or_404(Course, slug=slug)
    try:
        data  = json.loads(request.body)
        titre = data.get('titre', '').strip()
    except Exception:
        titre = request.POST.get('titre', '').strip()
    if not titre:
        return JsonResponse({'error': 'Titre requis'}, status=400)
    next_ordre = CourseModule.objects.filter(course=cours).count()
    module = CourseModule.objects.create(course=cours, titre=titre, ordre=next_ordre)
    return JsonResponse({'id': module.id, 'titre': module.titre, 'ordre': module.ordre})


@staff_only
@require_POST
def ajax_module_update(request, module_id):
    from cours.models import CourseModule
    module = get_object_or_404(CourseModule, id=module_id)
    try:
        data  = json.loads(request.body)
        titre = data.get('titre', module.titre).strip()
    except Exception:
        titre = request.POST.get('titre', module.titre).strip()
    if titre:
        module.titre = titre
        module.save(update_fields=['titre'])
    return JsonResponse({'ok': True, 'titre': module.titre})


@staff_only
@require_POST
def ajax_module_delete(request, module_id):
    from cours.models import CourseModule
    module = get_object_or_404(CourseModule, id=module_id)
    # Move orphaned lessons to standalone
    module.lessons.update(module=None)
    module.delete()
    return JsonResponse({'ok': True})


# ─── AJAX — LESSON ────────────────────────────────────────────────────────────

@staff_only
@require_POST
def ajax_lecon_create(request, slug):
    from cours.models import Course, CourseLesson, CourseModule
    cours = get_object_or_404(Course, slug=slug)
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST.dict()

    titre     = data.get('titre', 'Nouvelle leçon').strip()
    module_id = data.get('module_id')
    module    = None
    if module_id:
        module = CourseModule.objects.filter(id=module_id, course=cours).first()

    # Determine order
    if module:
        next_ordre = module.lessons.count()
    else:
        next_ordre = CourseLesson.objects.filter(course=cours, module__isnull=True).count()

    lecon = CourseLesson.objects.create(
        course=cours, module=module, titre=titre,
        ordre=next_ordre, content_type=data.get('content_type', 'text'),
    )
    return JsonResponse({
        'id': lecon.id, 'titre': lecon.titre,
        'module_id': module.id if module else None,
        'ordre': lecon.ordre,
    })


@staff_only
def ajax_lecon_get(request, lecon_id):
    from cours.models import CourseLesson
    lecon = get_object_or_404(CourseLesson, id=lecon_id)
    return JsonResponse({
        'id':              lecon.id,
        'titre':           lecon.titre,
        'contenu':         lecon.contenu,
        'video_youtube':   lecon.video_youtube or '',
        'content_type':    lecon.content_type,
        'duree_minutes':   lecon.duree_minutes,
        'is_free_preview': lecon.is_free_preview,
        'est_publiee':     lecon.est_publiee,
        'ordre':           lecon.ordre,
    })


@staff_only
@require_POST
def ajax_lecon_save(request, lecon_id):
    from cours.models import CourseLesson
    lecon = get_object_or_404(CourseLesson, id=lecon_id)
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST.dict()

    lecon.titre          = data.get('titre', lecon.titre).strip() or lecon.titre
    lecon.contenu        = data.get('contenu', lecon.contenu)
    lecon.video_youtube  = data.get('video_youtube', lecon.video_youtube) or None
    lecon.content_type   = data.get('content_type', lecon.content_type)
    lecon.duree_minutes  = int(data.get('duree_minutes', lecon.duree_minutes) or 10)
    lecon.is_free_preview = data.get('is_free_preview') in (True, 'true', '1', 'on')
    lecon.est_publiee    = data.get('est_publiee', True) not in (False, 'false', '0')
    lecon.save()
    return JsonResponse({'ok': True, 'id': lecon.id, 'titre': lecon.titre})


@staff_only
@require_POST
def ajax_lecon_delete(request, lecon_id):
    from cours.models import CourseLesson
    lecon = get_object_or_404(CourseLesson, id=lecon_id)
    lecon.delete()
    return JsonResponse({'ok': True})


# ─── AJAX — REORDER ───────────────────────────────────────────────────────────

@staff_only
@require_POST
def ajax_reorder(request, slug):
    from cours.models import Course, CourseModule, CourseLesson
    cours = get_object_or_404(Course, slug=slug)
    try:
        data  = json.loads(request.body)
        items = data.get('items', [])
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    for item in items:
        t  = item.get('type')
        pk = item.get('id')
        o  = item.get('order', 0)
        mid = item.get('module_id')
        if t == 'module':
            CourseModule.objects.filter(id=pk, course=course).update(ordre=o)
        elif t == 'lecon':
            qs = CourseLesson.objects.filter(id=pk, course=course)
            if mid:
                qs.update(ordre=o, module_id=mid)
            else:
                qs.update(ordre=o, module=None)
    return JsonResponse({'ok': True})


# ─── IMAGE UPLOAD ─────────────────────────────────────────────────────────────

@staff_only
@require_POST
def image_upload(request):
    from admin_panel.models import UploadedMedia
    import os
    f = request.FILES.get('file') or request.FILES.get('image')
    if not f:
        return JsonResponse({'error': 'Aucun fichier reçu'}, status=400)

    ext = os.path.splitext(f.name)[1].lower()
    mtype = 'image' if ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg') else \
            'pdf' if ext == '.pdf' else 'other'

    media = UploadedMedia.objects.create(
        file=f,
        name=f.name[:200],
        media_type=mtype,
        uploaded_by=request.user,
        file_size=f.size,
    )
    return JsonResponse({'ok': True, 'url': media.file.url, 'name': media.name, 'id': media.id})


# ─── INSERT-IN-LESSON API ENDPOINTS ───────────────────────────────────────────

@staff_only
def api_courses(request):
    """GET /api/courses/ — list all courses for the insert-in-lesson modal."""
    from cours.models import Course
    courses = list(
        Course.objects.order_by('titre').values('id', 'titre', 'slug', 'status')
    )
    for c in courses:
        c['title'] = c.pop('titre')
    return JsonResponse({'courses': courses})


@staff_only
def api_course_modules(request, slug):
    """GET /api/courses/<slug>/modules/ — list modules for a course."""
    from cours.models import Course, CourseModule
    cours = get_object_or_404(Course, slug=slug)
    modules = list(
        CourseModule.objects.filter(course=cours).order_by('ordre').values('id', 'titre', 'ordre')
    )
    return JsonResponse({'modules': modules})


@staff_only
def api_module_lessons(request, module_id):
    """GET /api/modules/<id>/lessons/ — list lessons for a module."""
    from cours.models import CourseModule, CourseLesson
    module = get_object_or_404(CourseModule, id=module_id)
    lessons = list(
        CourseLesson.objects.filter(module=module).order_by('ordre').values('id', 'titre', 'ordre')
    )
    return JsonResponse({'lessons': lessons})


@staff_only
@require_POST
def api_lesson_insert_sandbox(request, lesson_id):
    """POST /api/lessons/<id>/insert-sandbox/ — append [SANDBOX] marker to lesson content."""
    from cours.models import CourseLesson
    lesson = get_object_or_404(CourseLesson, id=lesson_id)
    try:
        body   = json.loads(request.body)
        marker = body.get('marker', '').strip()
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    if not marker:
        return JsonResponse({'error': 'Empty marker'}, status=400)
    lesson.contenu = (lesson.contenu or '') + '\n\n' + marker
    lesson.save(update_fields=['contenu'])
    return JsonResponse({'success': True, 'lesson_title': lesson.titre})


@staff_only
def api_formations(request):
    """GET /api/formations/ — list all formations."""
    from formation.models import Formation
    formations = list(
        Formation.objects.order_by('titre').values('id', 'titre', 'slug')
    )
    for f in formations:
        f['title'] = f.pop('titre')
    return JsonResponse({'formations': formations})


@staff_only
def api_formation_modules(request, slug):
    """GET /api/formations/<slug>/modules/ — list modules for a formation."""
    from formation.models import Formation, FormationModule
    formation = get_object_or_404(Formation, slug=slug)
    modules = list(
        FormationCourseModule.objects.filter(formation=formation).order_by('ordre').values('id', 'titre', 'ordre')
    )
    return JsonResponse({'modules': modules})


@staff_only
def api_formation_module_lessons(request, module_id):
    """GET /api/formation-modules/<id>/lessons/ — list lessons for a formation module."""
    from formation.models import FormationModule, FormationLesson
    module = get_object_or_404(FormationModule, id=module_id)
    lessons = list(
        FormationLesson.objects.filter(module=module).order_by('ordre').values('id', 'titre', 'ordre')
    )
    return JsonResponse({'lessons': lessons})


@staff_only
@require_POST
def api_formation_lesson_insert_sandbox(request, lesson_id):
    """POST /api/formation-lessons/<id>/insert-sandbox/ — append [SANDBOX] to formation lesson."""
    from formation.models import FormationLesson
    lesson = get_object_or_404(FormationLesson, id=lesson_id)
    try:
        body   = json.loads(request.body)
        marker = body.get('marker', '').strip()
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    if not marker:
        return JsonResponse({'error': 'Empty marker'}, status=400)
    lesson.contenu = (lesson.contenu or '') + '\n\n' + marker
    lesson.save(update_fields=['contenu'])
    return JsonResponse({'success': True, 'lesson_title': lesson.titre})
