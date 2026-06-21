from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from formation.models import Formation, FormationModule, FormationLesson

User = get_user_model()


class Command(BaseCommand):
    help = "Crée des formations d'exemple pour le test"

    def handle(self, *args, **options):
        instructeur, _ = User.objects.get_or_create(
            username='instructor1',
            defaults={'email': 'instructor@numeria.tg', 'is_staff': True},
        )

        formations_data = [
            {
                'title': 'Bootcamp Python Avancé',
                'short_description': 'Maîtrisez Python en 8 semaines intensives',
                'description': 'Un bootcamp complet couvrant la programmation avancée en Python, frameworks web, et déploiement en production.',
                'category': 'python',
                'level': 'intermediaire',
                'estimated_hours': 40,
                'objectives': 'Programmation Python\nFramework Django\nBases de données\nDéploiement',
                'prerequisites': 'Connaissances de base en programmation',
            },
            {
                'title': 'Masterclass IA et Machine Learning',
                'short_description': "Introduction aux concepts de l'IA et ML",
                'description': "Explorez les fondamentaux de l'intelligence artificielle, du machine learning et des réseaux de neurones.",
                'category': 'ia',
                'level': 'avance',
                'estimated_hours': 20,
                'objectives': 'Machine Learning\nTensorFlow\nPandas\nScikit-learn',
                'prerequisites': 'Python avancé requis',
            },
            {
                'title': 'Certification Web Developer',
                'short_description': 'Devenez développeur Web certifié',
                'description': 'Formation complète pour devenir développeur web full-stack avec certification reconnue.',
                'category': 'informatique',
                'level': 'debutant',
                'estimated_hours': 60,
                'objectives': 'HTML/CSS\nJavaScript\nReact\nNode.js',
                'prerequisites': 'Aucun prérequis',
            },
        ]

        for data in formations_data:
            slug = slugify(data['title'])
            formation, created = Formation.objects.get_or_create(
                slug=slug,
                defaults={
                    **data,
                    'status': 'published',
                    'created_by': instructeur,
                },
            )

            if created:
                module = FormationModule.objects.create(
                    formation=formation,
                    title='Module 1 : Introduction',
                    order=0,
                )
                FormationLesson.objects.create(
                    formation=formation,
                    module=module,
                    title=f"Leçon 1 : Introduction à {formation.title}",
                    order=0,
                    estimated_minutes=90,
                )
                FormationLesson.objects.create(
                    formation=formation,
                    module=module,
                    title='Leçon 2 : Concepts fondamentaux',
                    order=1,
                    estimated_minutes=90,
                )
                self.stdout.write(self.style.SUCCESS(f'✅ Formation créée : {formation.title}'))
            else:
                self.stdout.write(self.style.WARNING(f'⚠️  Formation existe déjà : {formation.title}'))

        self.stdout.write(self.style.SUCCESS('\n✅ Formations créées avec succès !\nAccédez à : /formations/'))
