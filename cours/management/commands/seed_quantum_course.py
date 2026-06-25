"""
Management command: seed_quantum_course
Crée un cours complet de Mécanique Quantique I (niveau Cohen-Tannoudji Vol. I)
en français, avec simulations matplotlib, exercices corrigés, et
explications pas-à-pas adaptées à l'auto-apprentissage.

Usage:
    python manage.py seed_quantum_course
    python manage.py seed_quantum_course --clean   # delete + recreate
    python manage.py seed_quantum_course --draft    # create as draft

RÈGLES D'ÉCHAPPEMENT (CRITIQUES):
- Source Python : `\\vec{F}` (2 backslashes) → DB : `\vec{F}` → MathJax rend ✓
- JAMAIS `\\\\vec{F}` (4 backslashes) → casse MathJax ✗
- Pour matplotlib : utiliser raw strings r'...' pour les labels LaTeX
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from cours.models import (
    Course, CourseModule, CourseLesson, LessonBlock,
    CodeExercise, MCQExercise, MCQChoice,
    FillBlankExercise, TrueFalseExercise,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def T(content):
    return {"type": "text", "content": content}

def S(title, code):
    return {"type": "sandbox", "title": title, "code": code}

def APP(title, enonce, correction):
    content = (
        "## 🎯 Exercice d'application — " + title + "\n\n"
        "**Énoncé.** " + enonce + "\n\n"
        "<details>\n"
        "<summary>📌 Voir la correction (clique pour déplier)</summary>\n\n"
        "**Correction.** " + correction + "\n\n"
        "</details>"
    )
    return {"type": "text", "content": content}

def MCQ(title, question, choices, explanation="", **kw):
    out = {"type": "mcq", "title": title, "question": question,
           "choices": choices, "explanation": explanation}
    out.update(kw)
    return out

def FB(title, text_with_blanks, answers, explanation="", **kw):
    out = {"type": "fill_blank", "title": title,
           "text_with_blanks": text_with_blanks, "answers": answers,
           "explanation": explanation}
    out.update(kw)
    return out

def TF(title, statements, explanation=""):
    return {"type": "true_false", "title": title,
            "statements": statements, "explanation": explanation}


# ─────────────────────────────────────────────────────────────────────────────
# Command
# ─────────────────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = "Seed a complete Quantum Mechanics I course (Cohen-Tannoudji style, in French)."

    def add_arguments(self, parser):
        parser.add_argument("--draft", action="store_true")
        parser.add_argument("--clean", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        slug = "mecanique-quantique-1"
        status = "draft" if options["draft"] else "published"
        if options["clean"]:
            d, _ = Course.objects.filter(slug=slug).delete()
            if d:
                self.stdout.write(self.style.WARNING(f"Deleted ({d} rows)."))
        course, created = Course.objects.get_or_create(slug=slug, defaults={
            "title": "Mécanique Quantique I · Du formalisme à l'atome d'hydrogène",
            "description": (
                "Un cours complet de mécanique quantique adapté de Cohen-Tannoudji, "
                "avec formalisme de Dirac, postulats, problèmes 1D (puits, oscillateur, "
                "barrière), moment cinétique, spin, atome d'hydrogène et méthodes "
                "d'approximation. Simulations matplotlib, exercices corrigés pas-à-pas."
            ),
            "short_description": (
                "Maîtrise la mécanique quantique : formalisme de Dirac, postulats, "
                "puits infini, oscillateur harmonique, spin, atome d'hydrogène."
            ),
            "category": "physique", "level": "intermediaire", "language": "fr",
            "price": 0, "is_free": True, "status": status, "estimated_hours": 70,
        })
        if not created:
            self.stdout.write(self.style.WARNING("Course exists — updating."))
        for md in COURSE_STRUCTURE:
            mod = self._mod(course, md)
            for ld in md["lessons"]:
                les = self._les(course, mod, ld)
                self._blocks(les, ld["blocks"])
        n_mod = CourseModule.objects.filter(course=course).count()
        n_les = CourseLesson.objects.filter(course=course).count()
        n_blk = LessonBlock.objects.filter(course_lesson__course=course).count()
        self.stdout.write(self.style.SUCCESS(
            f"\n✓ Seeded: {course.title}\n"
            f"  Modules: {n_mod}\n  Lessons: {n_les}\n  Blocks:  {n_blk}\n"
        ))

    def _mod(self, course, d):
        m, _ = CourseModule.objects.get_or_create(
            course=course, title=d["title"],
            defaults={"description": d.get("description", ""),
                      "order": d["order"], "is_active": True})
        return m

    def _les(self, course, mod, d):
        s = d.get("slug") or d["title"].lower().replace(" ", "-").replace("'", "-")
        l, _ = CourseLesson.objects.get_or_create(
            course=course, module=mod, title=d["title"],
            defaults={"slug": s, "order": d["order"],
                      "estimated_minutes": d.get("minutes", 45),
                      "is_free_preview": True, "is_active": True})
        return l

    def _blocks(self, lesson, blocks):
        LessonBlock.objects.filter(course_lesson=lesson).delete()
        for i, bd in enumerate(blocks):
            self._blk(lesson, bd, i)

    def _blk(self, lesson, data, idx):
        t = data["type"]
        b = LessonBlock(course_lesson=lesson, block_type=t, order=idx)
        if t == "text":
            b.text_content = data["content"]; b.save()
        elif t == "sandbox":
            b.sandbox_title = data.get("title", "Simulation")
            b.sandbox_initial_code = data.get("code", ""); b.save()
        elif t == "mcq":
            ex = MCQExercise.objects.create(
                course_lesson=lesson, title=data["title"],
                question=data["question"],
                instructions=data.get("instructions", ""),
                difficulty=data.get("difficulty", "medium"),
                points=data.get("points", 5),
                hint=data.get("hint", ""),
                explanation=data.get("explanation", ""),
                allow_multiple_correct=data.get("multiple", False),
                shuffle_choices=True)
            for i, c in enumerate(data["choices"]):
                MCQChoice.objects.create(exercise=ex, text=c["text"],
                    is_correct=c["correct"], feedback=c.get("feedback", ""),
                    order=i)
            b.mcq_exercise = ex; b.save()
        elif t == "fill_blank":
            ex = FillBlankExercise.objects.create(
                course_lesson=lesson, title=data["title"],
                instructions=data.get("instructions", ""),
                difficulty=data.get("difficulty", "medium"),
                points=data.get("points", 5),
                hint=data.get("hint", ""),
                explanation=data.get("explanation", ""),
                text_with_blanks=data["text_with_blanks"],
                answers=data["answers"], case_sensitive=False)
            b.fill_blank = ex; b.save()
        elif t == "true_false":
            ex = TrueFalseExercise.objects.create(
                course_lesson=lesson, title=data["title"],
                instructions=data.get("instructions", ""),
                difficulty=data.get("difficulty", "medium"),
                points=data.get("points", 6),
                hint=data.get("hint", ""),
                explanation=data.get("explanation", ""),
                statements=data["statements"], points_per_statement=2)
            b.true_false = ex; b.save()


# ─────────────────────────────────────────────────────────────────────────────
# COURSE STRUCTURE — 8 modules, ~20 lessons
# ─────────────────────────────────────────────────────────────────────────────

COURSE_STRUCTURE = []


# ═════════════════════════════════════════════════════════════════════════════
# MODULE 0 — INTRODUCTION : POURQUOI LA MÉCANIQUE QUANTIQUE ?
# ═════════════════════════════════════════════════════════════════════════════
COURSE_STRUCTURE.append({
    "order": 0,
    "title": "Introduction · Pourquoi la mécanique quantique ?",
    "description": (
        "Limites de la physique classique, dualité onde-corpuscule, "
        "effet photoélectrique, relations de de Broglie. Échelles quantiques."
    ),
    "lessons": [

        # ── Leçon 0.1 : Échelles quantiques ────────────────────────────────
        {
            "order": 0,
            "title": "Échelles quantiques et nécessité d'une nouvelle physique",
            "slug": "echelles-quantiques",
            "minutes": 45,
            "blocks": [
                T(
                    "# Échelles quantiques et nécessité d'une nouvelle physique\n\n"
                    "## 1. La crise de la physique classique (fin du XIXᵉ siècle)\n\n"
                    "À la fin du XIXᵉ siècle, la physique classique (mécanique newtonienne, électromagnétisme de Maxwell, thermodynamique) semblait capable d'expliquer tous les phénomènes observés. Pourtant, plusieurs expériences sont restées inexpliquées :\n\n"
                    "- Le **spectre de raies** des atomes (pourquoi les atomes émettent-ils à des longueurs d'onde discrètes ?)\n"
                    "- L'**effet photoélectrique** (pourquoi l'énergie des électrons éjectés dépend-elle de la fréquence, pas de l'intensité ?)\n"
                    "- La **catastrophe ultraviolette** (le rayonnement du corps noir divergeait à haute fréquence)\n"
                    "- La **stabilité des atomes** (un électron en orbite devrait rayonner et s'effondrer sur le noyau)\n\n"
                    "## 2. Échelles caractéristiques\n\n"
                    "La mécanique quantique devient pertinente aux petites échelles. Les ordres de grandeur typiques sont :\n\n"
                    "### Longueur\n"
                    "- Atome : $a_0 \\approx 0{,}529$ Å $= 5{,}29 \\times 10^{-11}$ m (rayon de Bohr)\n"
                    "- Noyau : $R \\sim 1$ à $7$ fm $= 10^{-15}$ à $10^{-14}$ m\n"
                    "- Longueur d'onde de de Broglie d'un électron à 1 eV : $\\lambda \\sim 12$ Å\n\n"
                    "### Énergie\n"
                    "- Électron dans un atome : $E \\sim 1$ à $10$ eV\n"
                    "- Électron dans un noyau : $E \\sim 1$ à $10$ MeV\n"
                    "- Photon visible : $E = h\\nu \\sim 2$ à $3$ eV\n\n"
                    "### Temps\n"
                    "- Transition atomique : $\\tau \\sim 10^{-8}$ s\n"
                    "- Période orbitale électronique : $T \\sim 10^{-16}$ s\n\n"
                    "## 3. Constantes fondamentales\n\n"
                    "- Constante de Planck : $h = 6{,}626 \\times 10^{-34}$ J·s\n"
                    "- Constante de Planck réduite : $\\hbar = h/(2\\pi) = 1{,}055 \\times 10^{-34}$ J·s $= 6{,}582 \\times 10^{-16}$ eV·s\n"
                    "- Vitesse de la lumière : $c = 2{,}998 \\times 10^{8}$ m/s\n"
                    "- Charge élémentaire : $e = 1{,}602 \\times 10^{-19}$ C\n"
                    "- Masse de l'électron : $m_e = 9{,}109 \\times 10^{-31}$ kg $= 0{,}511$ MeV/c²\n\n"
                    "## 4. Le quantum d'action $\\hbar$\n\n"
                    "La constante $\\hbar$ joue le rôle d'unité naturelle d'**action**. Une grandeur caractéristique d'action dans un système classique est $S \\sim E \\cdot T$ (énergie × temps). La règle empirique est :\n\n"
                    "$$\\boxed{\\;\\text{Régime quantique} \\iff S \\sim \\hbar\\;}$$\n\n"
                    "Si $S \\gg \\hbar$, la physique classique suffit. Si $S \\sim \\hbar$, il faut la mécanique quantique.\n\n"
                    "### Exemple : électron dans un atome\n"
                    "$S \\sim E \\cdot T \\sim (10 \\text{ eV}) \\times (10^{-16} \\text{ s}) \\sim 10^{-15} \\text{ eV·s} \\sim 15 \\, \\hbar$\n\n"
                    "L'action est de l'ordre de $\\hbar$ → **régime quantique**.\n\n"
                    "### Exemple : balle de tennis\n"
                    "$S \\sim (1 \\text{ J}) \\times (0{,}1 \\text{ s}) = 0{,}1$ J·s $\\sim 10^{33} \\, \\hbar$ → **régime classique**.\n\n"
                    "## 5. Limite relativiste\n\n"
                    "Quand les vitesses deviennent comparables à $c$, il faut ajouter la relativité restreinte. On distingue :\n"
                    "- **Mécanique quantique non relativiste** (Schrödinger) : $v \\ll c$, applicable aux électrons atomiques\n"
                    "- **Mécanique quantique relativiste** (Dirac, théorie des champs) : $v \\sim c$, nécessaire pour les électrons dans les noyaux ou les atomes lourds\n\n"
                    "> 💡 **Astuce** : Pour savoir si un phénomène est quantique, calcule $S/\\hbar$. Si le rapport est de l'ordre de 1 à 100, c'est quantique. S'il dépasse $10^{10}$, c'est classique."
                ),

                S(
                    "Échelles de longueur et d'énergie en physique",
                    "import matplotlib.pyplot as plt\n"
                    "import numpy as np\n"
                    "\n"
                    "fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 6))\n"
                    "\n"
                    "# Échelles de longueur\n"
                    "lengths = {\n"
                    "    'Univers': 26e9 * 9.461e15,  # années-lumière\n"
                    "    'Voie lactée': 100e3 * 9.461e15,\n"
                    "    'Système solaire': 9e12,\n"
                    "    'Terre': 6.4e6,\n"
                    "    'Humain': 1.7,\n"
                    "    'Cheveu': 1e-4,\n"
                    "    'Cellule': 1e-5,\n"
                    "    'Atome': 1e-10,\n"
                    "    'Noyau': 1e-15,\n"
                    "    'Proton': 1e-16,\n"
                    "}\n"
                    "names = list(lengths.keys())\n"
                    "vals = list(lengths.values())\n"
                    "colors = ['blue']*6 + ['orange']*2 + ['red']*2\n"
                    "ax1.barh(range(len(names)), np.log10(vals), color=colors)\n"
                    "ax1.set_yticks(range(len(names)))\n"
                    "ax1.set_yticklabels(names)\n"
                    "ax1.set_xlabel(r'$\\log_{10}$(longueur / m)')\n"
                    "ax1.set_title('Échelles de longueur')\n"
                    "ax1.axvspan(-11, -14, alpha=0.2, color='red', label='Quantique')\n"
                    "ax1.axvspan(-15, -17, alpha=0.2, color='purple', label='Subatomique')\n"
                    "ax1.legend(loc='lower right', fontsize=9)\n"
                    "ax1.grid(True, alpha=0.3, axis='x')\n"
                    "\n"
                    "# Échelles d'énergie\n"
                    "energies = {\n"
                    "    'Big Bang': 1e28,\n"
                    "    'Supernova': 1e44 / 6.242e18,  # J → eV\n"
                    "    'Bombe H': 4e15 / 6.242e18,\n"
                    "    'Réacteur': 1e9 / 6.242e18,\n"
                    "    'Molécule': 1 / 6.242e18,\n"
                    "    'Atome': 10,\n"
                    "    'Photon visible': 2,\n"
                    "    'Thermique (300K)': 0.025,\n"
                    "    'Noyau': 1e6,\n"
                    "}\n"
                    "names_e = list(energies.keys())\n"
                    "vals_e = list(energies.values())\n"
                    "colors_e = ['blue']*5 + ['orange']*2 + ['red']*2\n"
                    "ax2.barh(range(len(names_e)), np.log10(max(v, 1e-30) for v in vals_e), color=colors_e)\n"
                    "ax2.set_yticks(range(len(names_e)))\n"
                    "ax2.set_yticklabels(names_e)\n"
                    "ax2.set_xlabel(r'$\\log_{10}$(énergie / eV)')\n"
                    "ax2.set_title('Échelles d\\'énergie')\n"
                    "ax2.axvspan(0, 2, alpha=0.2, color='orange', label='Atome')\n"
                    "ax2.axvspan(5, 7, alpha=0.2, color='red', label='Noyau')\n"
                    "ax2.legend(loc='lower right', fontsize=9)\n"
                    "ax2.grid(True, alpha=0.3, axis='x')\n"
                    "\n"
                    "plt.tight_layout(); plt.savefig('plot.png')\n"
                    "print(f'hbar = {1.055e-34:.3e} J·s')\n"
                    "print(f'S_atome/hbar ~ 15 (régime quantique)')\n"
                    "print(f'S_balle/hbar ~ 1e33 (régime classique)')\n"
                ),

                APP(
                    "Ordre de grandeur quantique",
                    "On considère un électron de vitesse $v = 10^6$ m/s (vitesse typique dans un atome) dans une région de taille $L = 1$ Å.\n\n"
                    "1) Calculer son énergie cinétique (non relativiste).\n"
                    "2) Calculer l'action $S = p \\cdot L$ et la comparer à $\\hbar$.\n"
                    "3) Conclusion : ce système est-il quantique ?",
                    "1) **Énergie cinétique** : $E_c = \\tfrac{1}{2} m_e v^2 = \\tfrac{1}{2} \\times 9{,}11 \\times 10^{-31} \\times (10^6)^2 = 4{,}55 \\times 10^{-19}$ J $\\approx 2{,}84$ eV.\n\n"
                    "2) **Quantité de mouvement** : $p = m_e v = 9{,}11 \\times 10^{-25}$ kg·m/s.\n"
                    "**Action** : $S = p \\cdot L = 9{,}11 \\times 10^{-25} \\times 10^{-10} = 9{,}11 \\times 10^{-35}$ J·s.\n"
                    "**Rapport** : $S/\\hbar = 9{,}11 \\times 10^{-35} / 1{,}055 \\times 10^{-34} \\approx 0{,}86$.\n\n"
                    "3) **Conclusion** : $S \\sim \\hbar$ (rapport de l'ordre de 1), donc le système est en **régime quantique**. La mécanique classique ne suffit pas à décrire cet électron — il faut utiliser la mécanique quantique."
                ),

                MCQ(
                    "Échelle atomique",
                    "Le rayon de Bohr $a_0$ vaut environ :",
                    [
                        {"text": "0,5 fm", "correct": False, "feedback": "Trop petit — c'est l'échelle nucléaire."},
                        {"text": "0,5 Å", "correct": True, "feedback": "Exact ! $a_0 \\approx 0{,}529$ Å $= 5{,}29 \\times 10^{-11}$ m."},
                        {"text": "0,5 nm", "correct": False, "feedback": "Trop grand — c'est l'échelle moléculaire."},
                        {"text": "0,5 μm", "correct": False, "feedback": "Trop grand — c'est l'échelle cellulaire."}
                    ],
                    explanation="Le rayon de Bohr $a_0 = 4\\pi\\varepsilon_0 \\hbar^2 / (m_e e^2) \\approx 0{,}529$ Å."
                ),

                FB(
                    "Constantes fondamentales",
                    "La constante de Planck vaut $h = 6{,}626 \\times 10^{{{blank_1}}}$ J·s.\\n\\n"
                    "La constante réduite est $\\hbar = h / ({{blank_2}}\\pi)$.\\n\\n"
                    "Pour un électron atomique, $S/\\hbar \\sim 1$ indique un régime {{blank_3}}.",
                    {"blank_1": ["-34"], "blank_2": ["2"], "blank_3": ["quantique", "quantum"]},
                    explanation="$h \\approx 6{,}626 \\times 10^{-34}$ J·s, $\\hbar = h/(2\\pi)$, et $S \\sim \\hbar$ → régime quantique."
                ),

                TF(
                    "Vrai ou Faux ? Échelles quantiques",
                    [
                        {"statement": "La mécanique quantique est nécessaire quand $S \\sim \\hbar$.", "is_true": True},
                        {"statement": "Pour une balle de tennis, $S/\\hbar \\sim 1$.", "is_true": False, "statement_note": "Non, $S/\\hbar \\sim 10^{33}$ → régime classique."},
                        {"statement": "L'échelle atomique est de l'ordre de l'ångström (Å).", "is_true": True},
                        {"statement": "L'électron dans un atome a une énergie typique de 1 MeV.", "is_true": False, "statement_note": "C'est 1 eV (électron-volt), pas MeV."},
                        {"statement": "Quand $v \\sim c$, il faut utiliser la mécanique quantique relativiste.", "is_true": True}
                    ]
                ),
            ],
        },

        # ── Leçon 0.2 : Dualité onde-corpuscule ────────────────────────────
        {
            "order": 1,
            "title": "Dualité onde-corpuscule",
            "slug": "dualite-onde-corpuscule",
            "minutes": 50,
            "blocks": [
                T(
                    "# Dualité onde-corpuscule\n\n"
                    "## 1. Le photon : onde ou particule ?\n\n"
                    "En 1905, Einstein propose que la lumière soit constituée de **quanta** d'énergie — les photons. Chaque photon transporte une énergie :\n"
                    "$$\\boxed{\\;E = h\\nu = \\hbar\\omega\\;}$$\n\n"
                    "où $\\nu$ est la fréquence et $\\omega = 2\\pi\\nu$ la pulsation. Le photon a aussi une quantité de mouvement :\n"
                    "$$\\vec{p} = \\hbar \\vec{k}, \\quad |\\vec{k}| = 2\\pi/\\lambda$$\n\n"
                    "Cette hypothèse explique l'**effet photoélectrique** : un électron est éjecté d'un métal seulement si $h\\nu > W$ (où $W$ est le travail de sortie). Augmenter l'intensité augmente le **nombre** de photons, mais pas leur énergie individuelle.\n\n"
                    "## 2. Hypothèse de de Broglie (1924)\n\n"
                    "Louis de Broglie propose la **réciproque** : toute particule matérielle a une longueur d'onde associée :\n"
                    "$$\\boxed{\\;\\lambda = \\frac{h}{p} = \\frac{2\\pi}{k}\\;}$$\n\n"
                    "Cette longueur d'onde est appelée **longueur d'onde de de Broglie**.\n\n"
                    "### Exemple : électron à 100 eV\n"
                    "$p = \\sqrt{2 m_e E} = \\sqrt{2 \\times 9{,}11 \\times 10^{-31} \\times 100 \\times 1{,}6 \\times 10^{-19}} \\approx 5{,}4 \\times 10^{-24}$ kg·m/s\n"
                    "$\\lambda = h/p \\approx 1{,}23$ Å\n\n"
                    "Cette longueur d'onde est comparable à la distance interatomique → les électrons peuvent diffracter sur les cristaux.\n\n"
                    "## 3. Vérification expérimentale : Davisson-Germer (1927)\n\n"
                    "Davisson et Germer envoient un faisceau d'électrons sur un cristal de nickel. Ils observent des **pics de diffraction**, exactement comme pour les rayons X. La position des pics confirme $\\lambda = h/p$.\n\n"
                    "C'est la **première démonstration directe** de la nature ondulatoire de la matière.\n\n"
                    "## 4. Expérience des fentes de Young avec des électrons\n\n"
                    "L'expérience la plus troublante : on envoie des électrons **un par un** à travers deux fentes. Chaque électron laisse une tache ponctuelle sur l'écran (particule), mais après un grand nombre d'électrons, on voit apparaître une **figure d'interférence** (onde).\n\n"
                    "Conclusion vertigineuse :\n"
                    "- Un électron isolé passe par les **deux fentes à la fois** (comme une onde)\n"
                    "- Mais il est détecté en un **point unique** (comme une particule)\n\n"
                    "## 5. Le paradoxe de la mesure\n\n"
                    "Si on place un détecteur pour savoir par quelle fente passe l'électron, la figure d'interférence **disparaît**. L'acte de mesure force l'électron à se comporter comme une particule.\n\n"
                    "C'est le cœur de la mécanique quantique : **la mesure modifie le système**. Nous formaliserons cela avec les postulats.\n\n"
                    "## 6. Principe de complémentarité (Bohr)\n\n"
                    "Bohr propose que les aspects onde et corpuscule soient **complémentaires** : on ne peut pas observer les deux simultanément, mais les deux sont nécessaires pour une description complète.\n\n"
                    "> 💡 **Astuce** : La longueur d'onde de de Broglie $\\lambda = h/p$ est la formule la plus importante de cette leçon. Elle permet de décider si un objet manifestera un comportement quantique : si $\\lambda$ est comparable à la taille du système, c'est quantique."
                ),

                S(
                    "Longueur d'onde de de Broglie en fonction de l'énergie",
                    "import matplotlib.pyplot as plt\n"
                    "import numpy as np\n"
                    "\n"
                    "h = 6.626e-34\n"
                    "m_e = 9.109e-31\n"
                    "c = 2.998e8\n"
                    "\n"
                    "# Énergie cinétique en eV\n"
                    "E_eV = np.logspace(-3, 6, 500)  # de 1 meV à 1 MeV\n"
                    "E_J = E_eV * 1.602e-19\n"
                    "\n"
                    "# Non relativiste : lambda = h/sqrt(2mE)\n"
                    "mask_nr = E_J < 0.01 * m_e * c**2  # E < 0.01 mc²\n"
                    "lambda_nr = np.full_like(E_J, np.nan)\n"
                    "lambda_nr[mask_nr] = h / np.sqrt(2 * m_e * E_J[mask_nr])\n"
                    "\n"
                    "# Relativiste : lambda = hc/sqrt(E² + 2Emc²)\n"
                    "lambda_rel = h * c / np.sqrt(E_J**2 + 2 * E_J * m_e * c**2)\n"
                    "\n"
                    "fig, ax = plt.subplots(figsize=(10, 6))\n"
                    "ax.loglog(E_eV[mask_nr], lambda_nr[mask_nr] * 1e10, 'b-', lw=2.5, label=r'Non relativiste : $\\lambda = h/\\sqrt{2mE}$')\n"
                    "ax.loglog(E_eV, lambda_rel * 1e10, 'r--', lw=2, label=r'Relativiste : $\\lambda = hc/\\sqrt{E^2+2Emc^2}$')\n"
                    "\n"
                    "# Annotations\n"
                    "ax.axhline(0.529, color='green', ls=':', alpha=0.5, label=r'Rayon de Bohr $a_0 = 0{,}529$ Å')\n"
                    "ax.axhline(1.0, color='orange', ls=':', alpha=0.5, label=r'Distance interatomique typique (1 Å)')\n"
                    "ax.axvline(13.6, color='purple', ls=':', alpha=0.5, label=r'Énergie d\\'ionisation H (13,6 eV)')\n"
                    "\n"
                    "ax.set_xlabel(r'Énergie cinétique de l\\'électron (eV)', fontsize=12)\n"
                    "ax.set_ylabel(r'Longueur d\\'onde de de Broglie $\\lambda$ (Å)', fontsize=12)\n"
                    "ax.set_title(r'Longueur d\\'onde de de Broglie : $\\lambda = h/p$', fontsize=13)\n"
                    "ax.legend(fontsize=9, loc='upper right')\n"
                    "ax.grid(True, alpha=0.3, which='both')\n"
                    "ax.set_xlim(1e-3, 1e6)\n"
                    "ax.set_ylim(1e-4, 1e3)\n"
                    "\n"
                    "plt.tight_layout(); plt.savefig('plot.png')\n"
                    "print('À 100 eV (non relativiste) :')\n"
                    "E100 = 100 * 1.602e-19\n"
                    "lam = h / np.sqrt(2 * m_e * E100)\n"
                    "print(f'  lambda = {lam*1e10:.3f} Å')\n"
                    "print('À 100 keV (relativiste) :')\n"
                    "E100k = 1e5 * 1.602e-19\n"
                    "lam_r = h * c / np.sqrt(E100k**2 + 2*E100k*m_e*c**2)\n"
                    "print(f'  lambda = {lam_r*1e10:.4f} Å')\n"
                ),

                APP(
                    "Longueur d'onde d'un électron d'accélérateur",
                    "Un électron est accéléré par une différence de potentiel $V = 1000$ V.\n\n"
                    "1) Calculer son énergie cinétique en eV et en joules.\n"
                    "2) Calculer sa quantité de mouvement.\n"
                    "3) En déduire sa longueur d'onde de de Broglie.\n"
                    "4) Comparer à la longueur d'onde d'un photon de même énergie.",
                    "1) **Énergie cinétique** : $E = eV = 1000$ eV $= 1{,}602 \\times 10^{-16}$ J. (L'électron-volt est défini comme l'énergie acquise par un électron accéléré par 1 V.)\n\n"
                    "2) **Quantité de mouvement** (non relativiste car $E \\ll m_e c^2 \\approx 511$ keV) :\n"
                    "$$p = \\sqrt{2 m_e E} = \\sqrt{2 \\times 9{,}11 \\times 10^{-31} \\times 1{,}602 \\times 10^{-16}} \\approx 1{,}71 \\times 10^{-23} \\text{ kg·m/s}$$\n\n"
                    "3) **Longueur d'onde de de Broglie** :\n"
                    "$$\\lambda = \\frac{h}{p} = \\frac{6{,}626 \\times 10^{-34}}{1{,}71 \\times 10^{-23}} \\approx 3{,}88 \\times 10^{-11} \\text{ m} = 0{,}388 \\text{ Å}$$\n\n"
                    "4) **Photon de même énergie** : $\\lambda_{\\text{photon}} = hc/E = (6{,}626 \\times 10^{-34} \\times 3 \\times 10^8)/(1{,}602 \\times 10^{-16}) \\approx 12{,}4$ Å.\n\n"
                    "La longueur d'onde de l'électron est **32 fois plus courte** que celle du photon de même énergie ! C'est pourquoi les microscopes électroniques ont une résolution bien supérieure aux microscopes optiques."
                ),

                MCQ(
                    "Relation de de Broglie",
                    "La longueur d'onde de de Broglie d'une particule de quantité de mouvement $p$ est :",
                    [
                        {"text": "$\\lambda = h \\cdot p$", "correct": False, "feedback": "Inversé."},
                        {"text": "$\\lambda = h/p$", "correct": True, "feedback": "Exact ! $\\lambda = h/p = 2\\pi/k$."},
                        {"text": "$\\lambda = p/h$", "correct": False, "feedback": "Inversé."},
                        {"text": "$\\lambda = h p^2$", "correct": False}
                    ],
                    explanation="$\\lambda = h/p$. Plus $p$ est grand (particule rapide ou massive), plus $\\lambda$ est petit."
                ),

                FB(
                    "Photon et électron",
                    "Un photon d'énergie $E$ a une quantité de mouvement $p = E/{{blank_1}}$ où $c$ est la vitesse de la lumière.\\n\\n"
                    "Pour un électron non relativiste, $p = \\sqrt{2 m E}$. Sa longueur d'onde est $\\lambda = {{blank_2}}/p$.\\n\\n"
                    "Pour observer la diffraction des électrons par un cristal, $\\lambda$ doit être comparable à la distance {{blank_3}}.",
                    {"blank_1": ["c"], "blank_2": ["h"], "blank_3": ["interatomique", "inter-réticulaire", "interatomique du cristal"]},
                    explanation="Photon : $p = E/c$ (relativiste). Électron : $\\lambda = h/p$. Diffraction cristalline si $\\lambda \\sim d$ (distance interatomique)."
                ),

                TF(
                    "Vrai ou Faux ? Dualité",
                    [
                        {"statement": "Un photon transporte une énergie $E = h\\nu$.", "is_true": True},
                        {"statement": "La longueur d'onde de de Broglie vaut $\\lambda = h/p$ pour toute particule.", "is_true": True},
                        {"statement": "Dans l'expérience des fentes de Young, un électron isolé passe par une seule fente.", "is_true": False, "statement_note": "Non, il passe par les deux fentes à la fois (interférence), sauf si on le mesure."},
                        {"statement": "L'effet photoélectrique prouve que la lumière est uniquement une particule.", "is_true": False, "statement_note": "Il prouve l'aspect particulaire, mais la diffraction prouve l'aspect ondulatoire. Les deux sont complémentaires."},
                        {"statement": "Plus une particule est rapide, plus sa longueur d'onde de de Broglie est courte.", "is_true": True}
                    ]
                ),
            ],
        },

        # ── Leçon 0.3 : Effet photoélectrique et corps noir ────────────────
        {
            "order": 2,
            "title": "Effet photoélectrique et corps noir",
            "slug": "effet-photoelectrique-corps-noir",
            "minutes": 45,
            "blocks": [
                T(
                    "# Effet photoélectrique et corps noir\n\n"
                    "## 1. La catastrophe ultraviolette\n\n"
                    "Un **corps noir** est un objet idéal qui absorbe tout rayonnement incident. À l'équilibre thermique, il émet un spectre continu dépendant uniquement de sa température $T$. La physique classique (Rayleigh-Jeans) prédisait :\n"
                    "$$u(\\nu, T) = \\frac{8\\pi \\nu^2}{c^3} k_B T$$\n\n"
                    "Cette formule diverge à haute fréquence ($u \\propto \\nu^2$) : c'est la **catastrophe ultraviolette**. En pratique, l'énergie totale rayonnée serait infinie — absurde !\n\n"
                    "## 2. La solution de Planck (1900)\n\n"
                    "Planck propose que les échanges d'énergie entre matière et rayonnement se fassent par **quanta** discrets $E = h\\nu$. Il obtient la loi :\n"
                    "$$\\boxed{\\;u(\\nu, T) = \\frac{8\\pi h \\nu^3}{c^3} \\frac{1}{e^{h\\nu/(k_B T)} - 1}\\;}$$\n\n"
                    "Cette formule reproduit parfaitement les observations. À basse fréquence ($h\\nu \\ll k_B T$), on retrouve Rayleigh-Jeans. À haute fréquence, l'exponentielle fait chuter $u$ — plus de divergence.\n\n"
                    "Planck considérait $h$ comme un artifice mathématique. Einstein (1905) prendra $h$ au sérieux.\n\n"
                    "## 3. L'effet photoélectrique\n\n"
                    "Quand on éclaire un métal avec de la lumière, des électrons sont éjectés. Les observations inexplicables classiquement :\n\n"
                    "- L'énergie cinétique des électrons **ne dépend pas** de l'intensité lumineuse\n"
                    "- Elle **dépend linéairement** de la fréquence de la lumière\n"
                    "- Il existe une **fréquence seuil** $\\nu_0$ en dessous de laquelle aucun électron n'est éjecté, même à forte intensité\n\n"
                    "## 4. L'interprétation d'Einstein (1905)\n\n"
                    "Einstein propose que la lumière soit constituée de photons d'énergie $h\\nu$. Un électron est éjecté s'il absorbe un photon. La conservation de l'énergie donne :\n"
                    "$$\\boxed{\\;h\\nu = W + \\tfrac{1}{2} m_e v^2\\;}$$\n\n"
                    "où $W$ est le **travail de sortie** (énergie nécessaire pour extraire l'électron du métal). L'énergie cinétique maximale est :\n"
                    "$$E_{c,\\max} = h\\nu - W = h(\\nu - \\nu_0)$$\n\n"
                    "avec $\\nu_0 = W/h$ la fréquence seuil.\n\n"
                    "### Valeurs typiques de $W$\n"
                    "- Césium : $W = 2{,}1$ eV (très photosensible)\n"
                    "- Sodium : $W = 2{,}3$ eV\n"
                    "- Cuivre : $W = 4{,}7$ eV\n"
                    "- Zinc : $W = 4{,}3$ eV (UV nécessaire)\n\n"
                    "## 5. Vérification de Millikan (1916)\n\n"
                    "Millikan mesure précisément $E_{c,\\max}$ en fonction de $\\nu$. Il obtient une droite de pente $h$, confirmant la formule d'Einstein. La valeur mesurée de $h$ était en accord avec celle de Planck.\n\n"
                    "## 6. Implications\n\n"
                    "- La lumière a un aspect **corpusculaire** (photons)\n"
                    "- L'intensité lumineuse = nombre de photons, pas leur énergie individuelle\n"
                    "- La mécanique classique ne peut pas expliquer l'effet photoélectrique\n"
                    "- Cette découverte vaut à Einstein le prix Nobel en 1921\n\n"
                    "> 💡 **Astuce** : La formule $E = h\\nu$ relie une grandeur ondulatoire ($\\nu$) à une grandeur corpusculaire ($E$). C'est la première manifestation quantitative de la dualité onde-corpuscule."
                ),

                S(
                    "Loi de Planck vs Rayleigh-Jeans",
                    "import matplotlib.pyplot as plt\n"
                    "import numpy as np\n"
                    "\n"
                    "h = 6.626e-34\n"
                    "c = 2.998e8\n"
                    "kB = 1.381e-23\n"
                    "\n"
                    "# Fréquence en Hz (de 1e12 à 1e15 Hz = IR à UV)\n"
                    "nu = np.linspace(1e12, 1.5e15, 1000)\n"
                    "\n"
                    "fig, ax = plt.subplots(figsize=(10, 6))\n"
                    "\n"
                    "temperatures = [3000, 4000, 5000, 6000]  # K\n"
                    "colors = ['blue', 'green', 'orange', 'red']\n"
                    "\n"
                    "for T, color in zip(temperatures, colors):\n"
                    "    # Planck\n"
                    "    u_planck = (8*np.pi*h*nu**3/c**3) / (np.exp(h*nu/(kB*T)) - 1)\n"
                    "    # Rayleigh-Jeans (classique)\n"
                    "    u_rj = 8*np.pi*nu**2*kB*T/c**3\n"
                    "    \n"
                    "    ax.plot(nu*1e-12, u_planck*1e-15, color=color, lw=2.5, label=f'Planck, T={T} K')\n"
                    "    ax.plot(nu*1e-12, u_rj*1e-15, color=color, lw=1.5, ls='--', alpha=0.5, label=f'Rayleigh-Jeans, T={T} K' if T == 3000 else '')\n"
                    "\n"
                    "ax.set_xlabel(r'Fréquence $\\nu$ (THz)', fontsize=12)\n"
                    "ax.set_ylabel(r'Densité $u(\\nu)$ ($\\times 10^{-15}$ J·s/m³)', fontsize=12)\n"
                    "ax.set_title('Loi de Planck vs Rayleigh-Jeans : la catastrophe UV', fontsize=13)\n"
                    "ax.set_ylim(0, 8)\n"
                    "ax.legend(fontsize=9, loc='upper left')\n"
                    "ax.grid(True, alpha=0.3)\n"
                    "\n"
                    "# Annotation pour la catastrophe UV\n"
                    "ax.annotate('Catastrophe UV :\\nRayleigh-Jeans diverge',\n"
                    "            xy=(1500, 8), xytext=(800, 6),\n"
                    "            arrowprops=dict(arrowstyle='->', color='red'),\n"
                    "            fontsize=10, color='red')\n"
                    "\n"
                    "plt.tight_layout(); plt.savefig('plot.png')\n"
                    "print(f'Loi de Wien : nu_max = 2.82*kB*T/h')\n"
                    "for T in temperatures:\n"
                    "    nu_max = 2.82 * kB * T / h\n"
                    "    print(f'  T={T}K : nu_max = {nu_max*1e-12:.0f} THz (lambda = {c/nu_max*1e9:.0f} nm)')\n"
                ),

                APP(
                    "Seuil photoélectrique du sodium",
                    "Le sodium a un travail de sortie $W = 2{,}28$ eV.\n\n"
                    "1) Calculer la fréquence seuil $\\nu_0$.\n"
                    "2) Calculer la longueur d'onde seuil $\\lambda_0$.\n"
                    "3) Quelle est l'énergie cinétique maximale des photoélectrons pour une lumière de $\\lambda = 400$ nm ?\n"
                    "4) La lumière rouge ($\\lambda = 700$ nm) peut-elle éjecter des électrons du sodium ?",
                    "1) **Fréquence seuil** : $\\nu_0 = W/h = (2{,}28 \\times 1{,}602 \\times 10^{-19})/(6{,}626 \\times 10^{-34}) \\approx 5{,}51 \\times 10^{14}$ Hz.\n\n"
                    "2) **Longueur d'onde seuil** : $\\lambda_0 = c/\\nu_0 = (3 \\times 10^8)/(5{,}51 \\times 10^{14}) \\approx 544$ nm (vert-jaune).\n\n"
                    "3) **À $\\lambda = 400$ nm** (violet) : $E_{c,\\max} = h\\nu - W = hc/\\lambda - W$.\n"
                    "$$E_{c,\\max} = \\frac{6{,}626 \\times 10^{-34} \\times 3 \\times 10^8}{400 \\times 10^{-9}} - 2{,}28 \\times 1{,}602 \\times 10^{-19}$$\n"
                    "$$E_{c,\\max} = 4{,}97 \\times 10^{-19} - 3{,}65 \\times 10^{-19} = 1{,}32 \\times 10^{-19} \\text{ J} \\approx 0{,}82 \\text{ eV}$$\n\n"
                    "4) **Lumière rouge** ($\\lambda = 700$ nm) : $\\nu = c/\\lambda = 4{,}29 \\times 10^{14}$ Hz $< \\nu_0 = 5{,}51 \\times 10^{14}$ Hz. **Non**, la lumière rouge ne peut pas éjecter d'électrons du sodium, même à très forte intensité."
                ),

                MCQ(
                    "Effet photoélectrique",
                    "Si on augmente l'intensité de la lumière (sans changer la fréquence) :",
                    [
                        {"text": "L'énergie cinétique des photoélectrons augmente", "correct": False, "feedback": "Non, l'énergie cinétique ne dépend que de la fréquence."},
                        {"text": "Le nombre de photoélectrons augmente", "correct": True, "feedback": "Exact ! Plus de photons → plus d'électrons éjectés, mais même énergie."},
                        {"text": "Aucun effet", "correct": False},
                        {"text": "L'effet photoélectrique disparaît", "correct": False}
                    ],
                    explanation="L'intensité = nombre de photons. Chaque photon a la même énergie $h\\nu$. Plus de photons → plus d'électrons, mais même $E_c$."
                ),

                FB(
                    "Formules de l'effet photoélectrique",
                    "L'énergie d'un photon : $E = h{{blank_1}}$ où $\\nu$ est la fréquence.\\n\\n"
                    "L'équation d'Einstein : $h\\nu = W + {{blank_2}}$ où $W$ est le travail de sortie.\\n\\n"
                    "La fréquence seuil vaut $\\nu_0 = {{blank_3}}/h$.",
                    {"blank_1": ["nu", "ν"], "blank_2": ["E_c", "Ec", "1/2*m*v^2", "mv²/2"], "blank_3": ["W"]},
                    explanation="$E = h\\nu$, équation $h\\nu = W + E_c$, fréquence seuil $\\nu_0 = W/h$."
                ),

                TF(
                    "Vrai ou Faux ? Corps noir et photoélectrique",
                    [
                        {"statement": "La loi de Rayleigh-Jeans diverge à haute fréquence.", "is_true": True},
                        {"statement": "Planck a proposé que l'échange d'énergie se fait par quanta discrets.", "is_true": True},
                        {"statement": "L'énergie cinétique des photoélectrons dépend de l'intensité lumineuse.", "is_true": False, "statement_note": "Elle ne dépend que de la fréquence. L'intensité n'affecte que le nombre d'électrons."},
                        {"statement": "Il existe une fréquence seuil en dessous de laquelle aucun électron n'est éjecté.", "is_true": True},
                        {"statement": "Einstein a reçu le prix Nobel pour la relativité restreinte.", "is_true": False, "statement_note": "Il l'a reçu en 1921 pour l'effet photoélectrique."}
                    ]
                ),
            ],
        },
    ],
})


# ═════════════════════════════════════════════════════════════════════════════
# MODULE 1 — FORMALISME MATHÉMATIQUE
# ═════════════════════════════════════════════════════════════════════════════
COURSE_STRUCTURE.append({
    "order": 1,
    "title": "Formalisme mathématique · Espaces de Hilbert et opérateurs",
    "description": (
        "Espace de Hilbert, notation bra-ket de Dirac, opérateurs "
        "linéaires, observable, valeurs propres, vecteurs propres, "
        "évolution temporelle."
    ),
    "lessons": [

        # ── Leçon 1.1 : Espace de Hilbert et notation bra-ket ─────────────
        {
            "order": 0,
            "title": "Espace de Hilbert et notation bra-ket",
            "slug": "espace-hilbert-bra-ket",
            "minutes": 55,
            "blocks": [
                T(
                    "# Espace de Hilbert et notation bra-ket\n\n"
                    "## 1. L'espace des états quantiques\n\n"
                    "En mécanique quantique, l'état d'un système est décrit par un **vecteur** appartenant à un espace vectoriel complexe appelé **espace de Hilbert** $\\mathcal{H}$. Les propriétés requises :\n\n"
                    "- Espace vectoriel sur $\\mathbb{C}$\n"
                    "- Muni d'un **produit scalaire** hermitien\n"
                    "- **Complet** (toute suite de Cauchy converge)\n"
                    "- De dimension finie ou infinie dénombrable\n\n"
                    "## 2. Notation de Dirac (bra-ket)\n\n"
                    "Dirac a introduit une notation très compacte :\n\n"
                    "- Un vecteur d'état est noté $|\\psi\\rangle$ (**ket**)\n"
                    "- Le vecteur dual (conjugué hermitien) est noté $\\langle\\psi|$ (**bra**)\n"
                    "- Le produit scalaire de $|\\phi\\rangle$ et $|\\psi\\rangle$ est $\\langle\\phi|\\psi\\rangle$\n\n"
                    "## 3. Propriétés du produit scalaire\n\n"
                    "$$\\langle\\phi|\\psi\\rangle = \\langle\\psi|\\phi\\rangle^*$$\n"
                    "$$\\langle\\psi|\\psi\\rangle \\geq 0, \\quad \\langle\\psi|\\psi\\rangle = 0 \\iff |\\psi\\rangle = 0$$\n"
                    "$$\\langle\\phi|\\alpha\\psi + \\beta\\chi\\rangle = \\alpha\\langle\\phi|\\psi\\rangle + \\beta\\langle\\phi|\\chi\\rangle$$\n\n"
                    "## 4. Normalisation\n\n"
                    "Un état physique est défini à un facteur de phase près. On impose la **normalisation** :\n"
                    "$$\\boxed{\\;\\langle\\psi|\\psi\\rangle = 1\\;}$$\n\n"
                    "Si $|\\psi\\rangle$ n'est pas normalisé, on le remplace par $|\\psi\\rangle/\\sqrt{\\langle\\psi|\\psi\\rangle}$.\n\n"
                    "## 5. Bases orthonormées\n\n"
                    "Une base orthonormée $\\{|u_n\\rangle\\}_{n}$ vérifie :\n"
                    "$$\\langle u_m|u_n\\rangle = \\delta_{mn}$$\n\n"
                    "où $\\delta_{mn}$ est le symbole de Kronecker. Tout vecteur $|\\psi\\rangle$ se décompose :\n"
                    "$$|\\psi\\rangle = \\sum_n c_n |u_n\\rangle, \\quad c_n = \\langle u_n|\\psi\\rangle$$\n\n"
                    "La condition de normalisation devient $\\sum_n |c_n|^2 = 1$.\n\n"
                    "## 6. Relation de fermeture (résolution de l'identité)\n\n"
                    "$$\\boxed{\\;\\sum_n |u_n\\rangle\\langle u_n| = \\mathbb{1}\\;}$$\n\n"
                    "C'est l'identité opératorielle : appliquée à $|\\psi\\rangle$, redonne $|\\psi\\rangle$.\n\n"
                    "## 7. Cas continu\n\n"
                    "Pour une base continue (ex. position $|x\\rangle$), la somme devient une intégrale :\n"
                    "$$\\int |x\\rangle\\langle x|\\, dx = \\mathbb{1}$$\n"
                    "$$|\\psi\\rangle = \\int \\psi(x) |x\\rangle\\, dx, \\quad \\psi(x) = \\langle x|\\psi\\rangle$$\n\n"
                    "La fonction $\\psi(x) = \\langle x|\\psi\\rangle$ est la **fonction d'onde** dans la représentation de position.\n\n"
                    "## 8. Inégalité de Cauchy-Schwarz\n\n"
                    "$$|\\langle\\phi|\\psi\\rangle|^2 \\leq \\langle\\phi|\\phi\\rangle \\cdot \\langle\\psi|\\psi\\rangle$$\n\n"
                    "Égalité si et seulement si $|\\phi\\rangle$ et $|\\psi\\rangle$ sont colinéaires.\n\n"
                    "> 💡 **Astuce** : La notation bra-ket unifie vecteurs discrétisés et fonctions d'onde. $|\\psi\\rangle$ est l'objet abstrait, $\\psi(x) = \\langle x|\\psi\\rangle$ est sa représentation dans la base de position."
                ),

                S(
                    "Visualisation d'un ket dans une base orthonormée",
                    "import matplotlib.pyplot as plt\n"
                    "import numpy as np\n"
                    "\n"
                    "# Un état |psi> dans une base {|u1>, |u2>} à 2 dimensions\n"
                    "# c1 = <u1|psi>, c2 = <u2|psi> — complexes en général\n"
                    "c1 = 0.8 + 0.2j  # coefficient sur |u1>\n"
                    "c2 = 0.5 - 0.3j  # coefficient sur |u2>\n"
                    "# Vérification de la normalisation\n"
                    "norm = abs(c1)**2 + abs(c2)**2\n"
                    "c1, c2 = c1/np.sqrt(norm), c2/np.sqrt(norm)\n"
                    "\n"
                    "fig, axes = plt.subplots(1, 2, figsize=(13, 5))\n"
                    "\n"
                    "# Gauche : représentation dans la base |u1>, |u2>\n"
                    "ax = axes[0]\n"
                    "ax.set_xlim(-0.2, 1.2); ax.set_ylim(-0.2, 1.2)\n"
                    "# Axes u1, u2\n"
                    "ax.arrow(0, 0, 1, 0, head_width=0.03, color='blue', lw=2)\n"
                    "ax.arrow(0, 0, 0, 1, head_width=0.03, color='red', lw=2)\n"
                    "ax.text(1.05, -0.05, r'$|u_1\\rangle$', fontsize=14, color='blue')\n"
                    "ax.text(-0.1, 1.05, r'$|u_2\\rangle$', fontsize=14, color='red')\n"
                    "# État |psi> : parties réelles et imaginaires\n"
                    "ax.arrow(0, 0, c1.real, c1.imag, head_width=0.04, color='green', lw=2.5, length_includes_head=True)\n"
                    "ax.text(c1.real+0.05, c1.imag+0.05, r'$c_1 = \\langle u_1|\\psi\\rangle$', fontsize=11, color='green')\n"
                    "ax.set_title(r'Coefficient $c_1 = \\langle u_1|\\psi\\rangle$ dans le plan complexe', fontsize=11)\n"
                    "ax.set_xlabel('Partie réelle'); ax.set_ylabel('Partie imaginaire')\n"
                    "ax.set_aspect('equal'); ax.grid(True, alpha=0.3)\n"
                    "\n"
                    "# Droite : barres des |c_n|²\n"
                    "ax = axes[1]\n"
                    "n_labels = [r'$|c_1|^2$', r'$|c_2|^2$']\n"
                    "probs = [abs(c1)**2, abs(c2)**2]\n"
                    "ax.bar(n_labels, probs, color=['green', 'orange'], alpha=0.7, edgecolor='black')\n"
                    "ax.set_ylabel(r'Probabilité $|c_n|^2$', fontsize=12)\n"
                    "ax.set_title(rf'Normalisation : $\\sum |c_n|^2 = {sum(probs):.3f}$', fontsize=12)\n"
                    "ax.grid(True, alpha=0.3, axis='y')\n"
                    "ax.set_ylim(0, 1)\n"
                    "for i, p in enumerate(probs):\n"
                    "    ax.text(i, p+0.02, f'{p:.3f}', ha='center', fontsize=11)\n"
                    "\n"
                    "plt.tight_layout(); plt.savefig('plot.png')\n"
                    "print(f'c1 = {c1:.4f}, c2 = {c2:.4f}')\n"
                    "print(f'|c1|² + |c2|² = {abs(c1)**2 + abs(c2)**2:.4f} (normalisation OK)')\n"
                ),

                APP(
                    "Décomposition dans une base",
                    "Soit un état $|\\psi\\rangle$ dans une base orthonormée $\\{|u_1\\rangle, |u_2\\rangle, |u_3\\rangle\\}$ avec :\n"
                    "$|\\psi\\rangle = (1+i)|u_1\\rangle + 2|u_2\\rangle - i|u_3\\rangle$\n\n"
                    "1) Calculer la norme $\\langle\\psi|\\psi\\rangle$.\n"
                    "2) Normaliser $|\\psi\\rangle$.\n"
                    "3) Calculer la probabilité de trouver le système dans l'état $|u_2\\rangle$.",
                    "1) **Norme** : $\\langle\\psi|\\psi\\rangle = |1+i|^2 + |2|^2 + |-i|^2 = 2 + 4 + 1 = 7$.\n\n"
                    "2) **État normalisé** : $|\\psi_N\\rangle = |\\psi\\rangle/\\sqrt{7}$, soit :\n"
                    "$$|\\psi_N\\rangle = \\frac{1+i}{\\sqrt{7}}|u_1\\rangle + \\frac{2}{\\sqrt{7}}|u_2\\rangle - \\frac{i}{\\sqrt{7}}|u_3\\rangle$$\n\n"
                    "3) **Probabilité de $|u_2\\rangle$** : $P_2 = |\\langle u_2|\\psi_N\\rangle|^2 = |2/\\sqrt{7}|^2 = 4/7 \\approx 0{,}571$.\n\n"
                    "Vérification : $P_1 + P_2 + P_3 = 2/7 + 4/7 + 1/7 = 7/7 = 1$ ✓"
                ),

                MCQ(
                    "Produit scalaire hermitien",
                    "Quelle est la propriété du produit scalaire $\\langle\\phi|\\psi\\rangle$ ?",
                    [
                        {"text": "$\\langle\\phi|\\psi\\rangle = \\langle\\psi|\\phi\\rangle$", "correct": False, "feedback": "Non, il faut le conjuguer."},
                        {"text": "$\\langle\\phi|\\psi\\rangle = \\langle\\psi|\\phi\\rangle^*$", "correct": True, "feedback": "Exact ! Hermitien = conjugué symétrique."},
                        {"text": "$\\langle\\phi|\\psi\\rangle = -\\langle\\psi|\\phi\\rangle$", "correct": False, "feedback": "C'est antisymétrique, pas hermitien."},
                        {"text": "$\\langle\\phi|\\psi\\rangle = 0$", "correct": False}
                    ],
                    explanation="Le produit scalaire hermitien vérifie $\\langle\\phi|\\psi\\rangle = \\langle\\psi|\\phi\\rangle^*$."
                ),

                FB(
                    "Relation de fermeture",
                    "Pour une base orthonormée discrète $\\{|u_n\\rangle\\}$, la relation de fermeture est $\\sum_n |u_n\\rangle\\langle u_n| = {{blank_1}}$.\\n\\n"
                    "Pour une base continue $\\{|x\\rangle\\}$, elle devient $\\int |x\\rangle\\langle x|\\, dx = {{blank_2}}$.\\n\\n"
                    "La fonction d'onde est $\\psi(x) = \\langle {{blank_3}} | \\psi \\rangle$.",
                    {"blank_1": ["1", "I", "\\mathbb{1}", "identité"], "blank_2": ["1", "I", "\\mathbb{1}", "identité"], "blank_3": ["x"]},
                    explanation="Fermeture : $\\sum_n |u_n\\rangle\\langle u_n| = \\mathbb{1}$ (discret), $\\int |x\\rangle\\langle x|\\,dx = \\mathbb{1}$ (continu). Fonction d'onde : $\\psi(x) = \\langle x|\\psi\\rangle$."
                ),

                TF(
                    "Vrai ou Faux ? Formalisme",
                    [
                        {"statement": "Un état quantique est représenté par un vecteur dans un espace de Hilbert.", "is_true": True},
                        {"statement": "Le produit scalaire hermitien vérifie $\\langle\\phi|\\psi\\rangle = \\langle\\psi|\\phi\\rangle$.", "is_true": False, "statement_note": "C'est $\\langle\\phi|\\psi\\rangle = \\langle\\psi|\\phi\\rangle^*$."},
                        {"statement": "Un état physique est défini à un facteur près.", "is_true": True, "statement_note": "À un facteur de phase complexe près, qu'on fixe par normalisation."},
                        {"statement": "La relation de fermeture exprime l'identité comme une somme de projecteurs.", "is_true": True},
                        {"statement": "$\\langle u_m|u_n\\rangle = 0$ pour une base orthonormée.", "is_true": False, "statement_note": "C'est $\\delta_{mn}$ : 0 si $m \\neq n$, 1 si $m = n$."}
                    ]
                ),
            ],
        },

        # ── Leçon 1.2 : Opérateurs et observables ──────────────────────────
        {
            "order": 1,
            "title": "Opérateurs et observables",
            "slug": "operateurs-observables",
            "minutes": 50,
            "blocks": [
                T(
                    "# Opérateurs et observables\n\n"
                    "## 1. Définition\n\n"
                    "Un **opérateur linéaire** $A$ agit sur les kets : $|\\psi\\rangle \\mapsto A|\\psi\\rangle$. Linéarité :\n"
                    "$$A(\\alpha|\\psi\\rangle + \\beta|\\phi\\rangle) = \\alpha A|\\psi\\rangle + \\beta A|\\phi\\rangle$$\n\n"
                    "## 2. Opérateur adjoint\n\n"
                    "L'**adjoint** $A^\\dagger$ est défini par :\n"
                    "$$\\langle\\phi|A^\\dagger|\\psi\\rangle = \\langle\\psi|A|\\phi\\rangle^*$$\n\n"
                    "Propriétés :\n"
                    "- $(AB)^\\dagger = B^\\dagger A^\\dagger$\n"
                    "- $(A^\\dagger)^\\dagger = A$\n"
                    "- $(\\alpha A)^\\dagger = \\alpha^* A^\\dagger$\n\n"
                    "## 3. Opérateurs hermitiens\n\n"
                    "Un opérateur est **hermitien** (ou auto-adjoint) si $A = A^\\dagger$.\n\n"
                    "Propriétés fondamentales :\n"
                    "- Les **valeurs propres** sont **réelles**\n"
                    "- Les **vecteurs propres** associés à des valeurs propres distinctes sont **orthogonaux**\n"
                    "- On peut former une **base orthonormée** de vecteurs propres\n\n"
                    "$$A|u_n\\rangle = a_n |u_n\\rangle, \\quad a_n \\in \\mathbb{R}, \\quad \\langle u_m|u_n\\rangle = \\delta_{mn}$$\n\n"
                    "## 4. Observables\n\n"
                    "Une **observable** est un opérateur hermitien dont les vecteurs propres forment une base complète de l'espace de Hilbert. À toute grandeur physique mesurable (position, quantité de mouvement, énergie, spin...) est associée une observable.\n\n"
                    "### Observables fondamentales\n"
                    "- **Position** : $\\hat{x}$, valeur propre $x$ (continue)\n"
                    "- **Quantité de mouvement** : $\\hat{p}$, valeur propre $p$\n"
                    "- **Énergie** : $\\hat{H}$ (hamiltonien)\n"
                    "- **Moment cinétique** : $\\hat{L}$\n\n"
                    "## 5. Représentation de position\n\n"
                    "Dans la base $|x\\rangle$, les opérateurs fondamentaux agissent comme :\n"
                    "$$\\hat{x} \\psi(x) = x\\, \\psi(x)$$\n"
                    "$$\\hat{p} \\psi(x) = -i\\hbar \\frac{\\partial \\psi}{\\partial x}(x)$$\n\n"
                    "## 6. Relations de commutation\n\n"
                    "Le **commutateur** de deux opérateurs : $[A, B] = AB - BA$.\n\n"
                    "Relation fondamentale :\n"
                    "$$\\boxed{\\;[\\hat{x}, \\hat{p}] = i\\hbar\\;}$$\n\n"
                    "C'est le **cœur de la mécanique quantique**. Si $[A, B] = 0$, les deux observables peuvent être mesurées simultanément avec une précision arbitraire. Sinon, il y a une limite (Heisenberg).\n\n"
                    "## 7. Diagonalisation\n\n"
                    "Tout opérateur hermitien peut s'écrire :\n"
                    "$$A = \\sum_n a_n |u_n\\rangle\\langle u_n|$$\n\n"
                    "C'est la **décomposition spectrale**. Les $|u_n\\rangle$ forment une base orthonormée.\n\n"
                    "## 8. Projecteurs\n\n"
                    "Le projecteur sur le vecteur propre $|u_n\\rangle$ est :\n"
                    "$$P_n = |u_n\\rangle\\langle u_n|$$\n\n"
                    "Propriétés : $P_n^2 = P_n$, $P_n^\\dagger = P_n$, $P_n P_m = \\delta_{mn} P_n$.\n\n"
                    "> 💡 **Astuce** : Mesurer une observable revient à décomposer l'état sur ses vecteurs propres. Les valeurs possibles sont les valeurs propres."
                ),

                S(
                    "Vecteurs propres et valeurs propres d'un spin 1/2",
                    "import matplotlib.pyplot as plt\n"
                    "import numpy as np\n"
                    "\n"
                    "# Matrices de Pauli (opérateurs de spin)\n"
                    "sigma_x = np.array([[0, 1], [1, 0]], dtype=complex)\n"
                    "sigma_y = np.array([[0, -1j], [1j, 0]], dtype=complex)\n"
                    "sigma_z = np.array([[1, 0], [0, -1]], dtype=complex)\n"
                    "\n"
                    "fig, axes = plt.subplots(1, 3, figsize=(13, 4.5))\n"
                    "\n"
                    "for ax, sigma, name in zip(axes, [sigma_x, sigma_y, sigma_z], ['$\\\\sigma_x$', '$\\\\sigma_y$', '$\\\\sigma_z$']):\n"
                    "    # Valeurs et vecteurs propres\n"
                    "    vals, vecs = np.linalg.eigh(sigma)\n"
                    "    \n"
                    "    # Représenter les vecteurs propres dans le plan complexe\n"
                    "    for i, (val, vec) in enumerate(zip(vals, vecs.T)):\n"
                    "        color = 'red' if val > 0 else 'blue'\n"
                    "        # Composantes (réelles, imaginaires) des deux amplitudes\n"
                    "        ax.plot([0, vec[0].real], [0, vec[0].imag], color=color, lw=2, label=f'λ={val:+.0f}, c1')\n"
                    "        ax.plot([0, vec[1].real], [0, vec[1].imag], color=color, lw=2, ls='--', label=f'λ={val:+.0f}, c2')\n"
                    "    \n"
                    "    ax.set_xlim(-1.2, 1.2); ax.set_ylim(-1.2, 1.2)\n"
                    "    ax.set_xlabel('Réelle'); ax.set_ylabel('Imaginaire')\n"
                    "    ax.set_title(f'Vecteurs propres de {name}')\n"
                    "    ax.axhline(0, color='gray', lw=0.5); ax.axvline(0, color='gray', lw=0.5)\n"
                    "    ax.set_aspect('equal'); ax.grid(True, alpha=0.3)\n"
                    "    ax.legend(fontsize=8, loc='upper right')\n"
                    "\n"
                    "plt.suptitle('Valeurs propres ±1 et vecteurs propres des matrices de Pauli', fontsize=12, y=1.02)\n"
                    "plt.tight_layout(); plt.savefig('plot.png')\n"
                    "print('Valeurs propres des matrices de Pauli : toujours +1 et -1')\n"
                    "print('=> Le spin suivant un axe ne peut prendre que 2 valeurs (quantification)')\n"
                ),

                APP(
                    "Commutateur de x et p",
                    "On considère les opérateurs $\\hat{x}$ et $\\hat{p} = -i\\hbar \\frac{d}{dx}$ agissant sur les fonctions.\n\n"
                    "1) Calculer $[\\hat{x}, \\hat{p}]\\psi(x)$.\n"
                    "2) En déduire $[\\hat{x}, \\hat{p}]$.",
                    "1) **Calcul** : on applique $\\hat{x}\\hat{p} - \\hat{p}\\hat{x}$ à une fonction $\\psi(x)$.\n"
                    "$$\\hat{x}\\hat{p}\\psi = x \\cdot (-i\\hbar \\psi') = -i\\hbar x \\psi'$$\n"
                    "$$\\hat{p}\\hat{x}\\psi = -i\\hbar \\frac{d}{dx}(x\\psi) = -i\\hbar (\\psi + x\\psi')$$\n"
                    "$$[\\hat{x}, \\hat{p}]\\psi = \\hat{x}\\hat{p}\\psi - \\hat{p}\\hat{x}\\psi = -i\\hbar x\\psi' - (-i\\hbar\\psi - i\\hbar x\\psi') = i\\hbar \\psi$$\n\n"
                    "2) **Conclusion** : comme $[\\hat{x}, \\hat{p}]\\psi = i\\hbar\\psi$ pour toute $\\psi$, on a :\n"
                    "$$\\boxed{\\;[\\hat{x}, \\hat{p}] = i\\hbar\\;}$$\n\n"
                    "Ce commutateur non nul est à l'origine du principe d'incertitude de Heisenberg : on ne peut pas mesurer simultanément $x$ et $p$ avec une précision arbitraire."
                ),

                MCQ(
                    "Opérateur hermitien",
                    "Un opérateur hermitien $A$ vérifie :",
                    [
                        {"text": "$A = -A^\\dagger$ (anti-hermitien)", "correct": False},
                        {"text": "$A = A^\\dagger$", "correct": True, "feedback": "Exact ! C'est la définition."},
                        {"text": "$A = A^{-1}$", "correct": False, "feedback": "C'est un opérateur unitaire."},
                        {"text": "$A = 0$", "correct": False}
                    ],
                    explanation="Hermitien = auto-adjoint : $A = A^\\dagger$."
                ),

                FB(
                    "Commutateur et opérateurs",
                    "Le commutateur de $\\hat{x}$ et $\\hat{p}$ vaut $[\\hat{x}, \\hat{p}] = i{{blank_1}}$.\\n\\n"
                    "Dans la représentation de position, $\\hat{p} = -i\\hbar \\frac{d}{{{blank_2}}}$.\\n\\n"
                    "Un opérateur hermitien a des valeurs propres {{blank_3}}.",
                    {"blank_1": ["hbar", "ℏ"], "blank_2": ["dx"], "blank_3": ["réelles", "reelles", "réel"]},
                    explanation="$[\\hat{x}, \\hat{p}] = i\\hbar$, $\\hat{p} = -i\\hbar d/dx$, valeurs propres réelles."
                ),

                TF(
                    "Vrai ou Faux ? Opérateurs",
                    [
                        {"statement": "Un opérateur hermitien a des valeurs propres réelles.", "is_true": True},
                        {"statement": "Les vecteurs propres d'un opérateur hermitien sont toujours orthogonaux.", "is_true": False, "statement_note": "Seulement ceux associés à des valeurs propres distinctes ; on peut orthonormaliser ceux d'une même valeur propre."},
                        {"statement": "$[\\hat{x}, \\hat{p}] = 0$.", "is_true": False, "statement_note": "C'est $i\\hbar$."},
                        {"statement": "Une observable est un opérateur hermitien dont les vecteurs propres forment une base.", "is_true": True},
                        {"statement": "Si $[A, B] = 0$, on peut diagonaliser simultanément $A$ et $B$.", "is_true": True}
                    ]
                ),
            ],
        },

        # ── Leçon 1.3 : Équation de Schrödinger ────────────────────────────
        {
            "order": 2,
            "title": "Équation de Schrödinger et évolution temporelle",
            "slug": "equation-schrodinger",
            "minutes": 55,
            "blocks": [
                T(
                    "# Équation de Schrödinger et évolution temporelle\n\n"
                    "## 1. L'équation de Schrödinger dépendante du temps\n\n"
                    "L'évolution temporelle d'un état quantique est régie par :\n"
                    "$$\\boxed{\\;i\\hbar \\frac{\\partial}{\\partial t}|\\psi(t)\\rangle = \\hat{H}|\\psi(t)\\rangle\\;}$$\n\n"
                    "où $\\hat{H}$ est le **hamiltonien** (opérateur énergie). C'est l'équation fondamentale de la mécanique quantique non relativiste, postulée par Schrödinger en 1926.\n\n"
                    "## 2. Forme dans la représentation de position\n\n"
                    "Pour une particule de masse $m$ dans un potentiel $V(x, t)$ :\n"
                    "$$\\hat{H} = -\\frac{\\hbar^2}{2m}\\nabla^2 + V(\\vec{r}, t)$$\n\n"
                    "L'équation devient :\n"
                    "$$i\\hbar \\frac{\\partial \\psi}{\\partial t} = -\\frac{\\hbar^2}{2m}\\nabla^2\\psi + V(\\vec{r}, t)\\psi$$\n\n"
                    "En 1D : $i\\hbar \\partial_t \\psi = -\\frac{\\hbar^2}{2m}\\partial_x^2 \\psi + V(x,t)\\psi$.\n\n"
                    "## 3. Conservation de la norme\n\n"
                    "L'équation de Schrödinger conserve la norme :\n"
                    "$$\\frac{d}{dt}\\langle\\psi|\\psi\\rangle = 0$$\n\n"
                    "**Démonstration** : $\\frac{d}{dt}\\langle\\psi|\\psi\\rangle = \\langle\\dot{\\psi}|\\psi\\rangle + \\langle\\psi|\\dot{\\psi}\\rangle$. Or $|\\dot{\\psi}\\rangle = \\frac{1}{i\\hbar}\\hat{H}|\\psi\\rangle$ et $\\langle\\dot{\\psi}| = -\\frac{1}{i\\hbar}\\langle\\psi|\\hat{H}^\\dagger = -\\frac{1}{i\\hbar}\\langle\\psi|\\hat{H}$ (car $\\hat{H}$ hermitien). Donc $\\frac{d}{dt}\\langle\\psi|\\psi\\rangle = -\\frac{1}{i\\hbar}\\langle\\psi|\\hat{H}|\\psi\\rangle + \\frac{1}{i\\hbar}\\langle\\psi|\\hat{H}|\\psi\\rangle = 0$.\n\n"
                    "## 4. Solutions à énergie définie (états stationnaires)\n\n"
                    "Si $V$ ne dépend pas du temps, on cherche des solutions de la forme $\\psi(x, t) = \\phi(x)\\, f(t)$. L'équation se sépare :\n"
                    "$$i\\hbar \\frac{\\dot{f}}{f} = \\frac{1}{\\phi}\\hat{H}\\phi = E$$\n\n"
                    "où $E$ est une constante. On obtient deux équations :\n"
                    "- Temporelle : $f(t) = e^{-iEt/\\hbar}$\n"
                    "- Spatial (Schrödinger indépendant du temps) : $\\hat{H}\\phi = E\\phi$\n\n"
                    "## 5. Équation de Schrödinger indépendante du temps\n\n"
                    "$$\\boxed{\\;\\hat{H}\\phi_n(\\vec{r}) = E_n \\phi_n(\\vec{r})\\;}$$\n\n"
                    "Les solutions $\\phi_n$ sont les **états stationnaires** (vecteurs propres de $\\hat{H}$), et les $E_n$ sont les **niveaux d'énergie**.\n\n"
                    "La solution générale est une superposition :\n"
                    "$$\\psi(\\vec{r}, t) = \\sum_n c_n \\phi_n(\\vec{r})\\, e^{-iE_n t/\\hbar}$$\n\n"
                    "## 6. Opérateur d'évolution\n\n"
                    "Formellement, $|\\psi(t)\\rangle = U(t, t_0)|\\psi(t_0)\\rangle$ avec :\n"
                    "$$U(t, t_0) = e^{-i\\hat{H}(t-t_0)/\\hbar}$$\n\n"
                    "Propriétés : $U^\\dagger U = \\mathbb{1}$ (unitaire), $U(t_0, t_0) = \\mathbb{1}$.\n\n"
                    "## 7. Densité de probabilité\n\n"
                    "La quantité $|\\psi(x, t)|^2$ est la **densité de probabilité** de trouver la particule en $x$ à l'instant $t$. La conservation de la norme garantit que la probabilité totale est 1.\n\n"
                    "## 8. Courant de probabilité\n\n"
                    "En 1D : $j(x, t) = \\frac{\\hbar}{2mi}(\\psi^* \\partial_x \\psi - \\psi \\partial_x \\psi^*)$\n\n"
                    "Équation de continuité : $\\partial_t |\\psi|^2 + \\partial_x j = 0$ (conservation locale).\n\n"
                    "> 💡 **Astuce** : Pour un potentiel indépendant du temps, sépare temporel et spatial. Les états stationnaires $\\phi_n$ oscillent en phase $e^{-iE_n t/\\hbar}$, mais $|\\psi|^2$ reste constant."
                ),

                S(
                    "Évolution d'un paquet d'ondes gaussien",
                    "import matplotlib.pyplot as plt\n"
                    "import numpy as np\n"
                    "\n"
                    "# Paquet d'ondes gaussien libre (V=0)\n"
                    "# psi(x,t) = (2*pi*sigma^2)^(-1/4) * exp(-(x-v0*t)^2/(4*sigma^2)) * exp(i*k0*x)\n"
                    "hbar = 1.0\n"
                    "m = 1.0\n"
                    "sigma = 1.0\n"
                    "k0 = 5.0\n"
                    "v0 = hbar*k0/m\n"
                    "\n"
                    "x = np.linspace(-10, 20, 1000)\n"
                    "\n"
                    "fig, axes = plt.subplots(2, 2, figsize=(12, 8))\n"
                    "times = [0, 0.5, 1.0, 2.0]\n"
                    "\n"
                    "for ax, t in zip(axes.flat, times):\n"
                    "    # Paquet gaussien élargissant avec le temps\n"
                    "    sigma_t = np.sqrt(sigma**2 + (hbar*t/(2*m*sigma))**2)\n"
                    "    psi = (2*np.pi*sigma_t**2)**(-0.25) * np.exp(-(x - v0*t)**2/(4*sigma_t**2)) * np.exp(1j*k0*x)\n"
                    "    prob = np.abs(psi)**2\n"
                    "    \n"
                    "    ax.plot(x, prob, 'b-', lw=2.5)\n"
                    "    ax.fill_between(x, 0, prob, alpha=0.2, color='blue')\n"
                    "    ax.axvline(v0*t, color='red', ls='--', alpha=0.5, label=f'Centre: x={v0*t:.1f}')\n"
                    "    ax.set_xlim(-5, 20); ax.set_ylim(0, 0.6)\n"
                    "    ax.set_title(f't = {t}', fontsize=12)\n"
                    "    ax.set_xlabel(r'$x$')\n"
                    "    ax.set_ylabel(r'$|\\psi|^2$')\n"
                    "    ax.legend(fontsize=9)\n"
                    "    ax.grid(True, alpha=0.3)\n"
                    "\n"
                    "plt.suptitle(r'Évolution d\\'un paquet d\\'ondes libre : translation + élargissement', fontsize=13)\n"
                    "plt.tight_layout(); plt.savefig('plot.png')\n"
                    "print(f'Vitesse de groupe: v0 = hbar*k0/m = {v0}')\n"
                    "print(f'Le paquet se déplace à v0 et s\\'élargit (dispersion).')\n"
                ),

                APP(
                    "État stationnaire dans un puits",
                    "On considère un électron dans un puits infini de largeur $L = 1$ nm. Les niveaux d'énergie sont $E_n = n^2 \\pi^2 \\hbar^2/(2m_e L^2)$.\n\n"
                    "1) Calculer $E_1$ en eV.\n"
                    "2) Donner l'expression de $\\psi_1(x, t)$.\n"
                    "3) Que vaut $|\\psi_1(x, t)|^2$ ? Dépend-il du temps ?",
                    "1) **Énergie fondamentale** :\n"
                    "$$E_1 = \\frac{\\pi^2 \\hbar^2}{2 m_e L^2} = \\frac{\\pi^2 \\times (1{,}055 \\times 10^{-34})^2}{2 \\times 9{,}11 \\times 10^{-31} \\times (10^{-9})^2}$$\n"
                    "$$E_1 = \\frac{1{,}097 \\times 10^{-67}}{1{,}822 \\times 10^{-48}} \\approx 6{,}02 \\times 10^{-20} \\text{ J} \\approx 0{,}376 \\text{ eV}$$\n\n"
                    "2) **Fonction d'onde** : pour le niveau $n=1$, $\\phi_1(x) = \\sqrt{2/L}\\sin(\\pi x/L)$, donc :\n"
                    "$$\\psi_1(x, t) = \\sqrt{\\frac{2}{L}}\\sin\\!\\left(\\frac{\\pi x}{L}\\right) e^{-iE_1 t/\\hbar}$$\n\n"
                    "3) **Densité de probabilité** :\n"
                    "$$|\\psi_1(x, t)|^2 = \\frac{2}{L}\\sin^2\\!\\left(\\frac{\\pi x}{L}\\right) \\cdot |e^{-iE_1 t/\\hbar}|^2 = \\frac{2}{L}\\sin^2\\!\\left(\\frac{\\pi x}{L}\\right)$$\n\n"
                    "La densité **ne dépend pas du temps** : c'est un état stationnaire. La phase $e^{-iEt/\\hbar}$ disparaît dans le module."
                ),

                MCQ(
                    "Équation de Schrödinger",
                    "L'équation de Schrödinger dépendante du temps s'écrit :",
                    [
                        {"text": "$i\\hbar \\partial_t |\\psi\\rangle = \\hat{H}|\\psi\\rangle$", "correct": True, "feedback": "Exact ! C'est la forme postulée."},
                        {"text": "$\\hbar \\partial_t |\\psi\\rangle = \\hat{H}|\\psi\\rangle$", "correct": False, "feedback": "Il manque le $i$."},
                        {"text": "$i\\hbar \\partial_t |\\psi\\rangle = \\hat{p}|\\psi\\rangle$", "correct": False, "feedback": "C'est $\\hat{H}$, pas $\\hat{p}$."},
                        {"text": "$i\\hbar \\partial_t |\\psi\\rangle = V|\\psi\\rangle$", "correct": False, "feedback": "Le hamiltonien inclut aussi l'énergie cinétique."}
                    ],
                    explanation="$i\\hbar \\partial_t |\\psi\\rangle = \\hat{H}|\\psi\\rangle$ avec $\\hat{H} = \\hat{p}^2/(2m) + V$."
                ),

                FB(
                    "États stationnaires",
                    "Pour un potentiel indépendant du temps, les états stationnaires ont la forme $\\psi_n(x,t) = \\phi_n(x) \\cdot e^{{{blank_1}}}$ où $E_n$ est l'énergie.\\n\\n"
                    "L'équation aux valeurs propres est $\\hat{H}\\phi_n = {{blank_2}} \\phi_n$.\\n\\n"
                    "La densité de probabilité d'un état stationnaire ne dépend pas du {{blank_3}}.",
                    {"blank_1": ["-i*E_n*t/hbar", "-iE_n t/hbar", "-iE_nt/ℏ"], "blank_2": ["E_n", "En"], "blank_3": ["temps", "t"]},
                    explanation="$\\psi_n = \\phi_n e^{-iE_n t/\\hbar}$, $\\hat{H}\\phi_n = E_n\\phi_n$, $|\\psi_n|^2 = |\\phi_n|^2$ (indépendant du temps)."
                ),

                TF(
                    "Vrai ou Faux ? Schrödinger",
                    [
                        {"statement": "L'équation de Schrödinger conserve la norme.", "is_true": True},
                        {"statement": "Les états stationnaires ont une densité de probabilité indépendante du temps.", "is_true": True},
                        {"statement": "L'opérateur d'évolution $U(t, t_0)$ est hermitien.", "is_true": False, "statement_note": "Il est unitaire ($U^\\dagger U = 1$), pas hermitien."},
                        {"statement": "Pour $V$ indépendant du temps, on peut séparer variables spatiale et temporelle.", "is_true": True},
                        {"statement": "La densité de probabilité $|\\psi|^2$ dépend toujours du temps.", "is_true": False, "statement_note": "Pour un état stationnaire, elle est constante. Pour une superposition, elle oscille."}
                    ]
                ),
            ],
        },
    ],
})


# ═════════════════════════════════════════════════════════════════════════════
# MODULE 2 — POSTULATS DE LA MÉCANIQUE QUANTIQUE
# ═════════════════════════════════════════════════════════════════════════════
COURSE_STRUCTURE.append({
    "order": 2,
    "title": "Postulats de la mécanique quantique",
    "description": (
        "Les cinq postulats fondateurs : état quantique, observable, "
        "mesure, réduction du paquet d'onde, évolution. Principe "
        "d'incertitude de Heisenberg."
    ),
    "lessons": [

        # ── Leçon 2.1 : Les cinq postulats ─────────────────────────────────
        {
            "order": 0,
            "title": "Les cinq postulats de la mécanique quantique",
            "slug": "cinq-postulats",
            "minutes": 60,
            "blocks": [
                T(
                    "# Les cinq postulats de la mécanique quantique\n\n"
                    "La mécanique quantique repose sur **cinq postulats** non démontrables, validés par leur cohérence et leurs prédictions expérimentales. Ils font le lien entre les objets mathématiques (espace de Hilbert, opérateurs) et le monde physique (mesures, observables).\n\n"
                    "## Postulat 1 : État du système\n\n"
                    "L'état d'un système quantique est complètement décrit par un **vecteur d'état** $|\\psi(t)\\rangle$ appartenant à un espace de Hilbert $\\mathcal{H}$. Ce vecteur est normalisé : $\\langle\\psi|\\psi\\rangle = 1$.\n\n"
                    "L'état contient **toute** l'information accessible sur le système. En représentation de position, on utilise la fonction d'onde $\\psi(x, t) = \\langle x|\\psi(t)\\rangle$.\n\n"
                    "## Postulat 2 : Observable\n\n"
                    "À toute grandeur physique mesurable $A$ (position, énergie, spin, etc.) est associé un **opérateur hermitien** $\\hat{A}$ agissant sur $\\mathcal{H}$. Les opérateurs hermitiens ont des valeurs propres **réelles** — ce sont les résultats possibles de la mesure.\n\n"
                    "Exemples : $\\hat{x}$ (position), $\\hat{p} = -i\\hbar\\nabla$ (impulsion), $\\hat{H}$ (hamiltonien), $\\hat{L}$ (moment cinétique).\n\n"
                    "## Postulat 3 : Résultat de la mesure\n\n"
                    "Le résultat d'une mesure de l'observable $\\hat{A}$ est **nécessairement** l'une des valeurs propres $a_n$ de $\\hat{A}$. La probabilité d'obtenir $a_n$ lorsque le système est dans l'état $|\\psi\\rangle$ est :\n"
                    "$$\\boxed{\\;P(a_n) = |\\langle u_n|\\psi\\rangle|^2\\;}$$\n\n"
                    "où $|u_n\\rangle$ est le vecteur propre associé à $a_n$. Si $a_n$ est dégénéré (sous-espace propre de dimension $> 1$), la probabilité est la somme sur une base orthonormée du sous-espace propre.\n\n"
                    "## Postulat 4 : Réduction du paquet d'onde\n\n"
                    "Immédiatement après une mesure ayant donné $a_n$, le système se trouve dans l'état $|u_n\\rangle$ (ou sa projection sur le sous-espace propre). L'acte de mesure **modifie** l'état du système :\n"
                    "$$|\\psi\\rangle \\xrightarrow{\\,\\text{mesure}=a_n\\,} |u_n\\rangle$$\n\n"
                    "C'est la **réduction du paquet d'onde** (ou **postulat de projection**). Une nouvelle mesure immédiate donne $a_n$ avec probabilité 1.\n\n"
                    "## Postulat 5 : Évolution temporelle\n\n"
                    "Entre deux mesures, l'état évolue selon l'équation de Schrödinger :\n"
                    "$$\\boxed{\\;i\\hbar\\frac{d}{dt}|\\psi(t)\\rangle = \\hat{H}|\\psi(t)\\rangle\\;}$$\n\n"
                    "L'évolution est **déterministe** (connaissant $|\\psi(0)\\rangle$ et $\\hat{H}$, on connaît $|\\psi(t)\\rangle$), contrairement à la mesure qui est **probabiliste**.\n\n"
                    "## Espérance et écart-type\n\n"
                    "La **valeur moyenne** d'une observable $\\hat{A}$ dans l'état $|\\psi\\rangle$ est :\n"
                    "$$\\langle A \\rangle = \\langle\\psi|\\hat{A}|\\psi\\rangle$$\n\n"
                    "L'**écart-type** (incertitude) est $\\Delta A = \\sqrt{\\langle A^2 \\rangle - \\langle A \\rangle^2}$.\n\n"
                    "## Mesures successives et compatibilité\n\n"
                    "Deux observables $\\hat{A}$ et $\\hat{B}$ sont dites **compatibles** si $[\\hat{A}, \\hat{B}] = 0$. Elles peuvent être mesurées simultanément avec une précision arbitraire et possèdent une base de vecteurs propres communs. Sinon (incompatibles), il y a une limite fondamentale — le principe d'incertitude.\n\n"
                    "> 💡 **Astuce** : Le postulat 3 (probabilités $|c_n|^2$) et le postulat 4 (réduction) sont les plus contre-intuitifs. La mesure n'est plus une simple observation passive : elle **modifie** l'état du système de façon irréversible."
                ),

                S(
                    "Visualisation de la réduction du paquet d'onde",
                    "import matplotlib.pyplot as plt\n"
                    "import numpy as np\n"
                    "\n"
                    "# État initial : superposition des 4 premiers états d'un puits infini [0, L]\n"
                    "# psi(x) = sum_n c_n * sqrt(2/L) * sin(n*pi*x/L)\n"
                    "L = 1.0\n"
                    "x = np.linspace(0, L, 500)\n"
                    "coeffs = {1: 0.6, 2: 0.5j, 3: 0.4, 4: 0.45}  # c_n complexes\n"
                    "# Normalisation\n"
                    "norm = sum(abs(c)**2 for c in coeffs.values())\n"
                    "coeffs = {n: c/np.sqrt(norm) for n, c in coeffs.items()}\n"
                    "\n"
                    "def psi(x, coeffs, L):\n"
                    "    s = np.zeros_like(x, dtype=complex)\n"
                    "    for n, c in coeffs.items():\n"
                    "        s += c * np.sqrt(2/L) * np.sin(n*np.pi*x/L)\n"
                    "    return s\n"
                    "\n"
                    "psi_before = psi(x, coeffs, L)\n"
                    "prob_before = np.abs(psi_before)**2\n"
                    "\n"
                    "# Probabilités de mesure\n"
                    "probs = {n: abs(c)**2 for n, c in coeffs.items()}\n"
                    "\n"
                    "# Simulons une mesure qui donne n=2\n"
                    "n_measured = 2\n"
                    "psi_after = np.sqrt(2/L) * np.sin(n_measured*np.pi*x/L)\n"
                    "prob_after = np.abs(psi_after)**2\n"
                    "\n"
                    "fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))\n"
                    "\n"
                    "# Avant mesure\n"
                    "ax = axes[0]\n"
                    "ax.plot(x, prob_before, 'b-', lw=2.5)\n"
                    "ax.fill_between(x, 0, prob_before, alpha=0.2, color='blue')\n"
                    "ax.set_title(r'Avant mesure : $|\\psi\\rangle = \\sum_n c_n|n\\rangle$', fontsize=11)\n"
                    "ax.set_xlabel(r'$x/L$'); ax.set_ylabel(r'$|\\psi(x)|^2$')\n"
                    "ax.grid(True, alpha=0.3)\n"
                    "\n"
                    "# Probabilités de mesure\n"
                    "ax = axes[1]\n"
                    "ns = list(probs.keys())\n"
                    "ps = list(probs.values())\n"
                    "colors = ['gray'] * len(ns)\n"
                    "colors[ns.index(n_measured)] = 'red'\n"
                    "ax.bar(ns, ps, color=colors, alpha=0.7, edgecolor='black')\n"
                    "ax.set_xlabel(r'État $|n\\rangle$'); ax.set_ylabel(r'Probabilité $P(n) = |c_n|^2$')\n"
                    "ax.set_title(r'Mesure → résultat $n=2$', fontsize=11)\n"
                    "ax.set_xticks(ns)\n"
                    "ax.grid(True, alpha=0.3, axis='y')\n"
                    "for i, (n, p) in enumerate(zip(ns, ps)):\n"
                    "    ax.text(n, p+0.02, f'{p:.2f}', ha='center', fontsize=9)\n"
                    "\n"
                    "# Après mesure\n"
                    "ax = axes[2]\n"
                    "ax.plot(x, prob_after, 'r-', lw=2.5)\n"
                    "ax.fill_between(x, 0, prob_after, alpha=0.2, color='red')\n"
                    "ax.set_title(r'Après mesure : $|\\psi\\rangle = |2\\rangle$ (réduction)', fontsize=11)\n"
                    "ax.set_xlabel(r'$x/L$'); ax.set_ylabel(r'$|\\psi(x)|^2$')\n"
                    "ax.grid(True, alpha=0.3)\n"
                    "\n"
                    "plt.tight_layout(); plt.savefig('plot.png')\n"
                    "print('Probabilités avant mesure :')\n"
                    "for n, p in probs.items():\n"
                    "    print(f'  P(n={n}) = {p:.4f}')\n"
                    "print(f'Somme = {sum(probs.values()):.4f} (normalisation OK)')\n"
                    "print(f'Après mesure (n={n_measured}) : état |{n_measured}> avec probabilité 1')\n"
                ),

                APP(
                    "Probabilités de mesure sur un état superposé",
                    "On considère un système à trois niveaux d'énergie $E_1 < E_2 < E_3$ (états propres orthonormés $|1\\rangle, |2\\rangle, |3\\rangle$). L'état initial est :\n"
                    "$$|\\psi\\rangle = \\frac{1}{\\sqrt{6}}|1\\rangle + \\frac{1+i}{\\sqrt{3}}|2\\rangle - \\frac{i}{\\sqrt{6}}|3\\rangle$$\n\n"
                    "1) Vérifier la normalisation.\n"
                    "2) On mesure l'énergie. Quelles valeurs peut-on obtenir et avec quelles probabilités ?\n"
                    "3) On obtient $E_2$. Quel est l'état du système juste après la mesure ?\n"
                    "4) On mesure à nouveau l'énergie immédiatement après. Quel est le résultat ?",
                    "1) **Normalisation** : la norme vaut $|c_1|^2 + |c_2|^2 + |c_3|^2$.\n"
                    "$|c_1|^2 = |1/\\sqrt{6}|^2 = 1/6$\n"
                    "$|c_2|^2 = |(1+i)/\\sqrt{3}|^2 = |1+i|^2/3 = 2/3$\n"
                    "$|c_3|^2 = |-i/\\sqrt{6}|^2 = 1/6$\n"
                    "**Somme** : $1/6 + 2/3 + 1/6 = 1/6 + 4/6 + 1/6 = 6/6 = 1$ ✓\n\n"
                    "2) **Résultats possibles et probabilités** (postulat 3) : on peut obtenir $E_1$, $E_2$ ou $E_3$ avec probabilités :\n"
                    "$$P(E_1) = |c_1|^2 = 1/6 \\approx 0{,}167$$\n"
                    "$$P(E_2) = |c_2|^2 = 2/3 \\approx 0{,}667$$\n"
                    "$$P(E_3) = |c_3|^2 = 1/6 \\approx 0{,}167$$\n\n"
                    "3) **État après mesure** (postulat 4) : si on obtient $E_2$, l'état se réduit à $|\\psi'\\rangle = |2\\rangle$ (la phase complexe initiale disparaît).\n\n"
                    "4) **Nouvelle mesure** : comme le système est maintenant dans $|2\\rangle$ (vecteur propre de $\\hat{H}$), une mesure immédiate donne $E_2$ avec **probabilité 1**. C'est la cohérence de la mesure quantique."
                ),

                MCQ(
                    "Postulat de la mesure",
                    "Quand on mesure l'observable $\\hat{A}$ sur l'état $|\\psi\\rangle = \\sum_n c_n |u_n\\rangle$, la probabilité d'obtenir $a_k$ est :",
                    [
                        {"text": "$P(a_k) = c_k$", "correct": False, "feedback": "Il faut prendre le module au carré."},
                        {"text": "$P(a_k) = |c_k|^2$", "correct": True, "feedback": "Exact ! Règle de Born."},
                        {"text": "$P(a_k) = |c_k|$", "correct": False, "feedback": "Il faut élever au carré."},
                        {"text": "$P(a_k) = \\text{Re}(c_k)^2$", "correct": False, "feedback": "C'est le module complet, pas seulement la partie réelle."}
                    ],
                    explanation="Règle de Born : $P(a_k) = |\\langle u_k|\\psi\\rangle|^2 = |c_k|^2$."
                ),

                FB(
                    "Les cinq postulats",
                    "Le postulat 1 dit que l'état est un vecteur de {{blank_1}}.\n\n"
                    "Le postulat 3 dit que la probabilité de mesurer $a_n$ est $P(a_n) = |c_n|^{{{blank_2}}}$.\n\n"
                    "Le postulat {{blank_3}} dit qu'après la mesure, l'état se réduit au vecteur propre correspondant.",
                    {"blank_1": ["Hilbert"], "blank_2": ["2"], "blank_3": ["4"]},
                    explanation="Hilbert (postulat 1), $|c_n|^2$ (postulat 3, règle de Born), réduction du paquet d'onde (postulat 4)."
                ),

                TF(
                    "Vrai ou Faux ? Postulats",
                    [
                        {"statement": "L'état quantique contient toute l'information accessible sur le système.", "is_true": True},
                        {"statement": "Les valeurs propres d'une observable peuvent être complexes.", "is_true": False, "statement_note": "Une observable est hermitienne, donc ses valeurs propres sont réelles."},
                        {"statement": "La mesure modifie l'état du système (réduction du paquet d'onde).", "is_true": True},
                        {"statement": "L'évolution entre deux mesures est déterministe.", "is_true": True},
                        {"statement": "Deux observables compatibles ne peuvent pas être mesurées simultanément.", "is_true": False, "statement_note": "Au contraire : si $[A,B]=0$, elles peuvent l'être."}
                    ]
                ),
            ],
        },

        # ── Leçon 2.2 : Principe d'incertitude de Heisenberg ───────────────
        {
            "order": 1,
            "title": "Principe d'incertitude de Heisenberg",
            "slug": "principe-incertitude-heisenberg",
            "minutes": 55,
            "blocks": [
                T(
                    "# Principe d'incertitude de Heisenberg\n\n"
                    "## 1. Inégalité position-impulsion\n\n"
                    "Le principe d'incertitude de Heisenberg énonce qu'il est **impossible** de connaître simultanément avec une précision arbitraire la position et l'impulsion d'une particule :\n"
                    "$$\\boxed{\\;\\Delta x \\cdot \\Delta p \\geq \\frac{\\hbar}{2}\\;}$$\n\n"
                    "où $\\Delta x = \\sqrt{\\langle x^2 \\rangle - \\langle x \\rangle^2}$ et $\\Delta p = \\sqrt{\\langle p^2 \\rangle - \\langle p \\rangle^2}$ sont les **écarts-types** (incertitudes) de $x$ et $p$.\n\n"
                    "## 2. Interprétation physique\n\n"
                    "Cette limite est **fondamentale** — ce n'est pas une limite instrumentale. Même avec un appareil parfait, on ne pourrait pas dépasser $\\hbar/2$. C'est une conséquence directe de $[\\hat{x}, \\hat{p}] = i\\hbar$.\n\n"
                    "Le principe ne dit pas que la mesure de $x$ perturbe $p$ (bien que cela puisse être une image). Il dit que **la notion classique de trajectoire** (position et vitesse bien définies simultanément) **n'a pas de sens** en mécanique quantique.\n\n"
                    "## 3. Forme générale (Robertson)\n\n"
                    "Pour deux observables $\\hat{A}$ et $\\hat{B}$ quelconques :\n"
                    "$$\\boxed{\\;\\Delta A \\cdot \\Delta B \\geq \\frac{1}{2}|\\langle[\\hat{A}, \\hat{B}]\\rangle|\\;}$$\n\n"
                    "C'est l'**inégalité de Robertson**. Si $[\\hat{A}, \\hat{B}] = 0$, il n'y a pas de limite (les deux sont mesurables simultanément). Sinon, le produit des incertitudes est borné inférieurement.\n\n"
                    "### Exemples\n"
                    "- Position/impulsion : $[\\hat{x}, \\hat{p}] = i\\hbar \\Rightarrow \\Delta x \\Delta p \\geq \\hbar/2$\n"
                    "- Énergie/temps : $\\Delta E \\Delta t \\geq \\hbar/2$ (interprétation subtile — $t$ n'est pas un opérateur)\n"
                    "- Composantes de moment cinétique : $[\\hat{L}_x, \\hat{L}_y] = i\\hbar\\hat{L}_z \\Rightarrow \\Delta L_x \\Delta L_y \\geq (\\hbar/2)|\\langle L_z \\rangle|$\n\n"
                    "## 4. Le paquet d'ondes minimum\n\n"
                    "L'état qui sature l'inégalité ($\\Delta x \\Delta p = \\hbar/2$) est appelé **paquet d'ondes minimum**. C'est le **paquet gaussien** :\n"
                    "$$\\psi(x) = \\frac{1}{(2\\pi\\sigma^2)^{1/4}} e^{-(x-x_0)^2/(4\\sigma^2)} e^{ip_0 x/\\hbar}$$\n\n"
                    "Pour cet état : $\\Delta x = \\sigma$ et $\\Delta p = \\hbar/(2\\sigma)$, donc $\\Delta x \\Delta p = \\hbar/2$ exactement.\n\n"
                    "## 5. Trade-off : localisation vs délocalisation\n\n"
                    "Plus on localise la particule ($\\Delta x$ petit), plus son impulsion est incertaine ($\\Delta p$ grand). Réciproquement, une onde plane parfaitement définie en $p$ ($\\Delta p = 0$) est totalement délocalisée ($\\Delta x = \\infty$).\n\n"
                    "## 6. Conséquences physiques\n\n"
                    "- **Stabilité des atomes** : sans le principe d'incertitude, l'électron s'effondrerait sur le noyau. La localisation près du noyau ($\\Delta x$ petit) implique une grande incertitude en $p$, donc une grande énergie cinétique, qui empêche l'effondrement.\n"
                    "- **Taille de l'atome d'hydrogène** : minimiser $E = p^2/(2m) - e^2/(4\\pi\\varepsilon_0 r)$ avec $\\Delta p \\sim \\hbar/\\Delta x$ donne $\\Delta x \\sim a_0 = 0{,}529$ Å (rayon de Bohr).\n"
                    "- **Énergie du point zéro** : un oscillateur harmonique ne peut pas être au repos absolu, sinon $\\Delta x = 0$ et $\\Delta p = 0$ violeraient Heisenberg. Il reste une énergie résiduelle $E_0 = \\hbar\\omega/2$.\n\n"
                    "## 7. Vérification expérimentale\n\n"
                    "L'expérience des fentes de Young avec mesure « quelle fente ? » illustre le principe : si on localise la particule (quelle fente), la figure d'interférence disparaît — l'impulsion transverse devient indéterminée, effaçant les franges.\n\n"
                    "> 💡 **Astuce** : Le principe d'incertitude n'est pas une limite technologique. C'est une propriété intrinsèque de la nature quantique, liée au caractère ondulatoire de la matière."
                ),

                S(
                    "Trade-off position-impulsion pour un paquet gaussien",
                    "import matplotlib.pyplot as plt\n"
                    "import numpy as np\n"
                    "\n"
                    "# Trois paquets gaussiens de largeurs différentes\n"
                    "x = np.linspace(-6, 6, 1000)\n"
                    "hbar = 1.0\n"
                    "sigmas = [0.5, 1.0, 2.0]\n"
                    "colors = ['red', 'green', 'blue']\n"
                    "\n"
                    "fig, axes = plt.subplots(1, 2, figsize=(13, 5))\n"
                    "\n"
                    "# Espace des positions\n"
                    "ax = axes[0]\n"
                    "for sigma, color in zip(sigmas, colors):\n"
                    "    psi = (2*np.pi*sigma**2)**(-0.25) * np.exp(-x**2/(4*sigma**2))\n"
                    "    prob = np.abs(psi)**2\n"
                    "    ax.plot(x, prob, color=color, lw=2.5, label=rf'$\\sigma={sigma}$ ($\\Delta x={sigma}$)')\n"
                    "    ax.fill_between(x, 0, prob, alpha=0.15, color=color)\n"
                    "ax.set_xlabel(r'$x$', fontsize=12)\n"
                    "ax.set_ylabel(r'$|\\psi(x)|^2$', fontsize=12)\n"
                    "ax.set_title(r'Représentation position : $\\Delta x = \\sigma$', fontsize=12)\n"
                    "ax.legend(fontsize=10)\n"
                    "ax.grid(True, alpha=0.3)\n"
                    "ax.set_xlim(-5, 5)\n"
                    "\n"
                    "# Espace des impulsions (TF de la gaussienne → gaussienne)\n"
                    "ax = axes[1]\n"
                    "p = np.linspace(-6, 6, 1000)\n"
                    "for sigma, color in zip(sigmas, colors):\n"
                    "    sigma_p = hbar/(2*sigma)  # Delta p\n"
                    "    phi = (2*np.pi*sigma_p**2)**(-0.25) * np.exp(-p**2/(4*sigma_p**2))\n"
                    "    prob_p = np.abs(phi)**2\n"
                    "    ax.plot(p, prob_p, color=color, lw=2.5, label=rf'$\\Delta p={sigma_p:.2f}$')\n"
                    "    ax.fill_between(p, 0, prob_p, alpha=0.15, color=color)\n"
                    "ax.set_xlabel(r'$p$', fontsize=12)\n"
                    "ax.set_ylabel(r'$|\\tilde\\psi(p)|^2$', fontsize=12)\n"
                    "ax.set_title(r'Représentation impulsion : $\\Delta p = \\hbar/(2\\sigma)$', fontsize=12)\n"
                    "ax.legend(fontsize=10)\n"
                    "ax.grid(True, alpha=0.3)\n"
                    "ax.set_xlim(-5, 5)\n"
                    "\n"
                    "plt.suptitle(r'Trade-off Heisenberg : $\\Delta x \\cdot \\Delta p = \\hbar/2$ (état gaussien)', fontsize=13, y=1.02)\n"
                    "plt.tight_layout(); plt.savefig('plot.png')\n"
                    "print('Vérification du trade-off :')\n"
                    "for sigma in sigmas:\n"
                    "    dx = sigma\n"
                    "    dp = hbar/(2*sigma)\n"
                    "    print(f'  sigma={sigma} → Delta x={dx}, Delta p={dp:.3f}, produit={dx*dp:.4f} (hbar/2={hbar/2})')\n"
                ),

                APP(
                    "Inégalité de Heisenberg pour un état gaussien",
                    "On considère un paquet d'ondes gaussien :\n"
                    "$$\\psi(x) = \\left(\\frac{2\\alpha}{\\pi}\\right)^{1/4} e^{-\\alpha x^2} e^{i p_0 x/\\hbar}$$\n\n"
                    "1) Calculer $\\Delta x$ (on rappelle $\\langle x^{2n} \\rangle$ pour une gaussienne).\n"
                    "2) Calculer $\\langle p \\rangle$ et $\\Delta p$.\n"
                    "3) Vérifier le principe d'incertitude. Que vaut le produit $\\Delta x \\Delta p$ ?",
                    "1) **Calcul de $\\Delta x$** : par symétrie $\\langle x \\rangle = 0$. L'intégrale gaussienne $\\int_{-\\infty}^{+\\infty} x^2 e^{-2\\alpha x^2}dx = \\frac{1}{4\\alpha}\\sqrt{\\frac{\\pi}{2\\alpha}}$. Après normalisation ($\\int |\\psi|^2 dx = 1$) :\n"
                    "$$\\langle x^2 \\rangle = \\frac{1}{4\\alpha} \\Rightarrow \\Delta x = \\frac{1}{2\\sqrt{\\alpha}}$$\n\n"
                    "2) **Calcul de $\\langle p \\rangle$ et $\\Delta p$** : en utilisant $\\hat{p} = -i\\hbar \\partial_x$ :\n"
                    "$$\\langle p \\rangle = \\int \\psi^* (-i\\hbar \\partial_x) \\psi\\, dx = p_0$$\n"
                    "La phase $e^{ip_0 x/\\hbar}$ donne une impulsion moyenne $p_0$.\n"
                    "$$\\langle p^2 \\rangle = \\int \\psi^* (-\\hbar^2 \\partial_x^2) \\psi\\, dx = p_0^2 + \\alpha\\hbar^2$$\n"
                    "$$\\Delta p = \\sqrt{\\langle p^2 \\rangle - \\langle p \\rangle^2} = \\hbar\\sqrt{\\alpha}$$\n\n"
                    "3) **Produit** : $\\Delta x \\Delta p = \\frac{1}{2\\sqrt{\\alpha}} \\cdot \\hbar\\sqrt{\\alpha} = \\frac{\\hbar}{2}$.\n\n"
                    "L'inégalité de Heisenberg $\\Delta x \\Delta p \\geq \\hbar/2$ est donc **saturée** : l'état gaussien réalise le minimum d'incertitude. C'est pourquoi on l'appelle **état cohérent** ou **paquet minimum**."
                ),

                MCQ(
                    "Inégalité de Robertson",
                    "Pour deux observables $\\hat{A}$ et $\\hat{B}$, l'inégalité de Robertson est :",
                    [
                        {"text": "$\\Delta A \\cdot \\Delta B \\geq |\\langle AB \\rangle|$", "correct": False},
                        {"text": "$\\Delta A \\cdot \\Delta B \\geq \\frac{1}{2}|\\langle[A, B]\\rangle|$", "correct": True, "feedback": "Exact ! C'est la forme générale."},
                        {"text": "$\\Delta A \\cdot \\Delta B \\leq \\frac{1}{2}|\\langle[A, B]\\rangle|$", "correct": False, "feedback": "Sens inversé."},
                        {"text": "$\\Delta A \\cdot \\Delta B = 0$ si $[A,B]\\neq 0$", "correct": False}
                    ],
                    explanation="Robertson : $\\Delta A \\Delta B \\geq \\frac{1}{2}|\\langle[A,B]\\rangle|$. Pour $x$ et $p$, $[x,p]=i\\hbar$ → $\\Delta x \\Delta p \\geq \\hbar/2$."
                ),

                FB(
                    "Principe d'incertitude",
                    "Le principe d'incertitude de Heisenberg dit que $\\Delta x \\cdot \\Delta p \\geq \\hbar/{{blank_1}}$.\n\n"
                    "Cette limite est {{blank_2}} (ce n'est pas une limite instrumentale).\n\n"
                    "L'état qui sature l'inégalité est le paquet {{blank_3}}.",
                    {"blank_1": ["2"], "blank_2": ["fondamentale", "intrinsèque"], "blank_3": ["gaussien", "gaussienne"]},
                    explanation="$\\Delta x \\Delta p \\geq \\hbar/2$, limite fondamentale (pas instrumentale), saturée par le paquet gaussien (état minimum d'incertitude)."
                ),

                TF(
                    "Vrai ou Faux ? Heisenberg",
                    [
                        {"statement": "Le principe d'incertitude est une conséquence de $[\\hat{x}, \\hat{p}] = i\\hbar$.", "is_true": True},
                        {"statement": "Avec un meilleur instrument, on pourrait dépasser la limite $\\hbar/2$.", "is_true": False, "statement_note": "Non, c'est une limite fondamentale."},
                        {"statement": "Le paquet gaussien réalise le minimum d'incertitude $\\Delta x \\Delta p = \\hbar/2$.", "is_true": True},
                        {"statement": "Une onde plane parfaitement définie en $p$ est localisée en $x$.", "is_true": False, "statement_note": "Au contraire : $\\Delta p = 0$ implique $\\Delta x = \\infty$."},
                        {"statement": "Le principe d'incertitude explique la stabilité des atomes.", "is_true": True, "statement_note": "Sans lui, l'électron s'effondrerait sur le noyau."}
                    ]
                ),
            ],
        },
    ],
})


# ═════════════════════════════════════════════════════════════════════════════
# MODULE 3 — PROBLÈMES UNIDIMENSIONNELS
# ═════════════════════════════════════════════════════════════════════════════
COURSE_STRUCTURE.append({
    "order": 3,
    "title": "Problèmes unidimensionnels · Puits, oscillateur, effet tunnel",
    "description": (
        "Puits infini (particule dans une boîte), oscillateur harmonique "
        "quantique, marche et barrière de potentiel, effet tunnel et "
        "ses applications (STM, radioactivité α)."
    ),
    "lessons": [

        # ── Leçon 3.1 : Puits infini ───────────────────────────────────────
        {
            "order": 0,
            "title": "Puits infini (particule dans une boîte)",
            "slug": "puits-infini",
            "minutes": 55,
            "blocks": [
                T(
                    "# Puits infini : particule dans une boîte\n\n"
                    "## 1. Le modèle\n\n"
                    "Le **puits infini** (ou particule dans une boîte) est le problème quantique le plus simple. Une particule de masse $m$ est confinée dans une région $0 \\leq x \\leq L$ par un potentiel :\n"
                    "$$V(x) = \\begin{cases} 0 & \\text{si } 0 \\leq x \\leq L \\\\ +\\infty & \\text{sinon} \\end{cases}$$\n\n"
                    "À l'extérieur du puits ($x < 0$ ou $x > L$), $V = \\infty$ donc $\\psi = 0$. La particule ne peut pas sortir — c'est un confinement parfait.\n\n"
                    "## 2. Conditions aux limites\n\n"
                    "À l'intérieur du puits, l'équation de Schrödinger indépendante du temps s'écrit :\n"
                    "$$-\\frac{\\hbar^2}{2m}\\frac{d^2\\phi}{dx^2} = E\\phi$$\n\n"
                    "Comme $\\psi = 0$ à l'extérieur et que $\\psi$ doit être continue, on a les **conditions aux limites** :\n"
                    "$$\\boxed{\\;\\phi(0) = 0 \\quad \\text{et} \\quad \\phi(L) = 0\\;}$$\n\n"
                    "## 3. Solutions\n\n"
                    "La solution générale est $\\phi(x) = A\\sin(kx) + B\\cos(kx)$ avec $k = \\sqrt{2mE}/\\hbar$.\n\n"
                    "- $\\phi(0) = 0 \\Rightarrow B = 0$\n"
                    "- $\\phi(L) = 0 \\Rightarrow A\\sin(kL) = 0 \\Rightarrow kL = n\\pi$ avec $n \\in \\mathbb{N}^*$\n\n"
                    "La condition $k_n L = n\\pi$ **quantifie** l'énergie. Les états stationnaires sont :\n"
                    "$$\\boxed{\\;\\phi_n(x) = \\sqrt{\\frac{2}{L}}\\sin\\!\\left(\\frac{n\\pi x}{L}\\right), \\quad E_n = \\frac{n^2\\pi^2\\hbar^2}{2mL^2}, \\quad n = 1, 2, 3, \\dots\\;}$$\n\n"
                    "## 4. Propriétés\n\n"
                    "- **Quantification** : l'énergie ne prend que des valeurs discrètes $E_n \\propto n^2$.\n"
                    "- **Énergie fondamentale non nulle** : $E_1 = \\pi^2\\hbar^2/(2mL^2) > 0$. C'est l'**énergie du point zéro**. La particule ne peut jamais être au repos absolu (principe d'incertitude).\n"
                    "- **Parité** (pour un puits symétrique $[-L/2, L/2]$) : les états pairs ($n$ impair) sont symétriques, les états impairs ($n$ pair) sont antisymétriques.\n"
                    "- **Nœuds** : l'état $\\phi_n$ a $(n-1)$ nœuds (zéros) dans $]0, L[$.\n"
                    "- **Orthogonalité** : $\\langle\\phi_m|\\phi_n\\rangle = \\delta_{mn}$.\n\n"
                    "## 5. Densités de probabilité\n\n"
                    "Pour $\\phi_n$, $|\\phi_n(x)|^2 = (2/L)\\sin^2(n\\pi x/L)$. La probabilité n'est pas uniforme — il y a des **lobes** séparés par des nœuds. Classiquement, la probabilité serait uniforme ($1/L$).\n\n"
                    "## 6. Applications\n\n"
                    "- **Électron dans un quantum-dot** (boîte quantique) : les niveaux $E_n$ dépendent de $L$, ce qui permet de « accorder » la couleur d'émission en changeant la taille.\n"
                    "- **Modèle de Kronig-Penney** : extension périodique pour modéliser les électrons dans un cristal (apparition de bandes d'énergie).\n"
                    "- **Conjugaison des polyènes** : les électrons π dans une molécule linéaire conjuguée sont modélisés par un puits de longueur $L$.\n\n"
                    "## 7. Limite classique\n\n"
                    "Pour $n \\to \\infty$, $|\\phi_n|^2$ oscille très rapidement et la moyenne locale tend vers $1/L$ (densité classique). C'est le **principe de correspondance** de Bohr.\n\n"
                    "> 💡 **Astuce** : Le puits infini est un cas d'école. Ses résultats (quantification en $n^2$, énergie de point zéro, nœuds) sont qualitativement généraux et se retrouvent dans tous les problèmes confinés."
                ),

                S(
                    "États et densités du puits infini",
                    "import matplotlib.pyplot as plt\n"
                    "import numpy as np\n"
                    "\n"
                    "L = 1.0\n"
                    "x = np.linspace(0, L, 500)\n"
                    "\n"
                    "fig, axes = plt.subplots(1, 2, figsize=(13, 5))\n"
                    "\n"
                    "# Fonctions d'onde phi_n\n"
                    "ax = axes[0]\n"
                    "for n in [1, 2, 3, 4]:\n"
                    "    phi = np.sqrt(2/L) * np.sin(n*np.pi*x/L)\n"
                    "    # Décalage vertical pour visualisation\n"
                    "    ax.plot(x, phi + n, lw=2.5, label=rf'$\\phi_{n}(x)$, $E_{n} \\propto {n**2}$')\n"
                    "    ax.axhline(n, color='gray', ls=':', alpha=0.3)\n"
                    "ax.set_xlabel(r'$x/L$', fontsize=12)\n"
                    "ax.set_ylabel(r'$\\phi_n(x)$ (décalé)', fontsize=12)\n"
                    "ax.set_title(r'Fonctions d\\'onde $\\phi_n(x) = \\sqrt{2/L}\\sin(n\\pi x/L)$', fontsize=12)\n"
                    "ax.legend(fontsize=10, loc='upper right')\n"
                    "ax.grid(True, alpha=0.3)\n"
                    "ax.set_xlim(0, L)\n"
                    "\n"
                    "# Densités |phi_n|^2\n"
                    "ax = axes[1]\n"
                    "for n in [1, 2, 3, 4]:\n"
                    "    prob = (2/L) * np.sin(n*np.pi*x/L)**2\n"
                    "    ax.plot(x, prob + (n-1)*3, lw=2.5, label=rf'$|\\phi_{n}|^2$ ({n-1} noeuds)')\n"
                    "    ax.fill_between(x, (n-1)*3, prob + (n-1)*3, alpha=0.15)\n"
                    "ax.axhline(0, color='gray', lw=0.5)\n"
                    "ax.set_xlabel(r'$x/L$', fontsize=12)\n"
                    "ax.set_ylabel(r'$|\\phi_n(x)|^2$ (décalé)', fontsize=12)\n"
                    "ax.set_title(r'Densités de probabilité $|\\phi_n|^2$', fontsize=12)\n"
                    "ax.legend(fontsize=10, loc='upper right')\n"
                    "ax.grid(True, alpha=0.3)\n"
                    "ax.set_xlim(0, L)\n"
                    "\n"
                    "plt.tight_layout(); plt.savefig('plot.png')\n"
                    "print('Niveaux d\\'énergie En = n² * pi²*hbar²/(2mL²)')\n"
                    "for n in [1, 2, 3, 4]:\n"
                    "    print(f'  E{n}/E1 = {n**2}')\n"
                    "print(f'État fondamental non nul : E1 = pi² hbar²/(2mL²) > 0 (énergie de point zéro)')\n"
                ),

                APP(
                    "Électron dans un puits quantique de 1 nm",
                    "On considère un électron ($m_e = 9{,}11 \\times 10^{-31}$ kg) confiné dans un puits infini de largeur $L = 1$ nm.\n\n"
                    "1) Calculer l'énergie fondamentale $E_1$ en eV.\n"
                    "2) Calculer l'énergie du premier niveau excité $E_2$.\n"
                    "3) Quelle est la longueur d'onde du photon émis lors de la transition $n=2 \\to n=1$ ?",
                    "1) **Énergie fondamentale** : $E_1 = \\pi^2\\hbar^2/(2m_e L^2)$.\n"
                    "$$E_1 = \\frac{\\pi^2 \\times (1{,}055 \\times 10^{-34})^2}{2 \\times 9{,}11 \\times 10^{-31} \\times (10^{-9})^2} = \\frac{1{,}097 \\times 10^{-67}}{1{,}822 \\times 10^{-48}} = 6{,}02 \\times 10^{-20} \\text{ J}$$\n"
                    "$$E_1 = \\frac{6{,}02 \\times 10^{-20}}{1{,}602 \\times 10^{-19}} \\approx 0{,}376 \\text{ eV}$$\n\n"
                    "2) **Premier niveau excité** : $E_2 = 4 E_1 = 4 \\times 0{,}376 \\approx 1{,}50$ eV.\n\n"
                    "3) **Longueur d'onde du photon** : la transition émet un photon d'énergie $\\Delta E = E_2 - E_1 = 3 E_1 \\approx 1{,}13$ eV.\n"
                    "$$\\lambda = \\frac{hc}{\\Delta E} = \\frac{6{,}626 \\times 10^{-34} \\times 3 \\times 10^8}{1{,}13 \\times 1{,}602 \\times 10^{-19}} \\approx 1{,}10 \\times 10^{-6} \\text{ m} = 1{,}10 \\, \\mu\\text{m}$$\n\n"
                    "C'est dans le proche infrarouge. Les diodes laser et les puits quantiques sont conçus en jouant sur $L$ pour émettre à la longueur d'onde souhaitée."
                ),

                MCQ(
                    "Énergie du puits infini",
                    "Les niveaux d'énergie d'un puits infini de largeur $L$ sont proportionnels à :",
                    [
                        {"text": "$n$", "correct": False, "feedback": "Non, ce n'est pas linéaire."},
                        {"text": "$n^2$", "correct": True, "feedback": "Exact ! $E_n = n^2 \\pi^2 \\hbar^2/(2mL^2)$."},
                        {"text": "$1/n^2$", "correct": False, "feedback": "C'est le cas de l'hydrogène, pas du puits infini."},
                        {"text": "$\\sqrt{n}$", "correct": False}
                    ],
                    explanation="$E_n \\propto n^2$ pour le puits infini. C'est une signature du confinement linéaire."
                ),

                FB(
                    "Conditions aux limites du puits",
                    "Dans un puits infini $[0, L]$, les conditions aux limites sont $\\phi(0) = 0$ et $\\phi(L) = {{blank_1}}$.\n\n"
                    "Les fonctions d'onde sont $\\phi_n(x) = \\sqrt{2/L} \\sin(n\\pi x/L)$ avec $n \\geq {{blank_2}}$.\n"
                    "L'énergie fondamentale $E_1$ est {{blank_3}} (non nulle) : c'est l'énergie de point zéro.",
                    {"blank_1": ["0"], "blank_2": ["1"], "blank_3": ["positive", "non nulle", ">0", "strictement positive"]},
                    explanation="$\\phi(L)=0$, $n \\geq 1$, $E_1 > 0$ (énergie de point zéro due au confinement et au principe d'incertitude)."
                ),

                TF(
                    "Vrai ou Faux ? Puits infini",
                    [
                        {"statement": "L'énergie fondamentale d'un puits infini est non nulle.", "is_true": True, "statement_note": "C'est l'énergie de point zéro, $E_1 > 0$."},
                        {"statement": "Les niveaux d'énergie sont proportionnels à $n^2$.", "is_true": True},
                        {"statement": "L'état $\\phi_n$ possède $n$ nœuds dans l'intervalle $]0, L[$.", "is_true": False, "statement_note": "C'est $(n-1)$ nœuds."},
                        {"statement": "Les fonctions d'onde $\\phi_n$ forment une base orthonormée.", "is_true": True},
                        {"statement": "Plus le puits est large, plus les niveaux sont resserrés.", "is_true": True, "statement_note": "$E_n \\propto 1/L^2$ : $L$ grand → niveaux proches."}
                    ]
                ),
            ],
        },

        # ── Leçon 3.2 : Oscillateur harmonique ──────────────────────────────
        {
            "order": 1,
            "title": "Oscillateur harmonique quantique",
            "slug": "oscillateur-harmonique",
            "minutes": 60,
            "blocks": [
                T(
                    "# Oscillateur harmonique quantique\n\n"
                    "## 1. Le modèle\n\n"
                    "L'oscillateur harmonique est le problème le plus ubiquitaire de la physique. Toute particule dans un puits de potentiel $V(x)$ présente un minimum : au voisinage du minimum, on peut approximer $V(x) \\approx V_0 + \\frac{1}{2}V''(x_0)(x-x_0)^2$, soit un potentiel harmonique.\n\n"
                    "Le potentiel harmonique est :\n"
                    "$$V(x) = \\frac{1}{2}m\\omega^2 x^2$$\n\n"
                    "Le hamiltonien est :\n"
                    "$$\\hat{H} = \\frac{\\hat{p}^2}{2m} + \\frac{1}{2}m\\omega^2 \\hat{x}^2$$\n\n"
                    "## 2. Niveaux d'énergie\n\n"
                    "La résolution (par polynômes d'Hermite ou par opérateurs d'échelle) donne :\n"
                    "$$\\boxed{\\;E_n = \\hbar\\omega\\left(n + \\frac{1}{2}\\right), \\quad n = 0, 1, 2, \\dots\\;}$$\n\n"
                    "Les niveaux sont **équidistants** : $E_{n+1} - E_n = \\hbar\\omega$. L'énergie fondamentale $E_0 = \\hbar\\omega/2$ est l'**énergie du point zéro**.\n\n"
                    "## 3. Opérateurs d'échelle (création/annihilation)\n\n"
                    "On introduit les opérateurs sans dimension :\n"
                    "$$\\hat{a} = \\sqrt{\\frac{m\\omega}{2\\hbar}}\\left(\\hat{x} + \\frac{i\\hat{p}}{m\\omega}\\right), \\quad \\hat{a}^\\dagger = \\sqrt{\\frac{m\\omega}{2\\hbar}}\\left(\\hat{x} - \\frac{i\\hat{p}}{m\\omega}\\right)$$\n\n"
                    "Propriétés :\n"
                    "- $[\\hat{a}, \\hat{a}^\\dagger] = 1$\n"
                    "- $\\hat{H} = \\hbar\\omega(\\hat{a}^\\dagger\\hat{a} + \\frac{1}{2}) = \\hbar\\omega(\\hat{N} + \\frac{1}{2})$ où $\\hat{N} = \\hat{a}^\\dagger\\hat{a}$ est l'opérateur nombre.\n"
                    "- $\\hat{a}|n\\rangle = \\sqrt{n}|n-1\\rangle$ (annihilation)\n"
                    "- $\\hat{a}^\\dagger|n\\rangle = \\sqrt{n+1}|n+1\\rangle$ (création)\n\n"
                    "L'état fondamental vérifie $\\hat{a}|0\\rangle = 0$ (pas de quantum à annihiler).\n\n"
                    "## 4. Fonctions d'onde\n\n"
                    "$$\\phi_n(x) = \\left(\\frac{m\\omega}{\\pi\\hbar}\\right)^{1/4} \\frac{1}{\\sqrt{2^n n!}} H_n\\!\\left(\\sqrt{\\frac{m\\omega}{\\hbar}}x\\right) e^{-m\\omega x^2/(2\\hbar)}$$\n\n"
                    "où $H_n$ sont les **polynômes d'Hermite** :\n"
                    "- $H_0(y) = 1$\n"
                    "- $H_1(y) = 2y$\n"
                    "- $H_2(y) = 4y^2 - 2$\n"
                    "- $H_3(y) = 8y^3 - 12y$\n\n"
                    "Toutes les fonctions d'onde sont une gaussienne multipliée par un polynôme. Le facteur gaussien garantit la décroissance exponentielle à l'infini.\n\n"
                    "## 5. Comparaison classique/quantique\n\n"
                    "- **Classique** : la particule oscille entre $-x_{\\max}$ et $+x_{\\max}$ avec $x_{\\max} = \\sqrt{2E/(m\\omega^2)}$. Elle passe plus de temps aux extrémités (où elle ralentit).\n"
                    "- **Quantique** : $|\\phi_n(x)|^2$ a $(n+1)$ lobes. Pour $n \\to \\infty$, la densité quantique moyennée se rapproche de la distribution classique (principe de correspondance).\n\n"
                    "## 6. États cohérents\n\n"
                    "Un **état cohérent** $|\\alpha\\rangle = e^{-|\\alpha|^2/2} \\sum_n \\frac{\\alpha^n}{\\sqrt{n!}} |n\\rangle$ est l'état quantique qui ressemble le plus à un oscillateur classique. Il minimise l'incertitude ($\\Delta x \\Delta p = \\hbar/2$) et son centre suit la trajectoire classique $x(t) = x_0 \\cos(\\omega t) + (p_0/m\\omega)\\sin(\\omega t)$.\n\n"
                    "## 7. Applications\n\n"
                    "- **Vibrations moléculaires** : les niveaux vibrationnels des molécules diatomiques sont bien décrits par l'oscillateur harmonique (spectroscopie IR).\n"
                    "- **Phonons dans les solides** : les vibrations du réseau cristallin sont quantifiées en phonons (Einstein, Debye).\n"
                    "- **Champ électromagnétique quantique** : chaque mode du champ est un oscillateur harmonique ; les photons sont les quanta d'énergie $\\hbar\\omega$.\n\n"
                    "> 💡 **Astuce** : L'oscillateur harmonique est « l'atome d'hydrogène de la physique du solide ». Presque tout système au voisinage d'un équilibre stable se ramène à un ensemble d'oscillateurs harmoniques indépendants."
                ),

                S(
                    "États et densités de l'oscillateur harmonique",
                    "import matplotlib.pyplot as plt\n"
                    "import numpy as np\n"
                    "from scipy.special import hermite\n"
                    "\n"
                    "# Oscillateur harmonique : m=1, omega=1, hbar=1 (unités naturelles)\n"
                    "x = np.linspace(-5, 5, 1000)\n"
                    "\n"
                    "def phi_n(n, x):\n"
                    "    Hn = hermite(n)\n"
                    "    norm = 1.0/np.sqrt(2**n * np.math.factorial(n) * np.sqrt(np.pi))\n"
                    "    return norm * Hn(x) * np.exp(-x**2/2)\n"
                    "\n"
                    "fig, axes = plt.subplots(1, 2, figsize=(13, 5))\n"
                    "\n"
                    "# Fonctions d'onde\n"
                    "ax = axes[0]\n"
                    "for n in [0, 1, 2, 3]:\n"
                    "    psi = phi_n(n, x)\n"
                    "    ax.plot(x, psi + 2*n + 1, lw=2.5, label=rf'$\\phi_{n}$, $E_{n} = {n + 0.5}\\hbar\\omega$')\n"
                    "    ax.axhline(2*n + 1, color='gray', ls=':', alpha=0.3)\n"
                    "# Potentiel (parabole)\n"
                    "V = 0.5 * x**2\n"
                    "ax.plot(x, V, 'k--', lw=1, alpha=0.5, label=r'$V(x) = \\frac{1}{2}m\\omega^2 x^2$')\n"
                    "ax.set_xlabel(r'$x$ (unités $\\sqrt{\\hbar/m\\omega}$)', fontsize=11)\n"
                    "ax.set_ylabel(r'$\\phi_n(x)$ + offset', fontsize=11)\n"
                    "ax.set_title(r'Fonctions d\\'onde de l\\'oscillateur harmonique', fontsize=12)\n"
                    "ax.legend(fontsize=9, loc='upper right')\n"
                    "ax.grid(True, alpha=0.3)\n"
                    "ax.set_xlim(-5, 5); ax.set_ylim(-1, 10)\n"
                    "\n"
                    "# Densités |phi_n|^2\n"
                    "ax = axes[1]\n"
                    "for n in [0, 1, 2, 3]:\n"
                    "    prob = phi_n(n, x)**2\n"
                    "    ax.plot(x, prob + 2*n, lw=2.5, label=rf'$|\\phi_{n}|^2$')\n"
                    "    ax.fill_between(x, 2*n, prob + 2*n, alpha=0.15)\n"
                    "    ax.axhline(2*n, color='gray', ls=':', alpha=0.3)\n"
                    "ax.set_xlabel(r'$x$', fontsize=12)\n"
                    "ax.set_ylabel(r'$|\\phi_n(x)|^2$ + offset', fontsize=11)\n"
                    "ax.set_title(r'Densités de probabilité', fontsize=12)\n"
                    "ax.legend(fontsize=10, loc='upper right')\n"
                    "ax.grid(True, alpha=0.3)\n"
                    "ax.set_xlim(-5, 5)\n"
                    "\n"
                    "plt.tight_layout(); plt.savefig('plot.png')\n"
                    "print('Niveaux : E_n = hbar*omega*(n + 1/2)')\n"
                    "for n in [0, 1, 2, 3]:\n"
                    "    print(f'  E{n} = {n + 0.5} hbar*omega')\n"
                    "print(f'Energie de point zero : E0 = hbar*omega/2')\n"
                ),

                APP(
                    "Énergie de point zéro de l'oscillateur",
                    "On considère un oscillateur harmonique de masse $m = 1$ g et de pulsation $\\omega = 1$ rad/s, puis un oscillateur moléculaire de masse $m \\sim 10^{-26}$ kg et $\\omega \\sim 10^{14}$ rad/s.\n\n"
                    "1) Calculer l'énergie de point zéro dans chaque cas.\n"
                    "2) Comparer à l'énergie thermique $k_B T$ à température ambiante ($T = 300$ K).\n"
                    "3) Conclusion sur le caractère quantique.",
                    "1) **Énergie de point zéro** : $E_0 = \\hbar\\omega/2$.\n\n"
                    "- Oscillateur macroscopique : $E_0 = (1{,}055 \\times 10^{-34} \\times 1)/2 \\approx 5{,}3 \\times 10^{-35}$ J.\n"
                    "- Oscillateur moléculaire : $E_0 = (1{,}055 \\times 10^{-34} \\times 10^{14})/2 \\approx 5{,}3 \\times 10^{-21}$ J $\\approx 0{,}033$ eV.\n\n"
                    "2) **Énergie thermique** à $T = 300$ K : $k_B T = 1{,}381 \\times 10^{-23} \\times 300 \\approx 4{,}14 \\times 10^{-21}$ J $\\approx 0{,}026$ eV.\n\n"
                    "3) **Conclusion** :\n"
                    "- Pour l'oscillateur macroscopique : $E_0 \\sim 10^{-35}$ J, soit $E_0/(k_B T) \\sim 10^{-14}$. L'énergie de point zéro est complètement négligeable → comportement **classique**.\n"
                    "- Pour l'oscillateur moléculaire : $E_0 \\sim k_B T$. L'énergie de point zéro est comparable à l'énergie thermique → comportement **quantique**. Les vibrations moléculaires à basse température sont gelées dans l'état fondamental."
                ),

                MCQ(
                    "Niveaux de l'oscillateur harmonique",
                    "Les niveaux d'énergie de l'oscillateur harmonique quantique sont :",
                    [
                        {"text": "Proportionnels à $n^2$", "correct": False, "feedback": "C'est le puits infini."},
                        {"text": "Équidistants : $E_n = \\hbar\\omega(n+1/2)$", "correct": True, "feedback": "Exact ! Espacement constant $\\hbar\\omega$."},
                        {"text": "Proportionnels à $1/n^2$", "correct": False, "feedback": "C'est l'hydrogène."},
                        {"text": "Continus", "correct": False}
                    ],
                    explanation="$E_n = \\hbar\\omega(n+1/2)$. L'espacement $\\hbar\\omega$ est constant, signature de l'oscillateur harmonique."
                ),

                FB(
                    "Opérateurs d'échelle",
                    "L'opérateur d'annihilation est noté $\\hat{{{blank_1}}}$ et l'opérateur de création est noté $\\hat{{{blank_1}}}^\\dagger$.\n\n"
                    "L'opérateur $\\hat{a}|n\\rangle = \\sqrt{n}|n-1\\rangle$ abaisse le nombre de quanta de {{blank_2}}.\n\n"
                    "L'énergie du point zéro vaut $E_0 = \\hbar\\omega/{{blank_3}}$.",
                    {"blank_1": ["a"], "blank_2": ["1", "un"], "blank_3": ["2"]},
                    explanation="$\\hat{a}$ (annihilation), $\\hat{a}^\\dagger$ (création). $\\hat{a}|n\\rangle = \\sqrt{n}|n-1\\rangle$ diminue $n$ de 1. Énergie du point zéro $E_0 = \\hbar\\omega/2$."
                ),

                TF(
                    "Vrai ou Faux ? Oscillateur harmonique",
                    [
                        {"statement": "Les niveaux d'énergie sont équidistants.", "is_true": True},
                        {"statement": "L'énergie de point zéro est nulle.", "is_true": False, "statement_note": "Elle vaut $E_0 = \\hbar\\omega/2$ (principe d'incertitude)."},
                        {"statement": "Les fonctions d'onde sont des polynômes d'Hermite multipliés par une gaussienne.", "is_true": True},
                        {"statement": "Les opérateurs $\\hat{a}$ et $\\hat{a}^\\dagger$ commutent.", "is_true": False, "statement_note": "Non : $[\\hat{a}, \\hat{a}^\\dagger] = 1$."},
                        {"statement": "L'oscillateur harmonique modélise les vibrations moléculaires.", "is_true": True}
                    ]
                ),
            ],
        },

        # ── Leçon 3.3 : Barrière de potentiel et effet tunnel ──────────────
        {
            "order": 2,
            "title": "Barrière de potentiel et effet tunnel",
            "slug": "barriere-effet-tunnel",
            "minutes": 55,
            "blocks": [
                T(
                    "# Barrière de potentiel et effet tunnel\n\n"
                    "## 1. Marche de potentiel\n\n"
                    "Une **marche de potentiel** est définie par :\n"
                    "$$V(x) = \\begin{cases} 0 & \\text{si } x < 0 \\\\ V_0 & \\text{si } x \\geq 0 \\end{cases}$$\n\n"
                    "Une particule d'énergie $E$ arrive de la gauche. Deux cas :\n\n"
                    "### Cas $E > V_0$ (transmission classique)\n"
                    "Classiquement, la particule passe toujours. Quantiquement, il existe une probabilité de **réflexion** $R < 1$ :\n"
                    "$$R = \\left(\\frac{k_1 - k_2}{k_1 + k_2}\\right)^2, \\quad T = \\frac{4 k_1 k_2}{(k_1 + k_2)^2}$$\n"
                    "avec $k_1 = \\sqrt{2mE}/\\hbar$ et $k_2 = \\sqrt{2m(E-V_0)}/\\hbar$.\n\n"
                    "### Cas $E < V_0$ (réflexion totale, mais...)\n"
                    "Classiquement, la particule est toujours réfléchie. Quantiquement, $\\psi$ **pénètre** dans la zone interdite sur une distance $\\delta = \\hbar/\\sqrt{2m(V_0-E)}$ (exponentielle décroissante). La particule n'est pas détectée à droite, mais elle a une **probabilité non nulle** d'être trouvée à l'intérieur de la marche.\n\n"
                    "## 2. Barrière rectangulaire et effet tunnel\n\n"
                    "Une **barrière** de hauteur $V_0$ et de largeur $a$ :\n"
                    "$$V(x) = \\begin{cases} 0 & x < 0 \\text{ ou } x > a \\\\ V_0 & 0 \\leq x \\leq a \\end{cases}$$\n\n"
                    "Si $E < V_0$, la particule est classiquement réfléchie. Quantiquement, la fonction d'onde décroît exponentiellement dans la barrière mais, si $a$ est fini, elle a une amplitude non nulle à la sortie : la particule peut **traverser** !\n\n"
                    "C'est l'**effet tunnel**.\n\n"
                    "## 3. Coefficient de transmission\n\n"
                    "Pour $E < V_0$, le coefficient de transmission est :\n"
                    "$$\\boxed{\\;T \\approx \\frac{16 E(V_0-E)}{V_0^2} e^{-2\\kappa a}, \\quad \\kappa = \\frac{\\sqrt{2m(V_0-E)}}{\\hbar}\\;}$$\n\n"
                    "L'essentiel est la **dépendance exponentielle** $T \\sim e^{-2\\kappa a}$ : la transmission chute très vite avec l'épaisseur $a$ et la racine de la hauteur $(V_0 - E)$.\n\n"
                    "## 4. Interprétation\n\n"
                    "L'effet tunnel est une conséquence directe du caractère ondulatoire de la matière. Il est impossible en mécanique classique où l'énergie cinétique ne peut pas être négative.\n\n"
                    "En mécanique quantique, l'équation de Schrödinger admet des solutions exponentiellement décroissantes dans les régions interdites classiquement. Si la zone interdite est d'épaisseur finie, une partie de l'onde « traverse ».\n\n"
                    "## 5. Applications\n\n"
                    "### Microscope à effet tunnel (STM)\n"
                    "Une pointe métallique est placée très près d'une surface. Un courant tunnel traverse le vide (barrière de quelques Å). Le courant $I \\propto e^{-2\\kappa d}$ dépend exponentiellement de la distance pointe-surface $d$. En mesurant $I$, on obtient une image de la surface avec résolution atomique (Binnig & Rohrer, prix Nobel 1986).\n\n"
                    "### Radioactivité α\n"
                    "Dans un noyau, les particules α sont confinées par la barrière de potentiel nucléaire. Elles s'échappent par effet tunnel. La demi-vie $T_{1/2}$ dépend exponentiellement de l'énergie de la particule α (loi de Geiger-Nuttall).\n\n"
                    "### Diode tunnel et flash NAND\n"
                    "Les mémoires flash NAND utilisent l'effet tunnel pour injecter/extraire des électrons d'une grille flottante.\n\n"
                    "## 6. Paradoxe du temps de traversée\n\n"
                    "Le temps que met la particule à traverser la barrière est subtil. Certains modèles donnent un temps très court (voire nul), suggérant une « superluminescence » apparente. En réalité, il n'y a pas de trajectoire définie — la particule est décrite par une fonction d'onde.\n\n"
                    "> 💡 **Astuce** : L'effet tunnel illustre une différence marquée entre classique et quantique. La formule $T \\sim e^{-2\\kappa a}$ est universelle : tout phénomène tunnel (STM, radioactivité, diode) suit cette dépendance exponentielle."
                ),

                S(
                    "Coefficient de transmission T(E) d'une barrière",
                    "import matplotlib.pyplot as plt\n"
                    "import numpy as np\n"
                    "\n"
                    "# Barrière rectangulaire de hauteur V0 et largeur a\n"
                    "# T(E) = 1 / [1 + (V0^2 * sinh^2(kappa*a)) / (4*E*(V0-E))]\n"
                    "# pour E < V0, kappa = sqrt(2m(V0-E))/hbar\n"
                    "# en unités : hbar=1, m=1, V0=1, a=2 (arbitraire)\n"
                    "V0 = 1.0\n"
                    "a = 2.0\n"
                    "hbar = 1.0\n"
                    "m = 1.0\n"
                    "\n"
                    "def T_coeff(E, V0, a, m=1.0, hbar=1.0):\n"
                    "    E = np.asarray(E, dtype=float)\n"
                    "    T = np.zeros_like(E)\n"
                    "    # E > V0 : oscillations\n"
                    "    mask_high = E > V0\n"
                    "    k = np.sqrt(2*m*np.maximum(E[mask_high] - V0, 0))/hbar\n"
                    "    T[mask_high] = 1.0/(1 + (V0**2 * np.sin(k*a)**2)/(4*E[mask_high]*(E[mask_high]-V0)))\n"
                    "    # E < V0 : effet tunnel\n"
                    "    mask_low = (E < V0) & (E > 0)\n"
                    "    kappa = np.sqrt(2*m*(V0 - E[mask_low]))/hbar\n"
                    "    sinh_term = np.sinh(kappa*a)**2\n"
                    "    T[mask_low] = 1.0/(1 + (V0**2 * sinh_term)/(4*E[mask_low]*(V0-E[mask_low])))\n"
                    "    return T\n"
                    "\n"
                    "E = np.linspace(0.01, 3*V0, 1000)\n"
                    "T = T_coeff(E, V0, a)\n"
                    "\n"
                    "fig, ax = plt.subplots(figsize=(10, 6))\n"
                    "ax.plot(E/V0, T, 'b-', lw=2.5, label=rf'$T(E)$, $a={a}$, $V_0={V0}$')\n"
                    "ax.axvline(1, color='red', ls='--', alpha=0.5, label=r'$E = V_0$ (seuil classique)')\n"
                    "ax.axvspan(0, 1, alpha=0.15, color='orange', label=r'Effet tunnel ($E < V_0$)')\n"
                    "ax.axvspan(1, 3, alpha=0.15, color='green', label=r'Transmission classique ($E > V_0$)')\n"
                    "\n"
                    "# Annotations\n"
                    "ax.set_xlabel(r'$E/V_0$', fontsize=12)\n"
                    "ax.set_ylabel(r'Coefficient de transmission $T$', fontsize=12)\n"
                    "ax.set_title(r'Transmission d\\'une barrière : $T \\sim e^{-2\\kappa a}$ pour $E < V_0$', fontsize=13)\n"
                    "ax.legend(fontsize=10, loc='lower right')\n"
                    "ax.grid(True, alpha=0.3)\n"
                    "ax.set_xlim(0, 3); ax.set_ylim(0, 1.05)\n"
                    "\n"
                    "plt.tight_layout(); plt.savefig('plot.png')\n"
                    "print('Transmission pour quelques valeurs E/V0 (effet tunnel) :')\n"
                    "for E_val in [0.1, 0.3, 0.5, 0.8, 0.95]:\n"
                    "    kappa = np.sqrt(2*m*(V0 - E_val))/hbar\n"
                    "    T_approx = 16*E_val*(V0-E_val)/V0**2 * np.exp(-2*kappa*a)\n"
                    "    print(f'  E/V0={E_val:.2f} → T≈{T_approx:.4e} (kappa*a={kappa*a:.2f})')\n"
                ),

                APP(
                    "Période d'émission alpha du polonium-212",
                    "Le noyau de ${}^{212}\\text{Po}$ émet une particule α d'énergie $E_\\alpha = 8{,}95$ MeV avec une demi-vie $T_{1/2} = 0{,}3$ μs. La barrière de potentiel nucléaire a une hauteur $V_0 \\approx 25$ MeV et une largeur effective $a \\approx 30$ fm.\n\n"
                    "1) Calculer $\\kappa = \\sqrt{2m(V_0 - E)}/\\hbar$ pour la particule α ($m_\\alpha \\approx 6{,}64 \\times 10^{-27}$ kg).\n"
                    "2) Estimer le facteur $e^{-2\\kappa a}$.\n"
                    "3) En déduire un ordre de grandeur de la période d'émission (on suppose ~$10^{21}$ tentatives par seconde).",
                    "1) **Calcul de $\\kappa$** : $V_0 - E = 25 - 8{,}95 = 16{,}05$ MeV $= 16{,}05 \\times 10^6 \\times 1{,}602 \\times 10^{-19} = 2{,}57 \\times 10^{-12}$ J.\n"
                    "$$\\kappa = \\frac{\\sqrt{2 \\times 6{,}64 \\times 10^{-27} \\times 2{,}57 \\times 10^{-12}}}{1{,}055 \\times 10^{-34}} = \\frac{\\sqrt{3{,}41 \\times 10^{-38}}}{1{,}055 \\times 10^{-34}} \\approx 1{,}75 \\times 10^{15} \\text{ m}^{-1}$$\n\n"
                    "2) **Facteur tunnel** : $2\\kappa a = 2 \\times 1{,}75 \\times 10^{15} \\times 30 \\times 10^{-15} \\approx 105$.\n"
                    "$$e^{-2\\kappa a} = e^{-105} \\approx 3{,}2 \\times 10^{-46}$$\n\n"
                    "3) **Période** : si la particule α heurte la barrière ~$10^{21}$ fois par seconde, la probabilité de traverser par unité de temps est $\\lambda \\approx 10^{21} \\times 3{,}2 \\times 10^{-46} = 3{,}2 \\times 10^{-25}$ s$^{-1}$. La demi-vie estimée est :\n"
                    "$$T_{1/2} = \\frac{\\ln 2}{\\lambda} \\approx \\frac{0{,}693}{3{,}2 \\times 10^{-25}} \\approx 2{,}2 \\times 10^{24} \\text{ s} \\approx 7 \\times 10^{16} \\text{ ans}$$\n\n"
                    "L'accord n'est pas quantitatif (le vrai $T_{1/2}$ est de 0,3 μs) car notre modèle est très simplifié. Mais la **sensibilité exponentielle** est confirmée : doubler $a$ ou $\\sqrt{V_0 - E}$ divise $T_{1/2}$ par $e^2$ — d'où la loi de Geiger-Nuttall reliant $\\log T_{1/2}$ à $1/\\sqrt{E}$."
                ),

                MCQ(
                    "Effet tunnel",
                    "L'effet tunnel se manifeste quand :",
                    [
                        {"text": "$E > V_0$ (énergie supérieure à la barrière)", "correct": False, "feedback": "Non, dans ce cas la particule passe classiquement."},
                        {"text": "$E < V_0$ et la barrière a une épaisseur finie", "correct": True, "feedback": "Exact ! La particule traverse par effet tunnel."},
                        {"text": "La barrière est infiniment haute", "correct": False, "feedback": "Alors T=0 (confinement total)."},
                        {"text": "La particule est au repos", "correct": False}
                    ],
                    explanation="Effet tunnel : la particule traverse une barrière de hauteur $V_0 > E$ et d'épaisseur finie. Probabilité $T \\sim e^{-2\\kappa a}$."
                ),

                FB(
                    "Transmission tunnel",
                    "Le coefficient de transmission tunnel dépend exponentiellement de l'épaisseur : $T \\sim e^{{{blank_1}}\\kappa a}$ où $\\kappa = \\sqrt{{{blank_2}m(V_0-E)}}/\\hbar$.\n\n"
                    "Le microscope à effet tunnel ({{blank_3}}) exploite ce phénomène pour imager des surfaces à l'échelle atomique.",
                    {"blank_1": ["-2", "- 2"], "blank_2": ["2"], "blank_3": ["STM", "scanning tunneling microscope", "microscope à effet tunnel"]},
                    explanation="$T \\sim e^{-2\\kappa a}$, $\\kappa = \\sqrt{2m(V_0-E)}/\\hbar$. Le STM (Binnig & Rohrer, Nobel 1986) exploite la dépendance exponentielle en la distance pointe-surface."
                ),

                TF(
                    "Vrai ou Faux ? Effet tunnel",
                    [
                        {"statement": "L'effet tunnel est impossible en mécanique classique.", "is_true": True, "statement_note": "Classiquement, $E < V_0$ → réflexion totale."},
                        {"statement": "La transmission tunnel dépend exponentiellement de l'épaisseur de la barrière.", "is_true": True},
                        {"statement": "Le STM utilise l'effet tunnel pour obtenir une résolution atomique.", "is_true": True},
                        {"statement": "La radioactivité α est un effet tunnel.", "is_true": True, "statement_note": "Les particules α traversent la barrière de potentiel nucléaire."},
                        {"statement": "Une barrière infiniment large permet l'effet tunnel.", "is_true": False, "statement_note": "Plus $a$ est grand, plus $T \\to 0$. À $a=\\infty$, $T=0$."}
                    ]
                ),
            ],
        },
    ],
})


# ═════════════════════════════════════════════════════════════════════════════
# MODULE 4 — MOMENT CINÉTIQUE ET SPIN
# ═════════════════════════════════════════════════════════════════════════════
COURSE_STRUCTURE.append({
    "order": 4,
    "title": "Moment cinétique et spin",
    "description": (
        "Moment cinétique orbital, relations de commutation, harmoniques "
        "sphériques, spin 1/2, matrices de Pauli, expérience de "
        "Stern-Gerlach, précession de Larmor."
    ),
    "lessons": [

        # ── Leçon 4.1 : Moment cinétique orbital ───────────────────────────
        {
            "order": 0,
            "title": "Moment cinétique orbital",
            "slug": "moment-cinetique-orbital",
            "minutes": 60,
            "blocks": [
                T(
                    "# Moment cinétique orbital\n\n"
                    "## 1. Définition classique et opérateur quantique\n\n"
                    "Le moment cinétique classique est $\\vec{L} = \\vec{r} \\times \\vec{p}$. En mécanique quantique, on remplace $\\vec{r}$ et $\\vec{p}$ par leurs opérateurs :\n"
                    "$$\\hat{\\vec{L}} = \\hat{\\vec{r}} \\times \\hat{\\vec{p}}$$\n\n"
                    "Composantes : $\\hat{L}_i = \\epsilon_{ijk} \\hat{x}_j \\hat{p}_k$ (somme sur $j, k$). En coordonnées cartésiennes :\n"
                    "$$\\hat{L}_x = \\hat{y}\\hat{p}_z - \\hat{z}\\hat{p}_y, \\quad \\hat{L}_y = \\hat{z}\\hat{p}_x - \\hat{x}\\hat{p}_z, \\quad \\hat{L}_z = \\hat{x}\\hat{p}_y - \\hat{y}\\hat{p}_x$$\n\n"
                    "## 2. Relations de commutation\n\n"
                    "Les composantes de $\\vec{L}$ ne commutent pas entre elles :\n"
                    "$$\\boxed{\\;[\\hat{L}_i, \\hat{L}_j] = i\\hbar \\epsilon_{ijk} \\hat{L}_k\\;}$$\n\n"
                    "Par contre, $\\hat{L}^2 = \\hat{L}_x^2 + \\hat{L}_y^2 + \\hat{L}_z^2$ commute avec chaque composante :\n"
                    "$$[\\hat{L}^2, \\hat{L}_i] = 0, \\quad i = x, y, z$$\n\n"
                    "On peut donc mesurer simultanément $\\hat{L}^2$ et **une** composante (par convention $\\hat{L}_z$), mais pas deux composantes à la fois.\n\n"
                    "## 3. Vecteurs propres communs\n\n"
                    "On note $|l, m\\rangle$ les vecteurs propres communs à $\\hat{L}^2$ et $\\hat{L}_z$ :\n"
                    "$$\\boxed{\\;\\hat{L}^2 |l, m\\rangle = \\hbar^2 l(l+1) |l, m\\rangle, \\quad \\hat{L}_z |l, m\\rangle = \\hbar m |l, m\\rangle\\;}$$\n\n"
                    "où :\n"
                    "- $l = 0, 1, 2, 3, \\dots$ (entier positif) est le **nombre quantique secondaire**\n"
                    "- $m = -l, -l+1, \\dots, l-1, l$ (entier) est le **nombre quantique magnétique**\n\n"
                    "Pour un $l$ donné, il y a $(2l+1)$ valeurs de $m$ (dégénérescence).\n\n"
                    "## 4. Opérateurs d'échelle\n\n"
                    "On introduit $\\hat{L}_\\pm = \\hat{L}_x \\pm i \\hat{L}_y$ qui changent $m$ sans changer $l$ :\n"
                    "$$\\hat{L}_\\pm |l, m\\rangle = \\hbar \\sqrt{l(l+1) - m(m \\pm 1)} \\, |l, m \\pm 1\\rangle$$\n\n"
                    "Comme $m$ est borné ($-l \\leq m \\leq l$), il faut $\\hat{L}_+ |l, l\\rangle = 0$ et $\\hat{L}_- |l, -l\\rangle = 0$.\n\n"
                    "## 5. Harmoniques sphériques\n\n"
                    "En représentation de position (coordonnées sphériques $r, \\theta, \\phi$), les vecteurs propres $|l, m\\rangle$ deviennent les **harmoniques sphériques** $Y_l^m(\\theta, \\phi)$ :\n"
                    "$$\\langle \\theta, \\phi | l, m \\rangle = Y_l^m(\\theta, \\phi)$$\n\n"
                    "Exemples :\n"
                    "- $Y_0^0 = \\frac{1}{\\sqrt{4\\pi}}$ (état $s$, isotrope)\n"
                    "- $Y_1^0 = \\sqrt{\\frac{3}{4\\pi}} \\cos\\theta$\n"
                    "- $Y_1^{\\pm 1} = \\mp \\sqrt{\\frac{3}{8\\pi}} \\sin\\theta \\, e^{\\pm i\\phi}$\n"
                    "- $Y_2^0 = \\sqrt{\\frac{5}{16\\pi}} (3\\cos^2\\theta - 1)$\n\n"
                    "Les $Y_l^m$ forment une base orthonormée sur la sphère.\n\n"
                    "## 6. Forme explicite\n"
                    "$$Y_l^m(\\theta, \\phi) = \\epsilon_m \\sqrt{\\frac{2l+1}{4\\pi} \\frac{(l-|m|)!}{(l+|m|)!}} \\, P_l^{|m|}(\\cos\\theta) \\, e^{im\\phi}$$\n\n"
                    "où $P_l^{|m|}$ sont les **polynômes associés de Legendre** et $\\epsilon_m = (-1)^m$ pour $m \\geq 0$, $1$ sinon.\n\n"
                    "## 7. Interprétation physique\n\n"
                    "- $\\sqrt{l(l+1)} \\, \\hbar$ est le **module** du moment cinétique (quantifié, jamais nul sauf pour $l=0$).\n"
                    "- $m\\hbar$ est la **projection** sur l'axe $z$.\n"
                    "- Le **vecteur** $\\vec{L}$ ne peut pas être aligné avec $\\vec{z}$ (sinon $L_x = L_y = 0$, ce qui violerait le principe d'incertitude). Il décrit un cône autour de $z$ (précession quantique).\n\n"
                    "## 8. Application : atomes\n\n"
                    "Dans un atome, $l$ détermine la « sous-couche » ($s, p, d, f, \\dots$ pour $l = 0, 1, 2, 3, \\dots$). Le nombre quantique $m$ détermine l'orbitale dans la sous-couche. La dégénérescence $(2l+1)$ explique le tableau périodique (2 électrons par orbitale, en tenant compte du spin).\n\n"
                    "> 💡 **Astuce** : Les harmoniques sphériques sont aux fonctions angulaires ce que les sinus sont aux fonctions linéaires : une base naturelle pour développer toute fonction sur la sphère."
                ),

                S(
                    "Harmoniques sphériques Y_l^m",
                    "import matplotlib.pyplot as plt\n"
                    "import numpy as np\n"
                    "from scipy.special import sph_harm\n"
                    "\n"
                    "theta = np.linspace(0, np.pi, 100)\n"
                    "phi = np.linspace(0, 2*np.pi, 100)\n"
                    "THETA, PHI = np.meshgrid(theta, phi)\n"
                    "\n"
                    "fig = plt.figure(figsize=(14, 8))\n"
                    "\n"
                    "# Tracer |Y_l^m|^2 en projection 3D pour (l, m) = (0,0), (1,0), (1,1), (2,0), (2,1), (2,2)\n"
                    "lm_pairs = [(0,0), (1,0), (1,1), (2,0), (2,1), (2,2)]\n"
                    "\n"
                    "for i, (l, m) in enumerate(lm_pairs):\n"
                    "    Y = sph_harm(m, l, PHI, THETA)  # scipy: ordre (m, l, phi, theta)\n"
                    "    Y_real = np.real(Y)\n"
                    "    Ysq = np.abs(Y)**2\n"
                    "    \n"
                    "    # Coordonnées cartésiennes pour surface\n"
                    "    r = Ysq / Ysq.max() if Ysq.max() > 0 else np.ones_like(Ysq)\n"
                    "    X = r * np.sin(THETA) * np.cos(PHI)\n"
                    "    Ycoord = r * np.sin(THETA) * np.sin(PHI)\n"
                    "    Z = r * np.cos(THETA)\n"
                    "    \n"
                    "    ax = fig.add_subplot(2, 3, i+1, projection='3d')\n"
                    "    ax.plot_surface(X, Ycoord, Z, cmap='viridis', alpha=0.8)\n"
                    "    ax.set_title(rf'$|Y_{l}^{{{m}}}|^2$', fontsize=13)\n"
                    "    ax.set_axis_off()\n"
                    "\n"
                    "plt.suptitle(r'Densités angulaires $|Y_l^m(\\theta, \\phi)|^2$ (orbitales $s, p, d$)', fontsize=14)\n"
                    "plt.tight_layout(); plt.savefig('plot.png')\n"
                    "print('Valeurs propres de L² et Lz :')\n"
                    "for l, m in lm_pairs:\n"
                    "    L2_val = l*(l+1)\n"
                    "    Lz_val = m\n"
                    "    print(f'  l={l}, m={m}: L²= {L2_val} hbar², Lz= {Lz_val} hbar')\n"
                    "print('\\nPour l=2: module |L| = sqrt(6) hbar ≈ 2.45 hbar')\n"
                    "print('Pour l=2: m = -2, -1, 0, 1, 2 (5 valeurs)')\n"
                ),

                APP(
                    "Valeurs propres pour l=2",
                    "On considère un système avec $l = 2$.\n\n"
                    "1) Donner les valeurs possibles de $m$.\n"
                    "2) Calculer les valeurs propres de $\\hat{L}^2$ et $\\hat{L}_z$.\n"
                    "3) Quelle est la dégénérescence du niveau $l = 2$ ?\n"
                    "4) Calculer le rapport $|L_z|_{\\max}/|\\vec{L}|$ et commenter.",
                    "1) **Valeurs de $m$** : pour $l = 2$, $m \\in \\{-2, -1, 0, 1, 2\}$, soit 5 valeurs.\n\n"
                    "2) **Valeurs propres** :\n"
                    "$$\\hat{L}^2 |2, m\\rangle = \\hbar^2 \\cdot 2 \\cdot 3 \\, |2, m\\rangle = 6\\hbar^2 |2, m\\rangle$$\n"
                    "$$\\hat{L}_z |2, m\\rangle = \\hbar m |2, m\\rangle, \\quad m \\in \\{-2, -1, 0, 1, 2\}$$\n"
                    "Donc $L_z \\in \\{-2\\hbar, -\\hbar, 0, \\hbar, 2\\hbar\}$ et $|\\vec{L}| = \\sqrt{6}\\hbar \\approx 2{,}449 \\hbar$.\n\n"
                    "3) **Dégénérescence** : $2l + 1 = 5$ états distincts (un par valeur de $m$).\n\n"
                    "4) **Rapport** : $|L_z|_{\\max}/|\\vec{L}| = 2\\hbar / \\sqrt{6}\\hbar = 2/\\sqrt{6} \\approx 0{,}816$.\n\n"
                    "Le vecteur $\\vec{L}$ ne peut jamais être **aligné** avec l'axe $z$ (rapport $< 1$). Même dans l'état $|l, m=l\\rangle$ (maximisé), il reste un angle $\\theta$ tel que $\\cos\\theta = l/\\sqrt{l(l+1)} < 1$. C'est une conséquence directe du principe d'incertitude : connaître $L_z$ exactement interdit de connaître $L_x$ et $L_y$."
                ),

                MCQ(
                    "Relations de commutation",
                    "Le commutateur $[\\hat{L}_x, \\hat{L}_y]$ vaut :",
                    [
                        {"text": "$0$", "correct": False, "feedback": "Les composantes de $\\vec{L}$ ne commutent pas."},
                        {"text": "$i\\hbar \\hat{L}_z$", "correct": True, "feedback": "Exact ! Relation de commutation cyclique."},
                        {"text": "$i\\hbar \\hat{L}_x$", "correct": False},
                        {"text": "$\\hbar \\hat{L}_z$", "correct": False, "feedback": "Il manque le facteur $i$."}
                    ],
                    explanation="$[L_i, L_j] = i\\hbar \\epsilon_{ijk} L_k$. Pour $i=x, j=y$ : $\\epsilon_{xyz} = 1$ → $[L_x, L_y] = i\\hbar L_z$."
                ),

                FB(
                    "Nombres quantiques",
                    "Le nombre quantique $l$ prend les valeurs $l = 0, 1, 2, \\dots$ et le nombre $m$ prend les valeurs $m = -l, \\dots, {{blank_1}}$.\n\n"
                    "La valeur propre de $\\hat{L}^2$ est $\\hbar^2 l(l+{{blank_2}})$.\n"
                    "Pour $l = 3$, il y a {{blank_3}} valeurs possibles de $m$.",
                    {"blank_1": ["l", "+l"], "blank_2": ["1"], "blank_3": ["7", "2l+1"]},
                    explanation="$m \\in \\{-l, \\dots, +l\\}$, $L^2 = \\hbar^2 l(l+1)$, dégénérescence $2l+1 = 7$ pour $l=3$."
                ),

                TF(
                    "Vrai ou Faux ? Moment cinétique",
                    [
                        {"statement": "$[\\hat{L}^2, \\hat{L}_z] = 0$.", "is_true": True},
                        {"statement": "$[\\hat{L}_x, \\hat{L}_y] = 0$.", "is_true": False, "statement_note": "Non : $[L_x, L_y] = i\\hbar L_z$."},
                        {"statement": "Les composantes de $\\vec{L}$ ne peuvent pas être mesurées simultanément avec une précision arbitraire.", "is_true": True},
                        {"statement": "Le vecteur $\\vec{L}$ peut être aligné avec l'axe $z$.", "is_true": False, "statement_note": "Non, à cause du principe d'incertitude (rapport $l/\\sqrt{l(l+1)} < 1$)."},
                        {"statement": "Pour $l=0$, la fonction $Y_0^0$ est isotrope (constante sur la sphère).", "is_true": True, "statement_note": "$Y_0^0 = 1/\\sqrt{4\\pi}$."}
                    ]
                ),
            ],
        },

        # ── Leçon 4.2 : Spin 1/2 et matrices de Pauli ───────────────────────
        {
            "order": 1,
            "title": "Spin 1/2 et matrices de Pauli",
            "slug": "spin-pauli",
            "minutes": 60,
            "blocks": [
                T(
                    "# Spin 1/2 et matrices de Pauli\n\n"
                    "## 1. Le spin : moment cinétique intrinsèque\n\n"
                    "Le **spin** est un moment cinétique **intrinsèque** des particules, sans équivalent classique. Il ne dépend pas du mouvement spatial de la particule. Toutes les particules élémentaires ont un spin :\n"
                    "- Spin 0 : boson de Higgs\n"
                    "- Spin 1/2 : électron, proton, neutron, quarks (fermions)\n"
                    "- Spin 1 : photon, bosons W/Z, gluons\n"
                    "- Spin 2 : graviton (hypothétique)\n\n"
                    "Le spin est quantifié comme le moment cinétique orbital : $\\hat{\\vec{S}}^2$ a pour valeurs propres $\\hbar^2 s(s+1)$ avec $s$ entier ou demi-entier.\n\n"
                    "## 2. Spin 1/2\n\n"
                    "Pour le spin 1/2 : $s = 1/2$, $m_s \\in \\{-1/2, +1/2\}$. L'espace des états de spin est de dimension **2** : $\\mathcal{H}_s \\cong \\mathbb{C}^2$.\n\n"
                    "Base canonique : $|+\\rangle = |\\uparrow\\rangle$ (spin up selon $z$) et $|-\\rangle = |\\downarrow\\rangle$ (spin down).\n"
                    "$$\\hat{S}_z |\\pm\\rangle = \\pm \\frac{\\hbar}{2}|\\pm\\rangle, \\quad \\hat{\\vec{S}}^2 |\\pm\\rangle = \\frac{3\\hbar^2}{4}|\\pm\\rangle$$\n\n"
                    "## 3. Matrices de Pauli\n\n"
                    "On définit $\\hat{S}_i = \\frac{\\hbar}{2} \\sigma_i$ où les **matrices de Pauli** sont :\n"
                    "$$\\sigma_x = \\begin{pmatrix} 0 & 1 \\\\ 1 & 0 \\end{pmatrix}, \\quad \\sigma_y = \\begin{pmatrix} 0 & -i \\\\ i & 0 \\end{pmatrix}, \\quad \\sigma_z = \\begin{pmatrix} 1 & 0 \\\\ 0 & -1 \\end{pmatrix}$$\n\n"
                    "Propriétés :\n"
                    "- $\\sigma_i^2 = \\mathbb{1}$ (valeurs propres $\\pm 1$)\n"
                    "- $[\\sigma_i, \\sigma_j] = 2i \\epsilon_{ijk} \\sigma_k$\n"
                    "- $\\{\\sigma_i, \\sigma_j\\} = 2\\delta_{ij} \\mathbb{1}$ (anticommutateur)\n"
                    "- $\\text{tr}(\\sigma_i) = 0$, $\\det(\\sigma_i) = -1$\n\n"
                    "## 4. États propres de $\\hat{S}_x$ et $\\hat{S}_y$\n\n"
                    "Les vecteurs propres de $\\sigma_x$ sont :\n"
                    "$$|\\pm x\\rangle = \\frac{1}{\\sqrt{2}}(|+\\rangle \\pm |-\\rangle)$$\n\n"
                    "Ceux de $\\sigma_y$ :\n"
                    "$$|\\pm y\\rangle = \\frac{1}{\\sqrt{2}}(|+\\rangle \\pm i|-\\rangle)$$\n\n"
                    "Un état général de spin 1/2 s'écrit $|\\chi\\rangle = \\alpha|+\\rangle + \\beta|-\\rangle$ avec $|\\alpha|^2 + |\\beta|^2 = 1$.\n\n"
                    "## 5. Expérience de Stern-Gerlach (1922)\n\n"
                    "Un faisceau d'atomes d'argent (spin 1/2 de l'électron de valence) passe dans un champ magnétique **inhomogène** $\\vec{B}(z)$. Classiquement, on s'attendrait à un étalement continu (orientation aléatoire du spin).\n\n"
                    "Observation : le faisceau se sépare en **deux** taches distinctes — c'est la **quantification du spin**. Les atomes sont déviés vers le haut (spin up) ou vers le bas (spin down), rien entre les deux.\n\n"
                    "C'est la première démonstration directe de la quantification spatiale.\n\n"
                    "## 6. Précession de Larmor\n\n"
                    "Dans un champ magnétique $\\vec{B} = B\\vec{e}_z$, le hamiltonien de spin est :\n"
                    "$$\\hat{H} = -\\gamma \\hat{\\vec{S}} \\cdot \\vec{B} = -\\gamma B \\hat{S}_z = -\\frac{\\hbar\\omega_0}{2}\\sigma_z$$\n\n"
                    "où $\\gamma$ est le **rapport gyromagnétique** et $\\omega_0 = \\gamma B$ est la **pulsation de Larmor**.\n\n"
                    "L'évolution temporelle d'un état initial $|\\chi(0)\\rangle = \\alpha(0)|+\\rangle + \\beta(0)|-\\rangle$ est :\n"
                    "$$|\\chi(t)\\rangle = \\alpha(0) e^{i\\omega_0 t/2}|+\\rangle + \\beta(0) e^{-i\\omega_0 t/2}|-\\rangle$$\n\n"
                    "Les phases évoluent en sens opposés. Si $\\langle S_x(0) \\rangle \\neq 0$, le spin moyen effectue une **précession** autour de $\\vec{B}$ à la pulsation $\\omega_0$.\n\n"
                    "## 7. Résonance magnétique (RMN, IRM)\n\n"
                    "Si on ajoute un champ $B_1 \\cos(\\omega t)$ perpendiculaire à $B_z$, on observe des **transitions** entre $|+\\rangle$ et $|-\\rangle$ quand $\\omega \\approx \\omega_0$ (résonance).\n\n"
                    "Applications :\n"
                    "- **Résonance magnétique nucléaire (RMN)** : spectroscopie des noyaux (chimie)\n"
                    "- **Imagerie par résonance magnétique (IRM)** : imagerie médicale\n"
                    "- **Spectroscopie RMN** des protéines\n\n"
                    "## 8. Spin et statistique\n\n"
                    "Les particules de spin demi-entier ($1/2, 3/2, \\dots$) sont des **fermions** (principe d'exclusion de Pauli, fonction d'onde antisymétrique). Les particules de spin entier ($0, 1, 2, \\dots$) sont des **bosons** (pas d'exclusion, fonction d'onde symétrique).\n\n"
                    "> 💡 **Astuce** : Le spin 1/2 est le cas le plus simple mais aussi le plus riche. Toute la théorie des qubits (informatique quantique) repose sur l'espace de Hilbert à 2 dimensions $\\mathbb{C}^2$."
                ),

                S(
                    "Précession de spin dans un champ B",
                    "import matplotlib.pyplot as plt\n"
                    "import numpy as np\n"
                    "\n"
                    "# État initial : |chi(0)> = cos(theta/2) |+> + sin(theta/2) |->\n"
                    "# Évolution : phases opposées sur |+> et |->\n"
                    "theta = np.pi/3  # angle initial du spin par rapport à z\n"
                    "alpha0 = np.cos(theta/2)\n"
                    "beta0 = np.sin(theta/2)\n"
                    "\n"
                    "# <S_x>, <S_y>, <S_z> en fonction du temps (en unités hbar/2)\n"
                    "omega0 = 1.0\n"
                    "t = np.linspace(0, 4*np.pi/omega0, 200)\n"
                    "\n"
                    "# Vecteur de Bloch : (sin(theta)cos(omega0*t), sin(theta)sin(omega0*t), cos(theta))\n"
                    "Sx = np.sin(theta) * np.cos(omega0*t)\n"
                    "Sy = np.sin(theta) * np.sin(omega0*t)\n"
                    "Sz = np.cos(theta) * np.ones_like(t)\n"
                    "\n"
                    "fig = plt.figure(figsize=(13, 5))\n"
                    "\n"
                    "# 3D : trajectoire du spin\n"
                    "ax = fig.add_subplot(1, 2, 1, projection='3d')\n"
                    "ax.plot(Sx, Sy, Sz, 'b-', lw=2.5, label=r'Trajectoire de $\\langle \\vec{S} \\rangle$')\n"
                    "ax.quiver(0, 0, 0, Sx[0], Sy[0], Sz[0], color='red', arrow_length_ratio=0.15, lw=2.5, label='Initial')\n"
                    "ax.quiver(0, 0, 0, Sx[-1], Sy[-1], Sz[-1], color='green', arrow_length_ratio=0.15, lw=2.5, label='Final')\n"
                    "ax.quiver(0, 0, 0, 0, 0, 1, color='purple', arrow_length_ratio=0.1, lw=1.5, ls='--', label=r'$\\vec{B}$ (axe z)')\n"
                    "ax.set_xlim(-1, 1); ax.set_ylim(-1, 1); ax.set_zlim(-1, 1)\n"
                    "ax.set_xlabel(r'$S_x$'); ax.set_ylabel(r'$S_y$'); ax.set_zlabel(r'$S_z$')\n"
                    "ax.set_title(r'Précession de Larmor : $\\omega_0 = \\gamma B$', fontsize=11)\n"
                    "ax.legend(fontsize=9)\n"
                    "\n"
                    "# 2D : composantes en fonction du temps\n"
                    "ax = fig.add_subplot(1, 2, 2)\n"
                    "ax.plot(t, Sx, 'r-', lw=2, label=r'$\\langle S_x \\rangle / (\\hbar/2)$')\n"
                    "ax.plot(t, Sy, 'g-', lw=2, label=r'$\\langle S_y \\rangle / (\\hbar/2)$')\n"
                    "ax.plot(t, Sz, 'b-', lw=2, label=r'$\\langle S_z \\rangle / (\\hbar/2)$')\n"
                    "ax.axhline(0, color='gray', lw=0.5)\n"
                    "ax.set_xlabel(r'Temps $t$ (unités $1/\\omega_0$)', fontsize=11)\n"
                    "ax.set_ylabel(r'$\\langle S_i \\rangle / (\\hbar/2)$', fontsize=11)\n"
                    "ax.set_title(r'Composantes du spin vs temps', fontsize=12)\n"
                    "ax.legend(fontsize=10)\n"
                    "ax.grid(True, alpha=0.3)\n"
                    "\n"
                    "plt.tight_layout(); plt.savefig('plot.png')\n"
                    "print(f'Angle initial theta = {np.degrees(theta):.1f} deg')\n"
                    "print(f'\<S_z\> = {Sz[0]:.3f} (hbar/2) — constant (commute avec H)')\n"
                    "print(f'\<S_x\>(0) = {Sx[0]:.3f}, <S_x>(T) = {Sx[-1]:.3f}')\n"
                    "print(f'\<S_y\>(0) = {Sy[0]:.3f}, <S_y>(T) = {Sy[-1]:.3f}')\n"
                    "print(f'Période de précession : T = 2*pi/omega_0 = {2*np.pi/omega0:.3f}')\n"
                ),

                APP(
                    "États propres de S_x",
                    "On considère un spin 1/2 dans l'état $|+x\\rangle = \\frac{1}{\\sqrt{2}}(|+\\rangle + |-\\rangle)$.\n\n"
                    "1) Vérifier que $|+x\\rangle$ est état propre de $\\hat{S}_x$ avec valeur propre $+\\hbar/2$.\n"
                    "2) Calculer les probabilités de mesurer $\\pm \\hbar/2$ pour $\\hat{S}_z$ dans cet état.\n"
                    "3) Idem pour $\\hat{S}_y$.",
                    "1) **État propre de $\\hat{S}_x$** : on a $\\hat{S}_x = \\frac{\\hbar}{2}\\sigma_x = \\frac{\\hbar}{2}\\begin{pmatrix} 0 & 1 \\\\ 1 & 0 \\end{pmatrix}$.\n"
                    "Dans la base $\\{|+\\rangle, |-\\rangle\\}$ : $|+x\\rangle = \\frac{1}{\\sqrt{2}}\\begin{pmatrix} 1 \\\\ 1 \\end{pmatrix}$.\n"
                    "$$\\hat{S}_x |+x\\rangle = \\frac{\\hbar}{2} \\frac{1}{\\sqrt{2}} \\begin{pmatrix} 0 & 1 \\\\ 1 & 0 \\end{pmatrix} \\begin{pmatrix} 1 \\\\ 1 \\end{pmatrix} = \\frac{\\hbar}{2} \\frac{1}{\\sqrt{2}} \\begin{pmatrix} 1 \\\\ 1 \\end{pmatrix} = +\\frac{\\hbar}{2}|+x\\rangle$$\n"
                    "Donc $|+x\\rangle$ est bien état propre de $\\hat{S}_x$ avec valeur propre $+\\hbar/2$. ✓\n\n"
                    "2) **Probabilités pour $\\hat{S}_z$** : les états propres de $\\hat{S}_z$ sont $|+\\rangle$ et $|-\\rangle$, de valeurs propres $+\\hbar/2$ et $-\\hbar/2$.\n"
                    "$$P(+\\hbar/2) = |\\langle + | +x \\rangle|^2 = |1/\\sqrt{2}|^2 = 1/2$$\n"
                    "$$P(-\\hbar/2) = |\\langle - | +x \\rangle|^2 = |1/\\sqrt{2}|^2 = 1/2$$\n"
                    "Donc $\\langle S_z \\rangle = 0$.\n\n"
                    "3) **Probabilités pour $\\hat{S}_y$** : les états propres de $\\hat{S}_y$ sont $|\\pm y\\rangle = \\frac{1}{\\sqrt{2}}(|+\\rangle \\pm i|-\\rangle)$.\n"
                    "$$\\langle + y | + x \\rangle = \\frac{1}{2}(\\langle +| + i\\langle -|)(|+\\rangle + |-\\rangle) = \\frac{1}{2}(1 + i)$$\n"
                    "$$P(+\\hbar/2) = |1+i|^2/4 = 2/4 = 1/2$$\n"
                    "De même $P(-\\hbar/2) = 1/2$. Donc $\\langle S_y \\rangle = 0$.\n\n"
                    "Vérification : $\\langle \\vec{S}^2 \\rangle = \\langle S_x^2 + S_y^2 + S_z^2 \\rangle = (\\hbar/2)^2 + 0 + 0 = \\hbar^2/4 + 0 + 0$... attendu, on a $\\langle S_x^2 \\rangle = (\\hbar/2)^2$ (état propre) et $\\langle S_y^2 \\rangle = \\langle S_z^2 \\rangle = (\\hbar/2)^2$ (par symétrie). Donc $\\langle \\vec{S}^2 \\rangle = 3\\hbar^2/4$. ✓"
                ),

                MCQ(
                    "Matrices de Pauli",
                    "La matrice de Pauli $\\sigma_z$ a pour valeurs propres :",
                    [
                        {"text": "$0$ et $1$", "correct": False},
                        {"text": "$+1$ et $-1$", "correct": True, "feedback": "Exact ! Les valeurs propres de $\\sigma_z$ sont $\\pm 1$."},
                        {"text": "$+1/2$ et $-1/2$", "correct": False, "feedback": "Ce sont les valeurs propres de $S_z = \\hbar\\sigma_z/2$."},
                        {"text": "$+\\hbar/2$ et $-\\hbar/2$", "correct": False, "feedback": "Ce sont les valeurs propres de $S_z$, pas de $\\sigma_z$."}
                    ],
                    explanation="$\\sigma_z = \\text{diag}(1, -1)$ a pour valeurs propres $\\pm 1$. Pour $S_z = \\hbar\\sigma_z/2$, les valeurs propres sont $\\pm \\hbar/2$."
                ),

                FB(
                    "Stern-Gerlach et spin",
                    "L'expérience de Stern-Gerlach (1922) avec des atomes d'argent montre que le faisceau se sépare en {{blank_1}} taches, prouvant la quantification du spin.\n\n"
                    "Les matrices de Pauli vérifient $\\sigma_x^2 = \\sigma_y^2 = \\sigma_z^2 = {{blank_2}}$.\n\n"
                    "Le spin 1/2 fait de l'électron un {{blank_3}} (principe d'exclusion de Pauli).",
                    {"blank_1": ["2", "deux"], "blank_2": ["1", "I", "identité", "\mathbb{1}"], "blank_3": ["fermion", "fermions"]},
                    explanation="Stern-Gerlach : 2 taches (spin up/down). $\\sigma_i^2 = \\mathbb{1}$. Spin 1/2 → fermion (exclusion de Pauli)."
                ),

                TF(
                    "Vrai ou Faux ? Spin",
                    [
                        {"statement": "Le spin est un moment cinétique intrinsèque, sans équivalent classique.", "is_true": True},
                        {"statement": "Le spin 1/2 a un espace de Hilbert de dimension 2.", "is_true": True},
                        {"statement": "Les matrices de Pauli commutent entre elles.", "is_true": False, "statement_note": "Non : $[\\sigma_i, \\sigma_j] = 2i\\epsilon_{ijk}\\sigma_k$."},
                        {"statement": "L'expérience de Stern-Gerlach a démontré la quantification spatiale.", "is_true": True},
                        {"statement": "La précession de Larmor se fait à la pulsation $\\omega_0 = \\gamma B$.", "is_true": True}
                    ]
                ),
            ],
        },
    ],
})
