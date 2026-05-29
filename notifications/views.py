import json
import logging
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import models as db_models
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import render, redirect
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from .models import Notification
from .notifications import notify_user, notify_group, notify_all, get_notifications_for_user

logger = logging.getLogger(__name__)


@login_required
def notification_list(request):
    """Full notifications page for the authenticated user."""
    filter_type = request.GET.get('type', '')

    qs = Notification.objects.filter(
        db_models.Q(recipient=request.user) | db_models.Q(recipient__isnull=True)
    )
    if filter_type:
        qs = qs.filter(notification_type=filter_type)

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'notifications/list.html', {
        'page_obj': page_obj,
        'filter_type': filter_type,
        'types': Notification.TYPES,
    })


@login_required
@require_POST
def mark_read(request):
    """Mark all visible notifications as read for the current user (AJAX)."""
    Notification.objects.filter(
        db_models.Q(recipient=request.user) | db_models.Q(recipient__isnull=True),
        is_read=False,
    ).filter(recipient=request.user).update(is_read=True)
    # For broadcasts we cannot mark individually; a per-user read table would be
    # needed — for now we mark only personalised ones.
    return JsonResponse({'status': 'ok'})


@login_required
@require_POST
def mark_all_read(request):
    """Mark all personalised unread notifications as read."""
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    messages.success(request, _("Toutes les notifications ont été marquées comme lues."))
    return redirect('notifications:list')


@login_required
def unread_count(request):
    """Return the unread notification count as JSON (polled every 60s)."""
    count = Notification.objects.filter(
        db_models.Q(recipient=request.user) | db_models.Q(recipient__isnull=True),
        is_read=False,
    ).count()
    return JsonResponse({'count': count})


@staff_member_required
def send_notification(request):
    """Staff-only panel to compose and send notifications."""
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        message_text = request.POST.get('message', '').strip()
        notif_type = request.POST.get('notification_type', 'info')
        link = request.POST.get('link', '').strip() or None
        recipient_mode = request.POST.get('recipient_mode', 'everyone')
        specific_username = request.POST.get('specific_user', '').strip()

        if not title or not message_text:
            messages.error(request, _("Le titre et le message sont obligatoires."))
            return redirect('notifications:send')

        count = 0

        if recipient_mode == 'everyone':
            notify_all(title, message_text, notification_type=notif_type,
                       link=link, created_by=request.user)
            count = User.objects.filter(is_active=True).count()

        elif recipient_mode == 'students':
            from cours.models import InscriptionCours
            user_ids = InscriptionCours.objects.values_list('etudiant_id', flat=True).distinct()
            qs = User.objects.filter(id__in=user_ids, is_active=True)
            notify_group(qs, title, message_text, notification_type=notif_type,
                         link=link, created_by=request.user)
            count = qs.count()

        elif recipient_mode == 'mentees':
            from mentorat.models import RelationMentorat
            user_ids = RelationMentorat.objects.filter(
                est_active=True
            ).values_list('mentee__profil__utilisateur_id', flat=True).distinct()
            qs = User.objects.filter(id__in=user_ids, is_active=True)
            notify_group(qs, title, message_text, notification_type=notif_type,
                         link=link, created_by=request.user)
            count = qs.count()

        elif recipient_mode == 'mentors':
            from mentorat.models import RelationMentorat
            user_ids = RelationMentorat.objects.filter(
                est_active=True
            ).values_list('mentor__profil__utilisateur_id', flat=True).distinct()
            qs = User.objects.filter(id__in=user_ids, is_active=True)
            notify_group(qs, title, message_text, notification_type=notif_type,
                         link=link, created_by=request.user)
            count = qs.count()

        elif recipient_mode == 'applicants':
            from admissions.models import Candidature
            user_ids = Candidature.objects.filter(
                statut__in=['soumise', 'en_revue', 'acceptee']
            ).values_list('utilisateur_id', flat=True).distinct()
            qs = User.objects.filter(id__in=user_ids, is_active=True)
            notify_group(qs, title, message_text, notification_type=notif_type,
                         link=link, created_by=request.user)
            count = qs.count()

        elif recipient_mode == 'specific':
            user = User.objects.filter(
                db_models.Q(username=specific_username) |
                db_models.Q(email=specific_username),
                is_active=True,
            ).first()
            if not user:
                messages.error(request, _("Utilisateur introuvable : %(u)s") % {'u': specific_username})
                return redirect('notifications:send')
            notify_user(user, title, message_text, notification_type=notif_type,
                        link=link, created_by=request.user)
            count = 1

        messages.success(
            request,
            _("Notification envoyée à %(count)s utilisateur(s)") % {'count': count}
        )
        return redirect('notifications:send')

    recipient_choices = [
        ('everyone',   _('Tout le monde (broadcast)')),
        ('students',   _('Tous les étudiants inscrits à au moins un cours')),
        ('mentees',    _('Tous les mentorés actifs')),
        ('mentors',    _('Tous les mentors actifs')),
        ('applicants', _('Tous les candidats (soumis/acceptés)')),
        ('specific',   _('Utilisateur spécifique (par username ou email)')),
    ]
    return render(request, 'notifications/send.html', {
        'types': Notification.TYPES,
        'recipient_choices': recipient_choices,
    })
