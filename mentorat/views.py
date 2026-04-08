from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone
from .models import Mentor, Mentee, DemandeMentorat, RelationMentorat, SeanceMentorat
from .forms import InscriptionMentorForm, InscriptionMenteeForm, DemandeMentoratForm, SeanceMentoratForm, TerminerSeanceForm


def index(request):
    """
    Page d'accueil du mentorat.
    """
    mentors_count = Mentor.objects.filter(est_actif=True).count()
    mentees_count = Mentee.objects.filter(est_actif=True).count()
    relations_count = RelationMentorat.objects.filter(est_active=True).count()

    context = {
        'mentors_count': mentors_count,
        'mentees_count': mentees_count,
        'relations_count': relations_count,
    }
    return render(request, 'mentorat/index.html', context)


@login_required
def devenir_mentor(request):
    """
    Inscription en tant que mentor.
    """
    # Vérifier si l'utilisateur a déjà un profil mentor
    if hasattr(request.user, 'profil') and hasattr(request.user.profil, 'mentorat_mentor'):
        messages.info(request, "Vous êtes déjà inscrit en tant que mentor.")
        return redirect('mentorat:tableau_de_bord_mentor')

    if request.method == 'POST':
        form = InscriptionMentorForm(request.POST)
        if form.is_valid():
            mentor = form.save(commit=False)
            mentor.profil = request.user.profil
            mentor.save()
            messages.success(request, "Félicitations ! Vous êtes maintenant inscrit en tant que mentor.")
            return redirect('mentorat:tableau_de_bord_mentor')
    else:
        form = InscriptionMentorForm()

    return render(request, 'mentorat/devenir_mentor.html', {'form': form})


@login_required
def devenir_mentee(request):
    """
    Inscription en tant que mentoré.
    """
    # Vérifier si l'utilisateur a déjà un profil mentee
    if hasattr(request.user, 'profil') and hasattr(request.user.profil, 'mentorat_mentee'):
        messages.info(request, "Vous êtes déjà inscrit en tant que mentoré.")
        return redirect('mentorat:tableau_de_bord_mentee')

    if request.method == 'POST':
        form = InscriptionMenteeForm(request.POST)
        if form.is_valid():
            mentee = form.save(commit=False)
            mentee.profil = request.user.profil
            mentee.save()
            messages.success(request, "Vous êtes maintenant inscrit en tant que mentoré.")
            return redirect('mentorat:tableau_de_bord_mentee')
    else:
        form = InscriptionMenteeForm()

    return render(request, 'mentorat/devenir_mentee.html', {'form': form})


@login_required
def liste_mentors(request):
    """
    Liste des mentors disponibles.
    """
    mentors = Mentor.objects.filter(est_actif=True).select_related('profil__utilisateur')

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
        messages.error(request, "Vous devez d'abord vous inscrire en tant que mentoré.")
        return redirect('mentorat:devenir_mentee')

    mentee = request.user.profil.mentorat_mentee

    # Vérifier qu'il n'y a pas déjà une demande ou relation
    if DemandeMentorat.objects.filter(
        mentee=mentee,
        mentor=mentor,
        statut__in=['en_attente', 'acceptee']
    ).exists():
        messages.warning(request, "Vous avez déjà une demande en cours avec ce mentor.")
        return redirect('mentorat:detail_mentor', pk=mentor_pk)

    if RelationMentorat.objects.filter(
        mentee=mentee,
        mentor=mentor,
        est_active=True
    ).exists():
        messages.info(request, "Vous êtes déjà en relation de mentorat avec ce mentor.")
        return redirect('mentorat:tableau_de_bord_mentee')

    if request.method == 'POST':
        form = DemandeMentoratForm(request.POST)
        if form.is_valid():
            demande = form.save(commit=False)
            demande.mentee = mentee
            demande.mentor = mentor
            demande.save()
            messages.success(request, "Votre demande de mentorat a été envoyée !")
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
        messages.error(request, "Vous n'êtes pas inscrit en tant que mentor.")
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
        date_heure__gte=timezone.now(),
        statut='planifiee'
    ).select_related('relation__mentee__profil__utilisateur').order_by('date_heure')[:5]

    context = {
        'mentor': mentor,
        'demandes_recues': demandes_recues,
        'relations_actives': relations_actives,
        'seances_a_venir': seances_a_venir,
    }
    return render(request, 'mentorat/tableau_de_bord_mentor.html', context)


@login_required
def tableau_de_bord_mentee(request):
    """
    Tableau de bord du mentoré.
    """
    if not hasattr(request.user, 'profil') or not hasattr(request.user.profil, 'mentorat_mentee'):
        messages.error(request, "Vous n'êtes pas inscrit en tant que mentoré.")
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
        date_heure__gte=timezone.now(),
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
        messages.error(request, "Accès non autorisé.")
        return redirect('mentorat:index')

    if demande.mentor != request.user.profil.mentorat_mentor:
        messages.error(request, "Cette demande ne vous concerne pas.")
        return redirect('mentorat:tableau_de_bord_mentor')

    if action == 'accepter':
        demande.accepter()
        messages.success(request, f"Demande de {demande.mentee} acceptée !")
    elif action == 'refuser':
        demande.refuser()
        messages.success(request, f"Demande de {demande.mentee} refusée.")

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
        messages.error(request, "Accès non autorisé.")
        return redirect('mentorat:index')

    if request.method == 'POST':
        form = SeanceMentoratForm(request.POST)
        if form.is_valid():
            seance = form.save(commit=False)
            seance.relation = relation
            seance.save()
            messages.success(request, "Séance planifiée avec succès !")
            return redirect('mentorat:detail_relation', pk=relation_pk)
    else:
        form = SeanceMentoratForm()

    return render(request, 'mentorat/planifier_seance.html', {
        'form': form,
        'relation': relation
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
        messages.error(request, "Accès non autorisé.")
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
    seance = get_object_or_404(SeanceMentorat, pk=seance_pk, statut='planifiee')

    # Vérifier que l'utilisateur fait partie de la relation
    user_profil = request.user.profil
    if not (
        (hasattr(user_profil, 'mentorat_mentor') and seance.relation.mentor == user_profil.mentorat_mentor) or
        (hasattr(user_profil, 'mentorat_mentee') and seance.relation.mentee == user_profil.mentorat_mentee)
    ):
        messages.error(request, "Accès non autorisé.")
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
            messages.success(request, "Séance terminée avec succès !")
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
        messages.error(request, "Accès non autorisé.")
        return redirect('mentorat:index')

    if request.method == 'POST':
        relation.terminer()
        messages.success(request, "Relation de mentorat terminée.")
        if hasattr(user_profil, 'mentorat_mentor'):
            return redirect('mentorat:tableau_de_bord_mentor')
        else:
            return redirect('mentorat:tableau_de_bord_mentee')

    return render(request, 'mentorat/terminer_relation.html', {'relation': relation})
