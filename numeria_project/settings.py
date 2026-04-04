"""
Django settings for Numeria Institute.

Structure :
- Les valeurs sensibles viennent du fichier .env
- En développement : SQLite + DEBUG=True
- En production : PostgreSQL + DEBUG=False
"""

from pathlib import Path
from decouple import config, Csv
import dj_database_url
import os

# ── CHEMINS ────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent


# ── SÉCURITÉ ───────────────────────────────────────────────────────
# Lire depuis .env — jamais en dur dans le code
SECRET_KEY = config('SECRET_KEY')

# True en développement, False en production
DEBUG = config('DEBUG', default=False, cast=bool)

# Hôtes autorisés — séparés par des virgules dans .env
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost', cast=Csv())


# ── APPLICATIONS ───────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Nos applications
    'pages',
    'cours',
    'blog',
    'comptes',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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
            ],
        },
    },
]

WSGI_APPLICATION = 'numeria_project.wsgi.application'


# ── BASE DE DONNÉES ────────────────────────────────────────────────
# En développement : SQLite
# En production : PostgreSQL (défini dans DATABASE_URL)
USE_POSTGRES = config('USE_POSTGRES', default=False, cast=bool)

if USE_POSTGRES:
    # PostgreSQL — pour la production
    DATABASES = {
        'default': dj_database_url.config(
            default=config('DATABASE_URL'),
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    # SQLite — pour le développement local
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# ── VALIDATION DES MOTS DE PASSE ──────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ── INTERNATIONALISATION ───────────────────────────────────────────
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Abidjan'
USE_I18N = True
USE_TZ = True


# ── FICHIERS STATIQUES ─────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = []


# ── FICHIERS MÉDIAS (uploads) ──────────────────────────────────────
MEDIA_URL = config('MEDIA_URL', default='/media/')
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# ── AUTHENTIFICATION ───────────────────────────────────────────────
LOGIN_URL = '/comptes/connexion/'
LOGIN_REDIRECT_URL = '/comptes/tableau-de-bord/'
LOGOUT_REDIRECT_URL = '/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ── EMAIL ──────────────────────────────────────────────────────────
EMAIL_BACKEND = config(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.console.EmailBackend'
)
EMAIL_HOST = config('EMAIL_HOST', default='localhost')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = 'Numeria Institute <contact@numeriainstitute.com>'
CONTACT_EMAIL = config('CONTACT_EMAIL', default='contact@numeriainstitute.com')


# ── SÉCURITÉ EN PRODUCTION ─────────────────────────────────────────
if not DEBUG:
    # HTTPS obligatoire en production
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True