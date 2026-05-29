import logging
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _
from django_ratelimit.decorators import ratelimit
from cours.models import Cours
from blog.models import Article
from .models import HomePage, AboutPage, ContactPage, ContactMessage

logger = logging.getLogger(__name__)

User = get_user_model()


def accueil(request):
    """Vue de la page d'accueil."""
    from django.utils.translation import get_language
    current_lang = get_language()
    
    homepage = HomePage.objects.first()
    if not homepage:
        # Contenu par défaut en français
        homepage = HomePage.objects.create(
            hero_badge="Scientific Computing & AI",
            hero_title="La science accessible à tous les esprits curieux",
            hero_description="Des cours scientifiques de qualité, conçus pour les apprenants africains et francophones du monde entier. Du lycée à l'IA avancée.",
            hero_cta_primary_text="Découvrir les cours",
            hero_cta_primary_url="/cours/",
            hero_cta_secondary_text="Créer un compte",
            hero_cta_secondary_url="/comptes/inscription/",
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
            meta_description=_("Éducation scientifique accessible en Afrique. Cours de mathématiques, sciences et IA pour apprenants africains et francophones.")
        )
    
    # Traduire le contenu dynamiquement selon la langue
    if current_lang == 'en':
        homepage.hero_badge = "Scientific Computing & AI"
        homepage.hero_title = "Science accessible to all curious minds"
        homepage.hero_description = "Quality scientific courses designed for African and French-speaking learners worldwide. From high school to advanced AI."
        homepage.hero_cta_primary_text = "Discover courses"
        homepage.hero_cta_secondary_text = "Create account"
        homepage.features_title = "Why choose Numeria?"
        homepage.features = [
            {"icon": "🎓", "title": "Quality courses", "description": "Rigorous content validated by African experts."},
            {"icon": "🌍", "title": "Accessible everywhere", "description": "Learn wherever and whenever you want."},
            {"icon": "💰", "title": "Free to start", "description": "Discover our courses without commitment."}
        ]
        homepage.testimonials = [
            {"name": "Marie K.", "role": "Master's student", "text": "The courses are excellent and adapted to our African context."},
            {"name": "Jean T.", "role": "Professor", "text": "Finally a platform that understands our educational needs."}
        ]
        homepage.meta_title = "Home - Numeria Institute"
        homepage.meta_description = _("Accessible scientific education in Africa. Mathematics, science and AI courses for African and French-speaking learners.")
    
    cours_recents = Cours.objects.filter(est_publie=True)[:3]
    articles_recents = Article.objects.filter(est_publie=True)[:3]

    # Statistiques dynamiques depuis la base de données
    nb_etudiants = User.objects.filter(is_active=True).count()
    nb_cours = Cours.objects.filter(est_publie=True).count()

    contexte = {
        'homepage': homepage,
        'cours_recents': cours_recents,
        'articles_recents': articles_recents,
        'nb_etudiants': nb_etudiants,
        'nb_cours': nb_cours,
        'nb_pays': 5,  # Valeur statique honnête — suivi géographique non implémenté
    }
    return render(request, 'pages/accueil.html', contexte)


def robots_txt(request):
    """robots.txt dynamique."""
    from django.http import HttpResponse
    base_url = f"{request.scheme}://{request.get_host()}"
    content = f"""User-agent: *
Allow: /

Sitemap: {base_url}/sitemap.xml

Disallow: /admin/
Disallow: /analytics/
Disallow: /comptes/profil/supprimer/
Disallow: /comptes/profil/changer-mot-de-passe/
"""
    return HttpResponse(content, content_type='text/plain')


def confidentialite(request):
    """Politique de confidentialité."""
    return render(request, 'pages/confidentialite.html')


def cgu(request):
    """Conditions Générales d'Utilisation."""
    return render(request, 'pages/cgu.html')


def a_propos(request):
    """Vue de la page À propos."""
    from django.utils.translation import get_language
    current_lang = get_language()
    
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
            meta_description=_("Découvrez Numeria Institute, notre mission et notre équipe pour l'éducation scientifique en Afrique.")
        )
    
    # Traduire le contenu dynamiquement selon la langue
    if current_lang == 'en':
        aboutpage.title = "About Numeria Institute"
        aboutpage.content = "Numeria Institute was born from a simple observation: Sub-Saharan Africa is undergoing accelerated digital transformation, with a large and ambitious youth, but a glaring lack of practical training in computational sciences and artificial intelligence."
        aboutpage.mission_title = "Our Mission"
        aboutpage.mission_content = "To train a new generation of African digital scientists and engineers, capable of modeling, analyzing and solving the complex problems of the continent."
        aboutpage.vision_title = "Our Vision"
        aboutpage.vision_content = "To become the reference hub for applied tech training for the entire ECOWAS region."
        aboutpage.team = [
            {"name": "Dr. Roland M.", "role": "Founder & Director", "bio": "Expert in AI and computational sciences."}
        ]
        aboutpage.meta_title = "About - Numeria Institute"
        aboutpage.meta_description = _("Discover Numeria Institute, our mission and team for scientific education in Africa.")
    
    # Statistiques dynamiques
    total_cours = Cours.objects.filter(est_publie=True).count()
    total_etudiants = User.objects.filter(is_active=True).count()
    contexte = {
        'aboutpage': aboutpage,
        'total_cours': total_cours,
        'total_etudiants': total_etudiants,
    }
    return render(request, 'pages/a_propos.html', contexte)


@ratelimit(key='ip', rate='5/h', method='POST', block=True)
def contact(request):
    """Vue de la page Contact — sauvegarde en base uniquement, aucun email."""
    from .forms import FormulaireContact
    from django.contrib import messages

    contactpage = ContactPage.objects.first()
    if not contactpage:
        contactpage = ContactPage.objects.create(
            title="Contactez-nous",
            intro="Une question, une idée de partenariat ou simplement envie d'en savoir plus ? Nous sommes là pour vous.",
            address="Lomé, Togo",
            phone="+228 XX XX XX XX",
            email=settings.CONTACT_EMAIL,
            hours="Lundi-Vendredi: 9h-18h",
            meta_title="Contact - Numeria Institute",
            meta_description="Contactez Numeria Institute pour toute question ou partenariat."
        )
    elif contactpage.email != settings.CONTACT_EMAIL:
        contactpage.email = settings.CONTACT_EMAIL
        contactpage.save(update_fields=['email'])

    if request.method == 'POST':
        formulaire = FormulaireContact(request.POST)
        if formulaire.is_valid():
            nom = formulaire.cleaned_data['nom_complet']
            email_utilisateur = formulaire.cleaned_data['email']
            sujet = formulaire.cleaned_data['sujet']
            message_text = formulaire.cleaned_data['message']

            ContactMessage.objects.create(
                name=nom,
                email=email_utilisateur,
                subject=sujet,
                message=message_text,
            )

            # Notify all staff members via in-app notification
            try:
                from notifications.notifications import notify_group
                staff_qs = User.objects.filter(is_staff=True)
                notify_group(
                    staff_qs,
                    title=_("Nouveau message de contact"),
                    message=f"{nom} a envoyé un message : {sujet}",
                    notification_type='info',
                    link='/numeria-staff-portal/pages/contactmessage/',
                )
            except Exception as e:
                logger.error('Contact notification failed: %s', e)

            messages.success(
                request,
                _("✅ Merci {nom} ! Votre message a bien été reçu. Nous vous répondrons sous 24-48h.").format(nom=nom)
            )
            return redirect('contact')
    else:
        formulaire = FormulaireContact()

    return render(request, 'pages/contact.html', {'formulaire': formulaire, 'contactpage': contactpage})