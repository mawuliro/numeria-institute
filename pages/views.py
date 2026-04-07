from django.shortcuts import render, redirect, get_object_or_404
from cours.models import Cours
from blog.models import Article
from .models import HomePage, AboutPage, ContactPage


def accueil(request):
    """Vue de la page d'accueil."""
    homepage = HomePage.objects.first()
    if not homepage:
        homepage = HomePage.objects.create(
            hero_badge="Scientific Computing & AI",
            hero_title="La science accessible à tous les esprits curieux",
            hero_description="Des cours scientifiques de qualité, conçus pour les apprenants africains et francophones du monde entier. Du lycée à l'IA avancée.",
            hero_cta_primary_text="Découvrir les cours",
            hero_cta_primary_url="{% url 'cours:catalogue' %}",
            hero_cta_secondary_text="Créer un compte",
            hero_cta_secondary_url="{% url 'comptes:inscription' %}",
            stats_students=1500,
            stats_courses=25,
            stats_countries=15,
            features_title="Pourquoi choisir Numeria ?",
            features=[
                {"icon": "🎓", "title": "Cours de qualité", "description": "Contenu rigoureux validé par des experts africains."},
                {"icon": "🌍", "title": "Accessible partout", "description": "Apprenez où vous voulez, quand vous voulez."},
                {"icon": "💰", "title": "Gratuit pour commencer", "description": "Découvrez nos cours sans engagement."}
            ],
            testimonials=[
                {"name": "Marie K.", "role": "Étudiante en Master", "text": "Les cours sont excellents et adaptés à notre contexte africain."},
                {"name": "Jean T.", "role": "Professeur", "text": "Enfin une plateforme qui comprend nos besoins éducatifs."}
            ],
            meta_title="Accueil - Numeria Institute",
            meta_description="Éducation scientifique accessible en Afrique. Cours de mathématiques, sciences et IA pour apprenants africains et francophones."
        )
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
    if not aboutpage:
        aboutpage = AboutPage.objects.create(
            title="À propos de Numeria Institute",
            content="Numeria Institute est né d'un constat simple : l'Afrique subsaharienne connaît une transformation numérique accélérée, avec une jeunesse nombreuse et ambitieuse, mais un manque criant de formations pratiques en sciences computationnelles et intelligence artificielle.",
            mission_title="Notre mission",
            mission_content="Former une nouvelle génération de scientifiques et d'ingénieurs numériques africains, capables de modéliser, analyser et résoudre les problèmes complexes du continent.",
            vision_title="Notre vision",
            vision_content="Devenir le hub de référence en formation tech appliquée pour toute la région CEDEAO.",
            team=[
                {"name": "Dr. Roland M.", "role": "Fondateur & Directeur", "bio": "Expert en IA et sciences computationnelles."}
            ],
            meta_title="À propos - Numeria Institute",
            meta_description="Découvrez Numeria Institute, notre mission et notre équipe pour l'éducation scientifique en Afrique."
        )
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
    if not contactpage:
        contactpage = ContactPage.objects.create(
            title="Contactez-nous",
            intro="Une question, une idée de partenariat ou simplement envie d'en savoir plus ? Nous sommes là pour vous.",
            address="Lomé, Togo",
            phone="+228 XX XX XX XX",
            email="contact@numeriainstitute.com",
            hours="Lundi-Vendredi: 9h-18h",
            meta_title="Contact - Numeria Institute",
            meta_description="Contactez Numeria Institute pour toute question ou partenariat."
        )
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