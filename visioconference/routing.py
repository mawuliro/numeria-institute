from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/visio/<str:room_code>/', consumers.MeetingConsumer.as_asgi()),
]
