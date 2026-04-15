from django.urls import path
from . import views

app_name = 'formation'

urlpatterns = [
    # Formations
    path('', views.liste_formations, name='liste'),
    path('<slug:slug>/', views.detail_formation, name='detail'),
    
    # Sessions
    path('session/<int:session_id>/', views.detail_session, name='session_detail'),
    
    # Inscriptions
    path('session/<int:session_id>/inscrire/', views.inscrire_formation, name='inscrire'),
    path('inscription/<int:inscription_id>/paiement/', views.voir_paiement, name='voir_paiement'),
    
    # Accès au contenu
    path('mes-formations/', views.mes_formations, name='mes_formations'),
    path('lecon/<int:lecon_id>/', views.voir_lecon, name='voir_lecon'),
    
    # Certificats
    path('certificat/<uuid:id>/', views.detail_certificat, name='certificat_detail'),
    path('certificat/verifier/<str:token>/', views.verifier_certificat, name='certificat_verifier'),
]
