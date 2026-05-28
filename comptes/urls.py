from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views

app_name = 'comptes'

urlpatterns = [
    path('inscription/', views.inscription, name='inscription'),
    path('connexion/', views.connexion, name='connexion'),
    path('verify-email/sent/', views.verification_sent, name='verification_sent'),
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
    path('verify-email/resend/', views.resend_verification_email, name='resend_verification_email'),
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset_form.html',
        email_template_name='registration/password_reset_email.html',
        subject_template_name='registration/password_reset_subject.txt',
        html_email_template_name='registration/password_reset_email.html',
        success_url=reverse_lazy('comptes:password_reset_done')
    ), name='password_reset'),
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