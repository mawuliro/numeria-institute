import logging
from datetime import date
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordResetForm
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from .models import StaffActivityLog, ContactReply
from .utils import staff_only, log_staff_action
from notifications.notifications import notify_user, notify_group

logger = logging.getLogger(__name__)


# ─── DASHBOARD ────────────────────────────────────────────────────────────────

@staff_only
def dashboard(request):
    from pages.models import ContactMessage
    from admissions.models import Candidature
    from mentorat.models import DemandeMentorat
    from cours.models import Cours
    from paiements.models import Paiement

    today = date.today()
    first_of_month = today.replace(day=1)

    payments_qs = Paiement.objects.filter(
        statut='reussi', date_creation__date__gte=first_of_month
    )

    cards = {
        'unread_contacts': ContactMessage.objects.filter(status='unread').count(),
        'pending_candidacies': Candidature.objects.filter(statut='soumise').count(),
        'pending_mentorships': DemandeMentorat.objects.filter(statut='en_attente').count(),
        'total_users': User.objects.filter(is_active=True).count(),
        'total_courses': Cours.objects.filter(est_publie=True).count(),
        'payments_this_month': payments_qs.count(),
        'payments_amount': payments_qs.aggregate(t=Sum('montant_final'))['t'] or 0,
    }
    recent_activity = StaffActivityLog.objects.select_related(
        'performed_by', 'target_user'
    )[:10]

    return render(request, 'admin_panel/dashboard.html', {
        'cards': cards,
        'recent_activity': recent_activity,
    })


# ─── CONTACTS ─────────────────────────────────────────────────────────────────

@staff_only
def contacts_list(request):
    from pages.models import ContactMessage

    qs = ContactMessage.objects.all()

    status_filter = request.GET.get('status', '')
    if status_filter in ('unread', 'read', 'replied'):
        qs = qs.filter(status=status_filter)

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(email__icontains=q) | Q(subject__icontains=q))

    # Bulk mark-as-read
    if request.method == 'POST':
        ids = request.POST.getlist('selected')
        if ids:
            ContactMessage.objects.filter(id__in=ids).update(status='read', is_read=True)
            messages.success(request, _("Messages marqués comme lus."))
        return redirect(request.get_full_path())

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin_panel/contacts_list.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'q': q,
        'unread_count': ContactMessage.objects.filter(status='unread').count(),
        'status_choices': [
            ('', _('Tous')),
            ('unread', _('Non lus')),
            ('read', _('Lus')),
            ('replied', _('Répondus')),
        ],
    })


@staff_only
def contact_detail(request, message_id):
    from pages.models import ContactMessage
    from numeria_project.emails import send_contact_reply_email

    msg = get_object_or_404(ContactMessage, id=message_id)

    # Auto-mark as read on open
    if msg.status == 'unread':
        msg.status = 'read'
        msg.is_read = True
        msg.save(update_fields=['status', 'is_read'])

    if request.method == 'POST':
        to_field = request.POST.get('to', msg.email).strip()
        subject = request.POST.get('subject', f'Re: {msg.subject}').strip()
        reply_text = request.POST.get('message', '').strip()

        if not reply_text:
            messages.error(request, _("Le message de réponse ne peut pas être vide."))
        else:
            try:
                send_contact_reply_email(
                    to_email=to_field,
                    to_name=msg.name,
                    subject=subject,
                    reply_message=reply_text,
                    staff_name=request.user.get_full_name() or request.user.username,
                )
                ContactReply.objects.create(
                    contact_message=msg,
                    replied_by=request.user,
                    subject=subject,
                    message=reply_text,
                )
                msg.status = 'replied'
                msg.is_read = True
                msg.save(update_fields=['status', 'is_read'])

                staff_name = request.user.get_full_name() or request.user.username
                notify_group(
                    User.objects.filter(is_staff=True),
                    title=_("Réponse envoyée"),
                    message=f"{staff_name} a répondu à {msg.name}",
                    notification_type='info',
                    link=f'/admin-panel/contacts/{msg.id}/',
                    created_by=request.user,
                )
                log_staff_action(
                    performed_by=request.user,
                    action_type='contact_replied',
                    description=f"Réponse envoyée à {msg.name} ({msg.email}) — sujet: {msg.subject}",
                )
                messages.success(request, _("Réponse envoyée avec succès."))
                return redirect('admin_panel:contacts_list')
            except Exception as e:
                logger.error('contact_detail reply error: %s', e)
                messages.error(request, _("Erreur lors de l'envoi de l'email : %(err)s") % {'err': str(e)})

    replies = msg.replies.select_related('replied_by').all()
    return render(request, 'admin_panel/contact_detail.html', {
        'msg': msg,
        'replies': replies,
        'reply_subject': f'Re: {msg.subject}',
    })


# ─── CANDIDATURES ─────────────────────────────────────────────────────────────

@staff_only
def candidatures_list(request):
    from admissions.models import Candidature

    qs = Candidature.objects.select_related('utilisateur', 'campagne', 'reviewed_by').all()

    statut_filter = request.GET.get('statut', '')
    if statut_filter:
        qs = qs.filter(statut=statut_filter)

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(utilisateur__first_name__icontains=q) |
            Q(utilisateur__last_name__icontains=q) |
            Q(utilisateur__email__icontains=q) |
            Q(campagne__filiere__icontains=q) |
            Q(reference__icontains=q)
        )

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin_panel/candidatures_list.html', {
        'page_obj': page_obj,
        'statut_filter': statut_filter,
        'q': q,
        'statuts': [
            ('soumise', _('Soumise')),
            ('en_revue', _('En revue')),
            ('acceptee', _('Acceptée')),
            ('refusee', _('Refusée')),
            ('liste_attente', _('Liste d\'attente')),
            ('brouillon', _('Brouillon')),
        ],
    })


@staff_only
def candidature_detail(request, candidature_id):
    from admissions.models import Candidature
    candidature = get_object_or_404(
        Candidature.objects.select_related('utilisateur', 'campagne', 'reviewed_by'),
        id=candidature_id,
    )
    return render(request, 'admin_panel/candidature_detail.html', {
        'c': candidature,
    })


@staff_only
@require_POST
def candidature_action(request, candidature_id):
    from admissions.models import Candidature
    from numeria_project.emails import (
        send_candidacy_acceptance_email,
        send_candidacy_rejection_email,
    )

    candidature = get_object_or_404(Candidature, id=candidature_id)
    action = request.POST.get('action')
    notes = request.POST.get('notes', '').strip()

    if action == 'accept':
        candidature.statut = 'acceptee'
        candidature.commentaire_admin = notes
        candidature.date_decision = timezone.now()
        candidature.reviewed_by = request.user
        candidature.reviewed_at = timezone.now()
        candidature.save()
        try:
            send_candidacy_acceptance_email(candidature)
        except Exception as e:
            logger.error('candidacy accept email failed: %s', e)
        notify_user(
            candidature.utilisateur,
            title=_("Candidature acceptée !"),
            message=_("Votre candidature pour %(prog)s a été acceptée ! 🎉") % {
                'prog': candidature.campagne.filiere
            },
            notification_type='candidacy',
            link='/admissions/mes-candidatures/',
            created_by=request.user,
        )
        log_staff_action(request.user, 'candidacy_accepted',
                         f"Candidature {candidature.reference} acceptée ({candidature.campagne.filiere})",
                         target_user=candidature.utilisateur)
        messages.success(request, _("✅ Candidature de %(name)s acceptée.") % {
            'name': f"{candidature.prenom} {candidature.nom}"})

    elif action == 'reject':
        rejection_reason = request.POST.get('rejection_reason', '').strip()
        if not rejection_reason:
            messages.error(request, _("La raison de refus est obligatoire."))
            return redirect('admin_panel:candidature_detail', candidature_id=candidature_id)
        candidature.statut = 'refusee'
        candidature.rejection_reason = rejection_reason
        candidature.commentaire_admin = notes
        candidature.date_decision = timezone.now()
        candidature.reviewed_by = request.user
        candidature.reviewed_at = timezone.now()
        candidature.save()
        try:
            send_candidacy_rejection_email(
                candidature.utilisateur,
                candidature.campagne.filiere,
                rejection_reason,
            )
        except Exception as e:
            logger.error('candidacy reject email failed: %s', e)
        notify_user(
            candidature.utilisateur,
            title=_("Résultat de votre candidature"),
            message=_("Nous avons examiné votre candidature pour %(prog)s.") % {
                'prog': candidature.campagne.filiere
            },
            notification_type='candidacy',
            created_by=request.user,
        )
        log_staff_action(request.user, 'candidacy_rejected',
                         f"Candidature {candidature.reference} refusée. Raison: {rejection_reason[:100]}",
                         target_user=candidature.utilisateur)
        messages.success(request, _("Candidature de %(name)s refusée.") % {
            'name': f"{candidature.prenom} {candidature.nom}"})

    elif action == 'review':
        candidature.statut = 'en_revue'
        candidature.commentaire_admin = notes
        candidature.reviewed_by = request.user
        candidature.save()
        log_staff_action(request.user, 'candidacy_reviewing',
                         f"Candidature {candidature.reference} mise en revue",
                         target_user=candidature.utilisateur)
        messages.info(request, _("Candidature marquée comme en cours de révision."))

    elif action == 'waitlist':
        candidature.statut = 'liste_attente'
        candidature.commentaire_admin = notes
        candidature.date_decision = timezone.now()
        candidature.reviewed_by = request.user
        candidature.reviewed_at = timezone.now()
        candidature.save()
        notify_user(
            candidature.utilisateur,
            title=_("Liste d'attente"),
            message=_("Vous êtes sur la liste d'attente pour %(prog)s.") % {
                'prog': candidature.campagne.filiere
            },
            notification_type='candidacy',
            created_by=request.user,
        )
        log_staff_action(request.user, 'candidacy_waitlisted',
                         f"Candidature {candidature.reference} mise en liste d'attente",
                         target_user=candidature.utilisateur)
        messages.info(request, _("Candidature mise en liste d'attente."))

    return redirect('admin_panel:candidatures_list')


# ─── MENTORAT ─────────────────────────────────────────────────────────────────

@staff_only
def mentorat_list(request):
    from mentorat.models import DemandeMentorat

    qs = DemandeMentorat.objects.select_related(
        'mentee__profil__utilisateur',
        'mentor__profil__utilisateur',
    ).all()

    statut_filter = request.GET.get('statut', '')
    if statut_filter:
        qs = qs.filter(statut=statut_filter)

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(mentee__profil__utilisateur__first_name__icontains=q) |
            Q(mentee__profil__utilisateur__last_name__icontains=q) |
            Q(mentee__profil__utilisateur__email__icontains=q) |
            Q(message__icontains=q)
        )

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin_panel/mentorat_list.html', {
        'page_obj': page_obj,
        'statut_filter': statut_filter,
        'q': q,
        'statuts': [
            ('en_attente', _('En attente')),
            ('acceptee', _('Acceptée')),
            ('refusee', _('Refusée')),
            ('terminee', _('Terminée')),
        ],
    })


@staff_only
def mentorat_detail(request, demande_id):
    from mentorat.models import DemandeMentorat, Mentor
    demande = get_object_or_404(
        DemandeMentorat.objects.select_related(
            'mentee__profil__utilisateur',
            'mentor__profil__utilisateur',
        ),
        id=demande_id,
    )
    available_mentors = Mentor.objects.filter(
        est_actif=True, profil__est_menteur=True
    ).select_related('profil__utilisateur')
    return render(request, 'admin_panel/mentorat_detail.html', {
        'demande': demande,
        'available_mentors': available_mentors,
    })


@staff_only
@require_POST
def mentorat_action(request, demande_id):
    from mentorat.models import DemandeMentorat, Mentor
    from numeria_project.emails import (
        send_mentorship_acceptance_email,
        send_mentorship_confirmation_to_mentor,
    )

    demande = get_object_or_404(DemandeMentorat, id=demande_id)
    action = request.POST.get('action')
    notes = request.POST.get('notes', '').strip()

    mentee_user = demande.mentee.profil.utilisateur
    mentor_user = demande.mentor.profil.utilisateur

    if action == 'accept':
        demande.accepter()
        if notes:
            demande.admin_notes = notes
            demande.save(update_fields=['admin_notes'])
        try:
            send_mentorship_acceptance_email(demande)
        except Exception as e:
            logger.error('mentorship accept email failed: %s', e)
        try:
            send_mentorship_confirmation_to_mentor(demande.mentor, demande.mentee)
        except Exception as e:
            logger.error('mentorship mentor confirm email failed: %s', e)
        notify_user(
            mentee_user,
            title=_("Demande de mentorat acceptée"),
            message=_("%(mentor)s va vous accompagner comme mentor. 🤝") % {
                'mentor': mentor_user.get_full_name() or mentor_user.username
            },
            notification_type='mentorship',
            link='/mentorat/tableau-bord-mentee/',
            created_by=request.user,
        )
        notify_user(
            mentor_user,
            title=_("Nouveau mentee assigné"),
            message=_("%(mentee)s vous a été assigné comme mentee.") % {
                'mentee': mentee_user.get_full_name() or mentee_user.username
            },
            notification_type='mentorship',
            link='/mentorat/tableau-bord-mentor/',
            created_by=request.user,
        )
        log_staff_action(request.user, 'mentorship_accepted',
                         f"Mentorat accepté: {mentee_user} → {mentor_user}",
                         target_user=mentee_user)
        messages.success(request, _("✅ Demande de mentorat acceptée."))

    elif action == 'reject':
        rejection_reason = request.POST.get('rejection_reason', '').strip()
        if not rejection_reason:
            messages.error(request, _("La raison de refus est obligatoire."))
            return redirect('admin_panel:mentorat_detail', demande_id=demande_id)
        demande.refuser()
        demande.admin_notes = f"Refusé par {request.user.username}: {rejection_reason}"
        demande.save(update_fields=['admin_notes'])
        notify_user(
            mentee_user,
            title=_("Demande de mentorat"),
            message=_("Votre demande de mentorat n'a pas pu être satisfaite pour le moment."),
            notification_type='mentorship',
            created_by=request.user,
        )
        log_staff_action(request.user, 'mentorship_rejected',
                         f"Mentorat refusé: {mentee_user} → {mentor_user}. {rejection_reason[:80]}",
                         target_user=mentee_user)
        messages.info(request, _("Demande de mentorat refusée."))

    elif action == 'assign_mentor':
        mentor_id = request.POST.get('mentor_id')
        if mentor_id:
            try:
                new_mentor = Mentor.objects.get(id=mentor_id)
                demande.mentor = new_mentor
                demande.save(update_fields=['mentor'])
                messages.success(request, _("Mentor réassigné avec succès."))
            except Mentor.DoesNotExist:
                messages.error(request, _("Mentor introuvable."))
        return redirect('admin_panel:mentorat_detail', demande_id=demande_id)

    return redirect('admin_panel:mentorat_list')


# ─── USERS ────────────────────────────────────────────────────────────────────

@staff_only
def users_list(request):
    qs = User.objects.all().order_by('-date_joined')

    role_filter = request.GET.get('role', '')
    if role_filter == 'active':
        qs = qs.filter(is_active=True)
    elif role_filter == 'inactive':
        qs = qs.filter(is_active=False)
    elif role_filter == 'staff':
        qs = qs.filter(is_staff=True)

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q) |
            Q(email__icontains=q) | Q(username__icontains=q)
        )

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin_panel/users_list.html', {
        'page_obj': page_obj,
        'role_filter': role_filter,
        'q': q,
        'role_choices': [
            ('', _('Tous')),
            ('active', _('Actifs')),
            ('inactive', _('Inactifs')),
            ('staff', _('Staff')),
        ],
    })


@staff_only
def user_detail(request, user_id):
    from cours.models import InscriptionCours
    from admissions.models import Candidature
    from mentorat.models import DemandeMentorat
    from notifications.models import Notification
    from django.db import models as db_models

    target = get_object_or_404(User, id=user_id)
    inscriptions = InscriptionCours.objects.filter(
        etudiant=target
    ).select_related('cours')[:10]
    candidatures = Candidature.objects.filter(
        utilisateur=target
    ).select_related('campagne').order_by('-date_soumission')[:5]

    mentorship_requests = []
    if hasattr(target, 'profil') and hasattr(target.profil, 'mentorat_mentee'):
        mentorship_requests = DemandeMentorat.objects.filter(
            mentee=target.profil.mentorat_mentee
        ).select_related('mentor__profil__utilisateur')[:5]

    recent_notifications = Notification.objects.filter(
        db_models.Q(recipient=target) | db_models.Q(recipient__isnull=True)
    ).order_by('-created_at')[:10]

    return render(request, 'admin_panel/user_detail.html', {
        'target': target,
        'inscriptions': inscriptions,
        'candidatures': candidatures,
        'mentorship_requests': mentorship_requests,
        'recent_notifications': recent_notifications,
    })


@staff_only
@require_POST
def user_action(request, user_id):
    target = get_object_or_404(User, id=user_id)
    action = request.POST.get('action')

    if action == 'toggle_active':
        if target == request.user:
            messages.error(request, _("Vous ne pouvez pas vous désactiver vous-même."))
            return redirect('admin_panel:user_detail', user_id=user_id)
        target.is_active = not target.is_active
        target.save(update_fields=['is_active'])
        if target.is_active:
            log_staff_action(request.user, 'user_activated',
                             f"Utilisateur {target.username} activé", target_user=target)
            messages.success(request, _("Compte activé."))
        else:
            log_staff_action(request.user, 'user_deactivated',
                             f"Utilisateur {target.username} désactivé", target_user=target)
            messages.warning(request, _("Compte désactivé."))

    elif action == 'toggle_staff':
        if target == request.user:
            messages.error(request, _("Vous ne pouvez pas modifier votre propre statut staff."))
            return redirect('admin_panel:user_detail', user_id=user_id)
        target.is_staff = not target.is_staff
        target.save(update_fields=['is_staff'])
        messages.success(request, _("Statut staff mis à jour."))

    elif action == 'send_notification':
        title = request.POST.get('notif_title', '').strip()
        msg_text = request.POST.get('notif_message', '').strip()
        if title and msg_text:
            notify_user(target, title=title, message=msg_text,
                        notification_type='info', created_by=request.user)
            log_staff_action(request.user, 'notification_sent',
                             f"Notification envoyée à {target.username}: {title}",
                             target_user=target)
            messages.success(request, _("Notification envoyée."))
        else:
            messages.error(request, _("Titre et message requis."))
        return redirect('admin_panel:user_detail', user_id=user_id)

    elif action == 'reset_password':
        form = PasswordResetForm({'email': target.email})
        if form.is_valid():
            form.save(
                request=request,
                use_https=request.is_secure(),
                email_template_name='registration/password_reset_email.html',
                subject_template_name='registration/password_reset_subject.txt',
            )
            messages.success(
                request,
                _("Email de réinitialisation envoyé à %(email)s") % {'email': target.email}
            )
        else:
            messages.error(request, _("Impossible d'envoyer l'email (adresse invalide ?)"))
        return redirect('admin_panel:user_detail', user_id=user_id)

    return redirect('admin_panel:user_detail', user_id=user_id)


# ─── ACTIVITY LOG ─────────────────────────────────────────────────────────────

@staff_only
def activity_log(request):
    logs = StaffActivityLog.objects.select_related(
        'performed_by', 'target_user'
    )[:50]
    return render(request, 'admin_panel/activity_log.html', {'logs': logs})
