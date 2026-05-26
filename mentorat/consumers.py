import json
from collections import defaultdict

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model

from .models import SeanceMentorat
from formation.models import SessionFormation, InscriptionFormation

User = get_user_model()
ACTIVE_VIDEO_ROOMS = defaultdict(set)

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

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        ACTIVE_VIDEO_ROOMS[self.room_group_name].add(user.id)
        await self.accept()

        existing_participants = [uid for uid in ACTIVE_VIDEO_ROOMS[self.room_group_name] if uid != user.id]
        await self.send(text_data=json.dumps({
            'signal_type': 'peer_list',
            'user_ids': existing_participants,
        }))

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'peer.status',
                'event': 'peer_announce',
                'user_id': user.id,
            }
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        user = self.scope['user']
        if user.is_authenticated:
            ACTIVE_VIDEO_ROOMS[self.room_group_name].discard(user.id)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'peer.status',
                    'event': 'peer_left',
                    'user_id': user.id,
                }
            )

    async def receive(self, text_data=None, bytes_data=None):
        if text_data is None:
            return

        data = json.loads(text_data)
        signal_type = data.get('signal_type')
        payload = data.get('payload', {})
        user = self.scope['user']

        if signal_type == 'peer_announce':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'peer.status',
                    'event': 'peer_announce',
                    'user_id': user.id,
                }
            )
            return

        if signal_type not in {'sdp-offer', 'sdp-answer', 'ice-candidate'}:
            return

        target_id = payload.get('target_id')
        if target_id is None:
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'signal.message',
                'sender_id': user.id,
                'target_id': target_id,
                'signal_type': signal_type,
                'payload': payload,
            }
        )

    async def signal_message(self, event):
        await self.send(text_data=json.dumps({
            'sender_id': event['sender_id'],
            'target_id': event['target_id'],
            'signal_type': event['signal_type'],
            'payload': event['payload'],
        }))

    async def peer_status(self, event):
        await self.send(text_data=json.dumps({
            'signal_type': event['event'],
            'user_id': event['user_id'],
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
