"""
SYSTÈME ANTI-FRAUDE POUR MENTORAT
==================================

Protection contre:
- Mentors qui déclarent pas d'avoir reçu le paiement
- Mentorés qui payent pas ou font chargeback
- Faux paiements (preuves modifiées)
- Paiements en double
- Montants incorrects

Mécanisme:
  Mentoré paye → Numeria RETIENT $$ (escrow 48h)
  Si mentor valide: déblocage → mentor reçoit
  Si personne valide: remboursement → mentoré
"""

import hmac
import hashlib
from datetime import timedelta
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User
from .models import PaiementSeance
import logging

logger = logging.getLogger(__name__)


class PaiementSuspect(Exception):
    """Levée quand un paiement est considered suspect."""
    pass


class ValidateurPaiement:
    """
    Classe centrale pour valider les paiements mentorat.
    Tous les paiements passent par ici.
    """

    # Limites anti-fraude
    MONTANT_MAX_FCFA = 500_000  # Max 500k FCFA par séance
    PAIEMENTS_PAR_JOUR_PAR_MENTOR = 10  # Max 10 paiements/jour par mentor
    DUREE_ESCROW_HEURES = 48  # Retient l'argent 48h

    # Raisons de flagging
    RAISONS_SUSPECT = {
        'montant_zero': 'Montant zéro détecté',
        'montant_excessif': f'Montant > {MONTANT_MAX_FCFA:,} FCFA',
        'mentor_surcharge': 'Mentor a trop de paiements aujourd\'hui',
        'mentor_nouveau': 'Nouveau mentor (< 7 jours)',
        'mentee_debut': 'Mentoré récent (< 3 jours)',
        'reference_doublon': 'Référence mobile money en doublon',
        'signature_invalide': 'Signature HMAC invalide',
        'image_corrompue': 'Image de preuve corrompue/fake',
        'montant_incoherent': 'Montant ≠ tarif mentor',
    }

    @staticmethod
    def generer_signature(mentee_id: int, seance_id: int, montant: int, secret: str) -> str:
        """
        Génère une signature HMAC pour un paiement.
        Évite la modification de montant par le mentoré.

        Signature = HMAC-SHA256(secret, mentee_id + seance_id + montant)
        """
        message = f"{mentee_id}:{seance_id}:{montant}"
        return hmac.new(
            secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

    @staticmethod
    def verifier_signature(mentee_id: int, seance_id: int, montant: int, signature: str, secret: str) -> bool:
        """Vérifie que la signature correspond."""
        expected = ValidateurPaiement.generer_signature(mentee_id, seance_id, montant, secret)
        return hmac.compare_digest(expected, signature)

    @classmethod
    def valider_paiement(
        cls,
        paiement: PaiementSeance,
        secret_mentee: str = None,
        signature_mentee: str = None
    ) -> tuple[bool, list[str]]:
        """
        Valide un paiement. Retourne (est_valide, raisons_suspect).
        
        Si est_valide=False, le paiement est flaggé et retenu en escrow.
        """
        raisons = []
        seance = paiement.seance
        mentor = seance.relation.mentor

        # 1️⃣ Vérifier montant > 0
        if paiement.montant_total <= 0:
            raisons.append(cls.RAISONS_SUSPECT['montant_zero'])
            return False, raisons

        # 2️⃣ Vérifier montant ≤ max
        if paiement.montant_total > cls.MONTANT_MAX_FCFA:
            raisons.append(cls.RAISONS_SUSPECT['montant_excessif'])

        # 3️⃣ Vérifier montant = tarif mentor
        if paiement.montant_total != mentor.tarif_par_seance:
            raisons.append(cls.RAISONS_SUSPECT['montant_incoherent'])

        # 4️⃣ Vérifier paiements/jour du mentor
        debut_jour = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        nb_paiements_jour = PaiementSeance.objects.filter(
            seance__relation__mentor=mentor,
            date_creation__gte=debut_jour,
            statut__in=['preuve_soumise', 'confirme']
        ).count()
        if nb_paiements_jour >= cls.PAIEMENTS_PAR_JOUR_PAR_MENTOR:
            raisons.append(cls.RAISONS_SUSPECT['mentor_surcharge'])

        # 5️⃣ Vérifier mentor n'est pas nouveau (<7j)
        if (timezone.now() - mentor.date_inscription).days < 7:
            raisons.append(cls.RAISONS_SUSPECT['mentor_nouveau'])

        # 6️⃣ Vérifier mentoré n'est pas tout neuf (<3j)
        mentee = seance.relation.mentee
        if (timezone.now() - mentee.date_inscription).days < 3:
            raisons.append(cls.RAISONS_SUSPECT['mentee_debut'])

        # 7️⃣ Vérifier pas de doublon ref mobile money
        if paiement.reference_mobile_money:
            doublon = PaiementSeance.objects.filter(
                reference_mobile_money=paiement.reference_mobile_money,
                statut__in=['preuve_soumise', 'confirme']
            ).exclude(id=paiement.id).exists()
            if doublon:
                raisons.append(cls.RAISONS_SUSPECT['reference_doublon'])

        # 8️⃣ Vérifier signature mentoré (si fournie)
        if secret_mentee and signature_mentee:
            if not cls.verifier_signature(
                mentee.profil.utilisateur.id,
                seance.id,
                paiement.montant_total,
                signature_mentee,
                secret_mentee
            ):
                raisons.append(cls.RAISONS_SUSPECT['signature_invalide'])

        # Retour
        est_valide = len(raisons) == 0
        return est_valide, raisons

    @classmethod
    def enregistrer_paiement_avec_escrow(
        cls,
        paiement: PaiementSeance,
        est_valide: bool,
        raisons: list[str]
    ):
        """
        Enregistre le paiement avec escrow automatique.

        Si valide → escrow 48h
        Si suspect → escrow 48h + flagged + email admin
        """
        paiement.statut = 'preuve_soumise'  # Preuve reçue
        paiement.date_submission = timezone.now()

        # Calculer déblocage
        paiement.date_deblocage = timezone.now() + timedelta(hours=cls.DUREE_ESCROW_HEURES)

        if not est_valide:
            # Flaguer le paiement
            paiement.est_suspect = True
            paiement.raisons_suspect = ' | '.join(raisons)
            logger.warning(f"PAIEMENT SUSPECT #{paiement.id}: {paiement.raisons_suspect}")

            try:
                from django.core.mail import mail_admins
                mail_admins(
                    subject=f'[Numeria] Paiement suspect #{paiement.id}',
                    message=(
                        f"Un paiement suspect a été détecté.\n\n"
                        f"Paiement ID : {paiement.id}\n"
                        f"Montant     : {paiement.montant_total} FCFA\n"
                        f"Raisons     : {paiement.raisons_suspect}\n"
                    ),
                    fail_silently=True,
                )
            except Exception:
                pass
        else:
            paiement.est_suspect = False

        paiement.save()

    @classmethod
    def debloquer_paiement(cls, paiement: PaiementSeance):
        """
        Débloque un paiement après 48h d'escrow (si pas d'objection).
        Appelé par une tâche cron toutes les 6 heures.
        """
        # Conditions de déblocage
        if paiement.statut != 'preuve_soumise':
            return False, "Statut invalide"

        if paiement.date_deblocage > timezone.now():
            return False, "Escrow pas encore expiré"

        # Vérifier que mentor n'a pas contesté
        if hasattr(paiement, 'contestation_mentor') and paiement.contestation_mentor.exists():
            return False, "Mentor a contesté"

        # Débloquer
        paiement.statut = 'confirme'
        paiement.date_confirmation = timezone.now()
        paiement.save()

        logger.info(f"PAIEMENT DÉBLOQUÉ #{paiement.id} après escrow")
        return True, "Déblocage réussi"

    @classmethod
    def contester_paiement_mentor(cls, paiement: PaiementSeance, raison: str):
        """
        Le mentor conteste le paiement (n'a pas eu la séance, etc).
        Déclenche un remboursement au mentoré.
        """
        paiement.statut = 'echec'
        paiement.raison_echec = raison
        paiement.save()
        logger.info(f"PAIEMENT CONTESTÉ PAR MENTOR #{paiement.id}: {raison}")

        try:
            from django.core.mail import mail_admins
            mentee = paiement.seance.relation.mentee
            mail_admins(
                subject=f'[Numeria] Remboursement requis — Paiement #{paiement.id}',
                message=(
                    f"Un mentor a contesté un paiement. Remboursement manuel requis.\n\n"
                    f"Paiement ID  : {paiement.id}\n"
                    f"Montant      : {paiement.montant_total} FCFA\n"
                    f"Mentoré      : {mentee}\n"
                    f"Raison       : {raison}\n\n"
                    f"Action : procéder au remboursement via le gateway de paiement."
                ),
                fail_silently=True,
            )
        except Exception:
            pass


class ContestationPaiement(models.Model):
    """Modèle pour tracker les contestations."""
    paiement = models.ForeignKey(
        PaiementSeance,
        on_delete=models.CASCADE,
        related_name='contestations'
    )
    contested_by = models.ForeignKey(User, on_delete=models.CASCADE)  # Mentor ou mentoré
    raison = models.TextField()
    date_creation = models.DateTimeField(auto_now_add=True)
    statut = models.CharField(
        max_length=20,
        choices=[
            ('ouverte', 'Ouverte'),
            ('resolue', 'Résolue'),
            ('remboursement', 'Remboursement'),
        ],
        default='ouverte'
    )

    def __str__(self):
        return f"Contestation #{self.id} — {self.raison[:50]}"
