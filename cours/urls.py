from django.urls import path
from . import views

app_name = 'cours'

urlpatterns = [
    path('', views.catalogue, name='catalogue'),
    path('<int:cours_id>/', views.detail_cours, name='detail'),
    path('<int:cours_id>/inscrire/', views.inscrire_cours, name='inscrire'),
    path('<int:cours_id>/desinscrire/', views.se_desinscrire, name='desinscrire'),
    path('<int:cours_id>/evaluer/', views.evaluer_cours, name='evaluer'),
    path('<int:cours_id>/poser-question/', views.poser_question, name='poser_question'),
    path('lecon/<int:lecon_id>/terminer/', views.terminer_lecon, name='terminer_lecon'),
    path('lecon/<int:lecon_id>/annuler/', views.annuler_lecon, name='annuler_lecon'),
    path('exercice/<int:exercice_id>/soumettre/', views.soumettre_exercice, name='soumettre_exercice'),
    path('certificat/<int:inscription_id>/', views.telecharger_certificat, name='telecharger_certificat'),
    path('verifier/<str:code>/', views.verifier_certificat, name='verifier_certificat'),
    path('exercice/<int:exercise_id>/submit/', views.submit_code_exercise, name='submit_code_exercise'),
    path('exercice/<int:exercise_id>/solution/', views.get_exercise_solution, name='get_exercise_solution'),
    path('qcm/<int:mcq_id>/soumettre/', views.submit_mcq, name='submit_mcq'),
    path('qcm/<int:mcq_id>/statut/', views.get_mcq_status, name='mcq_status'),
    # New exercise types — all server-evaluated
    path('fill-blank/<int:exercise_id>/soumettre/', views.submit_fill_blank, name='submit_fill_blank'),
    path('vrai-faux/<int:exercise_id>/soumettre/', views.submit_true_false, name='submit_true_false'),
    path('ordre-code/<int:exercise_id>/soumettre/', views.submit_code_order, name='submit_code_order'),
    path('associations/<int:exercise_id>/soumettre/', views.submit_matching, name='submit_matching'),
    path('reponse-courte/<int:exercise_id>/soumettre/', views.submit_short_answer, name='submit_short_answer'),
]