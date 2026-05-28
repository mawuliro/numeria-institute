from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.conf import settings
from numeria_project.emails import send_mentorship_acceptance_email
from django.db.models import Q, Sum
from django.urls import reverse
from django.utils.translation import gettext as _
from paiements.service import creer_paiement, traiter_paiement
from paiements.constants import PAYMENT_PROVIDERS
from django.utils import timezone
from datetime import timedelta
from django.http import Http404
from .models import (
    Mentor,
    Mentee,
    MentorApplication,
    DemandeMentorat,
    RelationMentorat,
    SeanceMentorat,
    PaiementSeance,
)
from .forms import (
    MentorApplicationForm,
    MentorProfileForm,
    InscriptionMentorForm,
    InscriptionMenteeForm,
    DemandeMentoratForm,
    SeanceMentoratForm,
    TerminerSeanceForm,
    PaiementSeanceForm,
)


def index(request):
    """
    Page d'accueil du mentorat.
    """
    mentors_count = Mentor.objects.filter(est_actif=True, profil__est_menteur=True).count()
    mentees_count = Mentee.objects.filter(est_actif=True).count()
    relations_count = RelationMentorat.objects.filter(est_active=True).count()

    est_mentor = False
    est_mentee = False
    application_status = None
    if request.user.is_authenticated and hasattr(request.user, 'profil'):
        est_mentor = hasattr(request.user.profil, 'mentorat_mentor')
        est_mentee = hasattr(request.user.profil, 'mentorat_mentee')
        application = getattr(request.user.profil, 'application_mentor', None)
        if application:
            application_status = application.status

    context = {
        'mentors_count': mentors_count,
        'mentees_count': mentees_count,
        'relations_count': relations_count,
        'est_mentor': est_mentor,
        'est_mentee': est_mentee,
        'application_status': application_status,
    }
    return render(request, 'mentorat/index.html', context)


@login_required
def devenir_mentor(request):
    """
    Candidature pour devenir mentor.
    """
    if not hasattr(request.user, 'profil'):
        messages.error(request, _("Votre profil n'est pas configuré. Veuillez contacter l'administrateur."))
        return redirect('mentorat:index')

    profil = request.user.profil
    # Si le mentor est déjà approuvé, on lui permet d'éditer son profil.
    if hasattr(profil, 'mentorat_mentor'):
        mentor = profil.mentorat_mentor
        if request.method == 'POST':
            form = MentorProfileForm(request.POST, request.FILES, instance=mentor, profil=profil)
            if form.is_valid():
                form.save()
                messages.success(request, _("Votre profil mentor a été mis à jour."))
                return redirect('mentorat:tableau_de_bord_mentor')
        else:
            form = MentorProfileForm(instance=mentor, profil=profil)

        return render(request, 'mentorat/devenir_mentor.html', {
            'form': form,
            'is_mentor': True,
            'mentor': mentor,
        })

    application = getattr(profil, 'application_mentor', None)
    if application and application.status == 'pending':
        return render(request, 'mentorat/devenir_mentor.html', {
            'application': application,
            'application_pending': True,
        })

    if request.method == 'POST':
        form = MentorApplicationForm(request.POST, request.FILES, instance=application if application and application.status == 'rejected' else None)
        if form.is_valid():
            application = form.save(commit=False)
            application.profil = profil
            application.status = 'pending'
            application.save()
            if form.cleaned_data.get('certificate'):
                application.certificate = form.cleaned_data['certificate']
            if form.cleaned_data.get('cv'):
                application.cv = form.cleaned_data['cv']
            application.save()
            messages.success(request, _("Votre candidature a bien été envoyée. Un administrateur la validera prochainement."))
            return redirect('mentorat:devenir_mentor')
    else:
        form = MentorApplicationForm(instance=application if application and application.status == 'rejected' else None)

    return render(request, 'mentorat/devenir_mentor.html', {
        'form': form,
        'application_rejected': application and application.status == 'rejected',
        'rejection_notes': application.rejection_notes if application and application.status == 'rejected' else '',
    })


@login_required
def devenir_mentee(request):
    """
    Inscription en tant que mentoré.
    """
    # Vérifier que l'utilisateur a un profil
    if not hasattr(request.user, 'profil'):
        messages.error(request, _("Votre profil n'est pas configuré. Veuillez contacter l'administrateur."))
        return redirect('mentorat:index')

    # Vérifier si l'utilisateur a déjà un profil mentee
    if hasattr(request.user.profil, 'mentorat_mentee'):
        messages.info(request, _("Vous êtes déjà inscrit en tant que mentoré."))
        return redirect('mentorat:tableau_de_bord_mentee')

    if request.method == 'POST':
        form = InscriptionMenteeForm(request.POST)
        if form.is_valid():
            mentee = form.save(commit=False)
            mentee.profil = request.user.profil
            mentee.save()
            messages.success(request, _("Vous êtes maintenant inscrit en tant que mentoré."))
            return redirect('mentorat:tableau_de_bord_mentee')
    else:
        form = InscriptionMenteeForm()

    return render(request, 'mentorat/devenir_mentee.html', {'form': form})


@login_required
def liste_mentors(request):
    """
    Liste des mentors disponibles.
    """
    mentors = Mentor.objects.filter(est_actif=True, profil__est_menteur=True).select_related('profil__utilisateur')

    # Filtres
    domaine = request.GET.get('domaine')
    if domaine:
        mentors = mentors.filter(domaines_expertise=domaine)

    niveau = request.GET.get('niveau')
    if niveau:
        mentors = mentors.filter(niveau_experience=niveau)

    # Recherche
    query = request.GET.get('q')
    if query:
        mentors = mentors.filter(
            Q(profil__utilisateur__first_name__icontains=query) |
            Q(profil__utilisateur__last_name__icontains=query) |
            Q(bio_mentorat__icontains=query)
        )

    context = {
        'mentors': mentors,
        'domaines': Mentor.DOMAINES,
        'niveaux': Mentor.NIVEAUX_EXPERIENCE,
    }
    return render(request, 'mentorat/liste_mentors.html', context)


@login_required
def detail_mentor(request, pk):
    """
    Détail d'un mentor.
    """
    mentor = get_object_or_404(Mentor.objects.select_related('profil__utilisateur'), pk=pk)

    # Vérifier si l'utilisateur peut faire une demande
    peut_demander = False
    if hasattr(request.user, 'profil') and hasattr(request.user.profil, 'mentorat_mentee'):
        mentee = request.user.profil.mentorat_mentee
        # Vérifier qu'il n'y a pas déjà une demande ou relation active
        existe_demande = DemandeMentorat.objects.filter(
            mentee=mentee,
            mentor=mentor,
            statut__in=['en_attente', 'acceptee']
        ).exists()
        existe_relation = RelationMentorat.objects.filter(
            mentee=mentee,
            mentor=mentor,
            est_active=True
        ).exists()
        peut_demander = not (existe_demande or existe_relation)

    context = {
        'mentor': mentor,
        'peut_demander': peut_demander,
    }
    return render(request, 'mentorat/detail_mentor.html', context)


@login_required
def demander_mentorat(request, mentor_pk):
    """
    Faire une demande de mentorat.
    """
    mentor = get_object_or_404(Mentor, pk=mentor_pk)

    # Vérifications
    if not hasattr(request.user, 'profil') or not hasattr(request.user.profil, 'mentorat_mentee'):
        messages.error(request, _("Vous devez d'abord vous inscrire en tant que mentoré."))
        return redirect('mentorat:devenir_mentee')

    mentee = request.user.profil.mentorat_mentee

    # Vérifier qu'il n'y a pas déjà une demande ou relation
    if DemandeMentorat.objects.filter(
        mentee=mentee,
        mentor=mentor,
        statut__in=['en_attente', 'acceptee']
    ).exists():
        messages.warning(request, _("Vous avez déjà une demande en cours avec ce mentor."))
        return redirect('mentorat:detail_mentor', pk=mentor_pk)

    if RelationMentorat.objects.filter(
        mentee=mentee,
        mentor=mentor,
        est_active=True
    ).exists():
        messages.info(request, _("Vous êtes déjà en relation de mentorat avec ce mentor."))
        return redirect('mentorat:tableau_de_bord_mentee')

    if request.method == 'POST':
        form = DemandeMentoratForm(request.POST)
        if form.is_valid():
            demande = form.save(commit=False)
            demande.mentee = mentee
            demande.mentor = mentor
            demande.save()
            messages.success(request, _("Votre demande de mentorat a été envoyée !"))
            return redirect('mentorat:tableau_de_bord_mentee')
    else:
        form = DemandeMentoratForm()

    return render(request, 'mentorat/demander_mentorat.html', {
        'form': form,
        'mentor': mentor
    })


@login_required
def tableau_de_bord_mentor(request):
    """
    Tableau de bord du mentor.
    """
    if not hasattr(request.user, 'profil') or not hasattr(request.user.profil, 'mentorat_mentor'):
        messages.error(request, _("Vous n'êtes pas inscrit en tant que mentor."))
        return redirect('mentorat:devenir_mentor')

    mentor = request.user.profil.mentorat_mentor

    demandes_recues = DemandeMentorat.objects.filter(
        mentor=mentor,
        statut='en_attente'
    ).select_related('mentee__profil__utilisateur')

    relations_actives = RelationMentorat.objects.filter(
        mentor=mentor,
        est_active=True
    ).select_related('mentee__profil__utilisateur')

    seances_a_venir = SeanceMentorat.objects.filter(
        relation__mentor=mentor,
        date_heure__gte=timezone.now() - timedelta(hours=4),
        statut='planifiee'
    ).select_related('relation__mentee__profil__utilisateur').order_by('date_heure')[:5]

    # Revenus du mentor
    paiements_confirmes = PaiementSeance.objects.filter(
        seance__relation__mentor=mentor,
        statut='confirme'
    )
    paiements_en_attente = PaiementSeance.objects.filter(
        seance__relation__mentor=mentor,
        statut='preuve_soumise'
    )
    revenus_confirmes = paiements_confirmes.aggregate(total=Sum('montant_mentor'))['total'] or 0
    revenus_en_attente = paiements_en_attente.aggregate(total=Sum('montant_mentor'))['total'] or 0

    context = {
        'mentor': mentor,
        'demandes_recues': demandes_recues,
        'relations_actives': relations_actives,
        'seances_a_venir': seances_a_venir,
        'revenus_confirmes': revenus_confirmes,
        'revenus_en_attente': revenus_en_attente,
        'nb_paiements_confirmes': paiements_confirmes.count(),
    }
    return render(request, 'mentorat/tableau_de_bord_mentor.html', context)


def _is_seance_participant(user, seance):
    if not hasattr(user, 'profil'):
        return False
    profil = user.profil
    return (
        hasattr(profil, 'mentorat_mentor') and seance.relation.mentor == profil.mentorat_mentor
    ) or (
        hasattr(profil, 'mentorat_mentee') and seance.relation.mentee == profil.mentorat_mentee
    )


@staff_member_required
def admin_dashboard(request):
    """Tableau de bord administratif pour les candidatures de mentors."""
    pending_applications = MentorApplication.objects.filter(status='pending').count()
    approved_applications = MentorApplication.objects.filter(status='approved').count()
    rejected_applications = MentorApplication.objects.filter(status='rejected').count()
    mentors_count = Mentor.objects.filter(est_actif=True, profil__est_menteur=True).count()
    bookings = SeanceMentorat.objects.filter(statut='planifiee').count()
    return render(request, 'mentorat/admin_dashboard.html', {
        'pending_applications': pending_applications,
        'approved_applications': approved_applications,
        'rejected_applications': rejected_applications,
        'mentors_count': mentors_count,
        'bookings': bookings,
    })


@staff_member_required
def applications_list(request):
    """Liste des candidatures mentor disponibles pour admin."""
    applications = MentorApplication.objects.all().select_related('profil__utilisateur')
    return render(request, 'mentorat/admin_applications.html', {
        'applications': applications,
    })


@staff_member_required
def application_detail(request, application_pk):
    """Détail et modération d'une candidature de mentor."""
    application = get_object_or_404(MentorApplication.objects.select_related('profil__utilisateur'), pk=application_pk)
    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('rejection_notes', '')
        if action == 'approve':
            application.approve()
            messages.success(request, _('La candidature a été approuvée et le mentor a été activé.'))
        elif action == 'reject':
            application.reject(notes=notes)
            messages.success(request, _('La candidature a été rejetée.'))
        return redirect('mentorat:application_detail', application_pk=application.pk)
    return render(request, 'mentorat/admin_application_detail.html', {
        'application': application,
    })


@login_required
def video_seance(request, seance_pk):
    """Page de visioconférence pour une séance de mentorat en visio."""
    seance = get_object_or_404(
        SeanceMentorat.objects.select_related(
            'relation__mentor__profil__utilisateur',
            'relation__mentee__profil__utilisateur',
            'relation__mentor__profil',
            'relation__mentee__profil'
        ),
        pk=seance_pk,
        statut__in=['planifiee', 'en_cours']
    )

    if seance.modalite != 'visio':
        raise Http404("Cette séance n'est pas prévue en visioconférence.")

    if not _is_seance_participant(request.user, seance):
        raise Http404("Accès refusé.")

    mentor_user = seance.relation.mentor.profil.utilisateur
    mentee_user = seance.relation.mentee.profil.utilisateur
    current_user_id = request.user.id
    if current_user_id == mentor_user.id:
        role = 'mentor'
    elif current_user_id == mentee_user.id:
        role = 'mentee'
    else:
        raise Http404("Accès refusé.")

    participants = [
        {
            'id': mentor_user.id,
            'name': mentor_user.get_full_name() or mentor_user.username,
            'role': 'mentor',
        },
        {
            'id': mentee_user.id,
            'name': mentee_user.get_full_name() or mentee_user.username,
            'role': 'mentee',
        },
    ]

    context = {
        'room_type': 'mentorat_seance',
        'room_pk': seance.pk,
        'room_title': seance.titre,
        'room_description': seance.description or seance.relation.mentor.profil.utilisateur.get_full_name() or seance.relation.mentee.profil.utilisateur.get_full_name() or seance.titre,
        'room_modalite': seance.get_modalite_display(),
        'room_date': seance.date_heure.strftime('%d %B %Y'),
        'room_time': seance.date_heure.strftime('%H:%M'),
        'room_duration': f"{seance.duree_minutes} minutes",
        'room_participants': participants,
        'participants_count': len(participants),
        'participant_label': 'Mentor et mentee',
        'current_user_id': current_user_id,
        'current_user_name': request.user.get_full_name() or request.user.username,
        'role_label': 'Mentor' if role == 'mentor' else 'Mentee',
        'back_url': reverse('mentorat:detail_relation', kwargs={'pk': seance.relation.pk}),
        'back_label': "Retour à la relation",
        'room_notes': "Activez votre micro et votre caméra, puis lancez la session en groupe.",
    }
    return render(request, 'video_room.html', context)


@login_required
def tableau_de_bord_mentee(request):
    """
    Tableau de bord du mentoré.
    """
    if not hasattr(request.user, 'profil') or not hasattr(request.user.profil, 'mentorat_mentee'):
        messages.error(request, _("Vous n'êtes pas inscrit en tant que mentoré."))
        return redirect('mentorat:devenir_mentee')

    mentee = request.user.profil.mentorat_mentee

    demandes_envoyees = DemandeMentorat.objects.filter(
        mentee=mentee
    ).select_related('mentor__profil__utilisateur').order_by('-date_creation')

    relations_actives = RelationMentorat.objects.filter(
        mentee=mentee,
        est_active=True
    ).select_related('mentor__profil__utilisateur')

    seances_a_venir = SeanceMentorat.objects.filter(
        relation__mentee=mentee,
        date_heure__gte=timezone.now() - timedelta(hours=4),
        statut='planifiee'
    ).select_related('relation__mentor__profil__utilisateur').order_by('date_heure')[:5]

    context = {
        'mentee': mentee,
        'demandes_envoyees': demandes_envoyees,
        'relations_actives': relations_actives,
        'seances_a_venir': seances_a_venir,
    }
    return render(request, 'mentorat/tableau_de_bord_mentee.html', context)


@login_required
def gerer_demande(request, demande_pk, action):
    """
    Accepter ou refuser une demande de mentorat.
    """
    demande = get_object_or_404(DemandeMentorat, pk=demande_pk)

    # Vérifier que l'utilisateur est le mentor concerné
    if not hasattr(request.user, 'profil') or not hasattr(request.user.profil, 'mentorat_mentor'):
        messages.error(request, _("Accès non autorisé."))
        return redirect('mentorat:index')

    if demande.mentor != request.user.profil.mentorat_mentor:
        messages.error(request, _("Cette demande ne vous concerne pas."))
        return redirect('mentorat:tableau_de_bord_mentor')

    if action == 'accepter':
        demande.accepter()
        try:
            send_mentorship_acceptance_email(demande, language=getattr(request, 'LANGUAGE_CODE', None))
        except Exception:
            pass
        messages.success(request, _("Demande de %(mentee)s acceptée !") % {'mentee': demande.mentee})
    elif action == 'refuser':
        demande.refuser()
        messages.success(request, _("Demande de %(mentee)s refusée.") % {'mentee': demande.mentee})

    return redirect('mentorat:tableau_de_bord_mentor')


@login_required
def planifier_seance(request, relation_pk):
    """
    Planifier une nouvelle séance.
    """
    relation = get_object_or_404(RelationMentorat, pk=relation_pk, est_active=True)

    # Vérifier que l'utilisateur fait partie de la relation
    user_profil = request.user.profil
    if not (
        (hasattr(user_profil, 'mentorat_mentor') and relation.mentor == user_profil.mentorat_mentor) or
        (hasattr(user_profil, 'mentorat_mentee') and relation.mentee == user_profil.mentorat_mentee)
    ):
        messages.error(request, _("Accès non autorisé."))
        return redirect('mentorat:index')

    if request.method == 'POST':
        form = SeanceMentoratForm(request.POST)
        if form.is_valid():
            seance = form.save(commit=False)
            seance.relation = relation
            seance.save()
            # Si le mentor est payant, créer un paiement et rediriger vers le paiement
            if seance.est_payante():
                ip_mentoré = request.META.get('REMOTE_ADDR')
                user_agent = request.META.get('HTTP_USER_AGENT', '')
                paiement = PaiementSeance.creer_pour_seance(
                    seance,
                    ip_mentoré=ip_mentoré,
                    user_agent=user_agent,
                )
                messages.info(request, _("Séance planifiée. Veuillez procéder au paiement pour la confirmer."))
                return redirect('mentorat:paiement_seance', seance_pk=seance.pk)
            messages.success(request, _("Séance planifiée avec succès !"))
            return redirect('mentorat:detail_relation', pk=relation_pk)
    else:
        form = SeanceMentoratForm()

    return render(request, 'mentorat/planifier_seance.html', {
        'form': form,
        'relation': relation,
        'tarif': relation.mentor.tarif_par_seance,
    })


@login_required
def detail_relation(request, pk):
    """
    Détail d'une relation de mentorat.
    """
    relation = get_object_or_404(RelationMentorat, pk=pk, est_active=True)

    # Vérifier que l'utilisateur fait partie de la relation
    user_profil = request.user.profil
    if not (
        (hasattr(user_profil, 'mentorat_mentor') and relation.mentor == user_profil.mentorat_mentor) or
        (hasattr(user_profil, 'mentorat_mentee') and relation.mentee == user_profil.mentorat_mentee)
    ):
        messages.error(request, _("Accès non autorisé."))
        return redirect('mentorat:index')

    seances = SeanceMentorat.objects.filter(relation=relation).order_by('-date_heure')

    context = {
        'relation': relation,
        'seances': seances,
        'est_mentor': hasattr(user_profil, 'mentorat_mentor') and relation.mentor == user_profil.mentorat_mentor,
    }
    return render(request, 'mentorat/detail_relation.html', context)


@login_required
def terminer_seance(request, seance_pk):
    """
    Terminer une séance avec des notes.
    """
    seance = get_object_or_404(SeanceMentorat, pk=seance_pk, statut__in=['planifiee', 'en_cours'])

    # Vérifier que l'utilisateur fait partie de la relation
    user_profil = request.user.profil
    if not (
        (hasattr(user_profil, 'mentorat_mentor') and seance.relation.mentor == user_profil.mentorat_mentor) or
        (hasattr(user_profil, 'mentorat_mentee') and seance.relation.mentee == user_profil.mentorat_mentee)
    ):
        messages.error(request, _("Accès non autorisé."))
        return redirect('mentorat:index')

    if request.method == 'POST':
        form = TerminerSeanceForm(request.POST)
        if form.is_valid():
            notes_mentor = form.cleaned_data.get('notes_mentor', '')
            notes_mentee = form.cleaned_data.get('notes_mentee', '')

            # Déterminer qui écrit quoi
            if hasattr(user_profil, 'mentorat_mentor') and seance.relation.mentor == user_profil.mentorat_mentor:
                seance.notes_mentor = notes_mentor
            else:
                seance.notes_mentee = notes_mentee

            seance.statut = 'terminee'
            seance.save()
            messages.success(request, _("Séance terminée avec succès !"))
            return redirect('mentorat:detail_relation', pk=seance.relation.pk)
    else:
        form = TerminerSeanceForm()

    return render(request, 'mentorat/terminer_seance.html', {
        'form': form,
        'seance': seance
    })


@login_required
def terminer_relation(request, relation_pk):
    """
    Terminer une relation de mentorat.
    """
    relation = get_object_or_404(RelationMentorat, pk=relation_pk, est_active=True)

    # Vérifier que l'utilisateur fait partie de la relation
    user_profil = request.user.profil
    if not (
        (hasattr(user_profil, 'mentorat_mentor') and relation.mentor == user_profil.mentorat_mentor) or
        (hasattr(user_profil, 'mentorat_mentee') and relation.mentee == user_profil.mentorat_mentee)
    ):
        messages.error(request, _("Accès non autorisé."))
        return redirect('mentorat:index')

    if request.method == 'POST':
        relation.terminer()
        messages.success(request, _("Relation de mentorat terminée."))
        if hasattr(user_profil, 'mentorat_mentor'):
            return redirect('mentorat:tableau_de_bord_mentor')
        else:
            return redirect('mentorat:tableau_de_bord_mentee')

    return render(request, 'mentorat/terminer_relation.html', {'relation': relation})


@login_required
def paiement_seance(request, seance_pk):
    """
    Page de paiement pour une séance payante.
    Accessible uniquement par le mentee de la relation.
    """
    seance = get_object_or_404(SeanceMentorat, pk=seance_pk)

    # Seul le mentee doit payer
    user_profil = request.user.profil
    if not (hasattr(user_profil, 'mentorat_mentee') and seance.relation.mentee == user_profil.mentorat_mentee):
        messages.error(request, _("Accès non autorisé."))
        return redirect('mentorat:index')

    # Récupérer ou créer le paiement de séance associé
    paiement_seance, _ = PaiementSeance.objects.get_or_create(
        seance=seance,
        defaults={
            'montant_total': seance.relation.mentor.tarif_par_seance,
            'commission_numeria': round(seance.relation.mentor.tarif_par_seance * PaiementSeance.TAUX_COMMISSION / 100),
            'montant_mentor': round(seance.relation.mentor.tarif_par_seance * (100 - PaiementSeance.TAUX_COMMISSION) / 100),
        }
    )

    if paiement_seance.statut == 'confirme':
        messages.info(request, _("Ce paiement est déjà confirmé."))
        return redirect('mentorat:detail_relation', pk=seance.relation.pk)

    providers_disponibles = PAYMENT_PROVIDERS

    if request.method == 'POST' and 'provider' in request.POST:
        provider = request.POST.get('provider', 'sandbox')
        try:
            paiement, nouveau = creer_paiement(
                etudiant=request.user,
                paiement_seance=paiement_seance,
                provider=provider
            )

            paiement_seance.lier_paiement(paiement)

            if paiement.statut != 'reussi':
                traiter_paiement(paiement, provider)

            paiement_seance.confirmer()

            messages.success(
                request,
                "✅ Paiement réussi ! Votre séance de mentorat est confirmée."
            )
            return redirect('mentorat:detail_relation', pk=seance.relation.pk)

        except NotImplementedError:
            messages.warning(
                request,
                f"⚠️ Le provider '{provider}' n'est pas encore disponible. Contactez-nous à {settings.CONTACT_EMAIL}"
            )
            return redirect('mentorat:paiement_seance', seance_pk=seance.pk)

        except Exception as e:
            messages.error(request, f"❌ Erreur lors du paiement : {str(e)}")
            return redirect('mentorat:paiement_seance', seance_pk=seance.pk)

    if request.method == 'POST':
        form = PaiementSeanceForm(request.POST, request.FILES, instance=paiement_seance)
        if form.is_valid():
            p = form.save(commit=False)
            p.statut = 'preuve_soumise'
            p.date_submission = timezone.now()
            p.save()
            messages.success(request, _("Preuve de paiement envoyée. Votre séance sera confirmée après vérification."))
            return redirect('mentorat:detail_relation', pk=seance.relation.pk)
    else:
        form = PaiementSeanceForm(instance=paiement_seance)

    numeros_paiement = settings.MENTORAT_NUMEROS_PAIEMENT

    return render(request, 'mentorat/paiement_seance.html', {
        'seance': seance,
        'paiement': paiement_seance,
        'form': form,
        'numeros_paiement': numeros_paiement,
        'providers_disponibles': providers_disponibles,
    })
