from django.shortcuts import render, redirect, get_object_or_404
from cours.models import Cours
from blog.models import Article
from .models import HomePage, AboutPage, ContactPage


def accueil(request):
    """Vue de la page d'accueil."""
    homepage = HomePage.objects.first()
    cours_recents = Cours.objects.filter(est_publie=True)[:3]
    articles_recents = Article.objects.filter(est_publie=True)[:3]
    contexte = {
        'homepage': homepage,
        'cours_recents': cours_recents,
        'articles_recents': articles_recents,
    }
    return render(request, 'pages/accueil.html', contexte)


def a_propos(request):
    """Vue de la page À propos."""
    aboutpage = AboutPage.objects.first()
    # Statistiques dynamiques
    total_cours = Cours.objects.filter(est_publie=True).count()
    total_etudiants = 0  # TODO: compter les utilisateurs étudiants
    contexte = {
        'aboutpage': aboutpage,
        'total_cours': total_cours,
        'total_etudiants': total_etudiants,
    }
    return render(request, 'pages/a_propos.html', contexte)


def contact(request):
    """Vue de la page Contact."""
    contactpage = ContactPage.objects.first()
    contexte = {
        'contactpage': contactpage,
    }
    return render(request, 'pages/contact.html', contexte)
    from django.contrib.auth.models import User
    total_etudiants = User.objects.filter(is_active=True).count()

    contexte = {
        'total_cours': total_cours,
        'total_etudiants': total_etudiants,
    }
    return render(request, 'pages/a_propos.html', contexte)


def contact(request):
    """Vue de la page Contact avec formulaire fonctionnel."""
    from .forms import FormulaireContact
    from django.core.mail import send_mail
    from django.conf import settings

    if request.method == 'POST':
        formulaire = FormulaireContact(request.POST)

        if formulaire.is_valid():
            # Récupérer les données du formulaire
            nom = formulaire.cleaned_data['nom_complet']
            email = formulaire.cleaned_data['email']
            organisation = formulaire.cleaned_data.get('organisation', '')
            sujet = formulaire.cleaned_data['sujet']
            message = formulaire.cleaned_data['message']
            est_partenaire = formulaire.cleaned_data.get('est_partenaire', False)

            # Construire le message email
            contenu_email = f"""
Nouveau message depuis le site Numeria Institute
================================================

De : {nom}
Email : {email}
Organisation : {organisation or 'Non renseignée'}
Sujet : {sujet}
Partenariat : {'Oui' if est_partenaire else 'Non'}

Message :
---------
{message}

================================================
Envoyé depuis numeriainsitute.com
            """

            try:
                # Envoyer l'email (affiché dans le terminal en développement)
                send_mail(
                    subject=f'[Numeria] Nouveau message : {sujet} — {nom}',
                    message=contenu_email,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.CONTACT_EMAIL],
                    fail_silently=False,
                )
                messages_django = True
            except Exception:
                messages_django = False

            from django.contrib import messages
            messages.success(
                request,
                f"✅ Merci {nom} ! Ton message a bien été envoyé. Nous te répondrons sous 48h."
            )
            return redirect('contact')

    else:
        formulaire = FormulaireContact()

    return render(request, 'pages/contact.html', {'formulaire': formulaire})