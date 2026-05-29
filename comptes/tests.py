from django.contrib.auth.models import User
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse

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
