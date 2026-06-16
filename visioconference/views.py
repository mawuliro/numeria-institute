from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .models import ChatMessage, MeetingParticipant, MeetingRoom


def create_room(request):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect(f"{reverse('comptes:connexion')}?next={request.path}")

        title = request.POST.get('title', '').strip() or 'Réunion Numeria'
        max_participants = request.POST.get('max_participants', '10').strip()
        password = request.POST.get('password', '').strip() or None

        try:
            max_participants = int(max_participants)
        except ValueError:
            max_participants = 10

        max_participants = max(2, min(max_participants, 20))

        room = MeetingRoom(host=request.user, title=title, max_participants=max_participants, password=password)
        room.save()
        messages.success(request, 'Salle créée. Rejoignez le lobby pour préparer votre réunion.')
        return redirect('visioconference:lobby', room_code=room.room_code)

    return render(request, 'visioconference/create_join.html', {
        'page_title': 'Créer une réunion',
        'create_mode': True,
    })


def join_room(request):
    error = None
    if request.method == 'POST':
        room_code = (request.POST.get('room_code') or '').strip().upper()
        password = request.POST.get('password', '').strip()
        room = MeetingRoom.objects.filter(room_code=room_code, is_active=True).first()

        if not room:
            error = 'Aucune réunion active n’a été trouvée pour ce code.'
        elif room.password and room.password != password:
            error = 'Mot de passe invalide pour cette réunion.'
        elif not room.has_capacity():
            error = 'La réunion a atteint sa capacité maximale.'
        else:
            return redirect('visioconference:lobby', room_code=room.room_code)

        messages.error(request, error)

    return render(request, 'visioconference/create_join.html', {
        'page_title': 'Rejoindre une réunion',
        'join_mode': True,
    })


def lobby(request, room_code):
    room = get_object_or_404(MeetingRoom, room_code=room_code, is_active=True)
    return render(request, 'visioconference/lobby.html', {
        'room': room,
        'room_title': room.title,
        'display_name': request.user.get_full_name() or request.user.username if request.user.is_authenticated else 'Invité',
    })


@login_required
def meeting_room(request, room_code):
    room = get_object_or_404(MeetingRoom, room_code=room_code)
    if not room.is_active:
        messages.error(request, 'Cette réunion a été terminée.')
        return redirect('visioconference:create_room')

    participant, created = MeetingParticipant.objects.get_or_create(
        room=room,
        user=request.user,
        defaults={
            'is_host': room.host_id == request.user.id,
            'display_name': request.user.get_full_name() or request.user.username,
            'is_approved': room.host_id == request.user.id,
        }
    )
    if not created and participant.left_at is not None:
        participant.left_at = None
        participant.save()

    scheme = 'wss' if request.is_secure() else 'ws'
    ws_url = f"{scheme}://{request.get_host()}/ws/visio/{room.room_code}/"

    return render(request, 'visioconference/meeting_room.html', {
        'room': room,
        'is_host': room.host == request.user,
        'ws_url': ws_url,
    })


@login_required
def waiting_room(request, room_code):
    room = get_object_or_404(MeetingRoom, room_code=room_code, is_active=True)
    if room.host == request.user:
        return redirect('visioconference:meeting_room', room_code=room.room_code)

    participant = MeetingParticipant.objects.filter(room=room, user=request.user, left_at__isnull=True).first()
    if participant and participant.is_approved:
        return redirect('visioconference:meeting_room', room_code=room.room_code)

    scheme = 'wss' if request.is_secure() else 'ws'
    ws_url = f"{scheme}://{request.get_host()}/ws/visio/{room.room_code}/"

    return render(request, 'visioconference/waiting_room.html', {
        'room': room,
        'host_name': room.host.get_full_name() or room.host.username,
        'display_name': request.user.get_full_name() or request.user.username,
        'ws_url': ws_url,
    })


@login_required
def end_meeting(request, room_code):
    room = get_object_or_404(MeetingRoom, room_code=room_code)
    if room.host != request.user:
        return HttpResponseForbidden('Seul l’hôte peut terminer la réunion.')

    if request.method == 'POST':
        room.is_active = False
        room.save()
        messages.success(request, 'La réunion a été terminée pour tous les participants.')
        return redirect('accueil')

    raise Http404()
