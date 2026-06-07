import json
from collections import defaultdict

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import SeanceMentorat

# room_group_name -> { client_id: {channel_name, user_id, display_name} }
ACTIVE_VIDEO_ROOMS = defaultdict(dict)
# channel_name -> { room_group_name, user_id, client_id }
CHANNEL_CLIENTS = {}

RELAYED_SIGNAL_TYPES = {'sdp-offer', 'sdp-answer', 'ice-candidate'}


class VideoChatConsumer(AsyncWebsocketConsumer):
    """Salle de signalisation WebRTC pour les visioconférences mentorat/formation.

    Le navigateur gère la connexion peer-to-peer (audio/vidéo/écran) ; ce
    consumer ne fait que relayer les messages de signalisation (offres SDP,
    réponses, candidats ICE) et diffuser les événements de présence
    (arrivée/départ, chat, partage d'écran, main levée) à tous les membres
    du groupe de la salle.
    """

    async def connect(self):
        kwargs = self.scope['url_route']['kwargs']
        self.room_type = kwargs.get('room_type') or 'mentorat_seance'
        self.room_pk = kwargs.get('room_pk') or kwargs.get('seance_pk')
        self.room_group_name = f'video_{self.room_type}_{self.room_pk}'
        self.client_id = None

        user = self.scope['user']
        if not user.is_authenticated:
            await self.close()
            return

        room = await self.get_room(self.room_type, self.room_pk)
        if room is None or not await self.is_authorized(user, self.room_type, room):
            await self.close()
            return

        CHANNEL_CLIENTS[self.channel_name] = {
            'room_group_name': self.room_group_name,
            'user_id': user.id,
            'client_id': None,
        }

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

        client_info = CHANNEL_CLIENTS.pop(self.channel_name, None)
        if not client_info:
            return

        client_id = client_info.get('client_id')
        if client_id:
            ACTIVE_VIDEO_ROOMS[self.room_group_name].pop(client_id, None)
            await self.channel_layer.group_send(self.room_group_name, {
                'type': 'room.event',
                'event': 'peer_left',
                'user_id': client_info['user_id'],
                'client_id': client_id,
            })

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return
        try:
            data = json.loads(text_data)
        except (TypeError, ValueError):
            return

        signal_type = data.get('signal_type')
        payload = data.get('payload') or {}
        client_info = CHANNEL_CLIENTS.get(self.channel_name)
        if not client_info:
            return

        handler = {
            'peer_announce': self.handle_peer_announce,
            'screen_share': self.handle_screen_share,
            'chat': self.handle_chat,
            'raise_hand': self.handle_raise_hand,
        }.get(signal_type)

        if handler:
            await handler(client_info, payload)
        elif signal_type in RELAYED_SIGNAL_TYPES:
            await self.handle_relayed_signal(client_info, signal_type, payload)

    # ------------------------------------------------------------------
    # Incoming signal handlers
    # ------------------------------------------------------------------

    async def handle_peer_announce(self, client_info, payload):
        client_id = payload.get('client_id')
        if not client_id:
            return

        previous_id = client_info.get('client_id')
        if previous_id and previous_id != client_id:
            ACTIVE_VIDEO_ROOMS[self.room_group_name].pop(previous_id, None)

        user = self.scope['user']
        display_name = await self.get_display_name(user)

        client_info['client_id'] = client_id
        self.client_id = client_id
        ACTIVE_VIDEO_ROOMS[self.room_group_name][client_id] = {
            'channel_name': self.channel_name,
            'user_id': user.id,
            'display_name': display_name,
        }

        peers = [
            {'client_id': cid, 'user_id': info['user_id'], 'display_name': info['display_name']}
            for cid, info in ACTIVE_VIDEO_ROOMS[self.room_group_name].items()
            if cid != client_id
        ]
        await self.send(text_data=json.dumps({'signal_type': 'peer_list', 'peers': peers}))

        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'room.event',
            'event': 'peer_announce',
            'user_id': user.id,
            'client_id': client_id,
            'display_name': display_name,
        })

    async def handle_screen_share(self, client_info, payload):
        client_id = client_info.get('client_id')
        if not client_id:
            return
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'room.event',
            'event': 'screen_share',
            'user_id': client_info['user_id'],
            'client_id': client_id,
            'action': payload.get('action', 'start'),
        })

    async def handle_chat(self, client_info, payload):
        client_id = client_info.get('client_id')
        message = (payload.get('message') or '').strip()
        if not client_id or not message:
            return
        display_name = await self.get_display_name(self.scope['user'])
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'room.event',
            'event': 'chat',
            'user_id': client_info['user_id'],
            'client_id': client_id,
            'message': message[:2000],
            'sender_name': display_name,
        })

    async def handle_raise_hand(self, client_info, payload):
        client_id = client_info.get('client_id')
        if not client_id:
            return
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'room.event',
            'event': 'raise_hand',
            'user_id': client_info['user_id'],
            'client_id': client_id,
            'raised': bool(payload.get('raised', True)),
        })

    async def handle_relayed_signal(self, client_info, signal_type, payload):
        sender_client_id = client_info.get('client_id')
        target_client_id = payload.get('target_client_id') or payload.get('target_id')
        if not sender_client_id or target_client_id is None:
            return
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'relay.signal',
            'sender_client_id': sender_client_id,
            'target_client_id': target_client_id,
            'signal_type': signal_type,
            'payload': payload,
        })

    # ------------------------------------------------------------------
    # Group event handlers (broadcast to connected clients)
    # ------------------------------------------------------------------

    async def relay_signal(self, event):
        await self.send(text_data=json.dumps({
            'sender_client_id': event['sender_client_id'],
            'target_client_id': event['target_client_id'],
            'signal_type': event['signal_type'],
            'payload': event['payload'],
        }))

    async def room_event(self, event):
        message = {key: value for key, value in event.items() if key not in {'type'}}
        message['signal_type'] = message.pop('event')
        await self.send(text_data=json.dumps(message))

    # ------------------------------------------------------------------
    # Authorization helpers
    # ------------------------------------------------------------------

    @database_sync_to_async
    def get_display_name(self, user):
        return user.get_full_name() or user.username

    @database_sync_to_async
    def get_room(self, room_type, room_pk):
        if room_type == 'mentorat_seance':
            try:
                return SeanceMentorat.objects.select_related(
                    'relation__mentor__profil__utilisateur',
                    'relation__mentee__profil__utilisateur',
                ).get(pk=room_pk, statut__in=['planifiee', 'en_cours'])
            except SeanceMentorat.DoesNotExist:
                return None

        if room_type == 'formation_session':
            return {'pk': room_pk}

        return None

    @database_sync_to_async
    def is_authorized(self, user, room_type, room):
        if room_type == 'formation_session':
            return user.is_authenticated

        if room_type == 'mentorat_seance':
            profile = getattr(user, 'profil', None)
            if not profile:
                return False
            mentor = getattr(profile, 'mentorat_mentor', None)
            mentee = getattr(profile, 'mentorat_mentee', None)
            return (mentor is not None and room.relation.mentor_id == mentor.id) or \
                   (mentee is not None and room.relation.mentee_id == mentee.id)

        return False
