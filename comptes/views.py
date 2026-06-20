import logging
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from django.core.signing import BadSignature, SignatureExpired
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import reverse
from django.utils.translation import gettext as _
from django_ratelimit.decorators import ratelimit
from django.contrib.auth.views import PasswordResetView
from django.urls import reverse_lazy
from numeria_project.emails import send_verification_email, verify_email_token

logger = logging.getLogger(__name__)


class RatelimitedPasswordResetView(PasswordResetView):
    """Password reset with IP-based rate limiting to prevent email bombing."""
    template_name = 'registration/password_reset_form.html'
    email_template_name = 'registration/password_reset_email.html'
    subject_template_name = 'registration/password_reset_subject.txt'
    html_email_template_name = 'registration/password_reset_email.html'
    success_url = reverse_lazy('comptes:password_reset_done')

    @ratelimit(key='ip', rate='5/h', method='POST', block=True)
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
from .forms import FormulaireInscription, FormulaireConnexion, FormulaireProfil, VerificationResendForm
from .models import Profil


@ratelimit(key='ip', rate='10/h', method='POST', block=True)
def inscription(request):
    """Inscription d'un nouvel utilisateur — connexion immédiate, sans email de confirmation."""
    if request.user.is_authenticated:
        return redirect('comptes:tableau_de_bord')

    if request.method == 'POST':
        formulaire = FormulaireInscription(request.POST)
        if formulaire.is_valid():
            user = formulaire.save()
            send_verification_email(user, request)
            messages.success(request, _("Un email de vérification a été envoyé à ton adresse.") )
            return redirect('comptes:verification_sent')
        else:
            messages.error(request, _("Veuillez corriger les erreurs ci-dessous."))
    else:
        formulaire = FormulaireInscription()

    return render(request, 'comptes/inscription.html', {'formulaire': formulaire})


def verification_sent(request):
    return render(request, 'comptes/verification_sent.html')


def verify_email(request, token):
    try:
        user = verify_email_token(token)
    except SignatureExpired:
        return render(request, 'comptes/verification_expired.html')
    except (BadSignature, User.DoesNotExist, ValueError):
        return render(request, 'comptes/verification_invalid.html')

    user.is_active = True
    user.save()
    # SECURITY: Do NOT auto-login the user on email verification.
    # The verification link is sent in clear-text email and is valid for 24h;
    # anyone who obtains it (forwarded email, shared inbox, browser history)
    # would otherwise get a passwordless login. Require explicit authentication.
    messages.success(request, _("Ton email a été vérifié ! Tu peux maintenant te connecter."))
    return redirect('comptes:connexion')


@ratelimit(key='ip', rate='3/h', method='POST', block=True)
def resend_verification_email(request):
    if request.method == 'POST':
        formulaire = VerificationResendForm(request.POST)
        if formulaire.is_valid():
            email = formulaire.cleaned_data['email']
            try:
                user = User.objects.get(email=email, is_active=False)
                send_verification_email(user, request)
                messages.success(request, _("Un nouvel email de vérification a été envoyé."))
                return redirect('comptes:verification_sent')
            except User.DoesNotExist:
                messages.info(request, _("Aucun compte inactif n'est associé à cette adresse email."))
    else:
        formulaire = VerificationResendForm()

    return render(request, 'comptes/verification_resend.html', {'formulaire': formulaire})


@ratelimit(key='ip', rate='10/h', method='POST', block=True)
def connexion(request):
    """Connexion d'un utilisateur existant."""
    if request.user.is_authenticated:
        return redirect('comptes:tableau_de_bord')

    if request.method == 'POST':
        formulaire = FormulaireConnexion(request.POST)
        if formulaire.is_valid():
            username = formulaire.cleaned_data['username']
            password = formulaire.cleaned_data['password']

            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                messages.success(request, _("Bon retour, {first_name} ! 👋").format(first_name=user.first_name))

                next_url = request.GET.get('next', '')
                if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                    next_url = reverse('comptes:tableau_de_bord')
                return redirect(next_url)
            else:
                messages.error(request, _("Nom d'utilisateur ou mot de passe incorrect."))
    else:
        formulaire = FormulaireConnexion()

    return render(request, 'comptes/connexion.html', {'formulaire': formulaire})


@login_required
def deconnexion(request):
    """Déconnexion de l'utilisateur."""
    prenom = request.user.first_name
    logout(request)
    messages.success(request, _("À bientôt, {prenom} ! 👋").format(prenom=prenom))
    return redirect('accueil')


@login_required
def tableau_de_bord(request):
    """Tableau de bord complet de l'étudiant."""
    from cours.models import Course, InscriptionCours
    from blog.models import Article

    profil, cree = Profil.objects.get_or_create(utilisateur=request.user)

    inscriptions = InscriptionCours.objects.filter(
        etudiant=request.user
    ).select_related('course')

    total_inscrits  = inscriptions.count()
    total_termines  = inscriptions.filter(est_termine=True).count()
    en_cours        = inscriptions.filter(est_termine=False)

    if total_inscrits > 0:
        progression_totale = sum(i.progression for i in inscriptions) // total_inscrits
    else:
        progression_totale = 0

    ids_inscrits = inscriptions.values_list('course_id', flat=True)
    cours_recommandes = Course.objects.filter(
        status='published'
    ).exclude(
        id__in=ids_inscrits
    )[:3]

    articles_recents = Article.objects.filter(
        est_publie=True
    ).select_related('auteur', 'categorie').order_by('-date_creation')[:3]

    contexte = {
        'profil': profil,
        'inscriptions': inscriptions,
        'en_cours': en_cours,
        'total_inscrits': total_inscrits,
        'total_termines': total_termines,
        'progression_totale': progression_totale,
        'cours_recommandes': cours_recommandes,
        'articles_recents': articles_recents,
    }

    return render(request, 'comptes/tableau_de_bord.html', contexte)


@login_required
def modifier_profil(request):
    """Modifier les informations du profil avec photo."""
    profil, cree = Profil.objects.get_or_create(utilisateur=request.user)

    if request.method == 'POST':
        # request.FILES est crucial pour Cloudinary
        formulaire = FormulaireProfil(
            request.POST,
            request.FILES,  # ← Important pour l'upload Cloudinary
            instance=profil,
            user=request.user
        )
        if formulaire.is_valid():
            try:
                formulaire.save()
                messages.success(request, _("Ton profil a été mis à jour ! ✅"))
                return redirect('comptes:profil')
            except ValueError as e:
                if 'api_key' in str(e).lower():
                    # Cloudinary not configured — save all fields except photo.
                    # user.save() already ran inside formulaire.save(); only profil.save() failed.
                    cd = formulaire.cleaned_data
                    Profil.objects.filter(pk=profil.pk).update(
                        bio=cd.get('bio', ''),
                        pays=cd.get('pays', ''),
                        ville=cd.get('ville', ''),
                        niveau_etudes=cd.get('niveau_etudes', ''),
                        domaine=cd.get('domaine', ''),
                        linkedin=cd.get('linkedin', ''),
                        github=cd.get('github', ''),
                    )
                    messages.warning(request, _("Profil mis à jour, mais la photo n'a pas pu être enregistrée (Cloudinary non configuré)."))
                    return redirect('comptes:profil')
                raise
        else:
            if request.user.is_superuser:
                logger.debug('Profil form errors for user %s: %s', request.user.pk, formulaire.errors)
            messages.error(request, _("Veuillez corriger les erreurs."))
    else:
        formulaire = FormulaireProfil(instance=profil, user=request.user)

    return render(request, 'comptes/modifier_profil.html', {
        'formulaire': formulaire,
        'profil': profil,
    })


@login_required
def supprimer_photo(request):
    """
    Supprimer la photo de profil.
    Version Cloudinary : suppression via l'API.
    """
    if request.method == 'POST':
        profil, _ = Profil.objects.get_or_create(utilisateur=request.user)

        if profil.photo:
            # Suppression du fichier sur Cloudinary
            try:
                import cloudinary.uploader
                # public_id est automatiquement géré par CloudinaryField
                if hasattr(profil.photo, 'public_id'):
                    cloudinary.uploader.destroy(profil.photo.public_id)
            except Exception as e:
                # En développement, on ignore les erreurs Cloudinary
                logger.warning('Cloudinary photo deletion failed for user %s: %s', request.user.pk, e)

            # Vider le champ en base de données
            profil.photo = None
            profil.save()
            messages.success(request, _("Ta photo de profil a été supprimée. ✅"))
        else:
            messages.info(request, _("Tu n'as pas de photo de profil à supprimer."))

    return redirect('comptes:modifier_profil')


@login_required
def profil(request):
    """Page de profil de l'étudiant."""
    profil, cree = Profil.objects.get_or_create(utilisateur=request.user)
    return render(request, 'comptes/profil.html', {'profil': profil})


@login_required
def changer_mot_de_passe(request):
    """Changer le mot de passe."""
    if request.method == 'POST':
        formulaire = PasswordChangeForm(request.user, request.POST)
        if formulaire.is_valid():
            user = formulaire.save()
            update_session_auth_hash(request, user)
            messages.success(request, _("Ton mot de passe a été changé avec succès ! 🔐"))
            return redirect('comptes:profil')
        else:
            messages.error(request, _("Veuillez corriger les erreurs ci-dessous."))
    else:
        formulaire = PasswordChangeForm(request.user)

    return render(request, 'comptes/changer_mot_de_passe.html', {'formulaire': formulaire})


@login_required
def supprimer_compte(request):
    """Suppression définitive du compte."""
    if request.method == 'POST':
        password = request.POST.get('password')
        user = authenticate(request, username=request.user.username, password=password)

        if user is not None:
            prenom = request.user.first_name
            request.user.delete()
            messages.success(request, _("Ton compte a été supprimé, {prenom}. Nous espérons te revoir ! 👋").format(prenom=prenom))
            return redirect('accueil')
        else:
            messages.error(request, _("Mot de passe incorrect. Ton compte n'a pas été supprimé."))

    return render(request, 'comptes/supprimer_compte.html')