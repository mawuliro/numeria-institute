import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import strip_tags
from django.utils import translation

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


def send_verification_email(request, user, language=None):
    if not user.email:
        logger.warning('send_verification_email: utilisateur sans email %s', user.pk)
        return

    language = _get_language(language or getattr(request, 'LANGUAGE_CODE', None))
    token = make_email_verification_token(user)
    verification_url = request.build_absolute_uri(reverse('comptes:verify_email', args=[token]))
    logger.info('send_verification_email: sending to %s, url=%s', user.email, verification_url)
    subject = 'Confirm your Numeria account' if language == 'en' else 'Confirme ton compte Numeria'
    html_body = _render_template(
        f'emails/verify_email_{language}.html',
        {
            'user': user,
            'verification_url': verification_url,
            'site_name': 'Numeria Institute',
        },
        language=language,
    )
    text_content = strip_tags(html_body)
    try:
        _send_html_email(subject, text_content, html_body, [user.email])
        logger.info('send_verification_email: sent OK to %s', user.email)
    except Exception as e:
        logger.error('send_verification_email: FAILED for %s — %s', user.email, e)
        raise


def send_welcome_email(request, user, language=None):
    if not user.email:
        logger.warning('send_welcome_email: utilisateur sans email %s', user.pk)
        return

    language = _get_language(language or getattr(request, 'LANGUAGE_CODE', None))
    subject = 'Welcome to Numeria Institute!' if language == 'en' else 'Bienvenue sur Numeria Institute !'
    html_body = _render_template(
        f'emails/welcome_email_{language}.html',
        {
            'user': user,
            'cours_url': request.build_absolute_uri(reverse('cours:catalogue')),
            'site_name': 'Numeria Institute',
        },
        language=language,
    )
    text_content = strip_tags(html_body)
    _send_html_email(subject, text_content, html_body, [user.email])


def send_course_enrollment_email(user, cours, language=None):
    if not user.email:
        logger.warning('send_course_enrollment_email: utilisateur sans email %s', user.pk)
        return

    language = _get_language(language)
    subject = 'Course enrollment confirmed' if language == 'en' else f'Inscription au cours « {cours.titre} » confirmée'
    html_body = _render_template(
        f'emails/course_enrollment_{language}.html',
        {
            'user': user,
            'cours': cours,
            'site_name': 'Numeria Institute',
        },
        language=language,
    )
    text_content = strip_tags(html_body)
    _send_html_email(subject, text_content, html_body, [user.email])


def send_contact_form_emails(request, name, email, organisation, subject, message, is_partner=False, language=None):
    language = _get_language(language or getattr(request, 'LANGUAGE_CODE', None))
    admin_subject = f"[Numeria] Nouveau message : {subject} — {name}"
    admin_body = (
        f"Nouveau message depuis le site Numeria Institute\n\n"
        f"De : {name}\n"
        f"Email : {email}\n"
        f"Organisation : {organisation or 'Non renseignée'}\n"
        f"Sujet : {subject}\n"
        f"Partenariat : {'Oui' if is_partner else 'Non'}\n\n"
        f"Message :\n{message}\n"
        "\n---\nNumeria Institute"
    )
    send_mail(admin_subject, admin_body, settings.DEFAULT_FROM_EMAIL, [settings.CONTACT_EMAIL], fail_silently=False)

    html_body = _render_template(
        f'emails/contact_autoreply_{language}.html',
        {
            'name': name,
            'subject': subject,
            'organisation': organisation,
            'is_partner': is_partner,
            'site_name': 'Numeria Institute',
        },
        language=language,
    )
    text_content = strip_tags(html_body)
    user_subject = 'We received your message' if language == 'en' else 'Nous avons bien reçu votre message'
    _send_html_email(user_subject, text_content, html_body, [email])


def send_candidacy_acceptance_email(candidature, language=None):
    user = candidature.utilisateur
    if not user.email:
        logger.warning('send_candidacy_acceptance_email: utilisateur sans email %s', user.pk)
        return

    language = _get_language(language)
    subject = 'Your application has been accepted' if language == 'en' else 'Ta candidature a été acceptée'
    html_body = _render_template(
        f'emails/candidacy_accepted_{language}.html',
        {'candidature': candidature, 'site_name': 'Numeria Institute'},
        language=language,
    )
    text_content = strip_tags(html_body)
    _send_html_email(subject, text_content, html_body, [user.email])


def send_mentorship_acceptance_email(demande, language=None):
    user = demande.mentee.profil.utilisateur
    if not user.email:
        logger.warning('send_mentorship_acceptance_email: utilisateur sans email %s', user.pk)
        return

    language = _get_language(language)
    subject = 'Your mentoring request has been accepted' if language == 'en' else 'Ta demande de mentorat a été acceptée'
    html_body = _render_template(
        f'emails/mentorship_accepted_{language}.html',
        {'demande': demande, 'site_name': 'Numeria Institute'},
        language=language,
    )
    text_content = strip_tags(html_body)
    _send_html_email(subject, text_content, html_body, [user.email])
