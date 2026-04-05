"""
Service de paiement Numeria Institute.

Architecture extensible — pour ajouter un nouveau provider :
1. Créer une fonction process_PROVIDER(paiement, données)
2. L'ajouter dans le dictionnaire PROVIDERS
3. C'est tout !
"""

import uuid
from django.utils import timezone
from .models import Paiement
from cours.models import InscriptionCours


def generer_reference():
    """
    Génère une référence unique pour chaque paiement.
    Format : NIM-2025-XXXXXXXX
    """
    code = str(uuid.uuid4()).upper()[:8]
    annee = timezone.now().year
    return f"NIM-{annee}-{code}"


def creer_paiement(etudiant, cours, provider='sandbox'):
    """
    Crée un enregistrement de paiement en attente.
    Appelé quand l'étudiant clique sur "Payer".
    """
    # Vérifier qu'il n'y a pas déjà un paiement réussi
    paiement_existant = Paiement.objects.filter(
        etudiant=etudiant,
        cours=cours,
        statut='reussi'
    ).first()

    if paiement_existant:
        return paiement_existant, False  # False = déjà existant

    # Créer le nouveau paiement
    paiement = Paiement.objects.create(
        etudiant=etudiant,
        cours=cours,
        montant=cours.prix,
        devise='XOF',
        statut='en_attente',
        provider=provider,
        reference_numeria=generer_reference(),
    )

    return paiement, True  # True = nouveau paiement créé


def confirmer_paiement(paiement, reference_provider=None):
    """
    Confirme un paiement et inscrit l'étudiant au cours.
    Appelé par le webhook du provider ou en mode sandbox.
    """
    # Mettre à jour le statut
    paiement.statut = 'reussi'
    paiement.reference_provider = reference_provider or 'SANDBOX'
    paiement.save()

    # Inscrire automatiquement l'étudiant au cours
    inscription, cree = InscriptionCours.objects.get_or_create(
        etudiant=paiement.etudiant,
        cours=paiement.cours,
        defaults={
            'progression': 0,
            'est_termine': False,
        }
    )

    return inscription


def echouer_paiement(paiement, raison=''):
    """Marque un paiement comme échoué."""
    paiement.statut = 'echoue'
    paiement.notes = raison
    paiement.save()
    return paiement


def verifier_acces_cours(etudiant, cours):
    """
    Vérifie si un étudiant a accès à un cours payant.
    Retourne True si :
    - Le cours est gratuit
    - L'étudiant a un paiement réussi pour ce cours
    """
    if cours.est_gratuit:
        return True

    return Paiement.objects.filter(
        etudiant=etudiant,
        cours=cours,
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


# Dictionnaire des providers disponibles
PROVIDERS_DISPONIBLES = {
    'sandbox':  process_sandbox,
    'stripe':   process_stripe,
    'fedapay':  process_fedapay,
    'cinetpay': process_cinetpay,
    'mixx':     process_mixx,
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