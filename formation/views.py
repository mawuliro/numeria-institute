from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden, Http404
from django.urls import reverse
from django.utils.translation import gettext as _

from .models import (
    Formation, SessionFormation, InscriptionFormation,
    LeconFormation, ProgressionLecon, CertificatFormation
)


def liste_formations(request):
    """Page d'accueil des formations."""
    if request.user.is_authenticated and request.user.is_staff:
        # Les administrateurs voient toutes les formations non archivées,
        # même si elles ne sont pas encore publiées.
        formations = Formation.objects.filter(est_archivee=False).prefetch_related('sessions')
    else:
        formations = Formation.objects.filter(
            est_publiee=True,
            est_archivee=False
        ).prefetch_related('sessions')
    
    # Filtres optionnels
    type_filtre = request.GET.get('type')
    niveau_filtre = request.GET.get('niveau')
    
    if type_filtre:
        formations = formations.filter(type_formation=type_filtre)
    if niveau_filtre:
        formations = formations.filter(niveau=niveau_filtre)
    
    context = {
        'formations': formations,
        'types': Formation.TYPES_FORMATION,
        'niveaux': Formation.NIVEAUX,
    }
    return render(request, 'formation/liste.html', context)


def detail_formation(request, slug):
    """Détails d'une formation avec sessions."""
    formation = get_object_or_404(
        Formation.objects.prefetch_related('sessions', 'lecons', 'instructeurs'),
        slug=slug,
        est_publiee=True
    )
    
    # Sessions actives
    sessions_actives = formation.sessions_actives()
    
    context = {
        'formation': formation,
        'sessions': sessions_actives,
    }
    return render(request, 'formation/detail_formation.html', context)


def detail_session(request, session_id):
    """Détails d'une session."""
    session = get_object_or_404(SessionFormation, id=session_id)
    formation = session.formation
    
    # Vérifier si l'utilisateur est inscrit ou instructeur
    inscription = None
    est_instructeur = False
    if request.user.is_authenticated:
        inscription = InscriptionFormation.objects.filter(
            session=session,
            etudiant=request.user
        ).first()
        est_instructeur = session.get_instructeurs().filter(pk=request.user.pk).exists()

    peut_inscrire = session.est_ouverte_aux_inscriptions() and not inscription
    peut_rejoindre_visio = (
        session.modalite in ['visio', 'hybride'] and
        session.statut != 'annulee' and
        (est_instructeur or (inscription and inscription.a_acces()))
    )

    context = {
        'session': session,
        'formation': formation,
        'inscription': inscription,
        'est_instructeur': est_instructeur,
        'peut_inscrire': peut_inscrire,
        'peut_rejoindre_visio': peut_rejoindre_visio,
    }
    return render(request, 'formation/detail_session.html', context)


@login_required
def video_session(request, session_id):
    """Page de visioconférence pour une session de formation."""
    session = get_object_or_404(
        SessionFormation.objects.select_related('formation')
        .prefetch_related('instructeurs_session', 'formation__instructeurs', 'inscriptions__etudiant'),
        id=session_id
    )

    if session.statut == 'annulee':
        raise Http404("Cette session est annulée.")

    est_instructeur = session.get_instructeurs().filter(pk=request.user.pk).exists()
    inscription = InscriptionFormation.objects.filter(
        session=session,
        etudiant=request.user,
        statut__in=['confirmee', 'en_cours', 'terminee']
    ).first()

    if not est_instructeur and not inscription:
        raise Http404("Accès refusé.")

    if session.modalite not in ['visio', 'hybride']:
        raise Http404("Cette session n'est pas prévue en visioconférence.")

    instructors = list(session.get_instructeurs().all())
    participants = [
        {
            'id': instructor.id,
            'name': instructor.get_full_name() or instructor.username,
            'role': 'Instructeur',
        }
        for instructor in instructors
    ]

    if inscription:
        participants.append({
            'id': request.user.id,
            'name': request.user.get_full_name() or request.user.username,
            'role': 'Étudiant',
        })
    else:
        participants.append({
            'id': request.user.id,
            'name': request.user.get_full_name() or request.user.username,
            'role': 'Instructeur',
        })

    participant_count = session.inscriptions.filter(
        statut__in=['confirmee', 'en_cours', 'terminee']
    ).count() + len(instructors)

    context = {
        'room_type': 'formation_session',
        'room_pk': session.id,
        'room_title': session.nom,
        'room_description': session.formation.titre,
        'room_modalite': session.get_modalite_display(),
        'room_date': session.date_debut.strftime('%d %B %Y'),
        'room_time': '',
        'room_duration': None,
        'room_participants': participants,
        'participants_count': participant_count,
        'participant_label': f"{participant_count} participants attendus",
        'current_user_id': request.user.id,
        'current_user_name': request.user.get_full_name() or request.user.username,
        'role_label': 'Instructeur' if est_instructeur else 'Étudiant',
        'back_url': reverse('formation:session_detail', args=[session.id]),
        'back_label': "Retour à la session",
        'room_notes': "La session est prévue en visioconférence. Vérifiez votre connexion avant de rejoindre.",
    }
    return render(request, 'video_room.html', context)


@login_required
def inscrire_formation(request, session_id):
    """Inscription à une session."""
    session = get_object_or_404(SessionFormation, id=session_id)

    # Vérifications
    if not session.est_ouverte_aux_inscriptions():
        messages.error(request, _("Cette session n'est plus ouverte aux inscriptions."))
        return redirect('formation:session_detail', session_id=session.id)

    inscription = InscriptionFormation.objects.filter(session=session, etudiant=request.user).first()
    if inscription:
        if inscription.statut == 'en_attente':
            return redirect('paiements:page_paiement_formation', inscription_id=inscription.id)
        messages.warning(request, _("Vous êtes déjà inscrit à cette session."))
        return redirect('formation:mes_formations')

    # Créer inscription en attente de paiement
    inscription = InscriptionFormation.objects.create(
        session=session,
        etudiant=request.user,
        prix_paye_fcfa=session.prix_reduit_fcfa or session.prix_fcfa,
        statut='en_attente'  # En attente de paiement
    )

    messages.success(request, _("Inscription créée. Veuillez effectuer le paiement."))
    return redirect('paiements:page_paiement_formation', inscription_id=inscription.id)


@login_required
def voir_paiement(request, inscription_id):
    """Redirection vers la page de paiement centralisée."""
    inscription = get_object_or_404(
        InscriptionFormation,
        id=inscription_id,
        etudiant=request.user
    )
    return redirect('paiements:page_paiement_formation', inscription_id=inscription.id)


@login_required
def mes_formations(request):
    """Mes formations en cours et passées."""
    inscriptions = InscriptionFormation.objects.filter(
        etudiant=request.user
    ).select_related('session__formation').order_by('-date_inscription')
    
    context = {
        'inscriptions': inscriptions,
    }
    return render(request, 'formation/mes_formations.html', context)


@login_required
def voir_lecon(request, lecon_id):
    """Voir une leçon (accès conditionnel)."""
    lecon = get_object_or_404(LeconFormation, id=lecon_id)
    formation = lecon.formation
    
    # Vérifier accès: utilisateur doit être inscrit et avoir payé
    inscription = InscriptionFormation.objects.filter(
        session__formation=formation,
        etudiant=request.user,
        statut__in=['confirmee', 'en_cours']
    ).first()
    
    if not inscription:
        return HttpResponseForbidden("Vous n'avez pas accès à cette formation.")
    
    # Vérifier accès pas expiré
    if inscription.est_acces_expire():
        messages.error(request, _("Votre accès à cette formation a expiré."))
        return redirect('formation:mes_formations')
    
    # Enregistrer progression
    progression, _ = ProgressionLecon.objects.get_or_create(
        inscription=inscription,
        lecon=lecon
    )
    progression.est_commencee = True
    progression.save()
    
    # Leçons adjacentes
    lecon_suivante = lecon.get_next()
    lecon_precedente = lecon.get_previous()
    
    # Autres leçons pour sidebar
    autres_lecons = formation.lecons.all().order_by('ordre')
    
    # Récupérer les progressions pour toutes les leçons
    progressions = {p.lecon_id: p for p in inscription.progressions_lecons.all()}
    
    # Ajouter les progressions aux leçons
    for l in autres_lecons:
        l.progression = progressions.get(l.id)
    
    # Calculer la position actuelle
    lecon_actuelle = list(autres_lecons).index(lecon) + 1
    total_lecons = autres_lecons.count()
    
    context = {
        'lecon': lecon,
        'formation': formation,
        'inscription': inscription,
        'lecon_suivante': lecon_suivante,
        'lecon_precedente': lecon_precedente,
        'autres_lecons': autres_lecons,
        'lecon_actuelle': lecon_actuelle,
        'total_lecons': total_lecons,
        'date_expiration': inscription.acces_expire(),
    }
    return render(request, 'formation/voir_lecon.html', context)


def detail_certificat(request, id):
    """Voir un certificat (accès public si token)."""
    certificat = get_object_or_404(CertificatFormation, inscription__id=id)
    
    # Accès privé: utilisateur propriétaire du certificat
    if request.user.is_authenticated and request.user == certificat.inscription.etudiant:
        context = {
            'certificat': certificat,
            'est_proprietaire': True,
        }
        return render(request, 'formation/certificat.html', context)
    
    # Accès public: token requis
    token = request.GET.get('token')
    if not token or token != certificat.token_verification:
        return HttpResponseForbidden("Accès refusé.")
    
    context = {
        'certificat': certificat,
        'est_proprietaire': False,
    }
    return render(request, 'formation/certificat.html', context)


def verifier_certificat(request, token):
    """Vérifie un certificat par token (page publique)."""
    certificat = get_object_or_404(CertificatFormation, token_verification=token)
    
    if not certificat.est_valide():
        messages.warning(request, _("Ce certificat a expiré."))
    
    context = {
        'certificat': certificat,
        'est_valide': certificat.est_valide(),
    }
    return render(request, 'formation/verifier_certificat.html', context)
