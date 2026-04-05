from django.urls import path
from . import views

app_name = 'comptes'

urlpatterns = [
    path('inscription/', views.inscription, name='inscription'),
    path('connexion/', views.connexion, name='connexion'),
    path('deconnexion/', views.deconnexion, name='deconnexion'),
    path('tableau-de-bord/', views.tableau_de_bord, name='tableau_de_bord'),
    path('profil/', views.profil, name='profil'),
    path('profil/modifier/', views.modifier_profil, name='modifier_profil'),
    path('profil/supprimer-photo/', views.supprimer_photo, name='supprimer_photo'),  # Nouveau !
    path('profil/changer-mot-de-passe/', views.changer_mot_de_passe, name='changer_mot_de_passe'),
    path('profil/supprimer/', views.supprimer_compte, name='supprimer_compte'),
    path('debug-env/', views.debug_env, name='debug_env'),
]