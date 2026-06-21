from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path('ws/mentorat/video/<int:seance_pk>/', consumers.VideoChatConsumer.as_asgi()),
    path('ws/mentorat/video/<str:room_type>/<int:room_pk>/', consumers.VideoChatConsumer.as_asgi()),
]
