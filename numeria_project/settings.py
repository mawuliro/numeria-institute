"""
Django settings for Numeria Institute.

Structure :
- Les valeurs sensibles viennent du fichier .env (dev) ou variables Railway (prod)
- En développement : SQLite + DEBUG=True + médias locaux
- En production    : PostgreSQL + DEBUG=False + médias sur Cloudinary
"""

from pathlib import Path
from decouple import config, Csv
import dj_database_url
import os

# ── CHEMINS ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent


# ── SÉCURITÉ ───────────────────────────────────────────────────────────────
SECRET_KEY    = config('SECRET_KEY')
DEBUG         = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost', cast=Csv())


# ── CLOUDINARY (déclaré ici une seule fois, avant INSTALLED_APPS) ──────────
CLOUDINARY_URL = config('CLOUDINARY_URL', default='')


# ── APPLICATIONS ───────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'cloudinary_storage',        # ← DOIT être avant staticfiles
    'cloudinary',
    'django.contrib.staticfiles',
    'pages',
    'cours',
    'blog',
    'comptes',
    'paiements',
]


# ── MIDDLEWARE ─────────────────────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
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


# ── BASE DE DONNÉES ─────────────────────────────────────────────────────────
# Railway injecte DATABASE_URL automatiquement en production
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


# ── VALIDATION DES MOTS DE PASSE ────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ── INTERNATIONALISATION ─────────────────────────────────────────────────────
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE     = 'Africa/Abidjan'
USE_I18N      = True
USE_TZ        = True


# ── FICHIERS STATIQUES (CSS, JS) ─────────────────────────────────────────────
STATIC_URL       = '/static/'
STATIC_ROOT      = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = []

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# ── FICHIERS MÉDIAS ──────────────────────────────────────────
CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL', '') or config('CLOUDINARY_URL', default='')

if CLOUDINARY_URL.strip():
    import cloudinary
    cloudinary.config(cloudinary_url=CLOUDINARY_URL)
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
    CLOUDINARY_STORAGE = {'CLOUDINARY_URL': CLOUDINARY_URL}
else:
    MEDIA_URL  = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# ── AUTHENTIFICATION ─────────────────────────────────────────────────────────
LOGIN_URL          = '/comptes/connexion/'
LOGIN_REDIRECT_URL = '/comptes/tableau-de-bord/'
LOGOUT_REDIRECT_URL = '/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ── EMAIL ─────────────────────────────────────────────────────────────────────
EMAIL_BACKEND     = config('EMAIL_BACKEND',
                            default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST        = config('EMAIL_HOST',        default='smtp.gmail.com')
EMAIL_PORT        = config('EMAIL_PORT',        default=587, cast=int)
EMAIL_USE_TLS     = config('EMAIL_USE_TLS',     default=True, cast=bool)
EMAIL_HOST_USER   = config('EMAIL_HOST_USER',   default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL  = 'Numeria Institute <contact@numeriainstitute.com>'
CONTACT_EMAIL       = config('CONTACT_EMAIL', default='contact@numeriainstitute.com')


# ── SÉCURITÉ EN PRODUCTION ───────────────────────────────────────────────────
if not DEBUG:
    # Railway gère déjà HTTPS — redirection forcée désactivée
    # pour éviter la boucle de redirections
    SECURE_SSL_REDIRECT = False

    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE    = True

    # Faire confiance au proxy de Railway
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

    CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())