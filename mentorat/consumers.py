import json
from collections import defaultdict

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model

from .models import SeanceMentorat
from formation.models import SessionFormation, InscriptionFormation

User = get_user_model()
ACTIVE_VIDEO_ROOMS = defaultdict(dict)
CHANNEL_CLIENT_INFO = {}

class VideoChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_type = self.scope['url_route']['kwargs'].get('room_type') or 'mentorat_seance'
        self.room_pk = self.scope['url_route']['kwargs'].get('room_pk') or self.scope['url_route']['kwargs'].get('seance_pk')
        self.room_group_name = f'video_{self.room_type}_{self.room_pk}'

        user = self.scope['user']
        if not user.is_authenticated:
            await self.close()
            return

        self.room = await self.get_room(self.room_type, self.room_pk)
        if not self.room or not await self.is_authorized(user, self.room_type, self.room):
            await self.close()
            return

        CHANNEL_CLIENT_INFO[self.channel_name] = {
            'room_group_name': self.room_group_name,
            'user_id': user.id,
            'client_id': None,
        }

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        client_info = CHANNEL_CLIENT_INFO.get(self.channel_name)
        if client_info:
            client_id = client_info.get('client_id')
            user_id = client_info.get('user_id')
            if client_id:
                ACTIVE_VIDEO_ROOMS[self.room_group_name].pop(client_id, None)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'peer.status',
                        'event': 'peer_left',
                        'user_id': user_id,
                        'client_id': client_id,
                    }
                )
            CHANNEL_CLIENT_INFO.pop(self.channel_name, None)

    async def receive(self, text_data=None, bytes_data=None):
        if text_data is None:
            return

        data = json.loads(text_data)
        signal_type = data.get('signal_type')
        payload = data.get('payload', {})
        user = self.scope['user']
        client_info = CHANNEL_CLIENT_INFO.get(self.channel_name)
        if not client_info:
            return

        if signal_type == 'peer_announce':
            client_id = payload.get('client_id')
            if not client_id:
                return

            previous_id = client_info.get('client_id')
            if previous_id and previous_id != client_id:
                ACTIVE_VIDEO_ROOMS[self.room_group_name].pop(previous_id, None)

            client_info['client_id'] = client_id
            ACTIVE_VIDEO_ROOMS[self.room_group_name][client_id] = {
                'channel_name': self.channel_name,
                'user_id': user.id,
            }

            existing_participants = [
                {'client_id': cid, 'user_id': info['user_id']}
                for cid, info in ACTIVE_VIDEO_ROOMS[self.room_group_name].items()
                if cid != client_id
            ]
            await self.send(text_data=json.dumps({
                'signal_type': 'peer_list',
                'peers': existing_participants,
            }))

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'peer.status',
                    'event': 'peer_announce',
                    'user_id': user.id,
                    'client_id': client_id,
                }
            )
            return

        if signal_type not in {'sdp-offer', 'sdp-answer', 'ice-candidate'}:
            return

        if not client_info.get('client_id'):
            return

        target_id = payload.get('target_client_id') or payload.get('target_id')
        if target_id is None:
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'signal.message',
                'sender_client_id': client_info.get('client_id'),
                'target_client_id': target_id,
                'signal_type': signal_type,
                'payload': payload,
            }
        )

    async def signal_message(self, event):
        await self.send(text_data=json.dumps({
            'sender_client_id': event['sender_client_id'],
            'target_client_id': event['target_client_id'],
            'signal_type': event['signal_type'],
            'payload': event['payload'],
        }))

    async def peer_status(self, event):
        await self.send(text_data=json.dumps({
            'signal_type': event['event'],
            'user_id': event['user_id'],
            'client_id': event.get('client_id'),
        }))

    @database_sync_to_async
    def get_room(self, room_type, room_pk):
        if room_type == 'mentorat_seance':
            try:
                return SeanceMentorat.objects.select_related(
                    'relation__mentor__profil__utilisateur',
                    'relation__mentee__profil__utilisateur'
                ).get(pk=room_pk, statut='planifiee')
            except SeanceMentorat.DoesNotExist:
                return None

        if room_type == 'formation_session':
            try:
                return SessionFormation.objects.select_related('formation').get(pk=room_pk)
            except SessionFormation.DoesNotExist:
                return None

        return None

    @database_sync_to_async
    def is_authorized(self, user, room_type, room):
        if not hasattr(user, 'profil'):
            return False

        if room_type == 'mentorat_seance':
            profile = user.profil
            return (
                hasattr(profile, 'mentorat_mentor') and room.relation.mentor == profile.mentorat_mentor
            ) or (
                hasattr(profile, 'mentorat_mentee') and room.relation.mentee == profile.mentorat_mentee
            )

        if room_type == 'formation_session':
            if room.statut == 'annulee':
                return False

            if room.get_instructeurs().filter(pk=user.pk).exists():
                return True

            return InscriptionFormation.objects.filter(
                session=room,
                etudiant=user,
                statut__in=['confirmee', 'en_cours', 'terminee']
            ).exists()

        return False
