from django.urls import path
from . import views

app_name = 'cours'

urlpatterns = [
    path('', views.catalogue, name='catalogue'),
    path('<int:cours_id>/', views.detail_cours, name='detail'),
    path('<int:cours_id>/inscrire/', views.inscrire_cours, name='inscrire'),
    path('<int:cours_id>/desinscrire/', views.se_desinscrire, name='desinscrire'),
    path('lecon/<int:lecon_id>/terminer/', views.terminer_lecon, name='terminer_lecon'),
    path('lecon/<int:lecon_id>/annuler/', views.annuler_lecon, name='annuler_lecon'),
    path('exercice/<int:exercice_id>/soumettre/', views.soumettre_exercice, name='soumettre_exercice'),
    path('certificat/<int:inscription_id>/', views.telecharger_certificat, name='telecharger_certificat'),
    path('verifier/<str:code>/', views.verifier_certificat, name='verifier_certificat'),
]