from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from formation.models import Formation, SessionFormation, LeconFormation
from django.utils.text import slugify


class Command(BaseCommand):
    help = 'Crée des formations d\'exemple pour le test'

    def handle(self, *args, **options):
        # Récupérer un instructeur (ou créer)
        instructeur, _ = User.objects.get_or_create(
            username='instructor1',
            defaults={'email': 'instructor@numeria.tg', 'is_staff': True}
        )

        formations_data = [
            {
                'titre': 'Bootcamp Python Avancé',
                'description_courte': 'Maîtrisez Python en 8 semaines intensives',
                'description_longue': 'Un bootcamp complet couvrant la programmation avancée en Python, frameworks web, et déploiement en production.',
                'type_formation': 'bootcamp',
                'niveau': 'intermediaire',
                'duree_heures': 40,
                'competences': 'Programmation Python\nFramework Django\nBases de données\nDéploiement',
                'prerequis': 'Connaissances de base en programmation',
            },
            {
                'titre': 'Masterclass IA et Machine Learning',
                'description_courte': 'Introduction aux concepts de l\'IA et ML',
                'description_longue': 'Explorez les fondamentaux de l\'intelligence artificielle, du machine learning et des réseaux de neurones.',
                'type_formation': 'masterclass',
                'niveau': 'avance',
                'duree_heures': 20,
                'competences': 'Machine Learning\nTensorFlow\nPandas\nScikit-learn',
                'prerequis': 'Python avancé requis',
            },
            {
                'titre': 'Certification Web Developer',
                'description_courte': 'Devenez développeur Web certifié',
                'description_longue': 'Formation complète pour devenir développeur web full-stack avec certification reconnue.',
                'type_formation': 'certification',
                'niveau': 'debutant',
                'duree_heures': 60,
                'competences': 'HTML/CSS\nJavaScript\nReact\nNode.js',
                'prerequis': 'Aucun prérequis',
            },
        ]

        for data in formations_data:
            slug = slugify(data['titre'])
            formation, created = Formation.objects.get_or_create(
                slug=slug,
                defaults={
                    'titre': data['titre'],
                    'description_courte': data['description_courte'],
                    'description_longue': data['description_longue'],
                    'type_formation': data['type_formation'],
                    'niveau': data['niveau'],
                    'duree_heures': data['duree_heures'],
                    'competences_visees': data['competences'],
                    'prerequis': data['prerequis'],
                    'est_publiee': True,  # 🔑 IMPORTANT: Publier la formation
                    'est_archivee': False,
                }
            )

            if created:
                formation.instructeurs.add(instructeur)
                
                # Créer des sessions
                for i, mois in enumerate(['Janvier', 'Mars', 'Mai'], 1):
                    today = timezone.now().date()
                    session_start = today.replace(month=i*2)
                    
                    session, _ = SessionFormation.objects.get_or_create(
                        formation=formation,
                        slug=f"{slug}-{mois.lower()}",
                        defaults={
                            'nom': f'{mois} 2026',
                            'date_debut': session_start,
                            'date_fin': session_start + timedelta(days=60),
                            'date_debut_inscriptions': today,
                            'date_fin_inscriptions': session_start - timedelta(days=7),
                            'places_totales': 30,
                            'prix_fcfa': 150000,
                            'prix_reduit_fcfa': 120000,
                            'modalite': 'visio',
                            'statut': 'ouverture',
                        }
                    )
                    
                    # Créer quelques leçons
                    lecons_data = [
                        {
                            'titre': f'Leçon 1: Introduction à {formation.titre}',
                            'contenu_html': '<h2>Bienvenue</h2><p>Cette est la première leçon.</p>',
                        },
                        {
                            'titre': f'Leçon 2: Concepts fondamentaux',
                            'contenu_html': '<h2>Concepts clés</h2><p>Vous apprendrez les concepts essentiels.</p>',
                        },
                    ]
                    
                    for idx, lecon_data in enumerate(lecons_data, 1):
                        LeconFormation.objects.get_or_create(
                            formation=formation,
                            titre=lecon_data['titre'],
                            defaults={
                                'contenu_html': lecon_data['contenu_html'],
                                'ordre': idx,
                                'duree_minutes': 90,
                            }
                        )

                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Formation créée: {formation.titre} ({formation.sessions.count()} sessions)'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Formation existe déjà: {formation.titre}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                '\n✅ Formations d\'exemple créées avec succès!\n'
                'Accédez à: /fr/formations/'
            )
        )
