from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views

app_name = 'comptes'

urlpatterns = [
    path('inscription/', views.inscription, name='inscription'),
    path('verification-envoyee/', views.verification_sent, name='verification_sent'),
    path('verification/<str:token>/', views.verify_email, name='verify_email'),
    path('verification/renvoyer/', views.resend_verification_email, name='resend_verification_email'),
    path('connexion/', views.connexion, name='connexion'),
    path('password-reset/', views.RatelimitedPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html',
        success_url=reverse_lazy('comptes:password_reset_complete')
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html'
    ), name='password_reset_complete'),
    path('deconnexion/', views.deconnexion, name='deconnexion'),
    path('tableau-de-bord/', views.tableau_de_bord, name='tableau_de_bord'),
    path('profil/', views.profil, name='profil'),
    path('profil/modifier/', views.modifier_profil, name='modifier_profil'),
    path('profil/supprimer-photo/', views.supprimer_photo, name='supprimer_photo'),  # Nouveau !
    path('profil/changer-mot-de-passe/', views.changer_mot_de_passe, name='changer_mot_de_passe'),
    path('profil/supprimer/', views.supprimer_compte, name='supprimer_compte'),
]