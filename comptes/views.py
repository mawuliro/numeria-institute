from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from django.utils.translation import gettext as _
from .forms import FormulaireInscription, FormulaireConnexion, FormulaireProfil
from .models import Profil


def inscription(request):
    """Inscription d'un nouvel utilisateur."""
    if request.user.is_authenticated:
        return redirect('comptes:tableau_de_bord')

    if request.method == 'POST':
        formulaire = FormulaireInscription(request.POST)
        if formulaire.is_valid():
            user = formulaire.save()
            login(request, user)
            messages.success(request, _("Bienvenue sur Numeria, {first_name} ! 🎓").format(first_name=user.first_name))
            return redirect('comptes:tableau_de_bord')
        else:
            messages.error(request, _("Veuillez corriger les erreurs ci-dessous."))
    else:
        formulaire = FormulaireInscription()

    return render(request, 'comptes/inscription.html', {'formulaire': formulaire})


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

                next_url = request.GET.get('next', 'comptes:tableau_de_bord')
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
    from cours.models import Cours, InscriptionCours
    from blog.models import Article

    profil, cree = Profil.objects.get_or_create(utilisateur=request.user)

    inscriptions = InscriptionCours.objects.filter(
        etudiant=request.user
    ).select_related('cours')

    total_inscrits  = inscriptions.count()
    total_termines  = inscriptions.filter(est_termine=True).count()
    en_cours        = inscriptions.filter(est_termine=False)

    if total_inscrits > 0:
        progression_totale = sum(i.progression for i in inscriptions) // total_inscrits
    else:
        progression_totale = 0

    ids_inscrits = inscriptions.values_list('cours_id', flat=True)
    cours_recommandes = Cours.objects.filter(
        est_publie=True
    ).exclude(
        id__in=ids_inscrits
    )[:3]

    articles_recents = Article.objects.filter(est_publie=True)[:3]

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
            formulaire.save()
            messages.success(request, _("Ton profil a été mis à jour ! ✅"))
            return redirect('comptes:profil')
        else:
            # Debug en cas d'erreur
            if request.user.is_superuser:
                print(formulaire.errors)
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
                print(f"Erreur suppression Cloudinary: {e}")

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
            messages.success(request, "Ton mot de passe a été changé avec succès ! 🔐")
            return redirect('comptes:profil')
        else:
            messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
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