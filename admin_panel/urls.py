from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Contacts
    path('contacts/', views.contacts_list, name='contacts_list'),
    path('contacts/<int:message_id>/', views.contact_detail, name='contact_detail'),

    # Candidatures
    path('candidatures/', views.candidatures_list, name='candidatures_list'),
    path('candidatures/<int:candidature_id>/', views.candidature_detail, name='candidature_detail'),
    path('candidatures/<int:candidature_id>/action/', views.candidature_action, name='candidature_action'),

    # Mentorat
    path('mentorat/', views.mentorat_list, name='mentorat_list'),
    path('mentorat/<int:demande_id>/', views.mentorat_detail, name='mentorat_detail'),
    path('mentorat/<int:demande_id>/action/', views.mentorat_action, name='mentorat_action'),

    # Users
    path('utilisateurs/', views.users_list, name='users_list'),
    path('utilisateurs/<int:user_id>/', views.user_detail, name='user_detail'),
    path('utilisateurs/<int:user_id>/action/', views.user_action, name='user_action'),

    # Activity log
    path('activite/', views.activity_log, name='activity_log'),
]
