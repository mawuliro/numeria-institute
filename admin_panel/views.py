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
    from cours.models import Course
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
        'total_courses': Course.objects.filter(status='published').count(),
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
    ).select_related('course')[:10]
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
    """List exercises of all types with tab filter."""
    from cours.models import (
        CodeExercise, MCQExercise, FillBlankExercise, TrueFalseExercise,
        CodeOrderExercise, MatchingExercise, ShortAnswerExercise,
    )

    active_type = request.GET.get('type', 'all')
    q = request.GET.get('q', '').strip()

    MODEL_MAP = {
        'code':         CodeExercise,
        'mcq':          MCQExercise,
        'fill_blank':   FillBlankExercise,
        'true_false':   TrueFalseExercise,
        'code_order':   CodeOrderExercise,
        'matching':     MatchingExercise,
        'short_answer': ShortAnswerExercise,
    }

    if active_type in MODEL_MAP:
        models_to_query = {active_type: MODEL_MAP[active_type]}
    else:
        models_to_query = MODEL_MAP

    exercises = []
    for ex_type, model in models_to_query.items():
        qs = model.objects.select_related('course_lesson', 'formation_lesson').order_by('title')
        if q:
            qs = qs.filter(title__icontains=q)
        for ex in qs:
            ex._ex_type = ex_type
            exercises.append(ex)

    exercises.sort(key=lambda e: e.title.lower())

    TAB_CHOICES = [
        ('all',          '📊 Tous'),
        ('code',         '💻 Code'),
        ('mcq',          '🔘 QCM'),
        ('fill_blank',   '✏️ Trous'),
        ('true_false',   '✅ V/F'),
        ('code_order',   '🧩 Ordre'),
        ('matching',     '🔗 Asso.'),
        ('short_answer', '💬 Court'),
    ]
    return render(request, 'admin_panel/exercises_list.html', {
        'exercises':   exercises,
        'active_type': active_type,
        'q':           q,
        'tab_choices': TAB_CHOICES,
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
    from cours.models import CodeExercise, CourseLesson

    lecon = get_object_or_404(CourseLesson, id=lecon_id)

    if request.method == 'POST':
        f = _parse_exercise_fields(request)
        if not f['title'] or not f['starter_code'] or not f['solution_code']:
            messages.error(request, _("Titre, code de départ et solution sont obligatoires."))
        else:
            CodeExercise.objects.create(course_lesson=lecon, **f)
            log_staff_action(request.user, 'exercise_created',
                             f"Exercice créé: '{f['title']}' pour {lecon.title}")
            messages.success(request, _("Exercice créé avec succès."))
            return redirect('admin_panel:exercises_list')

    next_order = CodeExercise.objects.filter(course_lesson=lecon).count()
    return render(request, 'admin_panel/exercise_form.html', {
        'lecon': lecon,
        'next_order': next_order,
        'action': 'create',
        'lesson_type': 'cours',
        'eval_modes': CodeExercise.EVAL_MODES,
        'difficulties': CodeExercise.DIFFICULTY,
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
            CodeExercise.objects.create(formation_lesson=fl, course_lesson=None, **f)
            log_staff_action(request.user, 'exercise_created',
                             f"Exercice créé: '{f['title']}' pour {fl.title}")
            messages.success(request, _("Exercice créé avec succès."))
            return redirect('admin_panel:exercises_list')

    next_order = CodeExercise.objects.filter(formation_lesson=fl).count()
    return render(request, 'admin_panel/exercise_form.html', {
        'lecon':       fl,
        'next_order':  next_order,
        'action':      'create',
        'lesson_type': 'formation',
        'eval_modes':  CodeExercise.EVAL_MODES,
        'difficulties': CodeExercise.DIFFICULTY,
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
        'lecon':       ex.course_lesson or ex.formation_lesson,
        'lesson_type': lesson_type,
        'action':      'edit',
        'eval_modes':  CE.EVAL_MODES,
        'difficulties': CE.DIFFICULTY,
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
    from cours.models import ExerciseAttempt, CodeExercise
    from django.db.models import Count, Sum

    # ExerciseAttempt replaces removed StudentCodeSubmission
    qs = ExerciseAttempt.objects.filter(exercise_type='code').select_related('student').order_by('-submitted_at')

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

    # Leaderboard: top students by distinct correct exercises
    leaderboard = (
        ExerciseAttempt.objects
        .filter(exercise_type='code', is_correct=True)
        .values('student__id', 'student__first_name', 'student__last_name', 'student__username')
        .annotate(solved=Count('exercise_id', distinct=True), total_pts=Sum('points_earned'))
        .order_by('-total_pts')[:20]
    )

    all_exercises = CodeExercise.objects.select_related('course_lesson').order_by('course_lesson__course__title', 'order')

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
    from cours.models import ExerciseAttempt, CodeExercise
    import csv
    from django.http import HttpResponse as _HttpResponse

    response = _HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="submissions.csv"'

    writer = csv.writer(response)
    writer.writerow(['Student', 'Email', 'Exercise ID', 'Exercise Type',
                     'Correct', 'Attempts', 'Points Earned', 'Date'])

    # ExerciseAttempt replaces removed StudentCodeSubmission
    attempts = list(
        ExerciseAttempt.objects.filter(exercise_type='code')
        .select_related('student')
        .order_by('-submitted_at')[:5000]
    )
    # Batch-load all exercise titles in one query to avoid N+1 (was: 1 query
    # per attempt = up to 5000 extra queries per CSV export).
    ex_ids = {a.exercise_id for a in attempts if a.exercise_id}
    ex_titles = dict(
        CodeExercise.objects.filter(id__in=ex_ids).values_list('id', 'title')
    ) if ex_ids else {}
    for attempt in attempts:
        ex_title = ex_titles.get(attempt.exercise_id) or f'#{attempt.exercise_id}'
        writer.writerow([
            attempt.student.get_full_name() or attempt.student.username,
            attempt.student.email,
            ex_title,
            attempt.exercise_type,
            attempt.is_correct,
            attempt.attempt_number,
            attempt.points_earned,
            attempt.submitted_at.strftime('%Y-%m-%d %H:%M'),
        ])
    return response


# ─── MCQ ADMIN MANAGEMENT ────────────────────────────────────────────────────

@staff_only
def mcq_list(request):
    from cours.models import MCQExercise
    from formation.models import Formation
    from cours.models import Course

    type_filter = request.GET.get('type', '')
    qs = MCQExercise.objects.select_related(
        'course_lesson__course', 'formation_lesson__formation'
    ).prefetch_related('choices')

    if type_filter == 'cours':
        qs = qs.filter(course_lesson__isnull=False)
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


# ─── EXERCISE TYPE SELECTOR + PER-TYPE CREATION ───────────────────────────────

EXERCISE_TYPES = {
    'code':         ('💻', 'Code Python'),
    'qcm':          ('🔘', 'QCM'),
    'fill_blank':   ('✏️', 'Texte à trous'),
    'true_false':   ('✅', 'Vrai ou Faux'),
    'code_order':   ('🧩', 'Ordre de code'),
    'matching':     ('🔗', 'Associations'),
    'short_answer': ('💬', 'Réponse courte'),
    'grouped':      ('🧩', 'Exercice groupé'),
}


@staff_only
def exercise_type_selector(request, lecon_id):
    """Type selector for course lesson exercise creation."""
    from cours.models import CourseLesson
    lecon = get_object_or_404(CourseLesson, id=lecon_id)
    return render(request, 'admin_panel/exercise_type_selector.html', {
        'lecon': lecon,
        'lesson_type': 'cours',
        'exercise_types': EXERCISE_TYPES,
    })


@staff_only
def exercise_type_selector_formation(request, lecon_id):
    """Type selector for formation lesson exercise creation."""
    from formation.models import FormationLesson
    fl = get_object_or_404(FormationLesson, id=lecon_id)
    return render(request, 'admin_panel/exercise_type_selector.html', {
        'lecon': fl,
        'lesson_type': 'formation',
        'exercise_types': EXERCISE_TYPES,
    })


def _handle_exercise_creation(request, lecon, fl, ex_type):
    """
    Shared dispatcher for creating any exercise type for a lesson.
    lecon = Lecon instance or None, fl = FormationLesson instance or None.
    """
    from cours.models import (
        CodeExercise, LessonBlock, MCQExercise, MCQChoice,
        FillBlankExercise, TrueFalseExercise,
        CodeOrderExercise, MatchingExercise, ShortAnswerExercise,
        # TODO: GroupedExercise removed in rebuild — grouped exercise creation disabled
    )
    import json as _json

    lesson_type = 'formation' if fl else 'cours'
    lesson_obj  = fl or lecon
    back_url    = request.POST.get('back_url') or request.GET.get('back_url') or ''

    template_map = {
        'code':         'admin_panel/exercise_form.html',
        'qcm':          'admin_panel/exercise_form_qcm.html',
        'fill_blank':   'admin_panel/exercise_form_fill_blank.html',
        'true_false':   'admin_panel/exercise_form_true_false.html',
        'code_order':   'admin_panel/exercise_form_code_order.html',
        'matching':     'admin_panel/exercise_form_matching.html',
        'short_answer': 'admin_panel/exercise_form_short_answer.html',
        'grouped':      'admin_panel/exercise_form_grouped.html',
    }
    template = template_map.get(ex_type, 'admin_panel/exercise_form.html')

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if not title:
            messages.error(request, 'Le titre est obligatoire.')
        else:
            try:
                if ex_type == 'code':
                    f = _parse_exercise_fields(request)
                    if not f['starter_code'] or not f['solution_code']:
                        messages.error(request, 'Code de départ et solution sont obligatoires.')
                        return render(request, template, {'lecon': lesson_obj, 'lesson_type': lesson_type, 'action': 'create'})
                    CodeExercise.objects.create(
                        course_lesson=lecon, formation_lesson=fl, created_by=request.user, **f
                    )

                elif ex_type == 'qcm':
                    allow_multi = 'allow_multiple_correct' in request.POST
                    mcq = MCQExercise.objects.create(
                        course_lesson=lecon, formation_lesson=fl,
                        title=title,
                        question=request.POST.get('question', '').strip(),
                        explanation=request.POST.get('explanation', '').strip(),
                        hint=request.POST.get('hint', '').strip(),
                        difficulty=request.POST.get('difficulty', 'easy'),
                        points=int(request.POST.get('points', 5) or 5),
                        max_attempts=int(request.POST.get('max_attempts', 0) or 0),
                        allow_multiple_correct=allow_multi,
                        shuffle_choices=True,
                        created_by=request.user,
                    )
                    texts    = request.POST.getlist('choice_text')
                    corrects = request.POST.getlist('choice_correct')
                    for idx, text in enumerate(texts):
                        if text.strip():
                            MCQChoice.objects.create(
                                exercise=mcq, text=text.strip(),
                                is_correct=str(idx) in corrects,
                                order=idx,
                            )

                elif ex_type == 'fill_blank':
                    answers = {}
                    text = request.POST.get('text_with_blanks', '')
                    import re
                    blanks = re.findall(r'\{\{(blank_\w+)\}\}', text)
                    for blank in blanks:
                        raw = request.POST.get(f'answer_{blank}', '')
                        answers[blank] = [a.strip() for a in raw.split(',') if a.strip()]
                    FillBlankExercise.objects.create(
                        course_lesson=lecon, formation_lesson=fl, title=title,
                        instructions=request.POST.get('instructions', '').strip(),
                        text_with_blanks=text,
                        answers=answers,
                        case_sensitive='case_sensitive' in request.POST,
                        difficulty=request.POST.get('difficulty', 'easy'),
                        points=int(request.POST.get('points', 5) or 5),
                        hint=request.POST.get('hint', '').strip(),
                        explanation=request.POST.get('explanation', '').strip(),
                        max_attempts=int(request.POST.get('max_attempts', 0) or 0),
                    )

                elif ex_type == 'true_false':
                    stmts = []
                    for i, stmt in enumerate(request.POST.getlist('statement')):
                        if stmt.strip():
                            stmts.append({
                                'statement': stmt.strip(),
                                'is_true': f'is_true_{i}' in request.POST,
                                'explanation': request.POST.getlist('stmt_explanation')[i] if i < len(request.POST.getlist('stmt_explanation')) else '',
                            })
                    TrueFalseExercise.objects.create(
                        course_lesson=lecon, formation_lesson=fl, title=title,
                        statements=stmts,
                        points_per_statement=int(request.POST.get('points_per_statement', 2) or 2),
                        difficulty=request.POST.get('difficulty', 'easy'),
                        hint=request.POST.get('hint', '').strip(),
                    )

                elif ex_type == 'code_order':
                    lines_raw = request.POST.get('correct_solution', '')
                    correct_order = [l for l in lines_raw.split('\n') if l.strip() or l == '']
                    # Remove trailing empty lines
                    while correct_order and not correct_order[-1].strip():
                        correct_order.pop()
                    distractors_raw = request.POST.get('distractor_lines', '')
                    distractors = [l.strip() for l in distractors_raw.split('\n') if l.strip()]
                    CodeOrderExercise.objects.create(
                        course_lesson=lecon, formation_lesson=fl, title=title,
                        instructions=request.POST.get('instructions', '').strip(),
                        correct_order=correct_order,
                        distractor_lines=distractors,
                        difficulty=request.POST.get('difficulty', 'easy'),
                        points=int(request.POST.get('points', 10) or 10),
                        hint=request.POST.get('hint', '').strip(),
                        explanation=request.POST.get('explanation', '').strip(),
                        max_attempts=int(request.POST.get('max_attempts', 0) or 0),
                    )

                elif ex_type == 'matching':
                    lefts  = request.POST.getlist('left_item')
                    rights = request.POST.getlist('right_item')
                    pairs  = [{'left': l.strip(), 'right': r.strip()}
                              for l, r in zip(lefts, rights) if l.strip() and r.strip()]
                    MatchingExercise.objects.create(
                        course_lesson=lecon, formation_lesson=fl, title=title,
                        instructions=request.POST.get('instructions', '').strip(),
                        pairs=pairs,
                        difficulty=request.POST.get('difficulty', 'easy'),
                        points=int(request.POST.get('points', 8) or 8),
                        hint=request.POST.get('hint', '').strip(),
                        explanation=request.POST.get('explanation', '').strip(),
                    )

                elif ex_type == 'short_answer':
                    raw = request.POST.get('accepted_answers', '')
                    accepted = [a.strip() for a in raw.split(',') if a.strip()]
                    ShortAnswerExercise.objects.create(
                        course_lesson=lecon, formation_lesson=fl, title=title,
                        question=request.POST.get('question', '').strip(),
                        accepted_answers=accepted,
                        case_sensitive='case_sensitive' in request.POST,
                        difficulty=request.POST.get('difficulty', 'easy'),
                        points=int(request.POST.get('points', 5) or 5),
                        hint=request.POST.get('hint', '').strip(),
                        explanation=request.POST.get('explanation', '').strip(),
                        max_attempts=int(request.POST.get('max_attempts', 3) or 3),
                        is_code_answer='is_code_answer' in request.POST,
                    )

                elif ex_type == 'grouped':
                    qtype = request.POST.get('question_type', 'qcm')
                    question_count = int(request.POST.get('question_count', 0) or 0)
                    if question_count <= 0:
                        messages.error(request, 'Il faut au moins une question pour un exercice groupé.')
                        return render(request, template, {'lecon': lesson_obj, 'lesson_type': lesson_type, 'action': 'create'})

                    group_questions = []
                    created_exercises = []
                    for idx in range(question_count):
                        label = request.POST.get(f'question_label_{idx}', f'Q{idx + 1}').strip() or f'Q{idx + 1}'
                        if qtype == 'qcm':
                            question_text = request.POST.get(f'question_text_{idx}', '').strip()
                            if not question_text:
                                continue
                            mcq = MCQExercise.objects.create(
                                course_lesson=lecon, formation_lesson=fl,
                                title=f'{label} – {title}',
                                question=question_text,
                                explanation=request.POST.get(f'explanation_{idx}', '').strip(),
                                hint=request.POST.get('hint', '').strip(),
                                difficulty=request.POST.get('difficulty', 'easy'),
                                points=int(request.POST.get('points', 5) or 5),
                                max_attempts=int(request.POST.get('max_attempts', 0) or 0),
                                allow_multiple_correct='allow_multiple_correct' in request.POST,
                                shuffle_choices=True,
                                created_by=request.user,
                            )
                            answers = request.POST.getlist(f'choice_text_{idx}')
                            corrects = request.POST.getlist(f'choice_correct_{idx}')
                            for cidx, text in enumerate(answers):
                                if text.strip():
                                    MCQChoice.objects.create(
                                        exercise=mcq,
                                        text=text.strip(),
                                        is_correct=str(cidx) in corrects,
                                        order=cidx,
                                    )
                            created_exercises.append({'question_type': 'qcm', 'exercise_id': mcq.id, 'label': label})

                        elif qtype == 'fill_blank':
                            text_with_blanks = request.POST.get(f'text_with_blanks_{idx}', '').strip()
                            if not text_with_blanks:
                                continue
                            answers = {}
                            import re
                            blanks = re.findall(r'\{\{(blank_\w+)\}\}', text_with_blanks)
                            for blank in blanks:
                                raw = request.POST.get(f'answer_{idx}_{blank}', '')
                                answers[blank] = [a.strip() for a in raw.split(',') if a.strip()]
                            ex = FillBlankExercise.objects.create(
                                course_lesson=lecon, formation_lesson=fl,
                                title=f'{label} – {title}',
                                instructions=request.POST.get('instructions', '').strip(),
                                text_with_blanks=text_with_blanks,
                                answers=answers,
                                case_sensitive='case_sensitive' in request.POST,
                                difficulty=request.POST.get('difficulty', 'easy'),
                                points=int(request.POST.get('points', 5) or 5),
                                hint=request.POST.get('hint', '').strip(),
                                explanation=request.POST.get('explanation', '').strip(),
                                max_attempts=int(request.POST.get('max_attempts', 0) or 0),
                            )
                            created_exercises.append({'question_type': 'fill_blank', 'exercise_id': ex.id, 'label': label})

                        elif qtype == 'true_false':
                            statement = request.POST.get(f'statement_{idx}', '').strip()
                            if not statement:
                                continue
                            is_true = f'is_true_{idx}' in request.POST
                            ex = TrueFalseExercise.objects.create(
                                course_lesson=lecon, formation_lesson=fl,
                                title=f'{label} – {title}',
                                statements=[{
                                    'statement': statement,
                                    'is_true': is_true,
                                    'explanation': request.POST.get(f'stmt_explanation_{idx}', '').strip(),
                                }],
                                points_per_statement=int(request.POST.get('points_per_statement', 2) or 2),
                                difficulty=request.POST.get('difficulty', 'easy'),
                                hint=request.POST.get('hint', '').strip(),
                            )
                            created_exercises.append({'question_type': 'true_false', 'exercise_id': ex.id, 'label': label})

                        elif qtype == 'short_answer':
                            question_text = request.POST.get(f'question_text_{idx}', '').strip()
                            if not question_text:
                                continue
                            raw = request.POST.get(f'accepted_answers_{idx}', '')
                            accepted = [a.strip() for a in raw.split(',') if a.strip()]
                            ex = ShortAnswerExercise.objects.create(
                                course_lesson=lecon, formation_lesson=fl,
                                title=f'{label} – {title}',
                                question=question_text,
                                accepted_answers=accepted,
                                case_sensitive='case_sensitive' in request.POST,
                                difficulty=request.POST.get('difficulty', 'easy'),
                                points=int(request.POST.get('points', 5) or 5),
                                hint=request.POST.get('hint', '').strip(),
                                explanation=request.POST.get('explanation', '').strip(),
                                max_attempts=int(request.POST.get('max_attempts', 3) or 3),
                                is_code_answer='is_code_answer' in request.POST,
                            )
                            created_exercises.append({'question_type': 'short_answer', 'exercise_id': ex.id, 'label': label})

                    if not created_exercises:
                        messages.error(request, 'Aucune question valide n’a été trouvée.')
                        return render(request, template, {'lecon': lesson_obj, 'lesson_type': lesson_type, 'action': 'create'})

                    # TODO: GroupedExercise removed in rebuild — cannot create grouped blocks
                    messages.error(request, "Les exercices groupés ne sont pas encore disponibles dans la nouvelle version.")
                    return render(request, template, {'lecon': lesson_obj, 'lesson_type': lesson_type, 'action': 'create'})

                messages.success(request, f"Exercice '{title}' créé avec succès.")
                return redirect('admin_panel:exercises_list')

            except Exception as e:
                messages.error(request, f"Erreur lors de la création : {e}")

    from cours.models import CodeExercise as CE
    ctx = {
        'lecon': lesson_obj,
        'lesson_type': lesson_type,
        'action': 'create',
        'ex_type': ex_type,
        'back_url': back_url,
        'eval_modes': CE.EVAL_MODES,
        'difficulties': CE.DIFFICULTY,
    }
    return render(request, template, ctx)


@staff_only
def exercise_create_by_type(request, lecon_id, ex_type):
    from cours.models import CourseLesson
    lecon = get_object_or_404(CourseLesson, id=lecon_id)
    return _handle_exercise_creation(request, lecon, None, ex_type)


@staff_only
def exercise_create_formation_by_type(request, lecon_id, ex_type):
    from formation.models import FormationLesson
    fl = get_object_or_404(FormationLesson, id=lecon_id)
    return _handle_exercise_creation(request, None, fl, ex_type)
