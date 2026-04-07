# admissions/urls.py
from django.urls import path
from . import views

app_name = 'admissions'

urlpatterns = [
    path('', views.liste_campagnes, name='liste_campagnes'),
    path('campagne/<int:campagne_id>/', views.detail_campagne, name='detail_campagne'),
    path('campagne/<int:campagne_id>/paiement/', views.page_paiement_candidature, name='page_paiement_candidature'),  # ← Nom corrigé
    path('campagne/<int:campagne_id>/confirmation/', views.confirmation_paiement_candidature, name='confirmation_paiement_candidature'),  # ← Nom corrigé
    path('campagne/<int:campagne_id>/candidature/', views.candidature, name='candidature'),
    path('mes-candidatures/', views.mes_candidatures, name='mes_candidatures'),
    path('candidature/<int:candidature_id>/', views.detail_candidature, name='detail_candidature'),
    path('admin/candidatures/', views.admin_candidatures, name='admin_candidatures'),
    path('admin/candidature/<int:candidature_id>/changer-statut/', views.changer_statut, name='changer_statut'),
]