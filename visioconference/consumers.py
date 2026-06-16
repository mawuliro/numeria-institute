import json
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import ChatMessage, MeetingParticipant, MeetingRoom

User = get_user_model()


class MeetingConsumer(AsyncWebsocketConsumer):
    room_participants = {}
    room_peer_channels = {}
    channel_peer_map = {}
    room_waiting_requests = {}

    async def connect(self):
        self.room_code = self.scope['url_route']['kwargs']['room_code']
        self.room_group_name = f'visio_{self.room_code}'
        self.user = self.scope['user']
        self.peer_id = None
        self.username = self.user.get_full_name() if self.user.is_authenticated else 'Invité'
        self.user_id = self.user.id if self.user.is_authenticated else None

        room = await self.get_room(self.room_code)
        if not self.user.is_authenticated or not room or not room.is_active:
            await self.close(code=4001)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        MeetingConsumer.room_participants.setdefault(self.room_code, {})[self.channel_name] = {
            'peer_id': None,
            'username': self.username,
            'user_id': self.user_id,
        }
        await self.accept()

    async def disconnect(self, code):
        peer_id = MeetingConsumer.channel_peer_map.pop(self.channel_name, None)
        MeetingConsumer.room_participants.get(self.room_code, {}).pop(self.channel_name, None)
        if peer_id:
            MeetingConsumer.room_peer_channels.get(self.room_code, {}).pop(peer_id, None)
            MeetingConsumer.room_waiting_requests.get(self.room_code, {}).pop(peer_id, None)

        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

        if peer_id:
            await self.broadcast({
                'type': 'user_left',
                'peer_id': peer_id,
                'username': self.username,
            })
            await self.mark_participant_left(self.room_code, peer_id)
            await self.broadcast_waiting_list(self.room_code)

    async def receive(self, text_data=None, bytes_data=None):
        try:
            data = json.loads(text_data or '{}')
        except json.JSONDecodeError:
            return

        action = data.get('type')
        if action == 'join':
            await self.handle_join(data)
        elif action == 'leave':
            await self.handle_leave(data)
        elif action == 'waiting_request':
            await self.handle_waiting_request(data)
        elif action == 'admit_participant':
            await self.handle_admit_participant(data)
        elif action == 'reject_participant':
            await self.handle_reject_participant(data)
        elif action == 'remove_participant':
            await self.handle_remove_participant(data)
        elif action in {'offer', 'answer', 'ice_candidate'}:
            await self.forward_signal(data)
        elif action == 'chat':
            await self.handle_chat(data)
        elif action in {'raise_hand', 'mute_status', 'camera_status'}:
            await self.handle_state_change(data)
        elif action == 'mute_all':
            await self.handle_mute_all()
        elif action == 'camera_off_all':
            await self.handle_camera_off_all()
        elif action == 'end_meeting':
            await self.handle_end_meeting()

    async def broadcast(self, event):
        await self.channel_layer.group_send(self.room_group_name, {'type': 'broadcast_event', 'event': event})

    async def broadcast_event(self, event):
        await self.send(text_data=json.dumps(event['event']))

    async def handle_join(self, data):
        peer_id = data.get('peer_id')
        username = data.get('username') or self.username
        user_id = data.get('user_id') or self.user_id

        if not peer_id:
            await self.send(text_data=json.dumps({'type': 'error', 'message': 'Identifiant de session manquant.'}))
            return

        room = await self.get_room(self.room_code)
        if not room or not room.is_active:
            await self.send(text_data=json.dumps({'type': 'error', 'message': 'La réunion n’est pas disponible.'}))
            return

        existing = await self.get_active_participant(room)
        if existing and not existing.is_approved and room.host_id != self.user.id:
            await self.send(text_data=json.dumps({'type': 'error', 'message': 'Vous devez patienter dans la salle d’attente.'}))
            return
        if not existing and room.host_id != self.user.id and room.waiting_room:
            await self.send(text_data=json.dumps({'type': 'error', 'message': 'Vous devez rejoindre la salle d’attente pour être admis.'}))
            return

        if not await self.has_capacity(room, peer_id):
            await self.send(text_data=json.dumps({'type': 'error', 'message': 'La réunion a atteint sa capacité maximale.'}))
            return

        self.peer_id = peer_id
        self.username = username
        self.user_id = user_id
        MeetingConsumer.room_participants.setdefault(self.room_code, {})[self.channel_name] = {
            'peer_id': peer_id,
            'username': username,
            'user_id': user_id,
        }
        MeetingConsumer.room_peer_channels.setdefault(self.room_code, {})[peer_id] = self.channel_name
        MeetingConsumer.channel_peer_map[self.channel_name] = peer_id

        await self.save_participant(room, self.user, peer_id, username)
        existing = await self.get_participants(room)
        recent_messages = await self.get_recent_messages(room)

        await self.send(text_data=json.dumps({
            'type': 'participants_list',
            'participants': existing,
            'chat_history': recent_messages,
        }))

        await self.broadcast({
            'type': 'user_joined',
            'peer_id': peer_id,
            'username': username,
            'user_id': user_id,
        })

        if room.host_id == self.user.id:
            await self.broadcast_waiting_list(self.room_code)

    async def handle_leave(self, data):
        peer_id = data.get('peer_id') or self.peer_id
        room = await self.get_room(self.room_code)
        if not room or not peer_id:
            return

        await self.mark_participant_left(self.room_code, peer_id)
        MeetingConsumer.channel_peer_map.pop(self.channel_name, None)
        MeetingConsumer.room_peer_channels.get(self.room_code, {}).pop(peer_id, None)
        MeetingConsumer.room_waiting_requests.get(self.room_code, {}).pop(peer_id, None)
        MeetingConsumer.room_participants.get(self.room_code, {}).pop(self.channel_name, None)

        await self.broadcast({
            'type': 'user_left',
            'peer_id': peer_id,
            'username': self.username,
        })
        await self.broadcast_waiting_list(self.room_code)

    async def forward_signal(self, data):
        target = data.get('target')
        if not target:
            return
        payload = {
            'type': data['type'],
            'target': target,
            'from': self.peer_id,
            'username': self.username,
        }
        if data['type'] in {'offer', 'answer'}:
            payload['sdp'] = data.get('sdp')
        else:
            payload['candidate'] = data.get('candidate')
        await self.send_to_peer(target, payload)

    async def handle_chat(self, data):
        room = await self.get_room(self.room_code)
        if not room:
            return
        message_text = (data.get('message') or '').strip()
        if not message_text:
            return
        message = await self.save_chat_message(room, self.user, message_text)
        await self.broadcast({
            'type': 'chat',
            'sender': self.username,
            'message': message.content,
            'timestamp': message.timestamp.isoformat(),
        })

    async def handle_waiting_request(self, data):
        peer_id = data.get('peer_id')
        username = data.get('username') or self.username
        user_id = data.get('user_id') or self.user_id

        if not peer_id:
            await self.send(text_data=json.dumps({'type': 'error', 'message': 'Identifiant de session manquant.'}))
            return

        room = await self.get_room(self.room_code)
        if not room or not room.is_active:
            await self.send(text_data=json.dumps({'type': 'error', 'message': 'La réunion n’est pas disponible.'}))
            return

        if not await self.has_capacity(room, peer_id):
            await self.send(text_data=json.dumps({'type': 'error', 'message': 'La réunion a atteint sa capacité maximale.'}))
            return

        self.peer_id = peer_id
        self.username = username
        self.user_id = user_id
        MeetingConsumer.room_participants.setdefault(self.room_code, {})[self.channel_name] = {
            'peer_id': peer_id,
            'username': username,
            'user_id': user_id,
        }
        MeetingConsumer.room_peer_channels.setdefault(self.room_code, {})[peer_id] = self.channel_name
        MeetingConsumer.channel_peer_map[self.channel_name] = peer_id
        MeetingConsumer.room_waiting_requests.setdefault(self.room_code, {})[peer_id] = self.channel_name

        await self.save_participant(room, self.user, peer_id, username, approved=False)
        await self.send(text_data=json.dumps({'type': 'waiting', 'message': 'En attente d’admission de l’hôte.'}))
        await self.broadcast_waiting_list(self.room_code)

    async def handle_admit_participant(self, data):
        target = data.get('target')
        room = await self.get_room(self.room_code)
        if not room or room.host_id != self.user.id:
            return
        if not target:
            return

        participant = await self.admit_participant(room, target)
        if not participant:
            return

        MeetingConsumer.room_waiting_requests.get(self.room_code, {}).pop(target, None)
        await self.broadcast_waiting_list(self.room_code)
        await self.send_to_peer(target, {'type': 'admitted'})

    async def handle_reject_participant(self, data):
        target = data.get('target')
        room = await self.get_room(self.room_code)
        if not room or room.host_id != self.user.id:
            return
        if not target:
            return

        await self.reject_participant(room, target)
        MeetingConsumer.room_waiting_requests.get(self.room_code, {}).pop(target, None)
        await self.send_to_peer(target, {'type': 'rejected', 'message': 'Votre demande a été refusée par l’hôte.'})
        await self.broadcast_waiting_list(self.room_code)

    async def handle_remove_participant(self, data):
        target = data.get('target')
        room = await self.get_room(self.room_code)
        if not room or room.host_id != self.user.id:
            return
        if not target:
            return

        await self.mark_participant_left(self.room_code, target)
        MeetingConsumer.room_waiting_requests.get(self.room_code, {}).pop(target, None)
        await self.send_to_peer(target, {'type': 'removed', 'message': 'Vous avez été retiré de la réunion par l’hôte.'})
        await self.broadcast({
            'type': 'user_left',
            'peer_id': target,
            'username': '',
        })
        await self.broadcast_waiting_list(self.room_code)

    async def handle_state_change(self, data):
        event_type = data.get('type')
        peer_id = data.get('peer_id') or self.peer_id
        value = data.get('value')
        if not peer_id:
            return
        await self.broadcast({
            'type': event_type,
            'peer_id': peer_id,
            'value': value,
        })

    async def handle_mute_all(self):
        room = await self.get_room(self.room_code)
        if not room or room.host_id != self.user.id:
            return
        await self.broadcast({'type': 'mute_all'})

    async def handle_camera_off_all(self):
        room = await self.get_room(self.room_code)
        if not room or room.host_id != self.user.id:
            return
        await self.broadcast({'type': 'camera_off_all'})

    async def handle_end_meeting(self):
        room = await self.get_room(self.room_code)
        if not room or room.host_id != self.user.id:
            return
        await self.deactivate_room(room)
        await self.broadcast({'type': 'meeting_ended'})

    async def send_to_peer(self, peer_id, event):
        channel_name = MeetingConsumer.room_peer_channels.get(self.room_code, {}).get(peer_id)
        if not channel_name:
            return
        await self.channel_layer.send(channel_name, {'type': 'direct_event', 'event': event})

    async def direct_event(self, event):
        await self.send(text_data=json.dumps(event['event']))

    async def broadcast_waiting_list(self, room_code):
        waiting = await self.get_waiting_requests(room_code)
        await self.broadcast({'type': 'waiting_list', 'waiting': waiting})

    @database_sync_to_async
    def get_waiting_requests(self, room_code):
        try:
            room = MeetingRoom.objects.get(room_code=room_code)
        except MeetingRoom.DoesNotExist:
            return []
        return [
            {
                'peer_id': participant.peer_id,
                'username': participant.display_name or participant.user.get_full_name() or participant.user.username,
            }
            for participant in room.participants.filter(left_at__isnull=True, is_approved=False).order_by('joined_at')
        ]

    @database_sync_to_async
    def has_capacity(self, room, peer_id):
        active_count = room.participants.filter(left_at__isnull=True, is_approved=True).count()
        if room.participants.filter(room=room, user=self.user, left_at__isnull=True).exists():
            return True
        return active_count < room.max_participants

    @database_sync_to_async
    def get_active_participant(self, room):
        return room.participants.filter(user=self.user, left_at__isnull=True).first()

    @database_sync_to_async
    def admit_participant(self, room, peer_id):
        participant = room.participants.filter(peer_id=peer_id, left_at__isnull=True).first()
        if participant:
            participant.is_approved = True
            participant.save()
        return participant

    @database_sync_to_async
    def reject_participant(self, room, peer_id):
        participant = room.participants.filter(peer_id=peer_id, left_at__isnull=True).first()
        if participant:
            participant.left_at = timezone.now()
            participant.save()
        return participant

    @database_sync_to_async
    def get_room(self, room_code):
        try:
            return MeetingRoom.objects.get(room_code=room_code)
        except MeetingRoom.DoesNotExist:
            return None

    @database_sync_to_async
    def get_participants(self, room):
        items = []
        for participant in room.participants.filter(left_at__isnull=True, is_approved=True).order_by('joined_at'):
            items.append({
                'peer_id': participant.peer_id,
                'username': participant.display_name or participant.user.get_full_name() or participant.user.username,
                'is_host': participant.is_host,
            })
        return items

    @database_sync_to_async
    def get_recent_messages(self, room):
        messages = list(room.messages.order_by('-timestamp')[:30])
        messages.reverse()
        return [
            {
                'sender': message.sender.get_full_name() or message.sender.username,
                'message': message.content,
                'timestamp': message.timestamp.isoformat(),
            }
            for message in messages
        ]

    @database_sync_to_async
    def save_participant(self, room, user, peer_id, display_name, approved=True):
        participant, created = MeetingParticipant.objects.get_or_create(
            room=room,
            user=user,
            defaults={
                'peer_id': peer_id,
                'display_name': display_name,
                'is_host': room.host_id == user.id,
                'is_approved': room.host_id == user.id or approved,
            }
        )
        if not created:
            participant.peer_id = peer_id
            participant.display_name = display_name
            if participant.is_host or participant.is_approved:
                participant.is_approved = True
            participant.left_at = None
            participant.save()
        return participant

    @database_sync_to_async
    def mark_participant_left(self, room_code, peer_id):
        try:
            room = MeetingRoom.objects.get(room_code=room_code)
            participant = room.participants.filter(peer_id=peer_id, left_at__isnull=True).first()
            if participant:
                participant.left_at = timezone.now()
                participant.save()
        except MeetingRoom.DoesNotExist:
            pass

    @database_sync_to_async
    def save_chat_message(self, room, user, message_text):
        return ChatMessage.objects.create(room=room, sender=user, content=message_text)

    @database_sync_to_async
    def deactivate_room(self, room):
        room.is_active = False
        room.save()
