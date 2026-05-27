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
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.gzip.GZipMiddleware',  # Compress responses
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
    if not DEBUG:
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured(
            "DATABASE_URL est requis en production. "
            "Ajoutez-la dans les variables d'environnement Railway."
        )
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


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



CSRF_TRUSTED_ORIGINS = [
    "https://*.railway.app",
]

# ── MENTORAT — Numéros de paiement Mobile Money ──────────────────────────────
MENTORAT_NUMEROS_PAIEMENT = [
    {'operateur': 'TMoney', 'numero': config('MENTORAT_TMONEY', default='+228 93 00 00 00'), 'emoji': '📱'},
    {'operateur': 'Flooz',  'numero': config('MENTORAT_FLOOZ',  default='+228 95 00 00 00'), 'emoji': '📱'},
]

# ── AUTHENTIFICATION ─────────────────────────────────────────────────────────
LOGIN_URL           = '/comptes/connexion/'
LOGIN_REDIRECT_URL  = '/comptes/tableau-de-bord/'
LOGOUT_REDIRECT_URL = '/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ── EMAIL ─────────────────────────────────────────────────────────────────────
# Email backend selection: 'smtp' (SMTP), 'gmail' (Gmail), 'mailgun', or 'console' (dev)
_email_service = config('EMAIL_SERVICE', default='smtp').lower()

if _email_service == 'mailgun':
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.mailgun.org'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = config('MAILGUN_SMTP_USER', default='')
    EMAIL_HOST_PASSWORD = config('MAILGUN_SMTP_PASSWORD', default='')
elif _email_service == 'gmail':
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.gmail.com'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = config('GMAIL_EMAIL', default='')
    EMAIL_HOST_PASSWORD = config('GMAIL_APP_PASSWORD', default='')
else:  # default SMTP
    EMAIL_BACKEND = config('EMAIL_BACKEND',
                            default='django.core.mail.backends.console.EmailBackend' if DEBUG else 'django.core.mail.backends.smtp.EmailBackend')
    EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
    EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
    EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
    EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='Numeria Institute <contact@numeriainstitute.com>')
CONTACT_EMAIL = config('CONTACT_EMAIL', default='contact@numeriainstitute.com')
ADMIN_EMAIL = config('ADMIN_EMAIL', default='admin@numeriainstitute.com')

# Email configuration for production
if not DEBUG:
    EMAIL_TIMEOUT = 10  # Timeout for email connections


# ── SÉCURITÉ AVANCÉE ─────────────────────────────────────────────────────────
# Rate limiting and DDoS protection
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'

# Content Security Policy
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "cdn.jsdelivr.net", "unpkg.com", "*.google.com", "*.gstatic.com")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "cdn.jsdelivr.net", "unpkg.com")
CSP_IMG_SRC = ("'self'", "data:", "https:")
CSP_FONT_SRC = ("'self'", "data:", "cdn.jsdelivr.net")
CSP_CONNECT_SRC = ("'self'", "cloudinary.com", "res.cloudinary.com")

# Security headers in production
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_SECURITY_POLICY = {
        'default-src': ("'self'",),
        'script-src': ("'self'", "cdn.jsdelivr.net", "unpkg.com"),
        'style-src': ("'self'", "cdn.jsdelivr.net", "unpkg.com"),
        'img-src': ("'self'", "data:", "https:"),
    }
    
    # Prevent clickjacking
    X_FRAME_OPTIONS = 'DENY'
    
    # Force HTTPS
    SECURE_SSL_REDIRECT = False  # Railway handles HTTPS
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


# ── SÉCURITÉ EN PRODUCTION ───────────────────────────────────────────────────
if not DEBUG:
    SECURE_SSL_REDIRECT     = False   # Railway gère HTTPS — évite la boucle
    SESSION_COOKIE_SECURE   = True
    CSRF_COOKIE_SECURE      = True
    LANGUAGE_COOKIE_SAMESITE = 'Lax'
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    _extra_csrf = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())
    if _extra_csrf:
        CSRF_TRUSTED_ORIGINS = _extra_csrf


# ── LOGGING — Écriture des erreurs vers stdout (visible dans Railway) ─────────
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
    },
}
