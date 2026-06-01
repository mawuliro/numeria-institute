from django.urls import path
from . import views

app_name = 'formation'

urlpatterns = [
    path('', views.liste_formations, name='liste'),
    path('<slug:slug>/', views.detail_formation, name='detail'),
    path('<slug:formation_slug>/lecon/<slug:lesson_slug>/', views.voir_lecon, name='voir_lecon'),
]

