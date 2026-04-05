from django.urls import path
from . import views

app_name = 'paiements'

urlpatterns = [
    path('cours/<int:cours_id>/', views.page_paiement, name='page_paiement'),
    path('cours/<int:cours_id>/initier/', views.initier_paiement, name='initier'),
    path('confirmation/<int:paiement_id>/', views.confirmation_paiement, name='confirmation'),
    path('historique/', views.historique_paiements, name='historique'),
]