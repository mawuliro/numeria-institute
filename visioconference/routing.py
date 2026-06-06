from django.urls import path
from .consumers import MeetingConsumer

websocket_urlpatterns = [
    path('ws/visio/<str:room_code>/', MeetingConsumer.as_asgi()),
]
