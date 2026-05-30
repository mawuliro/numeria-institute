import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import strip_tags
from django.utils import translation
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

User = get_user_model()
EMAIL_VERIFICATION_SALT = 'numeria_email_verification'
EMAIL_VERIFICATION_MAX_AGE = 60 * 60 * 24


def _get_language(language):
    language = language or getattr(settings, 'LANGUAGE_CODE', 'fr')
    return language[:2]


def _render_template(template_name, context, language=None):
    language = _get_language(language)
    with translation.override(language):
        return render_to_string(template_name, context)


def _send_html_email(subject, text_content, html_content, recipient_list, from_email=None):
    from_email = from_email or settings.DEFAULT_FROM_EMAIL
    message = EmailMultiAlternatives(subject, text_content, from_email, recipient_list)
    if html_content:
        message.attach_alternative(html_content, 'text/html')
    message.send(fail_silently=False)


def make_email_verification_token(user):
    return signing.dumps({'user_id': user.pk}, salt=EMAIL_VERIFICATION_SALT)


def verify_email_token(token):
    data = signing.loads(token, salt=EMAIL_VERIFICATION_SALT, max_age=EMAIL_VERIFICATION_MAX_AGE)
    user_id = data.get('user_id')
    if not user_id:
        raise ValueError('Jeton de vérification invalide.')
    return User.objects.get(pk=user_id)


# ─── TRANSACTIONAL EMAILS (Gmail SMTP) ────────────────────────────────────────

def send_payment_confirmation_email(user, payment):
    """
    Send a payment receipt email after a successful payment.
    Called from paiements/views.py when a payment is confirmed.
    """
    if not user.email:
        logger.warning('send_payment_confirmation_email: user %s has no email', user.pk)
        return
    try:
        subject = 'Confirmation de paiement — Numeria Institute'
        if payment.cours:
            item_name = payment.cours.titre
        elif payment.formation_inscription:
            item_name = (
                f"{payment.formation_inscription.session.formation.titre}"
                f" — {payment.formation_inscription.session.nom}"
            )
        else:
            item_name = 'Paiement Numeria'
        html_body = render_to_string('emails/payment_confirmation.html', {
            'user': user,
            'payment': payment,
            'item_name': item_name,
            'site_name': 'Numeria Institute',
        })
        text_content = strip_tags(html_body)
        _send_html_email(subject, text_content, html_body, [user.email])
        logger.info('send_payment_confirmation_email: sent OK to %s', user.email)
    except Exception as e:
        logger.error('send_payment_confirmation_email: FAILED for %s — %s', user.email, e)


def send_candidacy_acceptance_email(candidature, language=None):
    """
    Send an acceptance email when an admin accepts a candidacy application.
    Called from admissions/views.py.
    """
    user = candidature.utilisateur
    if not user.email:
        logger.warning('send_candidacy_acceptance_email: user %s has no email', user.pk)
        return
    try:
        language = _get_language(language)
        subject = (
            'Your application has been accepted'
            if language == 'en'
            else 'Ta candidature a été acceptée — Numeria Institute'
        )
        html_body = _render_template(
            f'emails/candidacy_accepted_{language}.html',
            {'candidature': candidature, 'site_name': 'Numeria Institute'},
            language=language,
        )
        text_content = strip_tags(html_body)
        _send_html_email(subject, text_content, html_body, [user.email])
        logger.info('send_candidacy_acceptance_email: sent OK to %s', user.email)
    except Exception as e:
        logger.error('send_candidacy_acceptance_email: FAILED for %s — %s', user.email, e)


def send_mentorship_acceptance_email(demande, language=None):
    """
    Notify the mentee that their mentorship request was accepted.
    Called from mentorat/views.py when a mentor accepts a request.
    """
    mentee_user = demande.mentee.profil.utilisateur
    if not mentee_user.email:
        logger.warning('send_mentorship_acceptance_email: user %s has no email', mentee_user.pk)
        return
    try:
        language = _get_language(language)
        subject = (
            'Your mentoring request has been accepted'
            if language == 'en'
            else 'Ta demande de mentorat a été acceptée — Numeria Institute'
        )
        html_body = _render_template(
            f'emails/mentorship_accepted_{language}.html',
            {'demande': demande, 'site_name': 'Numeria Institute'},
            language=language,
        )
        text_content = strip_tags(html_body)
        _send_html_email(subject, text_content, html_body, [mentee_user.email])
        logger.info('send_mentorship_acceptance_email: sent OK to %s', mentee_user.email)
    except Exception as e:
        logger.error('send_mentorship_acceptance_email: FAILED for %s — %s', mentee_user.email, e)


def send_mentorship_confirmation_to_mentor(mentor, mentee, language=None):
    """
    Notify the mentor when a mentee accepts their invitation.
    """
    mentor_user = mentor.profil.utilisateur
    if not mentor_user.email:
        logger.warning('send_mentorship_confirmation_to_mentor: user %s has no email', mentor_user.pk)
        return
    try:
        language = _get_language(language)
        subject = (
            'A mentee accepted your invitation'
            if language == 'en'
            else 'Un mentoré a accepté votre invitation — Numeria Institute'
        )
        html_body = render_to_string('emails/mentorship_confirmation_mentor.html', {
            'mentor': mentor,
            'mentee': mentee,
            'site_name': 'Numeria Institute',
        })
        text_content = strip_tags(html_body)
        _send_html_email(subject, text_content, html_body, [mentor_user.email])
        logger.info('send_mentorship_confirmation_to_mentor: sent OK to %s', mentor_user.email)
    except Exception as e:
        logger.error(
            'send_mentorship_confirmation_to_mentor: FAILED for %s — %s', mentor_user.email, e
        )


def send_candidacy_rejection_email(user, programme_name, rejection_reason=None, language=None):
    """
    Send a polite rejection email when an admin rejects a candidacy.
    Called from admin_panel/views.py.
    """
    if not user.email:
        logger.warning('send_candidacy_rejection_email: user %s has no email', user.pk)
        return
    try:
        language = _get_language(language)
        subject = (
            'Your application result — Numeria Institute'
            if language == 'en'
            else 'Résultat de votre candidature — Numeria Institute'
        )
        html_body = _render_template(
            f'emails/candidacy_rejection_{language}.html',
            {
                'user': user,
                'programme_name': programme_name,
                'rejection_reason': rejection_reason,
                'site_name': 'Numeria Institute',
            },
            language=language,
        )
        text_content = strip_tags(html_body)
        _send_html_email(subject, text_content, html_body, [user.email])
        logger.info('send_candidacy_rejection_email: sent OK to %s', user.email)
    except Exception as e:
        logger.error('send_candidacy_rejection_email: FAILED for %s — %s', user.email, e)


def send_contact_reply_email(to_email, to_name, subject, reply_message, staff_name):
    """
    Send a reply email to a contact message sender.
    Called from admin_panel/views.py when staff replies to a contact message.
    """
    if not to_email:
        return
    try:
        html_body = render_to_string('emails/contact_reply.html', {
            'to_name': to_name,
            'subject': subject,
            'reply_message': reply_message,
            'staff_name': staff_name,
            'site_name': 'Numeria Institute',
        })
        text_content = strip_tags(html_body)
        _send_html_email(subject, text_content, html_body, [to_email])
        logger.info('send_contact_reply_email: sent OK to %s', to_email)
    except Exception as e:
        logger.error('send_contact_reply_email: FAILED for %s — %s', to_email, e)
        raise


def send_mentor_application_approval_email(application, language=None):
    if not application.profil.utilisateur.email:
        logger.warning('send_mentor_application_approval_email: user %s has no email', application.profil.utilisateur.pk)
        return
    try:
        language = _get_language(language)
        subject = (
            'Mentor application approved — Numeria Institute'
            if language == 'en'
            else 'Votre candidature mentor a été approuvée — Numeria Institute'
        )
        html_body = _render_template(
            f'emails/mentor_application_approved_{language}.html',
            {
                'application': application,
                'site_name': 'Numeria Institute',
            },
            language=language,
        )
        text_content = strip_tags(html_body)
        _send_html_email(subject, text_content, html_body, [application.profil.utilisateur.email])
        logger.info('send_mentor_application_approval_email: sent OK to %s', application.profil.utilisateur.email)
    except Exception as e:
        logger.error('send_mentor_application_approval_email: FAILED for %s — %s', application.profil.utilisateur.email, e)


def send_mentor_application_rejection_email(application, language=None):
    if not application.profil.utilisateur.email:
        logger.warning('send_mentor_application_rejection_email: user %s has no email', application.profil.utilisateur.pk)
        return
    try:
        language = _get_language(language)
        subject = (
            'Mentor application decision — Numeria Institute'
            if language == 'en'
            else 'Résultat de votre candidature mentor — Numeria Institute'
        )
        html_body = _render_template(
            f'emails/mentor_application_rejected_{language}.html',
            {
                'application': application,
                'site_name': 'Numeria Institute',
            },
            language=language,
        )
        text_content = strip_tags(html_body)
        _send_html_email(subject, text_content, html_body, [application.profil.utilisateur.email])
        logger.info('send_mentor_application_rejection_email: sent OK to %s', application.profil.utilisateur.email)
    except Exception as e:
        logger.error('send_mentor_application_rejection_email: FAILED for %s — %s', application.profil.utilisateur.email, e)


def send_welcome_email(request, user, language=None):
    """No longer called — removed from registration flow."""
    pass


def send_course_enrollment_email(user, cours, language=None):
    """No longer called — replaced by in-app notification."""
    pass


def send_contact_form_emails(request, name, email, organisation, subject, message,
                              is_partner=False, language=None):
    """No longer called — contact form now saves to DB only."""
    pass
