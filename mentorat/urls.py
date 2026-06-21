from django.urls import path
from . import views

app_name = 'mentorat'

urlpatterns = [
    # Pages principales
    path('', views.index, name='index'),
    path('mentors/', views.liste_mentors, name='liste_mentors'),
    path('mentor/<int:pk>/', views.detail_mentor, name='detail_mentor'),

    # Inscription
    path('devenir-mentor/', views.devenir_mentor, name='devenir_mentor'),
    path('devenir-mentee/', views.devenir_mentee, name='devenir_mentee'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-applications/', views.applications_list, name='applications_list'),
    path('admin-applications/<int:application_pk>/', views.application_detail, name='application_detail'),

    # Demandes de mentorat
    path('demander/<int:mentor_pk>/', views.demander_mentorat, name='demander_mentorat'),
    path('demande/<int:demande_pk>/<str:action>/', views.gerer_demande, name='gerer_demande'),

    # Tableaux de bord
    path('tableau-bord-mentor/', views.tableau_de_bord_mentor, name='tableau_de_bord_mentor'),
    path('tableau-bord-mentee/', views.tableau_de_bord_mentee, name='tableau_de_bord_mentee'),

    # Gestion des relations
    path('relation/<int:pk>/', views.detail_relation, name='detail_relation'),
    path('relation/<int:relation_pk>/planifier-seance/', views.planifier_seance, name='planifier_seance'),
    path('relation/<int:relation_pk>/terminer/', views.terminer_relation, name='terminer_relation'),

    # Gestion des séances
    path('seance/<int:seance_pk>/terminer/', views.terminer_seance, name='terminer_seance'),
    path('seance/<int:seance_pk>/paiement/', views.paiement_seance, name='paiement_seance'),
    path('seance/<int:seance_pk>/video/', views.video_seance, name='video_seance'),
]