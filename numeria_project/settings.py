"""
Django settings for Numeria Institute.

Structure :
- Les valeurs sensibles viennent du fichier .env (dev) ou variables Railway (prod)
- En développement : SQLite + DEBUG=True + médias locaux
- En production    : PostgreSQL + DEBUG=False + médias sur Cloudinary
"""

from pathlib import Path
from decouple import config, Csv
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ImproperlyConfigured
import dj_database_url
import os
import re

# ── CHEMINS ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent


# ── SÉCURITÉ ───────────────────────────────────────────────────────────────
SECRET_KEY    = config('SECRET_KEY')
DEBUG         = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost', cast=Csv())


# ── CLOUDINARY — détection anticipée ──────────────────────────────────────
_cloudinary_raw   = config('CLOUDINARY_URL', default='').strip()
_cloudinary_match = re.match(r'cloudinary://([^:]+):([^@]+)@(.+)', _cloudinary_raw) if _cloudinary_raw else None
USE_CLOUDINARY    = bool(_cloudinary_match)


# ── APPLICATIONS ───────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'axes',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.sitemaps',
    'cloudinary',           # ← NOUVEAU : Doit être avant cloudinary_storage
    'cloudinary_storage',   # ← NOUVEAU : Doit être avant staticfiles
    'channels',
    'pages',
    'cours',
    'blog',
    'comptes',
    'paiements',
    'analytics',
    'admissions',
    'communaute',
    'mentorat',
    'formation',  # ← NOUVEAU: Formations payantes
]


# ── MIDDLEWARE ─────────────────────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'axes.middleware.AxesMiddleware',           # ← brute-force protection
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.gzip.GZipMiddleware',
]

ROOT_URLCONF = 'numeria_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
            ],
        },
    },
]

WSGI_APPLICATION = 'numeria_project.wsgi.application'
ASGI_APPLICATION = 'numeria_project.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

# ── BASE DE DONNÉES ─────────────────────────────────────────────────────────
DATABASE_URL = os.environ.get('DATABASE_URL') or config('DATABASE_URL', default='')

if DATABASE_URL and not DATABASE_URL.startswith('sqlite'):
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
            ssl_require=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
    if not DEBUG:
        import warnings
        warnings.warn(
            "DATABASE_URL n'est pas définie. En production, ajoutez-la dans les variables Railway.",
            RuntimeWarning,
            stacklevel=2,
        )


# ── TÉLÉCHARGEMENT DE FICHIERS ──────────────────────────────────────────────
DATA_UPLOAD_MAX_MEMORY_SIZE = 3 * 1024 * 1024  # 3MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 3 * 1024 * 1024  # 3MB


# ── VALIDATION DES MOTS DE PASSE ────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ── INTERNATIONALISATION ─────────────────────────────────────────────────────
LANGUAGE_CODE = 'fr'

LANGUAGES = [
    ('fr', _('Français')),
    ('en', _('English')),
]

TIME_ZONE  = 'Africa/Abidjan'
USE_I18N   = True
USE_L10N   = True
USE_TZ     = True

LOCALE_PATHS = [BASE_DIR / 'locale']


# ── FICHIERS STATIQUES ───────────────────────────────────────────────────────
STATIC_URL       = '/static/'
STATIC_ROOT      = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = []
# Django 6 uses STORAGES dict — configured below after Cloudinary detection


# ── CLOUDINARY — Configuration complète ──────────────────────────────────────
CLOUDINARY_URL = config('CLOUDINARY_URL', default='')

# Cloudinary reads CLOUDINARY_URL from os.environ at import time.
# If the value is missing or invalid, we unset it so the import doesn't crash.
_valid_cloudinary = bool(re.match(r'cloudinary://[^:]+:[^@]+@.+', CLOUDINARY_URL))
if not _valid_cloudinary:
    os.environ.pop('CLOUDINARY_URL', None)

import cloudinary

if CLOUDINARY_URL:
    # Parse l'URL Cloudinary
    match = re.match(r'cloudinary://([^:]+):([^@]+)@(.+)', CLOUDINARY_URL)
    if match:
        api_key, api_secret, cloud_name = match.groups()
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True  # Important pour HTTPS
        )
        
        # Configuration pour le stockage
        CLOUDINARY_STORAGE = {
            'CLOUDINARY_URL': CLOUDINARY_URL,
            'CLOUDINARY_API_KEY': api_key,
            'CLOUDINARY_API_SECRET': api_secret,
            'CLOUDINARY_CLOUD_NAME': cloud_name,
        }

# ── STORAGES — Django 6 format (DEFAULT_FILE_STORAGE/STATICFILES_STORAGE are removed) ──
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL  = '/media/'

if not DEBUG and USE_CLOUDINARY:
    STORAGES = {
        "default": {
            "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
        },
    }
else:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
        },
    }



CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='https://web-production-8bcf4.up.railway.app',
    cast=Csv(),
)

# ── MENTORAT — Numéros de paiement Mobile Money ──────────────────────────────
MENTORAT_NUMEROS_PAIEMENT = [
    {'operateur': 'TMoney', 'numero': config('MENTORAT_TMONEY', default='+228 93 00 00 00'), 'emoji': '📱'},
    {'operateur': 'Flooz',  'numero': config('MENTORAT_FLOOZ',  default='+228 95 00 00 00'), 'emoji': '📱'},
]

# ── AUTHENTIFICATION ─────────────────────────────────────────────────────────
LOGIN_URL           = '/comptes/connexion/'
LOGIN_REDIRECT_URL  = '/comptes/tableau-de-bord/'
LOGOUT_REDIRECT_URL = '/'

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# django-axes — brute-force login protection
AXES_FAILURE_LIMIT         = 5
AXES_COOLOFF_TIME          = 1           # lock for 1 hour after 5 failures
AXES_LOCKOUT_TEMPLATE      = 'comptes/locked.html'
AXES_RESET_ON_SUCCESS      = True
AXES_ENABLE_ADMIN          = False       # keep admin unaffected

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── RATE LIMITING ─────────────────────────────────────────────────────────────
RATELIMIT_ENABLE    = True
RATELIMIT_USE_CACHE = 'default'


# ── EMAIL ─────────────────────────────────────────────────────────────────────
# Email backend selection: 'smtp', 'gmail', 'mailgun', 'brevo' or 'console'
EMAIL_SERVICE = config('EMAIL_SERVICE', default='smtp').strip().lower()


def _require_email_setting(name, value, service_name):
    if not value:
        raise ImproperlyConfigured(
            f"EMAIL_SERVICE={service_name} requires {name} to be set in the environment."
        )
    return value

if EMAIL_SERVICE == 'mailgun':
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.mailgun.org'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = _require_email_setting('MAILGUN_SMTP_USER', config('MAILGUN_SMTP_USER', default=''), 'mailgun')
    EMAIL_HOST_PASSWORD = _require_email_setting('MAILGUN_SMTP_PASSWORD', config('MAILGUN_SMTP_PASSWORD', default=''), 'mailgun')
elif EMAIL_SERVICE == 'gmail':
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.gmail.com'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = _require_email_setting('GMAIL_EMAIL', config('GMAIL_EMAIL', default=''), 'gmail')
    EMAIL_HOST_PASSWORD = _require_email_setting('GMAIL_APP_PASSWORD', config('GMAIL_APP_PASSWORD', default=''), 'gmail')
elif EMAIL_SERVICE == 'brevo':
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = config('EMAIL_HOST', default='smtp-relay.brevo.com')
    EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
    EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
    EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=False, cast=bool)
    EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='apikey')
    EMAIL_HOST_PASSWORD = _require_email_setting('EMAIL_HOST_PASSWORD', config('EMAIL_HOST_PASSWORD', default=''), 'brevo')
elif EMAIL_SERVICE == 'console':
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    EMAIL_HOST = config('EMAIL_HOST', default='')
    EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
    EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
    EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
elif EMAIL_SERVICE == 'smtp':
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
    EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
    EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
    EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
else:
    EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
    EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
    EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
    EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
    EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='Numeria Institute <numeriainstitude@gmail.com>')
CONTACT_EMAIL = config('CONTACT_EMAIL', default='numeriainstitude@gmail.com')
ADMIN_EMAIL = config('ADMIN_EMAIL', default='admin@numeriainstitute.com')
EMAIL_TIMEOUT = config('EMAIL_TIMEOUT', default=10, cast=int)


# ── SÉCURITÉ — EN-TÊTES ───────────────────────────────────────────────────────
X_FRAME_OPTIONS             = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY      = 'strict-origin-when-cross-origin'
SESSION_COOKIE_HTTPONLY     = True
SESSION_COOKIE_SAMESITE     = 'Lax'

# Railway terminates TLS at the edge — never redirect here (would loop).
# W008 is silenced because HTTPS enforcement is Railway's responsibility.
SECURE_SSL_REDIRECT     = False
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# HSTS — tell browsers to only connect via HTTPS for 1 year
SECURE_HSTS_SECONDS           = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD           = True

# Secure cookies — True in production (DEBUG=False), relaxed locally
SESSION_COOKIE_SECURE    = not DEBUG
CSRF_COOKIE_SECURE       = not DEBUG
LANGUAGE_COOKIE_SAMESITE = 'Lax'

SILENCED_SYSTEM_CHECKS = ['security.W008']  # SECURE_SSL_REDIRECT=False is intentional

# ── ERREURS — notification silencieuse ───────────────────────────────────────
ADMINS      = [('Roland', config('ADMIN_EMAIL', default='numeriainstitude@gmail.com'))]
SERVER_EMAIL = config('DEFAULT_FROM_EMAIL', default='Numeria Institute <numeriainstitude@gmail.com>')

# ── LOGGING — stdout pour Railway, security + axes auditables ─────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': True,
        },
        'axes': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': True,
        },
    },
}
