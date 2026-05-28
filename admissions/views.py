# admissions/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.utils.translation import gettext as _
from .models import CampagneRecrutement, Candidature
from .forms import FormulaireCandidature
from paiements.models import Paiement
from paiements.constants import PAYMENT_PROVIDERS
from numeria_project.emails import send_candidacy_acceptance_email
import uuid


def liste_campagnes(request):
    """Liste des campagnes de recrutement ouvertes"""
    campagnes = CampagneRecrutement.objects.filter(est_active=True)
    
    for campagne in campagnes:
        campagne.nb_candidatures = campagne.candidatures.filter(statut__in=['soumise', 'en_revue']).count()
    
    return render(request, 'admissions/liste_campagnes.html', {'campagnes': campagnes})


def detail_campagne(request, campagne_id):
    """Détail d'une campagne de recrutement"""
    campagne = get_object_or_404(CampagneRecrutement, id=campagne_id, est_active=True)
    
    a_candidate = False
    a_paiement_attente = False
    a_paiement_reussi = False
    paiement_id = None
    
    if request.user.is_authenticated:
        # Vérifier si déjà candidaté
        if Candidature.objects.filter(utilisateur=request.user, campagne=campagne).exists():
            a_candidate = True
        
        # Vérifier les paiements pour cette campagne
        paiement = Paiement.objects.filter(
            etudiant=request.user,
            reference_numeria__startswith=f"CAND-{campagne.id}",
        ).first()
        
        if paiement:
            paiement_id = paiement.id
            if paiement.statut == 'en_attente':
                a_paiement_attente = True
            elif paiement.statut == 'reussi':
                a_paiement_reussi = True
    
    return render(request, 'admissions/detail_campagne.html', {
        'campagne': campagne,
        'a_candidate': a_candidate,
        'a_paiement_attente': a_paiement_attente,
        'a_paiement_reussi': a_paiement_reussi,
        'paiement_id': paiement_id,
    })


@login_required
def page_paiement_candidature(request, campagne_id):
    """
    Page de paiement DÉDIÉE aux frais de candidature.
    """
    campagne = get_object_or_404(CampagneRecrutement, id=campagne_id)
    
    # Vérifier si la campagne est ouverte
    if not campagne.est_ouverte():
        messages.error(request, _("❌ Cette campagne de recrutement est fermée."))
        return redirect('admissions:liste_campagnes')
    
    # Vérifier si l'utilisateur a déjà candidaté
    if Candidature.objects.filter(utilisateur=request.user, campagne=campagne).exists():
        messages.warning(request, _("⚠️ Vous avez déjà candidaté pour cette formation."))
        return redirect('admissions:detail_campagne', campagne_id=campagne.id)
    
    # Vérifier si un paiement est déjà réussi
    paiement_reussi = Paiement.objects.filter(
        etudiant=request.user,
        reference_numeria__startswith=f"CAND-{campagne.id}",
        statut='reussi'
    ).first()
    
    if paiement_reussi:
        messages.success(request, _("✅ Vous avez déjà payé les frais de candidature. Vous pouvez maintenant postuler."))
        return redirect('admissions:candidature', campagne_id=campagne.id)
    
    # Vérifier si un paiement est en attente
    paiement_attente = Paiement.objects.filter(
        etudiant=request.user,
        reference_numeria__startswith=f"CAND-{campagne.id}",
        statut='en_attente'
    ).first()
    
    if request.method == 'POST':
        provider = request.POST.get('provider', 'sandbox')
        
        if provider == 'sandbox':
            # Mode sandbox - paiement immédiatement réussi
            if not paiement_attente:
                # Créer un nouveau paiement
                paiement = Paiement.objects.create(
                    etudiant=request.user,
                    cours=None,
                    montant_initial=campagne.frais_candidature,
                    montant_final=campagne.frais_candidature,
                    devise='XOF',
                    statut='reussi',
                    provider='sandbox',
                    reference_numeria=f"CAND-{campagne.id}-{uuid.uuid4().hex[:8].upper()}",
                    reference_provider='SANDBOX-CANDIDATURE',
                    notes=f"Frais de candidature - {campagne.nom}"
                )
            else:
                paiement = paiement_attente
                paiement.statut = 'reussi'
                paiement.save()
            
            messages.success(
                request, 
                _("✅ Paiement de {montant} FCFA réussi ! Vous pouvez maintenant remplir votre formulaire de candidature.").format(montant=campagne.frais_candidature)
            )
            return redirect('admissions:candidature', campagne_id=campagne.id)
        
        else:
            messages.warning(
                request, 
                _("⚠️ Seul le mode sandbox est disponible pour le moment. Les autres moyens de paiement arrivent bientôt.")
            )
    
    # Créer un paiement en attente si nécessaire
    if not paiement_attente and not paiement_reussi:
        paiement_attente = Paiement.objects.create(
            etudiant=request.user,
            cours=None,
            montant_initial=campagne.frais_candidature,
            montant_final=campagne.frais_candidature,
            devise='XOF',
            statut='en_attente',
            provider='sandbox',
            reference_numeria=f"CAND-{campagne.id}-{uuid.uuid4().hex[:8].upper()}",
            notes=f"Frais de candidature - {campagne.nom}"
        )
    
    context = {
        'campagne': campagne,
        'paiement': paiement_attente,
        'providers': PAYMENT_PROVIDERS,
    }
    
    return render(request, 'admissions/paiement_candidature.html', context)


@login_required
def confirmation_paiement_candidature(request, campagne_id):
    """Page de confirmation après paiement réussi"""
    campagne = get_object_or_404(CampagneRecrutement, id=campagne_id)
    
    paiement = Paiement.objects.filter(
        etudiant=request.user,
        reference_numeria__startswith=f"CAND-{campagne.id}",
        statut='reussi'
    ).first()
    
    if not paiement:
        messages.warning(request, _("Aucun paiement trouvé. Veuillez effectuer le paiement."))
        return redirect('admissions:page_paiement_candidature', campagne_id=campagne.id)
    
    return render(request, 'admissions/confirmation_paiement.html', {
        'campagne': campagne,
        'paiement': paiement
    })


@login_required
def candidature(request, campagne_id):
    """Formulaire de candidature - accessible APRÈS paiement ou si gratuit"""
    campagne = get_object_or_404(CampagneRecrutement, id=campagne_id)
    
    if not campagne.est_ouverte():
        messages.error(request, "❌ Cette campagne de recrutement est fermée.")
        return redirect('admissions:liste_campagnes')
    
    # Vérifier si l'utilisateur a déjà candidaté
    if Candidature.objects.filter(utilisateur=request.user, campagne=campagne).exists():
        messages.warning(request, "⚠️ Vous avez déjà soumis une candidature.")
        return redirect('admissions:detail_campagne', campagne_id=campagne.id)
    
    # Vérifier le paiement si la campagne est payante
    if campagne.frais_candidature > 0:
        paiement = Paiement.objects.filter(
            etudiant=request.user,
            reference_numeria__startswith=f"CAND-{campagne.id}",
            statut='reussi'
        ).first()
        
        if not paiement:
            messages.warning(
                request, 
                f"💳 Vous devez payer les frais de candidature de {campagne.frais_candidature} FCFA avant de postuler."
            )
            return redirect('admissions:page_paiement_candidature', campagne_id=campagne.id)
    
    if request.method == 'POST':
        formulaire = FormulaireCandidature(request.POST, request.FILES)
        if formulaire.is_valid():
            candidature = formulaire.save(commit=False)
            candidature.utilisateur = request.user
            candidature.campagne = campagne
            candidature.statut = 'soumise'
            
            # Lier le paiement si existe
            if campagne.frais_candidature > 0:
                paiement = Paiement.objects.filter(
                    etudiant=request.user,
                    reference_numeria__startswith=f"CAND-{campagne.id}",
                    statut='reussi'
                ).first()
                if paiement:
                    candidature.paiement = paiement
                    candidature.paiement_effectue = True
            
            candidature.save()
            
            messages.success(request, "✅ Votre candidature a été soumise avec succès !")
            return redirect('admissions:mes_candidatures')
        else:
            messages.error(request, "❌ Veuillez corriger les erreurs ci-dessous.")
    else:
        initial = {
            'nom': request.user.last_name,
            'prenom': request.user.first_name,
            'email_personnel': request.user.email,
        }
        
        if hasattr(request.user, 'profil') and request.user.profil:
            initial['pays'] = request.user.profil.pays or ''
            initial['ville'] = request.user.profil.ville or ''
        
        formulaire = FormulaireCandidature(initial=initial)
    
    return render(request, 'admissions/candidature.html', {
        'formulaire': formulaire,
        'campagne': campagne,
    })


@login_required
def mes_candidatures(request):
    """Liste des candidatures de l'utilisateur"""
    candidatures = Candidature.objects.filter(utilisateur=request.user).order_by('-date_soumission')
    return render(request, 'admissions/mes_candidatures.html', {'candidatures': candidatures})


@login_required
def detail_candidature(request, candidature_id):
    """Détail d'une candidature"""
    candidature = get_object_or_404(Candidature, id=candidature_id, utilisateur=request.user)
    return render(request, 'admissions/detail_candidature.html', {'candidature': candidature})


@staff_member_required
def admin_candidatures(request):
    """Liste des candidatures pour l'admin"""
    statut_filtre = request.GET.get('statut', '')
    campagne_filtre = request.GET.get('campagne', '')
    
    candidatures = Candidature.objects.all().select_related('utilisateur', 'campagne')
    
    if statut_filtre:
        candidatures = candidatures.filter(statut=statut_filtre)
    if campagne_filtre:
        candidatures = candidatures.filter(campagne_id=campagne_filtre)
    
    paginator = Paginator(candidatures, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    campagnes = CampagneRecrutement.objects.all()
    
    return render(request, 'admissions/admin_candidatures.html', {
        'candidatures': page_obj,
        'campagnes': campagnes,
        'statut_actuel': statut_filtre,
        'campagne_actuelle': campagne_filtre,
        'statuts': Candidature.STATUTS
    })


@staff_member_required
def changer_statut(request, candidature_id):
    """Changer le statut d'une candidature (admin)"""
    if request.method == 'POST':
        candidature = get_object_or_404(Candidature, id=candidature_id)
        nouveau_statut = request.POST.get('statut')
        commentaire = request.POST.get('commentaire', '')
        
        if nouveau_statut in dict(Candidature.STATUTS):
            candidature.statut = nouveau_statut
            candidature.commentaire_admin = commentaire
            candidature.date_decision = timezone.now()
            candidature.save()

            if nouveau_statut == 'acceptee':
                try:
                    send_candidacy_acceptance_email(candidature, language=getattr(request, 'LANGUAGE_CODE', None))
                except Exception:
                    pass

            messages.success(request, f"✅ Statut mis à jour : {dict(Candidature.STATUTS)[nouveau_statut]}")
    
    return redirect('admissions:admin_candidatures')