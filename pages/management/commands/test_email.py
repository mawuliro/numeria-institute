from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings


class Command(BaseCommand):
    help = 'Test email configuration by sending a test email'

    def add_arguments(self, parser):
        parser.add_argument(
            '--to',
            type=str,
            default=settings.CONTACT_EMAIL,
            help='Recipient email address (default: CONTACT_EMAIL)'
        )

    def handle(self, *args, **options):
        recipient = options['to']
        
        self.stdout.write(self.style.WARNING('Testing email configuration...'))
        self.stdout.write(f'Email Backend: {settings.EMAIL_BACKEND}')
        self.stdout.write(f'Email Host: {settings.EMAIL_HOST}')
        self.stdout.write(f'Email Port: {settings.EMAIL_PORT}')
        self.stdout.write(f'Email Use TLS: {settings.EMAIL_USE_TLS}')
        self.stdout.write(f'From Email: {settings.DEFAULT_FROM_EMAIL}')
        self.stdout.write(f'To Email: {recipient}\n')

        try:
            send_mail(
                subject='🧪 Test Email from Numeria Institute',
                message='''
This is a test email from Numeria Institute.

If you received this message, your email configuration is working correctly! ✅

Email Settings:
- Backend: {}
- Host: {}
- Port: {}
- Use TLS: {}

Best regards,
Numeria Institute Team
Lomé, Togo 🇹🇬
                '''.format(
                    settings.EMAIL_BACKEND,
                    settings.EMAIL_HOST,
                    settings.EMAIL_PORT,
                    settings.EMAIL_USE_TLS
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS(f'✅ Test email sent successfully to {recipient}!'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Failed to send test email: {str(e)}'))
            self.stdout.write(self.style.ERROR('\nTroubleshooting tips:'))
            self.stdout.write('1. Check your EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD')
            self.stdout.write('2. If using Gmail: Enable "Less secure app access" or use an App Password')
            self.stdout.write('3. If using Mailgun: Check your SMTP credentials')
            self.stdout.write('4. Check your email provider\'s firewall/port requirements')
