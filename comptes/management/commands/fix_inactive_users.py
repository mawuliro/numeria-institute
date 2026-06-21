from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = "Set is_active=True for all users who were left inactive by the old email-verification flow."

    def handle(self, *args, **options):
        inactive = User.objects.filter(is_active=False)
        count = inactive.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS("Aucun utilisateur inactif trouvé."))
            return
        inactive.update(is_active=True)
        self.stdout.write(self.style.SUCCESS(f"{count} utilisateur(s) activé(s) avec succès."))
