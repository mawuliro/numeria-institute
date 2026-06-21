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


@login_required
def video_session(request, session_pk):
    back_url = request.META.get('HTTP_REFERER', '/')
    current_user_name = request.user.get_full_name() or request.user.username
    context = {
        'room_type': 'formation_session',
        'room_pk': session_pk,
        'room_title': f'Visioconférence de formation #{session_pk}',
        'room_description': 'Session de formation en visioconférence',
        'room_modalite': 'Visio',
        'room_date': '',
        'room_time': '',
        'room_duration': '',
        'room_participants': [
            {
                'id': request.user.id,
                'name': current_user_name,
                'role': 'Participant',
            },
        ],
        'participants_count': 1,
        'participant_label': 'Participants',
        'current_user_id': request.user.id,
        'current_user_name': current_user_name,
        'role_label': 'Participant',
        'back_url': back_url,
        'back_label': 'Retour',
        'room_notes': 'Activez votre micro et votre caméra, puis rejoignez la session.',
    }
    return render(request, 'video_room.html', context)

