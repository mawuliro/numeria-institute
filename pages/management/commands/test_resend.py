from django.core.management.base import BaseCommand
from numeria_project.emails import send_email


class Command(BaseCommand):
    help = 'Test Resend email delivery'

    def handle(self, *args, **kwargs):
        success = send_email(
            to_email='numeriainstitude@gmail.com',
            subject='Numeria — Test Resend',
            html_content='<p>Resend is working correctly on Railway.</p>'
        )
        if success:
            self.stdout.write(self.style.SUCCESS('Email sent successfully'))
        else:
            self.stdout.write(self.style.ERROR('Email failed — check logs'))
