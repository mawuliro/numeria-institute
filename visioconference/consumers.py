import json
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import MeetingRoom, MeetingParticipant, ChatMessage

User = get_user_model()


class MeetingConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.room_code = self.scope['url_route']['kwargs']['room_code']
        self.room_group_name = f'visio_{self.room_code}'
        self.user = self.scope['user']
        self.peer_id = None

        if not self.user.is_authenticated:
            await self.close(code=4001)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if self.peer_id:
            await self.leave_room({'peer_id': self.peer_id})
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        event_type = content.get('type')

        if event_type == 'join_room':
            await self.join_room(content)
        elif event_type == 'leave_room':
            await self.leave_room(content)
        elif event_type == 'offer':
            await self.forward_signal('offer', content)
        elif event_type == 'answer':
            await self.forward_signal('answer', content)
        elif event_type == 'ice_candidate':
            await self.forward_signal('ice_candidate', content)
        elif event_type == 'chat_message':
            await self.chat_message(content)
        elif event_type == 'raise_hand':
            await self.participant_state_change(content, 'raise_hand')
        elif event_type == 'mute_status':
            await self.participant_state_change(content, 'mute_status')
        elif event_type == 'camera_status':
            await self.participant_state_change(content, 'camera_status')
        elif event_type == 'admit_participant':
            await self.admit_participant(content)

    async def broadcast_event(self, event):
        await self.send_json(event['event'])

    async def join_room(self, content):
        room = await self.get_room(self.room_code)
        if not room or not room.is_active:
            await self.send_json({'type': 'error', 'message': 'Cette réunion n’est plus active.'})
            return

        self.peer_id = content.get('peer_id')
        display_name = content.get('display_name') or self.user.get_full_name() or self.user.username
        if not self.peer_id:
            await self.send_json({'type': 'error', 'message': 'Identifiant de session manquant.'})
            return

        if room.host_id != self.user.id and not await self.room_has_capacity(room):
            await self.send_json({'type': 'error', 'message': 'La salle a atteint sa capacité maximale.'})
            return

        is_host = room.host_id == self.user.id
        participant = await self.create_participant(room, self.user, display_name, self.peer_id, is_host=is_host)

        participants = await self.fetch_active_participants(room)
        pending = await self.fetch_pending_participants(room)

        await self.send_json({
            'type': 'room_state',
            'room': {
                'room_code': room.room_code,
                'title': room.title,
                'host': room.host.get_full_name() or room.host.username,
                'max_participants': room.max_participants,
            },
            'participants': participants,
            'pending': pending,
            'is_host': is_host,
        })

        if is_host:
            await self.group_send({
                'type': 'broadcast_event',
                'event': {
                    'type': 'host_arrived',
                    'peer_id': self.peer_id,
                    'display_name': display_name,
                }
            })
            return

        if room.waiting_room:
            await self.send_json({'type': 'waiting_for_admission'})
            await self.group_send({
                'type': 'broadcast_event',
                'event': {
                    'type': 'waiting_room_request',
                    'peer_id': self.peer_id,
                    'display_name': display_name,
                    'requested_by': display_name,
                }
            })
            return

        await self.approve_participant(room, participant, notify=False)
        await self.group_send({
            'type': 'broadcast_event',
            'event': {
                'type': 'participant_join',
                'peer_id': participant.peer_id,
                'display_name': participant.display_name,
            }
        })

    async def leave_room(self, content):
        peer_id = content.get('peer_id') or self.peer_id
        room = await self.get_room(self.room_code)
        if not room:
            return

        participant = await self.deactivate_participant(room, peer_id)
        if not participant:
            return

        await self.group_send({
            'type': 'broadcast_event',
            'event': {
                'type': 'participant_leave',
                'peer_id': peer_id,
                'display_name': participant.display_name,
            }
        })

    async def forward_signal(self, signal_type, content):
        target = content.get('target')
        if not target:
            return
        await self.group_send({
            'type': 'broadcast_event',
            'event': {
                'type': signal_type,
                'target': target,
                'sender': self.peer_id,
                'sender_display_name': self.user.get_full_name() or self.user.username,
                'sdp': content.get('sdp'),
                'candidate': content.get('candidate'),
            }
        })

    async def chat_message(self, content):
        room = await self.get_room(self.room_code)
        if not room:
            return
        message_text = content.get('message', '').strip()
        if not message_text:
            return

        message = await self.save_chat_message(room, self.user, message_text)
        await self.group_send({
            'type': 'broadcast_event',
            'event': {
                'type': 'chat_message',
                'sender': self.user.get_full_name() or self.user.username,
                'content': message.content,
                'timestamp': message.timestamp.isoformat(),
            }
        })

    async def participant_state_change(self, content, state_type):
        room = await self.get_room(self.room_code)
        if not room:
            return
        await self.update_participant_state(room, self.peer_id, state_type, content.get('value'))
        await self.group_send({
            'type': 'broadcast_event',
            'event': {
                'type': state_type,
                'peer_id': self.peer_id,
                'value': content.get('value'),
            }
        })

    async def admit_participant(self, content):
        room = await self.get_room(self.room_code)
        if not room or room.host_id != self.user.id:
            await self.send_json({'type': 'error', 'message': 'Seul l’hôte peut admettre les participants.'})
            return

        peer_id = content.get('peer_id')
        participant = await self.get_pending_participant(room, peer_id)
        if not participant:
            await self.send_json({'type': 'error', 'message': 'Participant introuvable ou déjà admis.'})
            return

        participant = await self.approve_participant(room, participant)
        await self.group_send({
            'type': 'broadcast_event',
            'event': {
                'type': 'participant_join',
                'peer_id': participant.peer_id,
                'display_name': participant.display_name,
            }
        })
        await self.group_send({
            'type': 'broadcast_event',
            'event': {
                'type': 'participant_approved',
                'peer_id': peer_id,
            }
        })

    async def group_send(self, message):
        await self.channel_layer.group_send(self.room_group_name, message)

    @database_sync_to_async
    def get_room(self, room_code):
        try:
            return MeetingRoom.objects.get(room_code=room_code)
        except MeetingRoom.DoesNotExist:
            return None

    @database_sync_to_async
    def room_has_capacity(self, room):
        return room.has_capacity()

    @database_sync_to_async
    def create_participant(self, room, user, display_name, peer_id, is_host=False):
        participant, _ = MeetingParticipant.objects.get_or_create(
            room=room,
            user=user,
            peer_id=peer_id,
            defaults={
                'display_name': display_name,
                'is_host': is_host,
                'is_approved': is_host,
                'joined_at': timezone.now(),
            }
        )
        if not participant.is_approved and is_host:
            participant.is_approved = True
            participant.save()
        return participant

    @database_sync_to_async
    def fetch_active_participants(self, room):
        return [
            {
                'peer_id': participant.peer_id,
                'display_name': participant.display_name,
                'is_host': participant.is_host,
                'is_muted': participant.is_muted,
                'camera_on': participant.camera_on,
                'hand_raised': participant.hand_raised,
            }
            for participant in room.active_participants()
        ]

    @database_sync_to_async
    def fetch_pending_participants(self, room):
        return [
            {
                'peer_id': participant.peer_id,
                'display_name': participant.display_name,
            }
            for participant in room.pending_participants()
        ]

    @database_sync_to_async
    def deactivate_participant(self, room, peer_id):
        try:
            participant = MeetingParticipant.objects.filter(room=room, peer_id=peer_id, left_at__isnull=True).last()
            if not participant:
                return None
            participant.left_at = timezone.now()
            participant.save()
            return participant
        except MeetingParticipant.DoesNotExist:
            return None

    @database_sync_to_async
    def save_chat_message(self, room, user, message_text):
        return ChatMessage.objects.create(room=room, sender=user, content=message_text)

    @database_sync_to_async
    def update_participant_state(self, room, peer_id, state_type, value):
        kwargs = {}
        if state_type == 'raise_hand':
            kwargs['hand_raised'] = bool(value)
        elif state_type == 'mute_status':
            kwargs['is_muted'] = bool(value)
        elif state_type == 'camera_status':
            kwargs['camera_on'] = bool(value)
        MeetingParticipant.objects.filter(room=room, peer_id=peer_id, left_at__isnull=True).update(**kwargs)

    @database_sync_to_async
    def get_pending_participant(self, room, peer_id):
        return MeetingParticipant.objects.filter(room=room, peer_id=peer_id, left_at__isnull=True, is_approved=False).first()

    @database_sync_to_async
    def approve_participant(self, room, participant, notify=True):
        participant.is_approved = True
        participant.save()
        return participant
