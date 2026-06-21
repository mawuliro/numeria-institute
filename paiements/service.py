"""
Service de paiement Numeria Institute.

Architecture extensible — pour ajouter un nouveau provider :
1. Créer une fonction process_PROVIDER(paiement, données)
2. L'ajouter dans le dictionnaire PROVIDERS
3. C'est tout !
"""

import uuid
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.db import transaction
from .models import Paiement
from cours.models import InscriptionCours
from formation.models import InscriptionFormation


def generer_reference():
    """
    Génère une référence unique pour chaque paiement.
    Format : NIM-2025-XXXXXXXX
    """
    code = uuid.uuid4().hex.upper()[:16]
    annee = timezone.now().year
    return f"NIM-{annee}-{code}"


def creer_paiement(etudiant, course=None, formation=None, formation_inscription=None, paiement_seance=None, provider='sandbox', method=None):
    """
    Crée un enregistrement de paiement en attente.
    Appelé quand l'étudiant clique sur "Payer".
    `formation_inscription` is accepted for backwards compatibility; its .formation is used.
    """
    # Normalize: accept InscriptionFormation via formation_inscription kwarg
    if formation_inscription is not None and formation is None:
        formation = formation_inscription.formation

    cours = course  # Paiement model uses 'cours' FK

    if not cours and not formation and not paiement_seance:
        raise ValueError('Un paiement doit être associé à un cours, une formation ou une séance de mentorat.')

    if sum(bool(x) for x in [cours, formation, paiement_seance]) != 1:
        raise ValueError('Un paiement ne peut pas être lié à plusieurs objets en même temps.')

    if paiement_seance and paiement_seance.seance.relation.mentee.profil.utilisateur != etudiant:
        raise ValueError('La séance de mentorat doit appartenir au mentoré en cours.')

    # Vérifier s'il existe déjà un paiement actif pour cette séance
    if paiement_seance is not None:
        paiement_existant = None
        try:
            paiement_existant = paiement_seance.paiement
        except ObjectDoesNotExist:
            paiement_existant = None

        if paiement_existant and paiement_existant.statut != 'echoue':
            if paiement_existant.statut != 'reussi':
                paiement_existant.provider = provider
                paiement_existant.save(update_fields=['provider'])
            return paiement_existant, False

    # Vérifier qu'il n'y a pas déjà un paiement réussi pour un cours ou une formation
    paiement_existant = Paiement.objects.filter(
        etudiant=etudiant,
        cours=cours,
        formation=formation,
        statut='reussi'
    ).first()

    if paiement_existant:
        return paiement_existant, False  # False = déjà existant

    if paiement_seance:
        montant = paiement_seance.montant_total
    elif cours:
        montant = cours.price
    else:
        montant = formation.price

    if method is None:
        if provider == 'stripe':
            method = 'card'
        elif provider in ('mixx', 'moov'):
            method = provider

    paiement = Paiement.objects.create(
        etudiant=etudiant,
        cours=cours,
        formation=formation,
        montant_initial=montant,
        montant_final=montant,
        devise='XOF',
        statut='en_attente',
        provider=provider,
        method=method,
        reference_numeria=generer_reference(),
    )

    return paiement, True  # True = nouveau paiement créé


@transaction.atomic
def confirmer_paiement(paiement, reference_provider=None):
    """
    Confirme un paiement et inscrit l'étudiant au cours.
    Appelé par le webhook du provider ou en mode sandbox.
    Wrapped in an atomic transaction so payment + inscription always succeed or fail together.
    """
    # Mettre à jour le statut
    paiement.statut = 'reussi'
    paiement.reference_provider = reference_provider or 'SANDBOX'
    paiement.save()

    if paiement.formation_id:
        from formation.models import InscriptionFormation
        inscription = InscriptionFormation.objects.filter(
            formation=paiement.formation,
            etudiant=paiement.etudiant,
        ).first()
        if inscription:
            inscription.statut = 'confirmee'
            inscription.save(update_fields=['statut'])
        return inscription

    # Inscrire automatiquement l'étudiant au cours
    inscription, cree = InscriptionCours.objects.get_or_create(
        etudiant=paiement.etudiant,
        course=paiement.cours,
        defaults={
            'progression': 0,
            'est_termine': False,
        }
    )

    if cree:
        try:
            from numeria_project.emails import send_course_enrollment_email
            send_course_enrollment_email(paiement.etudiant, paiement.cours)
        except Exception:
            pass

    return inscription


def echouer_paiement(paiement, raison=''):
    """Marque un paiement comme échoué."""
    paiement.statut = 'echoue'
    paiement.notes = raison
    paiement.save()
    return paiement


def verifier_acces_cours(etudiant, course):
    """
    Vérifie si un étudiant a accès à un cours payant.
    Retourne True si :
    - Le cours est gratuit
    - L'étudiant a un paiement réussi pour ce cours
    """
    if course.is_free:
        return True

    return Paiement.objects.filter(
        etudiant=etudiant,
        cours=course,
        statut='reussi'
    ).exists()


def verifier_acces_formation(etudiant, formation):
    """
    Vérifie si un étudiant a accès à une formation payante.
    """
    return Paiement.objects.filter(
        etudiant=etudiant,
        formation=formation,
        statut='reussi'
    ).exists()


# ══════════════════════════════════════════════════════════════════
# PROVIDERS — Ajouter de nouveaux providers ici
# ══════════════════════════════════════════════════════════════════

def process_sandbox(paiement, donnees=None):
    """
    Provider sandbox — simule un paiement réussi instantanément.
    Utilisé pour les tests. Remplace par le vrai provider en production.
    """
    return confirmer_paiement(paiement, reference_provider='SANDBOX-TEST')


def process_stripe(paiement, donnees=None):
    """
    Provider Stripe — à implémenter quand le compte sera créé.
    """
    # TODO: Implémenter Stripe
    # import stripe
    # stripe.api_key = settings.STRIPE_SECRET_KEY
    # session = stripe.checkout.Session.create(...)
    raise NotImplementedError("Stripe pas encore configuré")


def process_fedapay(paiement, donnees=None):
    """
    Provider FedaPay — à implémenter quand le compte sera créé.
    """
    # TODO: Implémenter FedaPay
    raise NotImplementedError("FedaPay pas encore configuré")


def process_cinetpay(paiement, donnees=None):
    """
    Provider CinetPay — à implémenter quand le compte sera créé.
    """
    # TODO: Implémenter CinetPay
    raise NotImplementedError("CinetPay pas encore configuré")


def process_mixx(paiement, donnees=None):
    """
    Provider Mixx by YAS — à implémenter quand le compte sera créé.
    """
    # TODO: Implémenter Mixx by YAS
    raise NotImplementedError("Mixx by YAS pas encore configuré")


def process_moov(paiement, donnees=None):
    """
    Provider Moov Money — à implémenter quand le compte sera créé.
    """
    # TODO: Implémenter Moov Money
    raise NotImplementedError("Moov Money pas encore configuré")


# Dictionnaire des providers disponibles
PROVIDERS_DISPONIBLES = {
    'sandbox':  process_sandbox,
    'stripe':   process_stripe,
    'fedapay':  process_fedapay,
    'cinetpay': process_cinetpay,
    'mixx':     process_mixx,
    'moov':     process_moov,
}


def traiter_paiement(paiement, provider, donnees=None):
    """
    Point d'entrée principal — appelle le bon provider.
    """
    if provider not in PROVIDERS_DISPONIBLES:
        raise ValueError(f"Provider inconnu : {provider}")

    try:
        return PROVIDERS_DISPONIBLES[provider](paiement, donnees)
    except NotImplementedError:
        echouer_paiement(paiement, f"Provider {provider} pas encore configuré")
        raise