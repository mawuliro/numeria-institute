# analytics/views.py
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.db.models import Count, Sum, Avg
from django.db.models.functions import TruncDay
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from urllib.parse import urlencode
from cours.models import InscriptionCours, Course
from paiements.models import Paiement
from admissions.models import Candidature
from formation.models import InscriptionFormation
from mentorat.models import MentorApplication, PaiementSeance
from django.contrib.auth.models import User
from blog.models import Article
import json


@staff_member_required
def dashboard(request):
    """Dashboard analytics pour les admins"""
    
    today = timezone.now().date()
    last_30_days = today - timedelta(days=30)
    
    # ============================================================
    # 1. STATISTIQUES GÉNÉRALES
    # ============================================================
    
    stats_generales = {
        'total_utilisateurs': User.objects.count(),
        'total_etudiants': User.objects.filter(profil__isnull=False).count(),
        'nouveaux_30j': User.objects.filter(date_joined__date__gte=last_30_days).count(),
        'total_cours': Course.objects.filter(status='published').count(),
        'total_inscriptions': InscriptionCours.objects.count(),
        'taux_completion_moyen': InscriptionCours.objects.aggregate(Avg('progression'))['progression__avg'] or 0,
        'total_articles': Article.objects.filter(est_publie=True).count(),  # Article keeps est_publie
    }
    
    # ============================================================
    # 2. ÉVOLUTION DES INSCRIPTIONS (30 derniers jours)
    # ============================================================
    
    inscriptions_par_jour = (
        User.objects
        .filter(date_joined__date__gte=last_30_days)
        .annotate(jour=TruncDay('date_joined'))
        .values('jour')
        .annotate(count=Count('id'))
        .order_by('jour')
    )
    
    inscriptions_par_jour_data = {
        'labels': [item['jour'].strftime('%d/%m') for item in inscriptions_par_jour],
        'values': [item['count'] for item in inscriptions_par_jour]
    }
    
    # ============================================================
    # 3. REVENUS (paiements réussis) - CORRIGÉ : date_creation au lieu de date_paiement
    # ============================================================
    
    paiements = Paiement.objects.filter(
        statut='reussi',
        date_creation__date__gte=last_30_days  # ← CORRIGÉ : date_creation
    )
    
    revenus_par_jour = (
        paiements
        .annotate(jour=TruncDay('date_creation'))  # ← CORRIGÉ : date_creation
        .values('jour')
        .annotate(total=Sum('montant_final'))
        .order_by('jour')
    )
    
    revenus_par_jour_data = {
        'labels': [item['jour'].strftime('%d/%m') for item in revenus_par_jour],
        'values': [float(item['total']) for item in revenus_par_jour]
    }
    
    revenus_totaux = paiements.aggregate(total=Sum('montant_final'))['total'] or 0
    nombre_paiements = paiements.count()
    
    # ============================================================
    # 4. COURS LES PLUS POPULAIRES
    # ============================================================
    
    cours_populaires = (
        Course.objects
        .filter(status='published')
        .annotate(nombre_inscriptions=Count('inscriptions'))
        .order_by('-nombre_inscriptions')[:5]
        .values('title', 'nombre_inscriptions', 'price', 'is_free')
    )
    
    # ============================================================
    # 5. TAUX DE COMPLÉTION PAR COURS
    # ============================================================
    
    completion_par_cours = (
        Course.objects
        .filter(status='published', inscriptions__isnull=False)
        .annotate(
            progression_moyenne=Avg('inscriptions__progression')
        )
        .values('title', 'progression_moyenne')
        .order_by('-progression_moyenne')[:5]
    )

    completion_data = {
        'labels': [item['title'][:30] for item in completion_par_cours],
        'values': [round(item['progression_moyenne'] or 0, 1) for item in completion_par_cours]
    }
    
    # ============================================================
    # 6. ACTIVITÉ DES UTILISATEURS (connexions récentes)
    # ============================================================
    
    utilisateurs_actifs_7j = User.objects.filter(
        last_login__date__gte=today - timedelta(days=7)
    ).count()
    
    # ============================================================
    # 7. PENDING ADMIN VALIDATIONS
    # ============================================================

    pending_candidatures = Candidature.objects.filter(
        statut__in=['soumise', 'en_revue']
    ).count()
    pending_mentor_applications = MentorApplication.objects.filter(
        status='pending'
    ).count()
    pending_formation_inscriptions = InscriptionFormation.objects.filter(
        statut='en_attente'
    ).count()
    pending_mentor_payments = PaiementSeance.objects.filter(
        statut='preuve_soumise'
    ).count()

    def admin_filter_url(name, params):
        return f"{reverse(name)}?{urlencode(params)}"

    pending_admin_tasks = [
        {
            'titre': 'Candidatures à examiner',
            'count': pending_candidatures,
            'url': admin_filter_url('admin:admissions_candidature_changelist', {'statut': 'soumise'}),
            'details': 'Statuts soumise / en revue',
            'badge_class': 'bg-rose-500 text-white' if pending_candidatures else 'bg-slate-400 text-white',
        },
        {
            'titre': 'Demandes mentorat',
            'count': pending_mentor_applications,
            'url': admin_filter_url('admin:mentorat_mentorapplication_changelist', {'status': 'pending'}),
            'details': 'Candidatures de mentors en attente',
            'badge_class': 'bg-rose-500 text-white' if pending_mentor_applications else 'bg-slate-400 text-white',
        },
        {
            'titre': 'Inscriptions formations en attente',
            'count': pending_formation_inscriptions,
            'url': admin_filter_url('admin:formation_inscriptionformation_changelist', {'statut': 'en_attente'}),
            'details': 'Paiements à confirmer',
            'badge_class': 'bg-rose-500 text-white' if pending_formation_inscriptions else 'bg-slate-400 text-white',
        },
        {
            'titre': 'Preuves de paiement mentorat',
            'count': pending_mentor_payments,
            'url': admin_filter_url('admin:mentorat_paiementseance_changelist', {'statut': 'preuve_soumise'}),
            'details': 'Validation des preuves soumises',
            'badge_class': 'bg-rose-500 text-white' if pending_mentor_payments else 'bg-slate-400 text-white',
        },
    ]
    
    # ============================================================
    # 8. DISTRIBUTION DES NIVEAUX D'ÉTUDES
    # ============================================================
    
    niveaux_etudes = {
        'lycee': 0, 'licence': 0, 'master': 0,
        'doctorat': 0, 'professionnel': 0, 'autre': 0
    }

    for item in (
        User.objects
        .filter(profil__isnull=False, profil__niveau_etudes__in=niveaux_etudes)
        .values('profil__niveau_etudes')
        .annotate(count=Count('id'))
    ):
        niveaux_etudes[item['profil__niveau_etudes']] = item['count']
    
    # ============================================================
    # CONTEXTE
    # ============================================================
    
    context = {
        'stats_generales': stats_generales,
        'inscriptions_par_jour': json.dumps(inscriptions_par_jour_data),
        'revenus_par_jour': json.dumps(revenus_par_jour_data),
        'revenus_totaux': revenus_totaux,
        'nombre_paiements': nombre_paiements,
        'cours_populaires': cours_populaires,
        'completion_data': json.dumps(completion_data),
        'utilisateurs_actifs_7j': utilisateurs_actifs_7j,
        'pending_admin_tasks': pending_admin_tasks,
        'niveaux_etudes': niveaux_etudes,
        'periode_30j': last_30_days.strftime('%d/%m/%Y'),
    }
    
    return render(request, 'analytics/dashboard.html', context)