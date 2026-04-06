# analytics/views.py
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.db.models import Count, Sum, Avg
from django.db.models.functions import TruncDay
from django.utils import timezone
from datetime import timedelta
from cours.models import InscriptionCours, Cours
from paiements.models import Paiement
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
        'total_cours': Cours.objects.filter(est_publie=True).count(),
        'total_inscriptions': InscriptionCours.objects.count(),
        'taux_completion_moyen': InscriptionCours.objects.aggregate(Avg('progression'))['progression__avg'] or 0,
        'total_articles': Article.objects.filter(est_publie=True).count(),
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
        statut='réussi',
        date_creation__date__gte=last_30_days  # ← CORRIGÉ : date_creation
    )
    
    revenus_par_jour = (
        paiements
        .annotate(jour=TruncDay('date_creation'))  # ← CORRIGÉ : date_creation
        .values('jour')
        .annotate(total=Sum('montant'))
        .order_by('jour')
    )
    
    revenus_par_jour_data = {
        'labels': [item['jour'].strftime('%d/%m') for item in revenus_par_jour],
        'values': [float(item['total']) for item in revenus_par_jour]
    }
    
    revenus_totaux = paiements.aggregate(total=Sum('montant'))['total'] or 0
    nombre_paiements = paiements.count()
    
    # ============================================================
    # 4. COURS LES PLUS POPULAIRES
    # ============================================================
    
    cours_populaires = (
        Cours.objects
        .filter(est_publie=True)
        .annotate(nombre_inscriptions=Count('inscriptions'))
        .order_by('-nombre_inscriptions')[:5]
        .values('titre', 'nombre_inscriptions', 'prix', 'est_gratuit')
    )
    
    # ============================================================
    # 5. TAUX DE COMPLÉTION PAR COURS
    # ============================================================
    
    completion_par_cours = (
        Cours.objects
        .filter(est_publie=True, inscriptions__isnull=False)
        .annotate(
            progression_moyenne=Avg('inscriptions__progression')
        )
        .values('titre', 'progression_moyenne')
        .order_by('-progression_moyenne')[:5]
    )
    
    completion_data = {
        'labels': [item['titre'][:30] for item in completion_par_cours],
        'values': [round(item['progression_moyenne'] or 0, 1) for item in completion_par_cours]
    }
    
    # ============================================================
    # 6. ACTIVITÉ DES UTILISATEURS (connexions récentes)
    # ============================================================
    
    utilisateurs_actifs_7j = User.objects.filter(
        last_login__date__gte=today - timedelta(days=7)
    ).count()
    
    # ============================================================
    # 7. DISTRIBUTION DES NIVEAUX D'ÉTUDES
    # ============================================================
    
    niveaux_etudes = {
        'lycee': 0, 'licence': 0, 'master': 0, 
        'doctorat': 0, 'professionnel': 0, 'autre': 0
    }
    
    for user in User.objects.filter(profil__isnull=False):
        niveau = user.profil.niveau_etudes
        if niveau in niveaux_etudes:
            niveaux_etudes[niveau] += 1
    
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
        'niveaux_etudes': niveaux_etudes,
        'periode_30j': last_30_days.strftime('%d/%m/%Y'),
    }
    
    return render(request, 'analytics/dashboard.html', context)