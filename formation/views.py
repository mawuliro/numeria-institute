from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.db.models import Q
from django.utils import timezone

from .models import (
    Formation, SessionFormation, InscriptionFormation,
    LeconFormation, ProgressionLecon, CertificatFormation
)
from .forms import FormulairInscriptionFormation


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
    
    # Vérifier si l'utilisateur est inscrit
    inscription = None
    if request.user.is_authenticated:
        inscription = InscriptionFormation.objects.filter(
            session=session,
            etudiant=request.user
        ).first()
    
    context = {
        'session': session,
        'formation': formation,
        'inscription': inscription,
        'peut_inscrire': session.est_ouverte_aux_inscriptions() and not inscription,
    }
    return render(request, 'formation/detail_session.html', context)


@login_required
def inscrire_formation(request, session_id):
    """Inscription à une session."""
    session = get_object_or_404(SessionFormation, id=session_id)
    
    # Vérifications
    if not session.est_ouverte_aux_inscriptions():
        messages.error(request, "Cette session n'est plus ouverte aux inscriptions.")
        return redirect('formation:session_detail', session_id=session.id)
    
    # Vérifier doublon inscription
    if InscriptionFormation.objects.filter(session=session, etudiant=request.user).exists():
        messages.warning(request, "Vous êtes déjà inscrit à cette session.")
        return redirect('formation:mes_formations')
    
    # Créer inscription
    inscription = InscriptionFormation.objects.create(
        session=session,
        etudiant=request.user,
        prix_paye_fcfa=session.prix_reduit_fcfa or session.prix_fcfa,
        statut='en_attente'  # En attente de paiement
    )
    
    messages.success(request, "Inscription créée. Veuillez effectuer le paiement.")
    return redirect('formation:voir_paiement', inscription_id=inscription.id)


@login_required
def voir_paiement(request, inscription_id):
    """Page de paiement pour une inscription."""
    inscription = get_object_or_404(
        InscriptionFormation,
        id=inscription_id,
        etudiant=request.user
    )
    
    # Vérifier que l'inscription est en attente de paiement
    if inscription.statut != 'en_attente':
        messages.warning(request, "Cette inscription a déjà été traitée.")
        return redirect('formation:mes_formations')
    
    # Simuler la confirmation du paiement
    if request.method == 'POST':
        # En production, cela serait intégré avec un système de paiement réel
        inscription.statut = 'confirmee'
        inscription.date_paiement = timezone.now()
        inscription.save()
        messages.success(request, "Paiement confirmé! Bienvenue dans le cours.")
        return redirect('formation:mes_formations')
    
    context = {
        'inscription': inscription,
        'montant': inscription.prix_paye_fcfa,
    }
    return render(request, 'formation/paiement.html', context)


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
        messages.error(request, "Votre accès à cette formation a expiré.")
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
        messages.warning(request, "Ce certificat a expiré.")
    
    context = {
        'certificat': certificat,
        'est_valide': certificat.est_valide(),
    }
    return render(request, 'formation/verifier_certificat.html', context)
