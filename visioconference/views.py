from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import ChatMessage, MeetingParticipant, MeetingRoom


def create_room(request):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect(f"{reverse('comptes:connexion')}?next={request.path}")

        title = request.POST.get('title', '').strip() or 'Réunion Numeria'
        max_participants = request.POST.get('max_participants', '6').strip()
        password = request.POST.get('password', '').strip()

        try:
            max_participants = min(20, max(2, int(max_participants)))
        except ValueError:
            max_participants = 6

        room = MeetingRoom(host=request.user, title=title, max_participants=max_participants)
        if password:
            room.set_password(password)
        room.save()
        messages.success(request, 'Salle créée avec succès. Vous pouvez inviter des participants en partageant le lien.')
        return redirect('visioconference:meeting_room', room_code=room.room_code)

    return render(request, 'visioconference/create_join.html', {'create_mode': True})


def join_room(request):
    if request.method == 'POST':
        room_code = request.POST.get('room_code', '').strip().upper()
        password = request.POST.get('password', '').strip()
        room = MeetingRoom.objects.filter(room_code=room_code, is_active=True).first()

        if not room:
            messages.error(request, 'Aucune salle active ne correspond à ce code.')
            return redirect('visioconference:create_room')

        if room.password and not room.check_password(password):
            messages.error(request, 'Mot de passe incorrect pour cette salle.')
            return redirect('visioconference:join_room')

        if not room.has_capacity():
            messages.error(request, 'La salle est complète. Essayez une autre réunion ou demandez l’admission.')
            return redirect('visioconference:join_room')

        return redirect('visioconference:meeting_room', room_code=room.room_code)

    return render(request, 'visioconference/create_join.html', {'join_mode': True})


@login_required
def meeting_room(request, room_code):
    room = get_object_or_404(MeetingRoom, room_code=room_code)
    if not room.is_active:
        messages.error(request, 'Cette réunion a été terminée.')
        return redirect('visioconference:create_room')

    if room.password and request.GET.get('joined') != '1' and request.method == 'GET' and request.GET.get('password') is None:
        if room.host != request.user:
            messages.warning(request, 'Ce salon nécessite un mot de passe. Veuillez rejoindre la réunion depuis la page de connexion.')
            return redirect('visioconference:join_room')

    display_name = request.GET.get('display_name') or request.user.get_full_name() or request.user.username
    joined = request.GET.get('joined') == '1'
    participants = room.active_participants().select_related('user')
    pending_participants = room.pending_participants().select_related('user')
    chat_history = ChatMessage.objects.filter(room=room).order_by('timestamp')[:50]

    context = {
        'room': room,
        'display_name': display_name,
        'joined': joined,
        'is_host': room.host == request.user,
        'participants': participants,
        'pending_participants': pending_participants,
        'chat_history': chat_history,
    }

    if joined:
        return render(request, 'visioconference/meeting_room.html', context)
    return render(request, 'visioconference/lobby.html', context)


@login_required
def end_meeting(request, room_code):
    room = get_object_or_404(MeetingRoom, room_code=room_code)
    if room.host != request.user:
        return HttpResponseForbidden('Seul l’hôte peut terminer la réunion.')

    if request.method == 'POST':
        room.is_active = False
        room.save()
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'visio_{room_code}',
            {
                'type': 'broadcast_event',
                'event': {'type': 'meeting_ended'},
            }
        )
        participants = room.participants.order_by('joined_at')
        chat_history = ChatMessage.objects.filter(room=room).order_by('timestamp')
        duration_seconds = 0
        if participants.exists():
            first_join = participants.first().joined_at
            duration_seconds = int((timezone.now() - first_join).total_seconds())

        hours = duration_seconds // 3600
        minutes = (duration_seconds % 3600) // 60
        seconds = duration_seconds % 60
        duration_text = f"{hours:02d}h {minutes:02d}m {seconds:02d}s"

        return render(request, 'visioconference/post_meeting.html', {
            'room': room,
            'participants': participants,
            'chat_history': chat_history,
            'duration_text': duration_text,
        })

    raise Http404()
