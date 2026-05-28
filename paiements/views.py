from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from cours.models import Cours
from formation.models import InscriptionFormation
from .models import Paiement
from .service import (
    creer_paiement,
    traiter_paiement,
    verifier_acces_cours,
    verifier_acces_formation
)
from .constants import PAYMENT_PROVIDERS


@login_required
def page_paiement(request, cours_id):
    """
    Page de paiement pour un cours payant.
    Affiche le récapitulatif et les options de paiement.
    """
    cours = get_object_or_404(Cours, id=cours_id, est_publie=True)

    # Si le cours est gratuit, inscrire directement
    if cours.est_gratuit:
        messages.info(request, "Ce cours est gratuit !")
        return redirect('cours:inscrire', cours_id=cours_id)

    # Vérifier si déjà payé
    if verifier_acces_cours(request.user, cours):
        messages.info(request, "Tu as déjà accès à ce cours ! 🎓")
        return redirect('cours:detail', cours_id=cours_id)

    contexte = {
        'objet': cours,
        'objet_type': 'cours',
        'action_url': reverse('paiements:initier', args=[cours.id]),
        'providers_disponibles': PAYMENT_PROVIDERS,
    }

    return render(request, 'paiements/page_paiement.html', contexte)


@login_required
def page_paiement_formation(request, inscription_id):
    """
    Page de paiement pour une inscription de formation.
    """
    inscription = get_object_or_404(InscriptionFormation, id=inscription_id, etudiant=request.user)

    if inscription.statut == 'confirmee' or verifier_acces_formation(request.user, inscription.session):
        messages.info(request, "Cette inscription a déjà été payée.")
        return redirect('formation:session_detail', session_id=inscription.session.id)

    contexte = {
        'objet': inscription,
        'objet_type': 'formation',
        'providers_disponibles': PAYMENT_PROVIDERS,
        'action_url': reverse('paiements:initier_formation', args=[inscription.id]),
    }

    return render(request, 'paiements/page_paiement.html', contexte)


@login_required
def initier_paiement_formation(request, inscription_id):
    """
    Initie le paiement pour une inscription de formation.
    """
    if request.method != 'POST':
        return redirect('paiements:page_paiement_formation', inscription_id=inscription_id)

    inscription = get_object_or_404(InscriptionFormation, id=inscription_id, etudiant=request.user)

    if inscription.statut == 'confirmee':
        messages.info(request, "Cette inscription a déjà été payée.")
        return redirect('formation:session_detail', session_id=inscription.session.id)

    provider = request.POST.get('provider', 'sandbox')
    paiement, nouveau = creer_paiement(
        etudiant=request.user,
        formation_inscription=inscription,
        provider=provider
    )

    if not nouveau and paiement.statut == 'reussi':
        messages.info(request, "Tu as déjà payé cette formation.")
        return redirect('formation:session_detail', session_id=inscription.session.id)

    try:
        traiter_paiement(paiement, provider)
        messages.success(
            request,
            f"✅ Paiement réussi ! Tu es maintenant inscrit à la session '{inscription.session.nom}'."
        )
        return redirect('paiements:confirmation', paiement_id=paiement.id)

    except NotImplementedError:
        messages.warning(
            request,
            f"⚠️ Le provider '{provider}' n'est pas encore disponible. Contactez-nous à {settings.CONTACT_EMAIL}"
        )
        return redirect('paiements:page_paiement_formation', inscription_id=inscription.id)

    except Exception as e:
        messages.error(request, f"❌ Erreur lors du paiement : {str(e)}")
        return redirect('paiements:page_paiement_formation', inscription_id=inscription.id)


@login_required
def initier_paiement(request, cours_id):
    """
    Initie le paiement avec le provider choisi.
    """
    if request.method != 'POST':
        return redirect('paiements:page_paiement', cours_id=cours_id)

    cours = get_object_or_404(Cours, id=cours_id, est_publie=True)
    provider = request.POST.get('provider', 'sandbox')

    # Créer l'enregistrement de paiement
    paiement, nouveau = creer_paiement(
        etudiant=request.user,
        cours=cours,
        provider=provider
    )

    if not nouveau:
        messages.info(request, "Tu as déjà accès à ce cours ! 🎓")
        return redirect('cours:detail', cours_id=cours_id)

    try:
        # Traiter le paiement avec le provider choisi
        traiter_paiement(paiement, provider)

        messages.success(
            request,
            f"✅ Paiement réussi ! Tu es maintenant inscrit au cours '{cours.titre}'."
        )
        return redirect('paiements:confirmation', paiement_id=paiement.id)

    except NotImplementedError:
        messages.warning(
            request,
            f"⚠️ Le provider '{provider}' n'est pas encore disponible. "
            f"Contactez-nous à {settings.CONTACT_EMAIL}"
        )
        return redirect('paiements:page_paiement', cours_id=cours_id)

    except Exception as e:
        messages.error(request, f"❌ Erreur lors du paiement : {str(e)}")
        return redirect('paiements:page_paiement', cours_id=cours_id)


@login_required
def confirmation_paiement(request, paiement_id):
    """
    Page de confirmation après un paiement réussi.
    """
    paiement = get_object_or_404(
        Paiement,
        id=paiement_id,
        etudiant=request.user
    )

    return render(request, 'paiements/confirmation.html', {'paiement': paiement})


@login_required
def historique_paiements(request):
    """
    Historique de tous les paiements de l'étudiant.
    """
    paiements = Paiement.objects.filter(
        etudiant=request.user
    ).select_related('cours')

    contexte = {
        'paiements': paiements,
        'total_depense': sum(
            p.montant for p in paiements if p.statut == 'reussi'
        ),
    }
    return render(request, 'paiements/historique.html', contexte)