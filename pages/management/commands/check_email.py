from django.core.management.base import BaseCommand
from django.core.mail import send_mail, get_connection
from django.conf import settings


class Command(BaseCommand):
    help = 'Test Brevo SMTP connection and send a test email'

    def add_arguments(self, parser):
        parser.add_argument(
            '--to',
            default=settings.CONTACT_EMAIL,
            help='Recipient email address (default: CONTACT_EMAIL setting)',
        )

    def handle(self, *args, **options):
        recipient = options['to']

        self.stdout.write('── Email settings ──────────────────────────')
        self.stdout.write(f'  HOST     : {settings.EMAIL_HOST}')
        self.stdout.write(f'  PORT     : {settings.EMAIL_PORT}')
        self.stdout.write(f'  USER     : {settings.EMAIL_HOST_USER}')
        self.stdout.write(f'  TLS      : {settings.EMAIL_USE_TLS}')
        self.stdout.write(f'  TIMEOUT  : {settings.EMAIL_TIMEOUT}')
        self.stdout.write(f'  FROM     : {settings.DEFAULT_FROM_EMAIL}')
        self.stdout.write(f'  PASSWORD : {"✓ set" if settings.EMAIL_HOST_PASSWORD else "✗ MISSING"}')
        self.stdout.write(f'  TO       : {recipient}')
        self.stdout.write('────────────────────────────────────────────')

        self.stdout.write('\nTesting SMTP connection...')
        try:
            connection = get_connection()
            connection.open()
            self.stdout.write(self.style.SUCCESS('  ✓ SMTP connection opened'))
            connection.close()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Connection failed: {e}'))
            return

        self.stdout.write('\nSending test email...')
        try:
            send_mail(
                subject='Numeria — Test SMTP',
                message='SMTP connection is working correctly. This is a test from the check_email management command.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS(f'  ✓ Email sent successfully to {recipient}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Send failed: {e}'))
