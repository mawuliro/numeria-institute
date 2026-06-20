from django.urls import path
from . import views

app_name = 'visioconference'

urlpatterns = [
    # Landing page — renders the create/join page (same as /create/ but in GET mode)
    path('', views.create_room, name='index'),
    path('create/', views.create_room, name='create_room'),
    path('join/', views.join_room, name='join_room'),
    path('lobby/<str:room_code>/', views.lobby, name='lobby'),
    path('room/<str:room_code>/waiting/', views.waiting_room, name='waiting_room'),
    path('room/<str:room_code>/', views.meeting_room, name='meeting_room'),
    path('room/<str:room_code>/end/', views.end_meeting, name='end_meeting'),
]
