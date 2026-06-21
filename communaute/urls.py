from django.urls import path
from . import views

app_name = 'communaute'

urlpatterns = [
    path('', views.liste_categories, name='liste_categories'),
    path('categorie/<int:pk>/', views.detail_categorie, name='categorie_detail'),
    path('categorie/nouvelle/', views.creer_categorie, name='creer_categorie'),
    path('sujet/<int:pk>/', views.detail_sujet, name='sujet_detail'),
    path('sujet/nouveau/', views.creer_sujet, name='creer_sujet'),
    path('sujet/<int:pk>/repondre/', views.repondre_sujet, name='repondre_sujet'),
    path('sujet/<int:pk>/modifier/', views.modifier_sujet, name='modifier_sujet'),
    path('message/<int:pk>/modifier/', views.modifier_message, name='modifier_message'),
    path('message/<int:pk>/voter/', views.voter_message, name='voter_message'),
    path('profil/<str:username>/', views.profil_utilisateur, name='profil_utilisateur'),
    path('profil/modifier/', views.modifier_profil, name='modifier_profil'),
]