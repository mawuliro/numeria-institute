# 🎓 Numeria Institute — Version Django

> Version originale de la plateforme Numeria Institute, construite avec Django + Django REST Framework.
> Ce dépôt documente l'architecture qui a ensuite été migrée vers Next.js 16.

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![Django](https://img.shields.io/badge/Django-4.2-green)](https://djangoproject.com)
[![DRF](https://img.shields.io/badge/DRF-3.14-red)](https://www.django-rest-framework.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue)](https://postgresql.org)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

> **Note** : Cette version a été **migrée vers Next.js**.
> Le projet actif est désormais : <https://github.com/mawuliro/numeriainstitute>
> Ce dépôt est conservé à des fins d'archivage et de référence.

---

## 📖 Sommaire

- [Contexte](#contexte)
- [Stack technique](#stack-technique)
- [Architecture](#architecture)
- [Installation](#installation)
- [Structure du projet](#structure-du-projet)
- [Modèles de données](#modèles-de-données)
- [API REST](#api-rest)
- [Templates & Frontend](#templates--frontend)
- [Migration vers Next.js](#migration-vers-nextjs)
- [Licence](#licence)

---

## Contexte

Numeria Institute a démarré comme une application **Django** en 2024, avant d'être migrée vers **Next.js 16** en 2026 pour des raisons de performance (cold start, serverless) et d'expérience utilisateur (React Server Components, interactivité temps réel).

Cette version Django reste **fonctionnelle** et documente le modèle de données original qui a été transposé vers Prisma dans la version Next.js.

### Pourquoi Django au départ ?

- **Écosystème mature** : Django ORM, admin auto-générée, auth, i18n intégrés
- **Python partout** : scripts de seed, calculs scientifiques (NumPy, SciPy), notebooks Jupyter intégrables
- **DRF** : API REST propre pour une future app mobile
- **Stabilité** : Django 4.2 LTS, documentation excellente

### Pourquoi la migration vers Next.js ?

- **Cold start Python** : ~5 s sur Vercel serverless (vs ~50 ms pour Node.js)
- **SEO** : Next.js fait du SSR/SSG natif, Django nécessite Django SSR + CDN
- **Interactivité** : React + Server Actions > Django Templates + HTMX
- **Tailwind + shadcn/ui** : design system plus moderne que Bootstrap 5
- **Edge runtime** : middleware 50 ms vs Django middleware 5 s

---

## Stack technique

| Catégorie | Technologie |
|---|---|
| **Framework** | Django 4.2 LTS |
| **API** | Django REST Framework 3.14 |
| **DB** | PostgreSQL 15 + psycopg2 |
| **Auth** | Django auth + JWT (SimpleJWT) |
| **Templates** | Django Templates + Jinja2 |
| **CSS** | Bootstrap 5 + Bootstrap Icons |
| **JS** | Vanilla JS + HTMX (interactivité) |
| **Math rendering** | MathJax (CDN) |
| **Code highlighting** | Prism.js |
| **Forms** | Django Forms + Crispy Forms |
| **i18n** | Django i18n (gettext) |
| **Async tasks** | Celery + Redis |
| **Storage** | Django Storage + S3 (production) |
| **Server** | Gunicorn + Nginx (production) |

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Navigateur (Client)                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  HTML rendu par Django Templates                 │  │
│  │  • Bootstrap 5 + Bootstrap Icons                 │  │
│  │  • HTMX pour interactivité (sans rechargement)   │  │
│  │  • MathJax pour le LaTeX                         │  │
│  └──────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
                            │
                            ▼ (HTTP)
┌──────────────────────────────────────────────────────────┐
│              Nginx (Reverse Proxy + Static)            │
│  • Sert les fichiers statiques (CSS, JS, images)        │
│  • SSL termination                                       │
│  • Rate limiting                                         │
└──────────────────────────────────────────────────────────┘
                            │
                            ▼ (WSGI/ASGI)
┌──────────────────────────────────────────────────────────┐
│              Gunicorn (WSGI workers, Python)            │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Django 4.2                                      │  │
│  │  • URL routing                                   │  │
│  │  • Middleware (auth, CSRF, sessions)             │  │
│  │  • Views (function-based + class-based)          │  │
│  │  • Django ORM (PostgreSQL)                       │  │
│  │  • Django REST Framework (API)                   │  │
│  │  • Templates rendering                          │  │
│  └──────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│     PostgreSQL 15        │  │      Redis + Celery       │
│  • 27 tables             │  │  • Tasks async             │
│  • Django migrations     │  │  • Email queue             │
│  • Indexes               │  │  • Notifications           │
└──────────────────────────┘  └──────────────────────────┘
```

---

## Installation

### Prérequis

- **Python 3.10+**
- **PostgreSQL 15+** (ou Docker)
- **Redis** (pour Celery — optionnel en dev)
- **virtualenv** ou **conda**

### Étapes

```bash
# 1. Cloner le dépôt
git clone https://github.com/mawuliro/numeriainstitute-django.git
cd numeriainstitute-django

# 2. Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/macOS
# ou : venv\Scripts\activate  # Windows

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer les variables d'environnement
cp .env.example .env
# Édite .env :
#   DEBUG=True
#   SECRET_KEY=une-chaîne-aléatoire
#   DATABASE_URL=postgres://user:pass@localhost:5432/numeria
#   ALLOWED_HOSTS=localhost,127.0.0.1
#   EMAIL_HOST_USER=...
#   EMAIL_HOST_PASSWORD=...

# 5. Migrations
python manage.py migrate

# 6. Créer un superuser
python manage.py createsuperuser

# 7. (Optionnel) Seed les données initiales
python manage.py seed_courses

# 8. Lancer le serveur de dev
python manage.py runserver
```

Ouvre <http://localhost:8000> — c'est prêt ! 🎉

### Production

```bash
# Collecter les fichiers statiques
python manage.py collectstatic --noinput

# Lancer avec Gunicorn
gunicorn numeria.wsgi:application --bind 0.0.0.0:8000 --workers 4

# Optionnel : Daphne (ASGI, pour WebSockets)
daphne numeria.asgi:application --bind 0.0.0.0:8000
```

---

## Structure du projet

```
numeriainstitute-django/
├── numeria/                     # Projet Django principal
│   ├── settings.py              # Configuration (env-based)
│   ├── urls.py                  # Routes racines
│   ├── wsgi.py                  # WSGI entry point
│   ├── asgi.py                  # ASGI entry point (WebSockets)
│   └── celery.py                # Celery configuration
├── accounts/                    # App : auth, profils, permissions
│   ├── models.py                # User (custom), Profile, Role
│   ├── views.py                 # Login, signup, password reset
│   ├── forms.py                 # UserForm, SignupForm
│   ├── urls.py
│   └── migrations/
├── courses/                     # App : cours, modules, leçons
│   ├── models.py                # Course, Module, Lesson, Block
│   ├── admin.py                 # Admin auto-générée
│   ├── views.py                 # ListView, DetailView
│   ├── serializers.py           # DRF serializers
│   ├── urls.py
│   └── migrations/
├── exercises/                   # App : exercices (MCQ, fill-blank, etc.)
│   ├── models.py                # MCQ, Choice, FillBlank, TrueFalse, CodeEx
│   ├── views.py
│   └── ...
├── progress/                    # App : suivi de progression
│   ├── models.py                # LessonProgress, ExerciseProgress
│   └── ...
├── blog/                        # App : articles de blog
├── community/                   # App : forum (sujets, posts)
├── meetings/                    # App : visioconférence (Daily.co)
├── gamification/                # App : badges, streaks, XP
├── notifications/               # App : notifications in-app
├── templates/                   # Templates HTML (Django Templates)
│   ├── base.html                # Layout de base (Bootstrap 5)
│   ├── accounts/
│   ├── courses/
│   ├── blog/
│   └── ...
├── static/                      # Fichiers statiques
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   ├── main.js
│   │   └── htmx.min.js
│   └── img/
├── media/                       # Uploads utilisateurs (avatars, etc.)
├── requirements.txt
├── manage.py
├── .env.example
└── README.md
```

---

## Modèles de données

Le schéma Django comprend **27 modèles** organisés en 9 apps. La structure a été fidèlement transposée vers Prisma lors de la migration Next.js.

### Apps & modèles

#### `accounts` — Authentification

```python
class User(AbstractUser):
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    avatar = models.ImageField(upload_to='avatars/', null=True)
    bio = models.TextField(blank=True)
    preferred_language = models.CharField(max_length=2, default='fr')
    is_verified = models.BooleanField(default=False)
    failed_login_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True)
```

#### `courses` — Cours & contenu

- `Course` (slug, title, description, level, category, is_free, price)
- `CourseModule` (FK Course, title, order)
- `CourseLesson` (FK Module, title, slug, estimated_minutes, is_free_preview)
- `LessonBlock` (FK Lesson, polymorphic : text / sandbox / mcq / lab)

#### `exercises` — Exercices

- `MCQExercise` + `MCQChoice`
- `FillBlankExercise` (text_with_blanks + answers_json)
- `TrueFalseExercise` (statements_json)
- `CodeExercise` (starter_code + solution + test_code)
- `InteractiveLab` (simulation_code + slider_config + challenges)

#### `progress` — Suivi

- `Enrollment` (FK User + Course)
- `LessonProgress` (is_completed, completed_at)
- `ExerciseProgress` (is_solved, attempts_used)

#### `blog` — Blog

- `BlogPost` (title, slug, content, is_published, published_at)

#### `community` — Forum

- `CommunityTopic` (title, course, is_pinned, is_locked, views)
- `CommunityPost` (content, author)

#### `meetings` — Visioconférence

- `Meeting` (title, room_name, host, start_time, is_waiting_room_enabled)
- `MeetingParticipant` (status: waiting/admitted/left)

#### `gamification` — Gamification

- `UserBadge` (badge_type: first_lesson, course_complete, streak_7, etc.)
- `UserStreak` (current_streak, longest_streak, total_xp)

#### `notifications` — Notifications in-app

- `Notification` (title, message, link, is_read)

---

## API REST

L'API expose les endpoints CRUD principaux via Django REST Framework.

### Endpoints publics

| Méthode | URL | Description |
|---|---|---|
| `GET` | `/api/courses/` | Liste des cours publiés |
| `GET` | `/api/courses/{slug}/` | Détail d'un cours |
| `GET` | `/api/courses/{slug}/lessons/` | Liste des leçons |
| `GET` | `/api/blog/` | Articles de blog publiés |
| `GET` | `/api/blog/{slug}/` | Détail d'un article |
| `POST` | `/api/auth/login/` | Connexion (JWT) |
| `POST` | `/api/auth/signup/` | Inscription |
| `POST` | `/api/contact/` | Formulaire de contact |

### Endpoints authentifiés

| Méthode | URL | Description |
|---|---|---|
| `GET` | `/api/me/` | Profil utilisateur courant |
| `PATCH` | `/api/me/` | Mise à jour du profil |
| `GET` | `/api/me/progress/` | Progression de l'utilisateur |
| `POST` | `/api/courses/{id}/enroll/` | Inscription à un cours |
| `POST` | `/api/lessons/{id}/complete/` | Marquer une leçon terminée |
| `POST` | `/api/exercises/{id}/submit/` | Soumettre une réponse à un exercice |

### Endpoints admin (role STAFF/ADMIN)

| Méthode | URL | Description |
|---|---|---|
| `GET/POST/PATCH/DELETE` | `/api/admin/courses/` | CRUD cours |
| `GET/POST/PATCH/DELETE` | `/api/admin/users/` | CRUD utilisateurs |
| `GET/POST/PATCH/DELETE` | `/api/admin/blog/` | CRUD blog |
| `GET` | `/api/admin/stats/` | Statistiques dashboard |

### Authentification API

JWT via `djangorestframework-simplejwt` :

```bash
# Obtenir un token
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "...", "password": "..."}'

# Réponse :
# {"access": "eyJ...", "refresh": "..."}

# Utiliser le token
curl http://localhost:8000/api/me/ \
  -H "Authorization: Bearer eyJ..."
```

---

## Templates & Frontend

### Stack frontend

- **Bootstrap 5** : grille, composants, utilitaires
- **Bootstrap Icons** : icônes
- **HTMX** : interactivité sans framework JS lourd
- **Alpine.js** : interactivité légère (dropdowns, modals)
- **MathJax** : rendu LaTeX
- **Prism.js** : coloration syntaxique du code
- **Chart.js** : graphiques du dashboard admin

### Layout de base

```django
{# templates/base.html #}
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>{% block title %}Numeria Institute{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons/font/bootstrap-icons.css" rel="stylesheet">
    {% block extra_css %}{% endblock %}
</head>
<body>
    {% include "partials/header.html" %}
    <main class="container py-4">
        {% block content %}{% endblock %}
    </main>
    {% include "partials/footer.html" %}

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/htmx.org@1.9/dist/htmx.min.js"></script>
    {% block extra_js %}{% endblock %}
</body>
</html>
```

### Rendu des leçons

Le contenu des leçons utilise un template custom qui itère sur les blocs :

```django
{# templates/courses/lesson_detail.html #}
{% for block in lesson.blocks.all %}
  {% if block.block_type == 'text' %}
    {% include "courses/blocks/text.html" with content=block.text_content %}
  {% elif block.block_type == 'mcq' %}
    {% include "courses/blocks/mcq.html" with exercise=block.mcq %}
  {% elif block.block_type == 'sandbox' %}
    {% include "courses/blocks/sandbox.html" with block=block %}
  {% elif block.block_type == 'lab' %}
    {% include "courses/blocks/lab.html" with lab=block.lab %}
  {% endif %}
{% endfor %}
```

---

## Migration vers Next.js

La migration vers Next.js 16 a été motivée par :

1. **Performance** : cold start Python (~5 s) vs Node.js (~50 ms) sur Vercel serverless
2. **SEO** : Next.js SSR/SSG natif vs Django + CDN
3. **DX** : TypeScript strict + React Server Components > Django Templates
4. **Design** : Tailwind + shadcn/ui > Bootstrap 5
5. **Edge runtime** : middleware rapide (protection de routes)

### Mapping des modèles Django → Prisma

| Django Model | Prisma Model | Notes |
|---|---|---|
| `accounts.User` | `User` | Même champs + `firstName`, `lastName` ajoutés |
| `courses.Course` | `Course` | Identique |
| `courses.CourseModule` | `CourseModule` | Identique |
| `courses.CourseLesson` | `CourseLesson` | Identique |
| `courses.LessonBlock` | `LessonBlock` | Polymorphique via FKs optionnels |
| `exercises.MCQExercise` | `MCQExercise` | Identique |
| `exercises.MCQChoice` | `MCQChoice` | Identique |
| `exercises.FillBlankExercise` | `FillBlankExercise` | `answers_json` reste en String |
| `exercises.InteractiveLab` | `InteractiveLab` | `slider_config` + `challenges` en JSON |
| `progress.Enrollment` | `Enrollment` | Identique |
| `progress.LessonProgress` | `LessonProgress` | Identique |
| `blog.BlogPost` | `BlogPost` | Identique |
| `community.CommunityTopic` | `CommunityTopic` | Identique |
| `community.CommunityPost` | `CommunityPost` | Identique |
| `meetings.Meeting` | `Meeting` | Identique |
| `gamification.UserBadge` | `UserBadge` | Identique |
| `gamification.UserStreak` | `UserStreak` | Identique |
| `notifications.Notification` | `Notification` | Identique |

### Ce qui a été perdu dans la migration

- ❌ **Admin auto-générée** Django (remplacée par une admin custom Next.js)
- ❌ **Django ORM migrations** (remplacé par `prisma db push`)
- ❌ **DRF browsable API** (remplacé par Server Actions)
- ❌ **Django Forms + Crispy Forms** (remplacé par react-hook-form)
- ❌ **Celery async tasks** (à remplacer par Vercel Cron + Edge Functions)

### Ce qui a été gagné

- ✅ **Cold start** 100× plus rapide
- ✅ **React Server Components** (zéro JS sur pages statiques)
- ✅ **TypeScript strict** (vs Python dynamique)
- ✅ **Tailwind CSS 4** (design system moderne)
- ✅ **Pyodide** (Python dans le navigateur — pas besoin de serveur pour les sandboxes)
- ✅ **Edge middleware** (protection routes en 50 ms)
- ✅ **shadcn/ui** (composants accessibles et personnalisables)

---

## Licence

MIT — voir [LICENSE](LICENSE).

---

## 🔗 Liens

- **Version actuelle (Next.js)** : <https://github.com/mawuliro/numeriainstitute>
- **Site en production** : <https://numeriainstitute.vercel.app>
- **Auteur** : Mawulikplimi Roland ([@mawuliro](https://github.com/mawuliro))

---

<p align="center">
  Version archivée — Django 4.2<br>
  Fait à Lomé, Togo 🇹🇬
</p>
