from datetime import date

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from .models import Formation, SessionFormation


class SessionFormationValidationTests(TestCase):
    def setUp(self):
        couverture = SimpleUploadedFile(
            name='cover.jpg',
            content=b'fake-image-bytes',
            content_type='image/jpeg'
        )
        self.formation = Formation.objects.create(
            titre='Bootcamp Python Test',
            slug='bootcamp-python-test',
            description_courte='Une formation de test',
            description_longue='Description longue de test',
            type_formation='bootcamp',
            niveau='debutant',
            duree_heures=40,
            image_couverture=couverture,
            competences_visees='Python\nDjango',
            prerequis='Notions de base en programmation',
            est_publiee=True,
            est_archivee=False,
        )

    def test_date_fin_inscriptions_must_not_be_before_date_debut_inscriptions(self):
        session = SessionFormation(
            formation=self.formation,
            nom='Session test',
            slug='session-test',
            date_debut=date(2026, 5, 1),
            date_fin=date(2026, 5, 30),
            date_debut_inscriptions=date(2026, 4, 15),
            date_fin_inscriptions=date(2026, 4, 1),
            places_totales=20,
            prix_fcfa=150000,
            modalite='visio',
            statut='ouverture',
        )

        with self.assertRaises(ValidationError) as cm:
            session.full_clean()

        self.assertIn('date_fin_inscriptions', cm.exception.message_dict)

    def test_valid_session_saves_with_consistent_dates(self):
        session = SessionFormation.objects.create(
            formation=self.formation,
            nom='Session valide',
            slug='session-valide',
            date_debut=date(2026, 5, 1),
            date_fin=date(2026, 5, 30),
            date_debut_inscriptions=date(2026, 4, 1),
            date_fin_inscriptions=date(2026, 4, 15),
            places_totales=20,
            prix_fcfa=150000,
            modalite='visio',
            statut='ouverture',
        )

        self.assertEqual(session.date_fin_inscriptions, date(2026, 4, 15))
