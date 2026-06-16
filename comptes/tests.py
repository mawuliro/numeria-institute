from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import Profil
from numeria_project.emails import make_email_verification_token


class RegistrationEmailTests(TestCase):
    def setUp(self):
        self.client = Client()

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_inscription_sends_verification_email_and_keeps_user_inactive(self):
        response = self.client.post(reverse('comptes:inscription'), {
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'testuser@example.com',
            'password1': 'ComplexPass123',
            'password2': 'ComplexPass123',
        })

        self.assertRedirects(response, reverse('comptes:verification_sent'))
        user = User.objects.get(username='testuser')
        self.assertFalse(user.is_active)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Confirme ton compte Numeria', mail.outbox[0].subject)
        self.assertIn('Bonjour Test', mail.outbox[0].body)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_verify_email_activates_user_and_logs_in(self):
        user = User.objects.create_user(
            username='verifyuser',
            email='verifyuser@example.com',
            password='ComplexPass123',
            is_active=False,
        )
        token = make_email_verification_token(user)

        response = self.client.get(reverse('comptes:verify_email', args=[token]))
        user.refresh_from_db()

        self.assertTrue(user.is_active)
        self.assertRedirects(response, reverse('comptes:tableau_de_bord'))


class ComptesViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='activeuser',
            email='activeuser@example.com',
            password='ComplexPass123',
            first_name='Active',
            last_name='User',
        )
        Profil.objects.create(utilisateur=self.user)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_resend_verification_email_sends_message_for_inactive_user(self):
        inactive = User.objects.create_user(
            username='inactiveuser',
            email='inactiveuser@example.com',
            password='ComplexPass123',
            is_active=False,
        )
        Profil.objects.create(utilisateur=inactive)

        response = self.client.post(reverse('comptes:resend_verification_email'), {
            'email': inactive.email,
        })

        self.assertRedirects(response, reverse('comptes:verification_sent'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Confirme ton compte Numeria', mail.outbox[0].subject)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_resend_verification_email_for_unknown_email_shows_info(self):
        response = self.client.post(reverse('comptes:resend_verification_email'), {
            'email': 'unknown@example.com',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertTrue(any('Aucun compte inactif' in str(message) for message in messages))

    def test_connexion_with_valid_credentials_redirects_to_dashboard(self):
        response = self.client.post(reverse('comptes:connexion'), {
            'username': self.user.username,
            'password': 'ComplexPass123',
        })

        self.assertRedirects(response, reverse('comptes:tableau_de_bord'))

    def test_connexion_with_invalid_credentials_returns_form_errors(self):
        response = self.client.post(reverse('comptes:connexion'), {
            'username': self.user.username,
            'password': 'WrongPassword',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nom d'utilisateur ou mot de passe incorrect.")

    def test_changer_mot_de_passe_updates_password(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('comptes:changer_mot_de_passe'), {
            'old_password': 'ComplexPass123',
            'new_password1': 'NewComplexPass456',
            'new_password2': 'NewComplexPass456',
        })

        self.assertRedirects(response, reverse('comptes:profil'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewComplexPass456'))

    def test_supprimer_photo_without_photo_redirects_to_modifier_profil(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('comptes:supprimer_photo'))

        self.assertRedirects(response, reverse('comptes:modifier_profil'))

    def test_supprimer_compte_requires_password(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('comptes:supprimer_compte'), {
            'password': 'WrongPass123',
        })

        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username=self.user.username).exists())
        self.assertContains(response, 'Mot de passe incorrect. Ton compte n\'a pas été supprimé.')

    def test_supprimer_compte_with_valid_password_deletes_user(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('comptes:supprimer_compte'), {
            'password': 'ComplexPass123',
        })

        self.assertRedirects(response, reverse('accueil'))
        self.assertFalse(User.objects.filter(username=self.user.username).exists())
