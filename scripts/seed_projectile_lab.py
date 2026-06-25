#!/usr/bin/env python3
"""
Seed script — Lab interactif : Mouvement parabolique.

Ajoute au cours existant « Mécanique Classique » (slug :
``mecanique-classique``) un nouveau module « Labs interactifs » contenant
une leçon qui démontre le NOUVEAU type de bloc ``interactive_lab``.

Le lab embarque :
  - un code Python (Pyodide + matplotlib) qui simule un tir parabolique
    avec ou sans frottement quadratique ;
  - 4 sliders (vitesse initiale, angle, gravité, frottement) ;
  - 5 challenges adaptatifs avec branchage if/else (next_on_correct /
    next_on_wrong) couvrant portée, flèche et effet du frottement.

Le script est **idempotent** : le ré-exécuter met à jour le contenu du
lab en place (mêmes PK) au lieu de dupliquer les lignes.

Usage :

    cd /home/z/my-project/repos/numeria-institute
    python3 scripts/seed_projectile_lab.py

Pré-requis : Django installé + migration ``cours.0004_interactive_lab``
appliquée + cours ``mecanique-classique`` existant en base.
"""
from __future__ import annotations

import os
import sys

# ─── Django bootstrap (doit précéder tout import de modèles Django) ──────────
# Le script est conçu pour être lancé depuis la racine du dépôt :
#     cd /home/z/my-project/repos/numeria-institute
#     python3 scripts/seed_projectile_lab.py
# Le répertoire parent de ``scripts/`` (i.e. la racine du projet) doit
# donc être ajouté au PYTHONPATH pour que ``numeria_project.settings``
# soit importable.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'numeria_project.settings')

import django  # noqa: E402  (importé APRÈS l'ajustement de sys.path)
django.setup()

from django.db import transaction  # noqa: E402

from cours.models import (  # noqa: E402
    Course,
    CourseModule,
    CourseLesson,
    LessonBlock,
    InteractiveLab,
)


# ─────────────────────────────────────────────────────────────────────────────
# Configuration du lab
# ─────────────────────────────────────────────────────────────────────────────

COURSE_SLUG = 'mecanique-classique'

MODULE_TITLE = 'Labs interactifs'
MODULE_DESCRIPTION = (
    "Modules de simulation interactive : manipule les paramètres physiques "
    "en temps réel, observe la trajectoire se tracer sous tes yeux, puis "
    "réponds à des challenges adaptatifs qui s'ajustent à tes réponses."
)

LESSON_TITLE = 'Lab interactif : Mouvement parabolique'
LESSON_SLUG = 'lab-mouvement-parabolique'
LESSON_MINUTES = 25

LAB_TITLE = 'Lab : Mouvement parabolique'
LAB_POINTS = 20
LAB_DIFFICULTY = 'medium'
LAB_INSTRUCTIONS = (
    "**Objectif** — Explore la balistique en manipulant vitesse initiale, "
    "angle de tir, gravité et frottement.\n\n"
    "1. À gauche, ajuste les **sliders** puis clique sur **Exécuter** pour "
    "lancer la simulation Pyodide (matplotlib + numpy).\n"
    "2. La trajectoire s'affiche avec la **portée** (carré vert), la "
    "**flèche** (triangle rouge) et le **temps de vol** en légende.\n"
    "3. À droite, réponds aux **challenges** : chaque réponse déclenche "
    "soit une question plus difficile (si correct), soit une version "
    "avec indice (si faux)."
)

# Code Python exécuté côté navigateur par Pyodide. Doit définir
# ``simulate(params)`` retournant une ``matplotlib.figure.Figure``.
# Le widget côté client ajoute déjà les imports matplotlib/numpy/io/base64
# avant ce code — les réimporter est inoffensif (idempotent).
LAB_SIMULATION_CODE = '''import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

def simulate(params):
    v0 = params.get('v0', 30)
    angle = params.get('angle', 45)
    g = params.get('g', 9.81)
    drag = params.get('drag', 0.0)

    alpha = np.radians(angle)
    vx0 = v0 * np.cos(alpha)
    vy0 = v0 * np.sin(alpha)

    if drag < 0.001:
        # Solution analytique (champ uniforme, pas de frottement)
        T = 2 * vy0 / g
        t = np.linspace(0, T, 200)
        x = vx0 * t
        y = vy0 * t - 0.5 * g * t**2
    else:
        # Intégration numérique (Euler simple) avec frottement quadratique
        dt = 0.001
        t_max = 10
        t = [0]; x = [0]; y = [0]; vx = [vx0]; vy = [vy0]
        for _ in range(int(t_max / dt)):
            if y[-1] < 0 and len(t) > 1:
                break
            v = np.sqrt(vx[-1]**2 + vy[-1]**2)
            ax = -drag * v * vx[-1]
            ay = -g - drag * v * vy[-1]
            vx.append(vx[-1] + ax * dt)
            vy.append(vy[-1] + ay * dt)
            x.append(x[-1] + vx[-1] * dt)
            y.append(y[-1] + vy[-1] * dt)
            t.append(t[-1] + dt)
        x = np.array(x); y = np.array(y); t = np.array(t)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(x, y, 'b-', lw=2.5, label='Trajectoire')

    # Annotations : portée, flèche, temps de vol
    if drag < 0.001:
        P = v0**2 * np.sin(2 * alpha) / g
        h = (v0 * np.sin(alpha))**2 / (2 * g)
        T = 2 * v0 * np.sin(alpha) / g
    else:
        P = x[-1]
        h = max(y)
        T = t[-1]

    ax.plot(P, 0, 'gs', markersize=10, label=f'Portée: {P:.1f} m')
    ax.plot(x[np.argmax(y)], max(y), 'r^', markersize=10, label=f'Flèche: {h:.1f} m')
    ax.plot(0, 0, 'ko', markersize=6, label=f'Temps de vol: {T:.2f} s')

    ax.set_xlabel(r'Position $x$ (m)', fontsize=12)
    ax.set_ylabel(r'Hauteur $y$ (m)', fontsize=12)
    ax.set_title(
        f'Trajectoire parabolique (v₀={v0} m/s, α={angle}°, drag={drag})',
        fontsize=11,
    )
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    ax.set_aspect('equal')
    ax.axhline(0, color='black', lw=0.5)

    plt.tight_layout()
    return fig
'''

# Liste de sliders au format attendu par interactive_lab_widget.html.
# Chaque entrée : {name, label, min, max, step, default, unit}.
LAB_SLIDER_CONFIG = [
    {
        "name": "v0",
        "label": "Vitesse initiale",
        "min": 5,
        "max": 60,
        "step": 0.5,
        "default": 30,
        "unit": "m/s",
    },
    {
        "name": "angle",
        "label": "Angle de tir",
        "min": 0,
        "max": 90,
        "step": 1,
        "default": 45,
        "unit": "deg",
    },
    {
        "name": "g",
        "label": "Gravité",
        "min": 1,
        "max": 25,
        "step": 0.1,
        "default": 9.81,
        "unit": "m/s^2",
    },
    {
        "name": "drag",
        "label": "Frottement",
        "min": 0,
        "max": 0.05,
        "step": 0.001,
        "default": 0,
        "unit": "",
    },
]

# Challenges adaptatifs. Le serveur (submit_lab_answer) consulte
# ``next_on_correct`` / ``next_on_wrong`` pour choisir le challenge suivant.
# ``expected_value`` + ``tolerance`` sont évalués côté client (le serveur
# enregistre juste is_correct transmis par le widget).
LAB_CHALLENGES = [
    {
        "id": "q1",
        "question": (
            "Quelle est la portée pour v₀=20 m/s, α=45°, g=9.81, sans "
            "frottement ?"
        ),
        "expected_value": 40.78,
        "tolerance": 1.0,
        "unit": "m",
        "hint": "Utilise la formule de la portée vue dans le cours.",
        "explanation": (
            "P = v₀²·sin(2α)/g = 20²·sin(90°)/9.81 ≈ 400/9.81 ≈ 40.78 m."
        ),
        "next_on_correct": "q2",
        "next_on_wrong": "q1b",
    },
    {
        "id": "q1b",
        "question": (
            "Rappel : P = v₀²·sin(2α)/g. Calcule avec v₀=20, α=45°, g=9.81."
        ),
        "expected_value": 40.78,
        "tolerance": 2.0,
        "unit": "m",
        "hint": "sin(2 × 45°) = sin(90°) = 1.",
        "explanation": "P = 400 × 1 / 9.81 ≈ 40.78 m.",
        "next_on_correct": "q2",
        "next_on_wrong": None,
    },
    {
        "id": "q2",
        "question": (
            "Quelle est la flèche (hauteur max) pour v₀=20, α=45°, g=9.81 ?"
        ),
        "expected_value": 10.19,
        "tolerance": 0.5,
        "unit": "m",
        "hint": "La flèche est la hauteur maximale atteinte par le projectile.",
        "explanation": (
            "h = (v₀·sin α)² / (2g) = (20·sin 45°)² / (2·9.81) "
            "≈ (14.142)² / 19.62 ≈ 10.19 m."
        ),
        "next_on_correct": "q3",
        "next_on_wrong": "q2b",
    },
    {
        "id": "q2b",
        "question": (
            "Rappel : h = (v₀·sin α)² / (2g). Avec v₀=20, α=45°, g=9.81."
        ),
        "expected_value": 10.19,
        "tolerance": 1.0,
        "unit": "m",
        "hint": "sin(45°) ≈ 0.7071.",
        "explanation": (
            "h = (20 × 0.7071)² / 19.62 ≈ 200 / 19.62 ≈ 10.19 m."
        ),
        "next_on_correct": "q3",
        "next_on_wrong": None,
    },
    {
        "id": "q3",
        "question": (
            "En présence de frottement (drag=0.01), la portée diminue. "
            "Utilise le simulateur pour trouver la portée approximative "
            "avec v₀=30, α=45°, drag=0.01."
        ),
        "expected_value": 75.0,
        "tolerance": 10.0,
        "unit": "m",
        "hint": (
            "Règle le slider drag=0.01, v₀=30, angle=45°, clique sur "
            "« Exécuter » puis lis la valeur « Portee » affichée en vert."
        ),
        "explanation": (
            "Avec drag=0.01, le frottement quadratique réduit la portée "
            "d'environ 20-25 % par rapport au cas idéal (P_ideal = "
            "30²·sin(90°)/9.81 ≈ 91.7 m). Valeur attendue : ~75 m ± 10 m."
        ),
        "next_on_correct": None,
        "next_on_wrong": None,
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Logique de seed
# ─────────────────────────────────────────────────────────────────────────────

def _next_order(queryset) -> int:
    """Renvoie order + 1 du plus haut order trouvé (ou 1 si vide)."""
    last = queryset.order_by('-order').values_list('order', flat=True).first()
    return (last or 0) + 1


@transaction.atomic
def seed() -> None:
    # 1. Trouver le cours cible --------------------------------------------
    try:
        course = Course.objects.get(slug=COURSE_SLUG)
    except Course.DoesNotExist:
        print(
            f"❌ Erreur : cours '{COURSE_SLUG}' introuvable.\n"
            f"   Crée d'abord ce cours (admin panel ou seed script) "
            f"avant de lancer ce script.",
            file=sys.stderr,
        )
        sys.exit(1)
    print(f"✓ Cours trouvé : {course.title} (slug={course.slug}, id={course.id})")

    # 2. Créer / mettre à jour le module « Labs interactifs » à la fin ------
    #    On calcule l'order UNIQUEMENT à la création ; les ré-exécutions du
    #    script préservent l'order existant (sinon _next_order se base sur
    #    max(order)+1, qui inclurait le module lui-même et le décalerait à
    #    chaque exécution).
    existing_module = CourseModule.objects.filter(
        course=course, title=MODULE_TITLE
    ).first()
    module_defaults = {
        'description': MODULE_DESCRIPTION,
        'is_active': True,
    }
    if existing_module is None:
        module_defaults['order'] = _next_order(
            CourseModule.objects.filter(course=course)
        )
    module, mod_created = CourseModule.objects.update_or_create(
        course=course,
        title=MODULE_TITLE,
        defaults=module_defaults,
    )
    print(
        f"✓ Module {'créé' if mod_created else 'mis à jour'} : "
        f"{module.title} (id={module.id}, order={module.order})"
    )

    # 3. Créer / mettre à jour la leçon dans ce module ---------------------
    #    Même logique : order figé à la création, préservé en mise à jour.
    existing_lesson = CourseLesson.objects.filter(
        course=course, module=module, title=LESSON_TITLE
    ).first()
    lesson_defaults = {
        'slug': LESSON_SLUG,
        'estimated_minutes': LESSON_MINUTES,
        'is_free_preview': True,
        'is_active': True,
    }
    if existing_lesson is None:
        lesson_defaults['order'] = _next_order(
            CourseLesson.objects.filter(module=module)
        )
    lesson, les_created = CourseLesson.objects.update_or_create(
        course=course,
        module=module,
        title=LESSON_TITLE,
        defaults=lesson_defaults,
    )
    print(
        f"✓ Leçon {'créée' if les_created else 'mise à jour'} : "
        f"{lesson.title} (id={lesson.id}, slug={lesson.slug})"
    )

    # 4. Créer / mettre à jour l'InteractiveLab ----------------------------
    #    Ici l'`order` du lab (champ interne hérité de BaseExercise) reste 0
    #    car un seul lab vit par leçon — pas de risque de décalage.
    lab, lab_created = InteractiveLab.objects.update_or_create(
        course_lesson=lesson,
        title=LAB_TITLE,
        defaults={
            'instructions': LAB_INSTRUCTIONS,
            'simulation_code': LAB_SIMULATION_CODE,
            'slider_config': LAB_SLIDER_CONFIG,
            'challenges': LAB_CHALLENGES,
            'points': LAB_POINTS,
            'difficulty': LAB_DIFFICULTY,
            'is_active': True,
            # BaseExercise champs hérités
            'hint': '',
            'explanation': '',
            'max_attempts': 0,  # 0 = illimité
            'order': 0,
        },
    )
    print(
        f"✓ InteractiveLab {'créé' if lab_created else 'mis à jour'} : "
        f"{lab.title} (id={lab.id}, points={lab.points}, "
        f"sliders={len(lab.slider_config)}, challenges={len(lab.challenges)})"
    )

    # 5. Attacher un LessonBlock de type 'interactive_lab' -----------------
    #    `order` figé à 0 (premier et unique bloc de la leçon).
    block, blk_created = LessonBlock.objects.update_or_create(
        course_lesson=lesson,
        block_type='interactive_lab',
        defaults={
            'interactive_lab': lab,
            'order': 0,
        },
    )
    print(
        f"✓ LessonBlock {'créé' if blk_created else 'mis à jour'} : "
        f"id={block.id}, type=interactive_lab, order={block.order}"
    )

    # 6. Nettoyer les éventuels blocs lab orphelins (même leçon, type lab,
    #    mais un autre lab attaché) — seulement si le script est ré-exécuté
    #    après un renommage de LAB_TITLE. On garde le bloc qu'on vient
    #    d'upserter (block.id) et on supprime les autres.
    orphans = (
        LessonBlock.objects
        .filter(course_lesson=lesson, block_type='interactive_lab')
        .exclude(id=block.id)
    )
    if orphans.exists():
        n = orphans.count()
        orphans.delete()
        print(f"✓ {n} bloc(s) lab orphelin(s) supprimé(s).")

    # 7. Résumé final ------------------------------------------------------
    print()
    print("─── Résumé ───")
    print(f"  Cours      : {course.title} (id={course.id})")
    print(f"  Module     : {module.title} (id={module.id}, order={module.order})")
    print(f"  Leçon      : {lesson.title} (id={lesson.id}, slug={lesson.slug})")
    print(f"  Lab        : {lab.title} (id={lab.id})")
    print(f"  Sliders    : {len(lab.slider_config)} → "
          f"{[s['name'] for s in lab.slider_config]}")
    print(f"  Challenges : {len(lab.challenges)} → "
          f"{[c['id'] for c in lab.challenges]}")
    print(f"  Bloc       : id={block.id}, type=interactive_lab")
    print()
    print(
        "✓ Lab prêt. Accès : /cours/  →  module « Labs interactifs »  →  "
        "leçon « Lab interactif : Mouvement parabolique »."
    )


if __name__ == '__main__':
    seed()
