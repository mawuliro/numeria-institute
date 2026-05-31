import logging
from datetime import date
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordResetForm
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.core.validators import validate_email
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
    from mentorat.models import DemandeMentorat, MentorApplication
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
        'pending_mentor_applications': MentorApplication.objects.filter(status='pending').count(),
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
                validate_email(to_field)
                subject = subject.replace('\n', ' ').replace('\r', ' ')
            except ValidationError:
                messages.error(request, _("L'adresse email de destination n'est pas valide."))
                return render(request, 'admin_panel/contact_detail.html', {
                    'msg': msg,
                    'replies': msg.replies.select_related('replied_by').all(),
                    'reply_subject': subject,
                    'reply_to': to_field,
                    'reply_message': reply_text,
                })
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

    if action in ['accept', 'reject'] and candidature.statut in ['acceptee', 'refusee']:
        messages.warning(request, _("Cette candidature a déjà été traitée et ne peut plus être modifiée."))
        return redirect('admin_panel:candidature_detail', candidature_id=candidature_id)

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

    if action in ['accept', 'reject'] and demande.statut in ['acceptee', 'refusee', 'terminee']:
        messages.warning(request, _("Cette demande a déjà été traitée et ne peut plus être modifiée."))
        return redirect('admin_panel:mentorat_detail', demande_id=demande_id)

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


# ─── EXERCISE MANAGEMENT ──────────────────────────────────────────────────────

@staff_only
def exercises_list(request):
    """List all code exercises (Course AND Formation) with filters."""
    from cours.models import CodeExercise, StudentCodeSubmission, Cours
    from formation.models import Formation

    type_filter = request.GET.get('type', '')        # 'cours' | 'formation' | ''
    cours_filter = request.GET.get('cours', '')
    formation_filter = request.GET.get('formation', '')

    qs = CodeExercise.objects.select_related(
        'lecon__cours', 'formation_lesson__formation'
    )

    if type_filter == 'cours':
        qs = qs.filter(lecon__isnull=False)
    elif type_filter == 'formation':
        qs = qs.filter(formation_lesson__isnull=False)

    if cours_filter:
        qs = qs.filter(lecon__cours_id=cours_filter)
    if formation_filter:
        qs = qs.filter(formation_lesson__formation_id=formation_filter)

    qs = qs.order_by('title')
    exercises = list(qs)
    submission_counts = {
        ex.id: StudentCodeSubmission.objects.filter(
            exercise=ex, is_correct=True
        ).values('student').distinct().count()
        for ex in exercises
    }

    return render(request, 'admin_panel/exercises_list.html', {
        'exercises':        exercises,
        'submission_counts': submission_counts,
        'cours_list':       Cours.objects.order_by('titre'),
        'formation_list':   Formation.objects.order_by('titre'),
        'type_filter':      type_filter,
        'cours_filter':     cours_filter,
        'formation_filter': formation_filter,
    })


def _parse_exercise_fields(request):
    """Extract and validate exercise fields from POST data."""
    return {
        'title':            request.POST.get('title', '').strip(),
        'instructions':     request.POST.get('instructions', '').strip(),
        'starter_code':     request.POST.get('starter_code', '').strip(),
        'solution_code':    request.POST.get('solution_code', '').strip(),
        'expected_output':  request.POST.get('expected_output', '').strip(),
        'test_code':        request.POST.get('test_code', '').strip(),
        'evaluation_mode':  request.POST.get('evaluation_mode', 'exact'),
        'difficulty':       request.POST.get('difficulty', 'easy'),
        'hint':             request.POST.get('hint', '').strip(),
        'max_attempts':     int(request.POST.get('max_attempts', 0) or 0),
        'points':           int(request.POST.get('points', 10) or 10),
        'order':            int(request.POST.get('order', 0) or 0),
    }


@staff_only
def exercise_create(request, lecon_id):
    """Create a new code exercise for a Course lesson."""
    from cours.models import CodeExercise, Lecon

    lecon = get_object_or_404(Lecon, id=lecon_id)

    if request.method == 'POST':
        f = _parse_exercise_fields(request)
        if not f['title'] or not f['starter_code'] or not f['solution_code']:
            messages.error(request, _("Titre, code de départ et solution sont obligatoires."))
        else:
            CodeExercise.objects.create(lecon=lecon, **f)
            log_staff_action(request.user, 'notification_sent',
                             f"Exercice créé: '{f['title']}' pour {lecon.titre}")
            messages.success(request, _("Exercice créé avec succès."))
            return redirect('admin_panel:exercises_list')

    next_order = CodeExercise.objects.filter(lecon=lecon).count()
    return render(request, 'admin_panel/exercise_form.html', {
        'lecon': lecon,
        'next_order': next_order,
        'action': 'create',
        'lesson_type': 'cours',
        'eval_modes': CodeExercise.EVAL_MODES,
        'difficulties': CodeExercise.DIFFICULTY_CHOICES,
    })


@staff_only
def exercise_create_formation(request, lecon_id):
    """Create a new code exercise for a Formation lesson."""
    from cours.models import CodeExercise
    from formation.models import FormationLesson

    fl = get_object_or_404(FormationLesson, id=lecon_id)

    if request.method == 'POST':
        f = _parse_exercise_fields(request)
        if not f['title'] or not f['starter_code'] or not f['solution_code']:
            messages.error(request, _("Titre, code de départ et solution sont obligatoires."))
        else:
            CodeExercise.objects.create(formation_lesson=fl, lecon=None, **f)
            log_staff_action(request.user, 'notification_sent',
                             f"Exercice créé: '{f['title']}' pour {fl.titre}")
            messages.success(request, _("Exercice créé avec succès."))
            return redirect('admin_panel:exercises_list')

    next_order = CodeExercise.objects.filter(formation_lesson=fl).count()
    return render(request, 'admin_panel/exercise_form.html', {
        'lecon':       fl,
        'next_order':  next_order,
        'action':      'create',
        'lesson_type': 'formation',
        'eval_modes':  CodeExercise.EVAL_MODES,
        'difficulties': CodeExercise.DIFFICULTY_CHOICES,
    })


@staff_only
def exercise_edit(request, exercise_id):
    """Edit an existing code exercise."""
    from cours.models import CodeExercise

    ex = get_object_or_404(CodeExercise, id=exercise_id)

    if request.method == 'POST':
        ex.title            = request.POST.get('title', '').strip()
        ex.instructions     = request.POST.get('instructions', '').strip()
        ex.starter_code     = request.POST.get('starter_code', '').strip()
        ex.solution_code    = request.POST.get('solution_code', '').strip()
        ex.expected_output  = request.POST.get('expected_output', '').strip()
        ex.test_code        = request.POST.get('test_code', '').strip()
        ex.evaluation_mode  = request.POST.get('evaluation_mode', 'exact')
        ex.difficulty       = request.POST.get('difficulty', 'easy')
        ex.hint             = request.POST.get('hint', '').strip()
        ex.max_attempts     = int(request.POST.get('max_attempts', 0) or 0)
        ex.points           = int(request.POST.get('points', 10) or 10)
        ex.order            = int(request.POST.get('order', 0) or 0)
        ex.is_active        = 'is_active' in request.POST
        ex.save()
        messages.success(request, _("Exercice mis à jour."))
        return redirect('admin_panel:exercises_list')

    from cours.models import CodeExercise as CE
    lesson_type = 'formation' if ex.formation_lesson_id else 'cours'
    return render(request, 'admin_panel/exercise_form.html', {
        'exercise':    ex,
        'lecon':       ex.lecon or ex.formation_lesson,
        'lesson_type': lesson_type,
        'action':      'edit',
        'eval_modes':  CE.EVAL_MODES,
        'difficulties': CE.DIFFICULTY_CHOICES,
    })


@staff_only
@require_POST
def exercise_delete(request, exercise_id):
    from cours.models import CodeExercise
    ex = get_object_or_404(CodeExercise, id=exercise_id)
    title = ex.title
    ex.delete()
    messages.success(request, _("Exercice « %(title)s » supprimé.") % {'title': title})
    return redirect('admin_panel:exercises_list')


@staff_only
@require_POST
def exercise_reorder(request, exercise_id):
    """AJAX endpoint to update exercise order."""
    from cours.models import CodeExercise
    import json as _json
    ex = get_object_or_404(CodeExercise, id=exercise_id)
    try:
        body = _json.loads(request.body)
        ex.order = int(body.get('order', ex.order))
        ex.save(update_fields=['order'])
        from django.http import JsonResponse
        return JsonResponse({'ok': True})
    except Exception:
        from django.http import JsonResponse
        return JsonResponse({'ok': False}, status=400)


@staff_only
def exercise_results(request):
    """Student submission results table with filters and leaderboard."""
    from cours.models import StudentCodeSubmission, CodeExercise
    from django.db.models import Count, Sum

    qs = StudentCodeSubmission.objects.select_related(
        'student', 'exercise__lecon__cours'
    ).order_by('-submitted_at')

    correct_filter = request.GET.get('correct', '')
    if correct_filter == '1':
        qs = qs.filter(is_correct=True)
    elif correct_filter == '0':
        qs = qs.filter(is_correct=False)

    ex_filter = request.GET.get('exercise', '')
    if ex_filter:
        qs = qs.filter(exercise_id=ex_filter)

    paginator = Paginator(qs, 30)
    page_obj  = paginator.get_page(request.GET.get('page'))

    # Leaderboard: top students by distinct correct exercises * points
    leaderboard = (
        StudentCodeSubmission.objects
        .filter(is_correct=True)
        .values('student__id', 'student__first_name', 'student__last_name',
                'student__username')
        .annotate(solved=Count('exercise', distinct=True),
                  total_pts=Sum('exercise__points'))
        .order_by('-total_pts')[:20]
    )

    all_exercises = CodeExercise.objects.select_related('lecon').order_by('lecon__cours__titre', 'order')

    return render(request, 'admin_panel/exercise_results.html', {
        'page_obj': page_obj,
        'leaderboard': leaderboard,
        'all_exercises': all_exercises,
        'correct_filter': correct_filter,
        'ex_filter': ex_filter,
    })


@staff_only
def exercise_results_csv(request):
    """Export submissions as CSV."""
    from cours.models import StudentCodeSubmission
    import csv
    from django.http import HttpResponse as _HttpResponse

    response = _HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="submissions.csv"'

    writer = csv.writer(response)
    writer.writerow(['Student', 'Email', 'Exercise', 'Lesson', 'Course',
                     'Correct', 'Attempts', 'Time(s)', 'Date'])

    for sub in StudentCodeSubmission.objects.select_related(
        'student', 'exercise__lecon__cours'
    ).order_by('-submitted_at')[:5000]:
        writer.writerow([
            sub.student.get_full_name() or sub.student.username,
            sub.student.email,
            sub.exercise.title,
            sub.exercise.lecon.titre,
            sub.exercise.lecon.cours.titre,
            sub.is_correct,
            sub.attempt_number,
            sub.time_spent_seconds,
            sub.submitted_at.strftime('%Y-%m-%d %H:%M'),
        ])
    return response


# ─── MCQ ADMIN MANAGEMENT ────────────────────────────────────────────────────

@staff_only
def mcq_list(request):
    from cours.models import MCQExercise
    from formation.models import Formation
    from cours.models import Cours

    type_filter = request.GET.get('type', '')
    qs = MCQExercise.objects.select_related(
        'lesson__cours', 'formation_lesson__formation'
    ).prefetch_related('choices')

    if type_filter == 'cours':
        qs = qs.filter(lesson__isnull=False)
    elif type_filter == 'formation':
        qs = qs.filter(formation_lesson__isnull=False)

    q = request.GET.get('q', '').strip()
    if q:
        from django.db.models import Q as DQ
        qs = qs.filter(DQ(title__icontains=q) | DQ(question__icontains=q))

    qs = qs.order_by('title')

    return render(request, 'admin_panel/mcq_list.html', {
        'mcqs':        qs,
        'type_filter': type_filter,
        'q':           q,
    })


@staff_only
def mcq_edit(request, mcq_id):
    from cours.models import MCQExercise, MCQChoice
    mcq = get_object_or_404(MCQExercise, id=mcq_id)
    if request.method == 'POST':
        mcq.title       = request.POST.get('title', mcq.title).strip()
        mcq.question    = request.POST.get('question', mcq.question)
        mcq.explanation = request.POST.get('explanation', mcq.explanation)
        mcq.hint        = request.POST.get('hint', mcq.hint)
        mcq.difficulty  = request.POST.get('difficulty', mcq.difficulty)
        mcq.points      = int(request.POST.get('points', mcq.points) or mcq.points)
        mcq.max_attempts = int(request.POST.get('max_attempts', mcq.max_attempts) or 0)
        mcq.is_active   = 'is_active' in request.POST
        mcq.save()
        messages.success(request, 'QCM mis à jour.')
        return redirect('admin_panel:mcq_list')
    return render(request, 'admin_panel/mcq_edit.html', {
        'mcq':    mcq,
        'choices': mcq.choices.all(),
    })


@staff_only
@require_POST
def mcq_delete(request, mcq_id):
    from cours.models import MCQExercise
    mcq = get_object_or_404(MCQExercise, id=mcq_id)
    title = mcq.title
    mcq.delete()
    messages.success(request, f'QCM «{title}» supprimé.')
    return redirect('admin_panel:mcq_list')
