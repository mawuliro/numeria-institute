from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from comptes.models import Profil
from .consumers import VideoChatConsumer
from .models import Mentee, Mentor, RelationMentorat, SeanceMentorat


def _create_user_with_profil(username, role):
    user = User.objects.create_user(
        username=username, email=f'{username}@example.com', password='ComplexPass123',
    )
    profil = Profil.objects.create(utilisateur=user, role=role)
    return user, profil


class VideoSeanceAccessTests(TestCase):
    def setUp(self):
        self.mentor_user, mentor_profil = _create_user_with_profil('mentoruser', 'mentor')
        self.mentee_user, mentee_profil = _create_user_with_profil('menteeuser', 'mentee')
        self.outsider, _ = _create_user_with_profil('outsider', 'mentee')

        self.mentor = Mentor.objects.create(
            profil=mentor_profil,
            domaines_expertise='informatique',
            niveau_experience='avance',
            disponibilite='hebdomadaire',
            bio_mentorat='Bio',
        )
        self.mentee = Mentee.objects.create(
            profil=mentee_profil,
            objectifs='competences',
            niveau_etudes='licence',
            besoins='Besoins',
        )
        self.relation = RelationMentorat.objects.create(mentor=self.mentor, mentee=self.mentee)
        self.seance_visio = SeanceMentorat.objects.create(
            relation=self.relation,
            titre='Séance de mentorat',
            date_heure=timezone.now(),
            statut='planifiee',
            modalite='visio',
        )
        self.seance_presentiel = SeanceMentorat.objects.create(
            relation=self.relation,
            titre='Séance en présentiel',
            date_heure=timezone.now(),
            statut='planifiee',
            modalite='presentiel',
        )

    def test_mentor_can_access_video_room(self):
        self.client.force_login(self.mentor_user)
        response = self.client.get(reverse('mentorat:video_seance', args=[self.seance_visio.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['room_type'], 'mentorat_seance')
        self.assertEqual(response.context['role_label'], 'Mentor')

    def test_mentee_can_access_video_room(self):
        self.client.force_login(self.mentee_user)
        response = self.client.get(reverse('mentorat:video_seance', args=[self.seance_visio.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['role_label'], 'Mentee')

    def test_outsider_cannot_access_video_room(self):
        self.client.force_login(self.outsider)
        response = self.client.get(reverse('mentorat:video_seance', args=[self.seance_visio.pk]))

        self.assertEqual(response.status_code, 404)

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse('mentorat:video_seance', args=[self.seance_visio.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertIn('/comptes/connexion/', response.url)

    def test_non_visio_seance_returns_404(self):
        self.client.force_login(self.mentor_user)
        response = self.client.get(reverse('mentorat:video_seance', args=[self.seance_presentiel.pk]))

        self.assertEqual(response.status_code, 404)


class VideoChatConsumerAuthorizationTests(TestCase):
    def setUp(self):
        self.mentor_user, mentor_profil = _create_user_with_profil('mentoruser2', 'mentor')
        self.mentee_user, mentee_profil = _create_user_with_profil('menteeuser2', 'mentee')
        self.outsider, _ = _create_user_with_profil('outsider2', 'mentee')

        self.mentor = Mentor.objects.create(
            profil=mentor_profil,
            domaines_expertise='informatique',
            niveau_experience='avance',
            disponibilite='hebdomadaire',
            bio_mentorat='Bio',
        )
        self.mentee = Mentee.objects.create(
            profil=mentee_profil,
            objectifs='competences',
            niveau_etudes='licence',
            besoins='Besoins',
        )
        self.relation = RelationMentorat.objects.create(mentor=self.mentor, mentee=self.mentee)
        self.seance = SeanceMentorat.objects.create(
            relation=self.relation,
            titre='Séance de mentorat',
            date_heure=timezone.now(),
            statut='planifiee',
            modalite='visio',
        )
        self.consumer = VideoChatConsumer()

    async def test_get_room_returns_seance_for_valid_pk(self):
        room = await self.consumer.get_room('mentorat_seance', self.seance.pk)

        self.assertEqual(room.pk, self.seance.pk)

    async def test_get_room_returns_none_for_unknown_pk(self):
        room = await self.consumer.get_room('mentorat_seance', self.seance.pk + 1000)

        self.assertIsNone(room)

    async def test_mentor_is_authorized(self):
        room = await self.consumer.get_room('mentorat_seance', self.seance.pk)

        self.assertTrue(await self.consumer.is_authorized(self.mentor_user, 'mentorat_seance', room))

    async def test_mentee_is_authorized(self):
        room = await self.consumer.get_room('mentorat_seance', self.seance.pk)

        self.assertTrue(await self.consumer.is_authorized(self.mentee_user, 'mentorat_seance', room))

    async def test_outsider_is_not_authorized(self):
        room = await self.consumer.get_room('mentorat_seance', self.seance.pk)

        self.assertFalse(await self.consumer.is_authorized(self.outsider, 'mentorat_seance', room))
