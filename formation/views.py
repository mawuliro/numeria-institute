from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render

from .models import Formation, FormationLesson, InscriptionFormation
from cours.models import LessonBlock


def liste_formations(request):
    qs = Formation.objects.all()
    # For now: show published only to non-staff
    if not (request.user.is_authenticated and request.user.is_staff):
        qs = qs.filter(status='published')
    return render(request, 'formation/liste.html', {'formations': qs})


def detail_formation(request, slug):
    formation = get_object_or_404(Formation, slug=slug)
    if formation.status != 'published' and not (request.user.is_authenticated and request.user.is_staff):
        raise Http404()
    lessons = formation.lessons.filter(is_active=True).order_by('order')
    return render(request, 'formation/detail_formation.html', {'formation': formation, 'lessons': lessons})


@login_required
def voir_lecon(request, formation_slug, lesson_slug):
    formation = get_object_or_404(Formation, slug=formation_slug)
    lesson = get_object_or_404(FormationLesson, formation=formation, slug=lesson_slug, is_active=True)

    # Enrollment gate (or free preview)
    if not lesson.is_free_preview:
        ins = InscriptionFormation.objects.filter(formation=formation, etudiant=request.user).first()
        if not ins or ins.statut not in ('confirmee', 'en_cours', 'terminee'):
            return HttpResponseForbidden("Vous n'avez pas accès à cette formation.")

    blocks = LessonBlock.objects.filter(formation_lesson=lesson).order_by('order')

    return render(request, 'formation/voir_lecon.html', {
        'formation': formation,
        'lecon': lesson,
        'blocks': blocks,
    })

