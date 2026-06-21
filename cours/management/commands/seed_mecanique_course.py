r"""
Management command: seed_mecanique_course
Creates a complete Classical Mechanics course with Python simulations.
All strings containing apostrophes use double quotes.

Escaping rules (note: in this docstring, double backslashes are written as-is):

- LaTeX in text blocks (rendered by MathJax): use two backslashes in Python
  source so DB stores one backslash. Example: source vec-F -> DB vec-F -> MathJax OK.
- LaTeX in matplotlib labels: use raw strings r'...' with two backslashes
  in source.
- Newlines in matplotlib titles: use backslash-n (two chars) in source so
  DB stores a single backslash-n which Pyodide parses as a newline.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from cours.models import (Course, CourseModule, CourseLesson, LessonBlock,
    CodeExercise, MCQExercise, MCQChoice, FillBlankExercise, TrueFalseExercise)


# ---------------------------------------------------------------------------
# Block helpers — each returns a dict consumed by Command._blk()
# ---------------------------------------------------------------------------

def T(content):
    """Text block (Markdown + LaTeX)."""
    return {"type": "text", "content": content}


def S(title, code):
    """Sandbox block (matplotlib code that saves to plot.png)."""
    return {"type": "sandbox", "title": title, "code": code}


def APP(title, enonce, correction):
    """Application exercise with full correction (rendered as a text block)."""
    content = (
        "## 🎯 Exercice d'application — " + title + "\n\n"
        "**Énoncé.** " + enonce + "\n\n"
        "<details>\n"
        "<summary><b>📌 Voir la correction (clique pour déplier)</b></summary>\n\n"
        "**Correction.** " + correction + "\n\n"
        "</details>"
    )
    return {"type": "text", "content": content}


def MCQ(title, question, choices, explanation="", **kw):
    """Multiple-choice question. choices is a list of dicts:
       {"text": ..., "correct": bool, "feedback": ...}"""
    out = {"type": "mcq", "title": title, "question": question,
           "choices": choices, "explanation": explanation}
    out.update(kw)
    return out


def FB(title, text_with_blanks, answers, explanation="", **kw):
    """Fill-in-the-blank exercise."""
    out = {"type": "fill_blank", "title": title,
           "text_with_blanks": text_with_blanks, "answers": answers,
           "explanation": explanation}
    out.update(kw)
    return out


def TF(title, statements, explanation=""):
    """True/False exercise. statements is a list of dicts:
       {"statement": ..., "is_true": bool, "statement_note": optional}"""
    return {"type": "true_false", "title": title,
            "statements": statements, "explanation": explanation}


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = "Seed a complete Classical Mechanics course with simulations."

    def add_arguments(self, parser):
        parser.add_argument("--draft", action="store_true")
        parser.add_argument("--clean", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        slug = "mecanique-classique"
        status = "draft" if options["draft"] else "published"
        if options["clean"]:
            d, _ = Course.objects.filter(slug=slug).delete()
            if d:
                self.stdout.write(self.style.WARNING(f"Deleted ({d} rows)."))
        course, created = Course.objects.get_or_create(slug=slug, defaults={
            "title": "Mécanique Classique · De Newton à Lagrange",
            "description": ("Un cours complet de mécanique classique avec simulations "
                "Python interactives. Couvre la cinématique, la dynamique, l'énergie, "
                "les collisions, les oscillateurs, la gravitation et une introduction "
                "à la mécanique analytique de Lagrange."),
            "short_description": ("Maîtrise la mécanique : cinématique, forces, énergie, "
                "collisions, oscillateurs, gravitation, Lagrange."),
            "category": "physique", "level": "debutant", "language": "fr",
            "price": 0, "is_free": True, "status": status, "estimated_hours": 50})
        if not created:
            self.stdout.write(self.style.WARNING("Course exists - updating."))
        for md in COURSE_STRUCTURE:
            mod = self._mod(course, md)
            for ld in md["lessons"]:
                les = self._les(course, mod, ld)
                self._blocks(les, ld["blocks"])
        self.stdout.write(self.style.SUCCESS(
            f"\n✓ Seeded: {course.title}\n"
            f"  Modules: {CourseModule.objects.filter(course=course).count()}\n"
            f"  Lessons: {CourseLesson.objects.filter(course=course).count()}\n"
            f"  Blocks:  {LessonBlock.objects.filter(course_lesson__course=course).count()}\n"))

    def _mod(self, course, d):
        m, _ = CourseModule.objects.get_or_create(course=course, title=d["title"],
            defaults={"description": d.get("description", ""),
                      "order": d["order"], "is_active": True})
        return m

    def _les(self, course, mod, d):
        s = d.get("slug") or d["title"].lower().replace(" ", "-").replace("'", "-")
        l, _ = CourseLesson.objects.get_or_create(course=course, module=mod, title=d["title"],
            defaults={"slug": s, "order": d["order"],
                      "estimated_minutes": d.get("minutes", 25),
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
            b.text_content = data["content"]
            b.save()
        elif t == "sandbox":
            b.sandbox_title = data.get("title", "Simulation")
            b.sandbox_initial_code = data.get("code", "")
            b.save()
        elif t == "mcq":
            ex = MCQExercise.objects.create(
                course_lesson=lesson, title=data["title"], question=data["question"],
                instructions=data.get("instructions", ""),
                difficulty=data.get("difficulty", "easy"),
                points=data.get("points", 5),
                hint=data.get("hint", ""),
                explanation=data.get("explanation", ""),
                allow_multiple_correct=data.get("multiple", False),
                shuffle_choices=True)
            for i, c in enumerate(data["choices"]):
                MCQChoice.objects.create(exercise=ex, text=c["text"],
                    is_correct=c["correct"], feedback=c.get("feedback", ""), order=i)
            b.mcq_exercise = ex
            b.save()
        elif t == "fill_blank":
            ex = FillBlankExercise.objects.create(
                course_lesson=lesson, title=data["title"],
                instructions=data.get("instructions", ""),
                difficulty=data.get("difficulty", "easy"),
                points=data.get("points", 5),
                hint=data.get("hint", ""),
                explanation=data.get("explanation", ""),
                text_with_blanks=data["text_with_blanks"],
                answers=data["answers"], case_sensitive=False)
            b.fill_blank = ex
            b.save()
        elif t == "true_false":
            ex = TrueFalseExercise.objects.create(
                course_lesson=lesson, title=data["title"],
                instructions=data.get("instructions", ""),
                difficulty=data.get("difficulty", "easy"),
                points=data.get("points", 10),
                hint=data.get("hint", ""),
                explanation=data.get("explanation", ""),
                statements=data["statements"], points_per_statement=2)
            b.true_false = ex
            b.save()


# ---------------------------------------------------------------------------
# Course structure — 7 modules, ~22 lessons, ~170 blocks
# ---------------------------------------------------------------------------

COURSE_STRUCTURE = [

    # =====================================================================
    # MODULE 0 — CINÉMATIQUE
    # =====================================================================
    {"order": 0, "title": "Cinématique · Décrire le mouvement",
     "description": "Vecteurs, repères, position, vitesse, accélération, "
                    "MRU, MRUA, projectile, mouvement circulaire.",
     "lessons": [

        # -----------------------------------------------------------------
        # Lesson 0.1 — Vecteurs et repères
        # -----------------------------------------------------------------
        {"order": 0, "title": "Vecteurs et repères", "slug": "vecteurs-reperes",
         "minutes": 30, "blocks": [
            T(
                "# Vecteurs et repères en physique\n\n"
                "## 1. Qu'est-ce qu'un vecteur ?\n\n"
                "Un **vecteur** est une grandeur qui possède quatre caractéristiques :\n"
                "- une **direction** (l'orientation de la droite support) ;\n"
                "- un **sens** (vers où on va le long de cette droite) ;\n"
                "- une **norme** (la valeur numérique, en unités physiques) ;\n"
                "- un **point d'application** (là où il s'exerce).\n\n"
                "Exemples de grandeurs vectorielles : la force $\\vec{F}$, "
                "la vitesse $\\vec{v}$, l'accélération $\\vec{a}$, la position $\\vec{r}$, "
                "le champ électrique $\\vec{E}$.\n\n"
                "## 2. Repère cartésien\n\n"
                "Un **repère** est un système d'axes qui permet de repérer un point "
                "dans l'espace. Le plus courant est le **repère cartésien** "
                "$(O, \\vec{i}, \\vec{j}, \\vec{k})$ :\n\n"
                "- $O$ : origine ;\n"
                "- $\\vec{i}, \\vec{j}, \\vec{k}$ : vecteurs unitaires orthogonaux "
                "(axes $x, y, z$).\n\n"
                "Un vecteur position s'écrit : "
                "$$\\vec{r} = x\\,\\vec{i} + y\\,\\vec{j} + z\\,\\vec{k}$$\n\n"
                "## 3. Norme d'un vecteur\n\n"
                "La norme (longueur) d'un vecteur $\\vec{v} = (v_x, v_y, v_z)$ est :\n"
                "$$|\\vec{v}| = \\sqrt{v_x^2 + v_y^2 + v_z^2}$$\n\n"
                "## 4. Opérations sur les vecteurs\n\n"
                "### Addition\n"
                "$$\\vec{A} + \\vec{B} = (A_x + B_x,\\; A_y + B_y,\\; A_z + B_z)$$\n\n"
                "### Multiplication par un scalaire\n"
                "$$k \\cdot \\vec{A} = (kA_x,\\; kA_y,\\; kA_z)$$\n\n"
                "### Produit scalaire\n"
                "$$\\vec{A} \\cdot \\vec{B} = A_x B_x + A_y B_y + A_z B_z "
                "= |\\vec{A}||\\vec{B}|\\cos\\theta$$\n\n"
                "Le produit scalaire est **nul** si et seulement si les vecteurs sont "
                "**perpendiculaires** ($\\theta = 90°$).\n\n"
                "### Produit vectoriel\n"
                "$$\\vec{A} \\wedge \\vec{B} \\;\\text{est perpendiculaire à }\\; "
                "\\vec{A}\\;\\text{et}\\;\\vec{B},\\;\\; "
                "|\\vec{A} \\wedge \\vec{B}| = |\\vec{A}||\\vec{B}|\\sin\\theta$$\n\n"
                "> 💡 **Astuce** : Toujours choisir un repère *avant* de projeter les "
                "forces. Le choix du bon repère (par exemple le long d'un plan incliné) "
                "simplifie considérablement les calculs."
            ),
            S(
                "Repère cartésien 2D et vecteurs unitaires",
                "import matplotlib.pyplot as plt\n"
                "import numpy as np\n"
                "from matplotlib.patches import FancyArrowPatch\n"
                "\n"
                "fig, ax = plt.subplots(figsize=(7, 6))\n"
                "ax.set_xlim(-1, 6); ax.set_ylim(-1, 6)\n"
                "# Axes principaux\n"
                "ax.add_patch(FancyArrowPatch((0,0), (5.5,0), arrowstyle='->', mutation_scale=20, color='black', lw=2))\n"
                "ax.add_patch(FancyArrowPatch((0,0), (0,5.5), arrowstyle='->', mutation_scale=20, color='black', lw=2))\n"
                "ax.text(5.7, -0.2, r'$x$', fontsize=14)\n"
                "ax.text(-0.3, 5.7, r'$y$', fontsize=14)\n"
                "# Vecteurs unitaires\n"
                "ax.add_patch(FancyArrowPatch((0,0), (1,0), arrowstyle='->', mutation_scale=15, color='red', lw=2.5))\n"
                "ax.add_patch(FancyArrowPatch((0,0), (0,1), arrowstyle='->', mutation_scale=15, color='red', lw=2.5))\n"
                "ax.text(1.1, -0.25, r'$\\vec{i}$', fontsize=13, color='red')\n"
                "ax.text(-0.25, 1.1, r'$\\vec{j}$', fontsize=13, color='red')\n"
                "# Point M(3, 2)\n"
                "ax.plot(3, 2, 'ko', ms=6)\n"
                "ax.add_patch(FancyArrowPatch((0,0), (3,2), arrowstyle='->', mutation_scale=18, color='blue', lw=2))\n"
                "ax.text(1.5, 1.4, r'$\\vec{r}$', fontsize=14, color='blue')\n"
                "ax.text(3.1, 2.1, r'$M(3,2)$', fontsize=11)\n"
                "# Projection en pointillés\n"
                "ax.plot([3,3], [0,2], 'g--', lw=1)\n"
                "ax.plot([0,3], [2,2], 'g--', lw=1)\n"
                "ax.set_title(r'Repère cartésien $(O, \\vec{i}, \\vec{j})$', fontsize=12)\n"
                "ax.set_aspect('equal'); ax.grid(True, alpha=0.3)\n"
                "plt.tight_layout(); plt.savefig('plot.png')\n"
                "print('Repère tracé. M = (3, 2), |r| =', np.sqrt(13))\n"
            ),
            S(
                "Addition vectorielle et produit scalaire",
                "import matplotlib.pyplot as plt\n"
                "import numpy as np\n"
                "from matplotlib.patches import FancyArrowPatch\n"
                "\n"
                "A = np.array([3.0, 1.0])\n"
                "B = np.array([1.0, 2.0])\n"
                "C = A + B\n"
                "\n"
                "fig, ax = plt.subplots(figsize=(7, 6))\n"
                "ax.set_xlim(-0.5, 5); ax.set_ylim(-0.5, 4)\n"
                "def arrow(p, q, color, label):\n"
                "    ax.add_patch(FancyArrowPatch(p, q, arrowstyle='->', mutation_scale=20, color=color, lw=2.2))\n"
                "    ax.text((p[0]+q[0])/2, (p[1]+q[1])/2 + 0.15, label, fontsize=13, color=color)\n"
                "arrow((0,0), tuple(A), 'blue', r'$\\vec{A}$')\n"
                "arrow(tuple(A), tuple(C), 'red', r'$\\vec{B}$')\n"
                "arrow((0,0), tuple(C), 'green', r'$\\vec{A}+\\vec{B}$')\n"
                "ax.set_title(r'Addition vectorielle : $\\vec{A}+\\vec{B}$ (règle du triangle)', fontsize=11)\n"
                "ax.set_xlabel(r'$x$'); ax.set_ylabel(r'$y$')\n"
                "ax.set_aspect('equal'); ax.grid(True, alpha=0.3)\n"
                "plt.tight_layout(); plt.savefig('plot.png')\n"
                "print(f'A = {A}, B = {B}, A+B = {C}')\n"
                "print(f'|A| = {np.linalg.norm(A):.3f}')\n"
                "print(f'|B| = {np.linalg.norm(B):.3f}')\n"
                "print(f'A.B = {np.dot(A,B):.3f}')\n"
                "theta = np.degrees(np.arccos(np.dot(A,B)/(np.linalg.norm(A)*np.linalg.norm(B))))\n"
                "print(f'angle(A,B) = {theta:.1f} deg')\n"
            ),
            APP(
                "Vecteur vitesse d'un drone",
                "Un drone se déplace du point $A(0, 0)$ au point $B(60, 80)$ "
                "(en mètres) en $10$ s. Sa vitesse moyenne est-elle constante ? "
                "Calcule la norme du vecteur déplacement $\\vec{AB}$, la norme de "
                "la vitesse moyenne $\\vec{v}_{moy}$, et l'angle que fait $\\vec{AB}$ "
                "avec l'axe $x$.",
                "On a $\\vec{AB} = (60 - 0)\\,\\vec{i} + (80 - 0)\\,\\vec{j} = "
                "60\\,\\vec{i} + 80\\,\\vec{j}$ (en m).\n\n"
                "**Norme du déplacement** :\n"
                "$$|\\vec{AB}| = \\sqrt{60^2 + 80^2} = \\sqrt{3600 + 6400} = "
                "\\sqrt{10000} = 100\\;\\text{m}.$$\n\n"
                "**Vitesse moyenne** (vecteur) :\n"
                "$$\\vec{v}_{moy} = \\frac{\\vec{AB}}{\\Delta t} = "
                "\\frac{60\\,\\vec{i} + 80\\,\\vec{j}}{10} = "
                "6\\,\\vec{i} + 8\\,\\vec{j}\\;\\;\\text{m/s}.$$\n\n"
                "**Norme** : $|\\vec{v}_{moy}| = \\sqrt{6^2 + 8^2} = 10$ m/s.\n\n"
                "**Angle avec l'axe $x$** :\n"
                "$$\\theta = \\arctan\\!\\left(\\frac{80}{60}\\right) = "
                "\\arctan(4/3) \\approx 53{,}1°.$$\n\n"
                "Le drone s'est déplacé à 10 m/s dans une direction à ~53° au-dessus "
                "de l'horizontale. Si l'énoncé précise que le mouvement est rectiligne "
                "et uniforme, alors la vitesse instantanée est constante et égale à "
                "la vitesse moyenne."
            ),
            MCQ(
                "Norme d'un vecteur",
                "Quelle est la norme du vecteur $\\vec{v} = (3, 4)$ ?",
                [
                    {"text": "7", "correct": False, "feedback": "3+4=7 mais ce n'est pas ainsi que se calcule une norme."},
                    {"text": "5", "correct": True, "feedback": "Exact ! $\\sqrt{3^2+4^2}=\\sqrt{25}=5$."},
                    {"text": "25", "correct": False, "feedback": "C'est le carré de la norme, pas la norme."},
                    {"text": "12", "correct": False, "feedback": "$3\\times 4=12$ est le produit des composantes, sans signification physique ici."}
                ],
                explanation="$|\\vec{v}|=\\sqrt{v_x^2+v_y^2}=\\sqrt{9+16}=5$."
            ),
            MCQ(
                "Perpendicularité",
                "Deux vecteurs non nuls $\\vec{A}$ et $\\vec{B}$ sont perpendiculaires "
                "si et seulement si :",
                [
                    {"text": "$\\vec{A}\\cdot\\vec{B}=0$", "correct": True, "feedback": "Oui : produit scalaire nul $\\Leftrightarrow$ angle de 90°."},
                    {"text": "$\\vec{A}\\wedge\\vec{B}=0$", "correct": False, "feedback": "Non : produit vectoriel nul $\\Leftrightarrow$ vecteurs parallèles."},
                    {"text": "$|\\vec{A}|=|\\vec{B}|$", "correct": False, "feedback": "Ce n'est qu'une égalité de longueur, sans lien avec l'angle."},
                    {"text": "$\\vec{A}+\\vec{B}=\\vec{0}$", "correct": False, "feedback": "Cela signifie $\\vec{A}=-\\vec{B}$ (opposés, donc parallèles)."}
                ],
                explanation="$\\vec{A}\\cdot\\vec{B}=|\\vec{A}||\\vec{B}|\\cos\\theta=0 \\Leftrightarrow \\cos\\theta=0 \\Leftrightarrow \\theta=90°$."
            ),
            FB(
                "Composantes d'un vecteur",
                "Un vecteur $\\vec{v}$ a pour composantes $v_x = 6$ et $v_y = 8$. "
                "Sa norme vaut {{blank_1}}. "
                "L'angle qu'il fait avec l'axe $x$ vaut {{blank_2}} degrés "
                "(arrondi à l'entier). "
                "Si on multiplie $\\vec{v}$ par $-2$, la nouvelle norme vaut {{blank_3}}.",
                {"blank_1": ["10"], "blank_2": ["53"], "blank_3": ["20"]},
                explanation="$|\\vec{v}|=\\sqrt{36+64}=10$ ; $\\theta=\\arctan(8/6)\\approx 53°$ ; "
                            "$|-2\\vec{v}|=2|\\vec{v}|=20$."
            ),
            TF(
                "Vrai ou Faux ? Vecteurs",
                [
                    {"statement": "La vitesse est une grandeur vectorielle.", "is_true": True,
                     "statement_note": "Elle a direction, sens et norme."},
                    {"statement": "La norme d'un vecteur peut être négative.", "is_true": False,
                     "statement_note": "Une norme est toujours positive (c'est une racine carrée)."},
                    {"statement": "Si $\\vec{A}\\cdot\\vec{B}=0$ alors $\\vec{A}=\\vec{0}$ ou $\\vec{B}=\\vec{0}$.",
                     "is_true": False, "statement_note": "Faux : ils peuvent simplement être perpendiculaires."},
                    {"statement": "La masse est une grandeur vectorielle.", "is_true": False,
                     "statement_note": "La masse est un scalaire."},
                    {"statement": "Le produit vectoriel $\\vec{A}\\wedge\\vec{B}$ est anticommutatif : "
                                   "$\\vec{A}\\wedge\\vec{B}=-\\vec{B}\\wedge\\vec{A}$.",
                     "is_true": True, "statement_note": "Propriété fondamentale du produit vectoriel."}
                ]
            )
        ]},

        # -----------------------------------------------------------------
        # Lesson 0.2 — Position, vitesse, accélération
        # -----------------------------------------------------------------
        {"order": 1, "title": "Position, vitesse et accélération",
         "slug": "position-vitesse-acceleration", "minutes": 35, "blocks": [
            T(
                "# Position, vitesse et accélération\n\n"
                "## 1. Vecteur position\n\n"
                "La **position** d'un objet à l'instant $t$ est donnée par le vecteur "
                "position $\\vec{r}(t)$ :\n"
                "$$\\vec{r}(t) = x(t)\\,\\vec{i} + y(t)\\,\\vec{j} + z(t)\\,\\vec{k}$$\n\n"
                "## 2. Vecteur vitesse\n\n"
                "La **vitesse instantanée** est la dérivée de la position par rapport "
                "au temps :\n"
                "$$\\vec{v}(t) = \\frac{d\\vec{r}}{dt} = \\dot{\\vec{r}} = "
                "v_x\\,\\vec{i} + v_y\\,\\vec{j} + v_z\\,\\vec{k}$$\n\n"
                "où $v_x = \\dot{x}$, $v_y = \\dot{y}$, $v_z = \\dot{z}$.\n\n"
                "La **vitesse scalaire** (norme) est : "
                "$$v = |\\vec{v}| = \\sqrt{v_x^2 + v_y^2 + v_z^2}$$\n\n"
                "## 3. Vecteur accélération\n\n"
                "L'**accélération instantanée** est la dérivée de la vitesse (donc la "
                "dérivée seconde de la position) :\n"
                "$$\\vec{a}(t) = \\frac{d\\vec{v}}{dt} = \\frac{d^2\\vec{r}}{dt^2}$$\n\n"
                "## 4. Cas particulier : MRUA\n\n"
                "Pour un **Mouvement Rectiligne Uniformément Accéléré** "
                "(accélération $a$ constante) :\n"
                "$$x(t) = x_0 + v_0\\, t + \\tfrac{1}{2}\\, a\\, t^2$$\n"
                "$$v(t) = v_0 + a\\, t$$\n"
                "$$v^2 - v_0^2 = 2\\, a\\, (x - x_0)$$\n\n"
                "Cette dernière relation est très utile car elle élimine le temps.\n\n"
                "## 5. Coord. polaires et base de Frenet\n\n"
                "Pour un mouvement curviligne, on utilise souvent la **base de Frenet** "
                "$(\\vec{T}, \\vec{N})$ : $\\vec{T}$ tangent à la trajectoire, "
                "$\\vec{N}$ perpendiculaire dirigé vers le centre de courbure.\n"
                "$$\\vec{a} = \\frac{dv}{dt}\\,\\vec{T} + \\frac{v^2}{R}\\,\\vec{N}$$\n\n"
                "> 💡 **Astuce** : La composante normale $v^2/R$ est toujours positive "
                "et dirigée vers le centre de courbure. Pour un mouvement circulaire "
                "uniforme, $dv/dt = 0$ et toute l'accélération est centripète."
            ),
            S(
                "MRUA : tracer x(t), v(t), a(t)",
                "import matplotlib.pyplot as plt\n"
                "import numpy as np\n"
                "\n"
                "t = np.linspace(0, 10, 200)\n"
                "x0, v0, a = 0.0, 5.0, 2.0\n"
                "x = x0 + v0*t + 0.5*a*t**2\n"
                "v = v0 + a*t\n"
                "acc = np.full_like(t, a)\n"
                "\n"
                "fig, axes = plt.subplots(3, 1, figsize=(8, 10), sharex=True)\n"
                "axes[0].plot(t, x, 'b-', lw=2)\n"
                "axes[0].set_ylabel(r'$x(t)$ [m]')\n"
                "axes[0].set_title(r'MRUA : $x(t)=x_0+v_0 t+\\frac{1}{2}at^2$')\n"
                "axes[0].grid(True, alpha=0.3)\n"
                "axes[1].plot(t, v, 'r-', lw=2)\n"
                "axes[1].set_ylabel(r'$v(t)$ [m/s]')\n"
                "axes[1].grid(True, alpha=0.3)\n"
                "axes[2].plot(t, acc, 'g-', lw=2)\n"
                "axes[2].set_ylabel(r'$a(t)$ [m/s$^2$]')\n"
                "axes[2].set_xlabel(r'$t$ [s]')\n"
                "axes[2].grid(True, alpha=0.3)\n"
                "plt.tight_layout(); plt.savefig('plot.png')\n"
                "print(f'A t=10s : x={x[-1]:.1f} m, v={v[-1]:.1f} m/s, a={a} m/s^2')\n"
            ),
            APP(
                "Voiture qui accélère",
                "Une voiture démarre du repos ($v_0=0$) avec une accélération constante "
                "$a=3$ m/s². (a) Quelle est sa vitesse après 5 s ? (b) Quelle distance "
                "a-t-elle parcourue en 5 s ? (c) Quelle est sa vitesse après avoir "
                "parcouru 60 m ?",
                "**(a) Vitesse à $t=5$ s** :\n"
                "$$v = v_0 + at = 0 + 3 \\times 5 = 15\\;\\text{m/s} = 54\\;\\text{km/h}.$$\n\n"
                "**(b) Distance parcourue en 5 s** :\n"
                "$$x = x_0 + v_0 t + \\tfrac{1}{2}at^2 = 0 + 0 + \\tfrac{1}{2}\\times 3 \\times 25 "
                "= 37{,}5\\;\\text{m}.$$\n\n"
                "**(c) Vitesse après 60 m** — on utilise $v^2 - v_0^2 = 2a(x-x_0)$ :\n"
                "$$v^2 = 0 + 2 \\times 3 \\times 60 = 360 \\quad\\Rightarrow\\quad "
                "v = \\sqrt{360} \\approx 18{,}97\\;\\text{m/s} \\approx 68{,}3\\;\\text{km/h}.$$\n\n"
                "On peut vérifier la cohérence : pour parcourir 60 m il faut "
                "$t = v/a \\approx 6{,}32$ s, ce qui donne bien $x=\\tfrac12\\times 3 \\times 6{,}32^2 "
                "\\approx 60$ m."
            ),
            MCQ(
                "Vitesse et dérivée",
                "La vitesse est la dérivée de ___ par rapport au temps.",
                [
                    {"text": "L'accélération", "correct": False, "feedback": "Non, c'est l'inverse : l'accélération est la dérivée de la vitesse."},
                    {"text": "La position", "correct": True, "feedback": "Exact ! $\\vec{v}=d\\vec{r}/dt$."},
                    {"text": "La force", "correct": False, "feedback": "La force est liée à l'accélération via $\\vec{F}=m\\vec{a}$."},
                    {"text": "L'énergie", "correct": False, "feedback": "L'énergie n'intervient pas dans la définition de la vitesse."}
                ],
                explanation="$\\vec{v}(t) = \\dfrac{d\\vec{r}}{dt}$."
            ),
            MCQ(
                "Relation indépendante du temps",
                "Quelle relation MRUA élimine le temps $t$ ?",
                [
                    {"text": "$x = x_0 + v_0 t + \\frac12 at^2$", "correct": False, "feedback": "Cette équation contient $t$."},
                    {"text": "$v = v_0 + at$", "correct": False, "feedback": "Cette équation contient aussi $t$."},
                    {"text": "$v^2 - v_0^2 = 2a(x-x_0)$", "correct": True, "feedback": "Bravo ! Relation très utile quand on ne connaît pas $t$."},
                    {"text": "$a = dv/dt$", "correct": False, "feedback": "C'est la définition générale de $a$, pas une relation MRUA."}
                ],
                explanation="$v^2 - v_0^2 = 2a(x-x_0)$ s'obtient en éliminant $t$ entre "
                            "$v=v_0+at$ et $x=x_0+v_0 t+\\tfrac12 at^2$."
            ),
            FB(
                "Compléter les équations du MRUA",
                "Pour un MRUA : $x(t) = x_0 + v_0 t + {{blank_1}}\\, a\\, t^2$ ; "
                "$v(t) = {{blank_2}} + a\\, t$ ; "
                "l'accélération est la dérivée de la {{blank_3}} par rapport au temps.",
                {"blank_1": ["0.5", "1/2", "\\frac{1}{2}"],
                 "blank_2": ["v_0", "v0"],
                 "blank_3": ["vitesse", "vitesse v"]},
                explanation="Le coefficient $\\tfrac12$ provient de l'intégration de $v=v_0+at$ ; "
                            "la vitesse initiale est $v_0$ ; l'accélération est $\\dot{v}$."
            ),
            TF(
                "Vrai ou Faux ? Cinématique",
                [
                    {"statement": "L'accélération est la dérivée seconde de la position par rapport au temps.",
                     "is_true": True},
                    {"statement": "La norme de la vitesse peut être négative.", "is_true": False,
                     "statement_note": "Une norme est positive ; le signe indique un sens le long d'un axe orienté."},
                    {"statement": "Dans un MRUA, l'accélération est constante.", "is_true": True},
                    {"statement": "L'unité SI de l'accélération est m/s.", "is_true": False,
                     "statement_note": "C'est m/s²."},
                    {"statement": "La composante normale de l'accélération vaut $v^2/R$.",
                     "is_true": True}
                ]
            )
        ]},

        # -----------------------------------------------------------------
        # Lesson 0.3 — MRU / MRUA et distance de freinage
        # -----------------------------------------------------------------
        {"order": 2, "title": "Mouvement rectiligne : MRU et MRUA",
         "slug": "mru-mrua-freinage", "minutes": 30, "blocks": [
            T(
                "# Mouvement rectiligne : MRU et MRUA\n\n"
                "## 1. Mouvement Rectiligne Uniforme (MRU)\n\n"
                "Vitesse **constante** (donc $a=0$) le long d'une droite :\n"
                "$$x(t) = x_0 + v\\, t$$\n\n"
                "## 2. Mouvement Rectiligne Uniformément Accéléré (MRUA)\n\n"
                "Accélération **constante** :\n"
                "$$v(t) = v_0 + a\\, t, \\quad x(t) = x_0 + v_0 t + \\tfrac12 a t^2$$\n\n"
                "## 3. Distance de freinage\n\n"
                "Si la voiture freine avec une décélération $a<0$ jusqu'à s'arrêter "
                "($v=0$), la **distance de freinage** $d_f$ vaut :\n"
                "$$d_f = \\frac{v_0^2}{2|a|}$$\n\n"
                "Elle dépend du **carré** de la vitesse initiale : doubler la vitesse "
                "multiplie la distance de freinage par **4**.\n\n"
                "## 4. Distance de réaction\n\n"
                "Le conducteur a un **temps de réaction** $t_r \\approx 1$ s pendant "
                "lequel la voiture continue à vitesse constante. La distance de "
                "réaction vaut $d_r = v_0\\, t_r$.\n\n"
                "## 5. Distance d'arrêt\n\n"
                "$$d_{arr} = d_r + d_f = v_0\\, t_r + \\frac{v_0^2}{2|a|}$$\n\n"
                "> 💡 **Astuce** : Sur route mouillée, $|a|$ est divisée par environ 2 "
                "(adhérence réduite), donc $d_f$ est doublée. À 130 km/h sur autoroute "
                "sèche, $d_{arr} \\approx 130$ m ; sur sol mouillé, près de 200 m."
            ),
            S(
                "MRU vs MRUA — comparaison",
                "import matplotlib.pyplot as plt\n"
                "import numpy as np\n"
                "\n"
                "t = np.linspace(0, 8, 200)\n"
                "x_mru = 5 * t                  # v = 5 m/s constant\n"
                "x_mrua = 0.5 * 1.5 * t**2      # demarre de 0, a = 1.5 m/s^2\n"
                "\n"
                "fig, ax = plt.subplots(figsize=(8, 5))\n"
                "ax.plot(t, x_mru, 'b-', lw=2, label=r'MRU : $v=5$ m/s (constante)')\n"
                "ax.plot(t, x_mrua, 'r-', lw=2, label=r'MRUA : $a=1{,}5$ m/s$^2$')\n"
                "ax.set_xlabel(r'$t$ [s]'); ax.set_ylabel(r'$x(t)$ [m]')\n"
                "ax.set_title('Comparaison MRU vs MRUA')\n"
                "ax.legend(); ax.grid(True, alpha=0.3)\n"
                "plt.tight_layout(); plt.savefig('plot.png')\n"
                "print(f'A t=8 s : MRU x={x_mru[-1]:.1f} m ; MRUA x={x_mrua[-1]:.1f} m')\n"
            ),
            S(
                "Distance de freinage vs vitesse initiale",
                "import matplotlib.pyplot as plt\n"
                "import numpy as np\n"
                "\n"
                "v0 = np.linspace(0, 50, 100)   # m/s (= 0 a 180 km/h)\n"
                "a_dec = 7.0                    # m/s^2 (freinage fort sur sol sec)\n"
                "d_f = v0**2 / (2*a_dec)\n"
                "\n"
                "fig, ax = plt.subplots(figsize=(8, 5))\n"
                "ax.plot(v0*3.6, d_f, 'r-', lw=2, label=r'$d_f = v_0^2/(2|a|)$')\n"
                "ax.set_xlabel(r'$v_0$ [km/h]')\n"
                "ax.set_ylabel(r'Distance de freinage $d_f$ [m]')\n"
                "ax.set_title(r'Freinage ($|a|=7$ m/s$^2$) : $d_f \\propto v_0^2$')\n"
                "ax.legend(); ax.grid(True, alpha=0.3)\n"
                "plt.tight_layout(); plt.savefig('plot.png')\n"
                "print(f'A 50 km/h : d_f = {d_f[np.argmin(abs(v0*3.6-50))]:.1f} m')\n"
                "print(f'A 130 km/h : d_f = {d_f[np.argmin(abs(v0*3.6-130))]:.1f} m')\n"
                "print(f'A 130 km/h, distance x4 par rapport a 50 km/h')\n"
            ),
            APP(
                "Distance d'arrêt à 130 km/h",
                "Une voiture roule à $130$ km/h sur autoroute. Le temps de réaction "
                "du conducteur est $t_r = 1{,}0$ s et la décélération maximale de "
                "freinage est $|a| = 7{,}0$ m/s². Calcule la distance de réaction, "
                "la distance de freinage et la distance d'arrêt totale. Que devient "
                "cette distance d'arrêt si la route est mouillée ($|a|$ divisé par 2) ?",
                "Conversion : $v_0 = 130/3{,}6 \\approx 36{,}1$ m/s.\n\n"
                "**Distance de réaction** :\n"
                "$$d_r = v_0\\, t_r \\approx 36{,}1 \\times 1 = 36{,}1\\;\\text{m}.$$\n\n"
                "**Distance de freinage (sol sec)** :\n"
                "$$d_f = \\frac{v_0^2}{2|a|} = \\frac{36{,}1^2}{2\\times 7} = "
                "\\frac{1303}{14} \\approx 93{,}1\\;\\text{m}.$$\n\n"
                "**Distance d'arrêt totale** : "
                "$d_{arr} = d_r + d_f \\approx 36{,}1 + 93{,}1 \\approx 129{,}2$ m.\n\n"
                "**Sur route mouillée** ($|a| = 3{,}5$ m/s²) :\n"
                "$$d_f' = \\frac{1303}{2\\times 3{,}5} \\approx 186{,}1\\;\\text{m},\\quad "
                "d_{arr}' \\approx 36{,}1 + 186{,}1 \\approx 222\\;\\text{m}.$$\n\n"
                "On voit que la distance d'arrêt est presque doublée sur sol mouillé. "
                "C'est pourquoi il est recommandé de réduire la vitesse de 20 km/h "
                "sur autoroute mouillée (110 km/h au lieu de 130 km/h)."
            ),
            MCQ(
                "Effet du doublement de vitesse",
                "Si on double la vitesse initiale $v_0$, la distance de freinage "
                "$d_f = v_0^2/(2|a|)$ est multipliée par :",
                [
                    {"text": "2", "correct": False, "feedback": "Non, ce n'est pas linéaire."},
                    {"text": "4", "correct": True, "feedback": "Exact : $d_f \\propto v_0^2$."},
                    {"text": "8", "correct": False, "feedback": "Trop."},
                    {"text": "1 (inchangée)", "correct": False, "feedback": "Faux, la distance augmente."}
                ],
                explanation="$d_f$ est proportionnelle à $v_0^2$, donc doubler $v_0$ "
                            "multiplie $d_f$ par $2^2 = 4$."
            ),
            MCQ(
                "Distance de réaction",
                "À 90 km/h, avec un temps de réaction de 1 s, quelle est la distance "
                "de réaction ?",
                [
                    {"text": "9 m", "correct": False, "feedback": "Tu as oublié de convertir en m/s."},
                    {"text": "25 m", "correct": True, "feedback": "$v=90/3{,}6=25$ m/s, donc $d_r=25\\times 1=25$ m."},
                    {"text": "90 m", "correct": False, "feedback": "Tu as utilisé 90 km/h comme si c'était des m/s."},
                    {"text": "45 m", "correct": False, "feedback": "Non, divise bien par 3,6."}
                ],
                explanation="$v = 90/3{,}6 = 25$ m/s, donc $d_r = v t_r = 25 \\times 1 = 25$ m."
            ),
            FB(
                "Compléter les formules",
                "Distance de freinage : $d_f = \\dfrac{v_0^2}{2\\,{{blank_1}}}$ ; "
                "Distance de réaction : $d_r = v_0 \\times {{blank_2}}$ ; "
                "Distance d'arrêt : $d_{arr} = d_r + {{blank_3}}$.",
                {"blank_1": ["|a|", "a", "a|"], "blank_2": ["t_r", "tr", "t_r"],
                 "blank_3": ["d_f", "d_f"]},
                explanation="La décélération apparaît au dénominateur ; le temps de réaction "
                            "multiplie $v_0$ ; la distance d'arrêt est la somme des deux."
            ),
            TF(
                "Vrai ou Faux ? Freinage",
                [
                    {"statement": "Doubler la vitesse multiplie la distance de freinage par 4.",
                     "is_true": True},
                    {"statement": "La distance de réaction dépend de l'état de la route.",
                     "is_true": False, "statement_note": "Elle ne dépend que de $v_0$ et $t_r$."},
                    {"statement": "Sur route mouillée, la distance de freinage augmente.",
                     "is_true": True},
                    {"statement": "Le temps de réaction moyen est d'environ 1 seconde.",
                     "is_true": True},
                    {"statement": "La distance de freinage est proportionnelle à $v_0$.",
                     "is_true": False, "statement_note": "Elle est proportionnelle à $v_0^2$."}
                ]
            )
        ]},

        # -----------------------------------------------------------------
        # Lesson 0.4 — Mouvement parabolique (projectile)
        # -----------------------------------------------------------------
        {"order": 3, "title": "Mouvement parabolique (projectile)",
         "slug": "projectile-parabolique", "minutes": 40, "blocks": [
            T(
                "# Mouvement parabolique (projectile)\n\n"
                "## 1. Décomposition du mouvement\n\n"
                "Un projectile lancé avec une vitesse initiale $\\vec{v}_0$ faisant un "
                "angle $\\theta$ avec l'horizontale n'est soumis qu'à son poids "
                "(on néglige les frottements de l'air).\n\n"
                "**Horizontale** ($x$) : mouvement **uniforme**\n"
                "$$a_x = 0, \\quad v_x = v_0 \\cos\\theta, \\quad "
                "x(t) = v_0 \\cos\\theta \\cdot t$$\n\n"
                "**Verticale** ($y$) : mouvement **uniformément accéléré** ($a_y=-g$)\n"
                "$$v_y(t) = v_0 \\sin\\theta - g\\, t, \\quad "
                "y(t) = v_0 \\sin\\theta \\cdot t - \\tfrac12 g t^2$$\n\n"
                "## 2. Équation de la trajectoire\n\n"
                "En éliminant $t$ entre $x(t)$ et $y(t)$ :\n"
                "$$y(x) = x\\tan\\theta - \\frac{g\\, x^2}{2 v_0^2 \\cos^2\\theta}$$\n\n"
                "C'est l'équation d'une **parabole**.\n\n"
                "## 3. Portée\n\n"
                "$$R = \\frac{v_0^2 \\sin(2\\theta)}{g}$$\n\n"
                "La portée est **maximale** pour $\\theta = 45°$ ($\\sin 90° = 1$).\n\n"
                "## 4. Hauteur maximale\n\n"
                "$$h_{max} = \\frac{v_0^2 \\sin^2\\theta}{2g}$$\n\n"
                "## 5. Temps de vol\n\n"
                "$$t_{vol} = \\frac{2 v_0 \\sin\\theta}{g}$$\n\n"
                "> 💡 **Astuce** : Deux angles complémentaires ($\\theta$ et $90°-\\theta$) "
                "donnent la **même portée**. Par exemple $30°$ et $60°$ atteignent le "
                "même $R$, mais avec des hauteurs maximales différentes."
            ),
            S(
                "Trajectoire parabolique pour plusieurs angles",
                "import matplotlib.pyplot as plt\n"
                "import numpy as np\n"
                "\n"
                "g = 9.81\n"
                "v0 = 20.0  # m/s\n"
                "angles = [15, 30, 45, 60, 75]\n"
                "\n"
                "fig, ax = plt.subplots(figsize=(9, 6))\n"
                "for theta_deg in angles:\n"
                "    th = np.radians(theta_deg)\n"
                "    t_vol = 2*v0*np.sin(th)/g\n"
                "    t = np.linspace(0, t_vol, 200)\n"
                "    x = v0*np.cos(th)*t\n"
                "    y = v0*np.sin(th)*t - 0.5*g*t**2\n"
                "    ax.plot(x, y, lw=2, label=r'$\\theta=%d°$' % theta_deg)\n"
                "ax.set_xlabel(r'$x$ [m]'); ax.set_ylabel(r'$y$ [m]')\n"
                "ax.set_title(r'Trajectoires pour $v_0=20$ m/s')\n"
                "ax.legend(); ax.grid(True, alpha=0.3)\n"
                "ax.set_aspect('equal')\n"
                "plt.tight_layout(); plt.savefig('plot.png')\n"
                "R45 = v0**2 * np.sin(np.radians(90))/g\n"
                "print(f'Portee max (a 45 deg) : R = {R45:.2f} m')\n"
                "print(f'Hauteur max (a 45 deg) : h = {(v0**2*np.sin(np.radians(45))**2/(2*g)):.2f} m')\n"
            ),
            S(
                "Portée vs angle",
                "import matplotlib.pyplot as plt\n"
                "import numpy as np\n"
                "\n"
                "g = 9.81\n"
                "v0 = 20.0\n"
                "theta = np.linspace(0, 90, 200)\n"
                "R = v0**2 * np.sin(2*np.radians(theta)) / g\n"
                "\n"
                "fig, ax = plt.subplots(figsize=(8, 5))\n"
                "ax.plot(theta, R, 'b-', lw=2)\n"
                "ax.axvline(45, color='r', ls='--', label=r'Maximum à $\\theta=45°$')\n"
                "ax.set_xlabel(r'Angle $\\theta$ [deg]')\n"
                "ax.set_ylabel(r'Portée $R$ [m]')\n"
                "ax.set_title(r'$R(\\theta)=v_0^2\\sin(2\\theta)/g$,  $v_0=20$ m/s')\n"
                "ax.legend(); ax.grid(True, alpha=0.3)\n"
                "plt.tight_layout(); plt.savefig('plot.png')\n"
                "print(f'Portee max = {R.max():.2f} m a theta = 45 deg')\n"
                "print(f'R(30 deg) = R(60 deg) = {v0**2*np.sin(np.radians(60))/g:.2f} m (angles complementaires)')\n"
            ),
            APP(
                "Tir au basket",
                "Un joueur lance un ballon à $v_0 = 8$ m/s avec un angle $\\theta = 55°$. "
                "Le ballon part d'une hauteur $h_0 = 2{,}0$ m. (a) Calcule la portée "
                "théorique si le ballon retombe à la même hauteur. (b) Quelle est la "
                "hauteur maximale atteinte (au-dessus du point de départ) ? (c) Combien "
                "de temps le ballon met-il à atteindre cette hauteur ?",
                "Données : $g = 9{,}81$ m/s², $v_0 = 8$ m/s, $\\theta = 55°$.\n"
                "$\\sin(55°) \\approx 0{,}819$, $\\cos(55°) \\approx 0{,}574$.\n\n"
                "**(a) Portée** (à hauteur égale) :\n"
                "$$R = \\frac{v_0^2 \\sin(2\\theta)}{g} = "
                "\\frac{64 \\times \\sin(110°)}{9{,}81} \\approx "
                "\\frac{64 \\times 0{,}940}{9{,}81} \\approx 6{,}13\\;\\text{m}.$$\n\n"
                "**(b) Hauteur maximale** :\n"
                "$$h_{max} = \\frac{v_0^2 \\sin^2\\theta}{2g} = "
                "\\frac{64 \\times 0{,}819^2}{2 \\times 9{,}81} \\approx "
                "\\frac{64 \\times 0{,}671}{19{,}62} \\approx 2{,}19\\;\\text{m}.$$\n"
                "Le ballon atteint donc une hauteur absolue de $h_0 + h_{max} \\approx "
                "4{,}19$ m.\n\n"
                "**(c) Temps pour atteindre $h_{max}$** :\n"
                "$$t_{mont} = \\frac{v_0 \\sin\\theta}{g} = \\frac{8 \\times 0{,}819}{9{,}81} "
                "\\approx 0{,}668\\;\\text{s}.$$\n\n"
                "Le panier est à 3,05 m, le ballon atteint donc largement la hauteur "
                "nécessaire, mais la portée de 6,13 m doit correspondre à la distance "
                "joueur-panier pour un tir réussi."
            ),
            MCQ(
                "Angle de portée maximale",
                "Pour quelle valeur de $\\theta$ la portée $R = v_0^2\\sin(2\\theta)/g$ "
                "est-elle maximale ?",
                [
                    {"text": "30°", "correct": False, "feedback": "Donne $\\sin 60° \\approx 0{,}866$."},
                    {"text": "45°", "correct": True, "feedback": "Oui : $\\sin 90° = 1$, valeur maximale du sinus."},
                    {"text": "60°", "correct": False, "feedback": "Donne $\\sin 120° = \\sin 60°$, même portée qu'à 30°."},
                    {"text": "90°", "correct": False, "feedback": "Tir vertical : portée nulle."}
                ],
                explanation="$\\sin(2\\theta)$ est maximal pour $2\\theta = 90°$, donc $\\theta = 45°$."
            ),
            MCQ(
                "Angles complémentaires",
                "Pour $\\theta = 30°$ et $\\theta' = 60°$ (avec le même $v_0$), "
                "quelle proposition est vraie ?",
                [
                    {"text": "Les portées sont différentes.", "correct": False, "feedback": "Non, elles sont égales."},
                    {"text": "Les portées sont égales, $h_{max}$ aussi.", "correct": False, "feedback": "Les portées sont égales mais pas les hauteurs max."},
                    {"text": "Les portées sont égales, $h_{max}(60°) > h_{max}(30°)$.", "correct": True, "feedback": "Exact ! $\\sin^2(60°) > \\sin^2(30°)$."},
                    {"text": "Les temps de vol sont égaux.", "correct": False, "feedback": "Non, $t_{vol} \\propto \\sin\\theta$ donc différent."}
                ],
                explanation="$\\sin(2\\times 30°) = \\sin(60°) = \\sin(120°) = \\sin(2\\times 60°)$, "
                            "donc $R$ est le même. Mais $\\sin^2(60°) > \\sin^2(30°)$, donc "
                            "$h_{max}$ est plus grand à 60°."
            ),
            FB(
                "Équations du projectile",
                "Pour un projectile : $x(t) = v_0 \\cos\\theta \\cdot {{blank_1}}$ ; "
                "$y(t) = v_0 \\sin\\theta \\cdot t - \\frac12 g\\,{{blank_2}}$ ; "
                "la portée vaut $R = v_0^2 \\sin(2\\theta) / {{blank_3}}$.",
                {"blank_1": ["t"], "blank_2": ["t^2", "t**2"], "blank_3": ["g"]},
                explanation="$x$ évolue linéairement avec $t$, $y$ avec $t^2$, et "
                            "la portée fait intervenir $g$ au dénominateur."
            ),
            TF(
                "Vrai ou Faux ? Projectile",
                [
                    {"statement": "Sans frottement, la trajectoire est une parabole.",
                     "is_true": True},
                    {"statement": "Le mouvement horizontal est uniformément accéléré.",
                     "is_true": False, "statement_note": "Il est uniforme ($a_x=0$)."},
                    {"statement": "La portée maximale est atteinte à 45°.",
                     "is_true": True},
                    {"statement": "Au sommet de la trajectoire, $v_y = 0$.",
                     "is_true": True},
                    {"statement": "Le temps de vol ne dépend pas de l'angle de tir.",
                     "is_true": False, "statement_note": "$t_{vol} \\propto \\sin\\theta$."}
                ]
            )
        ]},

        # -----------------------------------------------------------------
        # Lesson 0.5 — Mouvement circulaire uniforme
        # -----------------------------------------------------------------
        {"order": 4, "title": "Mouvement circulaire uniforme",
         "slug": "mouvement-circulaire-uniforme", "minutes": 35, "blocks": [
            T(
                "# Mouvement circulaire uniforme (MCU)\n\n"
                "## 1. Définition\n\n"
                "Un point est en **mouvement circulaire uniforme** s'il parcourt un "
                "cercle de rayon $R$ à **vitesse scalaire constante** $v$.\n\n"
                "## 2. Grandeurs angulaires\n\n"
                "L'angle balayé est $\\theta(t) = \\omega\\, t$ où $\\omega$ est la "
                "**vitesse angulaire** (en rad/s).\n\n"
                "Relation entre vitesse linéaire et angulaire :\n"
                "$$v = \\omega\\, R$$\n\n"
                "La **période** $T$ (temps d'un tour) et la **fréquence** $f$ :\n"
                "$$T = \\frac{2\\pi}{\\omega}, \\quad f = \\frac{1}{T}, \\quad "
                "\\omega = 2\\pi f$$\n\n"
                "## 3. Accélération centripète\n\n"
                "Bien que la vitesse scalaire soit constante, le **vecteur** vitesse "
                "change de direction, donc il y a une accélération. Dans la base de "
                "Frenet :\n"
                "$$\\vec{a} = \\frac{v^2}{R}\\,\\vec{N}$$\n\n"
                "L'accélération est **centripète** (dirigée vers le centre du cercle), "
                "de norme :\n"
                "$$a = \\frac{v^2}{R} = \\omega^2 R$$\n\n"
                "## 4. Application : virage routier\n\n"
                "Pour qu'une voiture prenne un virage de rayon $R$ à la vitesse $v$, "
                "le frottement des pneus doit fournir la force centripète :\n"
                "$$f = m\\,\\frac{v^2}{R}$$\n\n"
                "> 💡 **Astuce** : Si $v$ double, l'accélération centripète est "
                "multipliée par **4**. C'est pourquoi les virages serrés sont "
                "beaucoup plus dangereux à grande vitesse."
            ),
            S(
                "MCU : cercle et vecteurs v, a",
                "import matplotlib.pyplot as plt\n"
                "import numpy as np\n"
                "from matplotlib.patches import FancyArrowPatch\n"
                "\n"
                "R = 3.0\n"
                "omega = 2.0  # rad/s\n"
                "theta_pts = np.linspace(0, 2*np.pi, 9)[:-1]\n"
                "\n"
                "fig, ax = plt.subplots(figsize=(7, 7))\n"
                "theta = np.linspace(0, 2*np.pi, 200)\n"
                "ax.plot(R*np.cos(theta), R*np.sin(theta), 'b-', lw=2)\n"
                "ax.plot(0, 0, 'ko')\n"
                "\n"
                "for th in theta_pts:\n"
                "    px, py = R*np.cos(th), R*np.sin(th)\n"
                "    # vitesse tangente (vers le sens trigo)\n"
                "    vx, vy = -R*omega*np.sin(th), R*omega*np.cos(th)\n"
                "    v_norm = np.hypot(vx, vy)\n"
                "    vx, vy = vx/v_norm*1.2, vy/v_norm*1.2\n"
                "    # acceleration centripete\n"
                "    ax_x, ax_y = -np.cos(th)*1.0, -np.sin(th)*1.0\n"
                "    ax.add_patch(FancyArrowPatch((px,py), (px+vx,py+vy), arrowstyle='->', mutation_scale=12, color='green', lw=2))\n"
                "    ax.add_patch(FancyArrowPatch((px,py), (px+ax_x,py+ax_y), arrowstyle='->', mutation_scale=12, color='red', lw=2))\n"
                "ax.plot(R*np.cos(theta_pts), R*np.sin(theta_pts), 'ko', ms=5)\n"
                "ax.text(0.1, 0.1, 'O', fontsize=12)\n"
                "ax.set_xlim(-5, 5); ax.set_ylim(-5, 5)\n"
                "ax.set_aspect('equal'); ax.grid(True, alpha=0.3)\n"
                "ax.set_title(r'MCU : $\\vec{v}$ tangent, $\\vec{a}=v^2/R\\,\\vec{N}$ centripète', fontsize=11)\n"
                "plt.tight_layout(); plt.savefig('plot.png')\n"
                "print('v = omega*R =', omega*R, 'm/s')\n"
                "print('a = v^2/R =', (omega*R)**2/R, 'm/s^2')\n"
                "print('T = 2*pi/omega =', 2*np.pi/omega, 's')\n"
            ),
            APP(
                "Satellite en orbite circulaire basse",
                "L'ISS orbite à $h = 400$ km d'altitude (rayon $R = 6770$ km) avec "
                "une période $T = 92{,}7$ min. (a) Calcule sa vitesse angulaire $\\omega$, "
                "sa vitesse linéaire $v$ et l'accélération centripète. (b) Compare "
                "l'accélération à $g = 9{,}81$ m/s².",
                "Données : $R = 6{,}77\\times 10^6$ m, $T = 92{,}7 \\times 60 = 5562$ s.\n\n"
                "**(a) Vitesse angulaire** :\n"
                "$$\\omega = \\frac{2\\pi}{T} = \\frac{2\\pi}{5562} \\approx "
                "1{,}13\\times 10^{-3}\\;\\text{rad/s}.$$\n\n"
                "**Vitesse linéaire** :\n"
                "$$v = \\omega R = 1{,}13\\times 10^{-3} \\times 6{,}77\\times 10^6 "
                "\\approx 7647\\;\\text{m/s} \\approx 27{,}5\\;\\text{km/h}\\times 1000 "
                "\\approx 27 500\\;\\text{km/h}.$$\n\n"
                "**Accélération centripète** :\n"
                "$$a = \\frac{v^2}{R} = \\frac{7647^2}{6{,}77\\times 10^6} \\approx "
                "8{,}64\\;\\text{m/s}^2.$$\n\n"
                "**(b) Comparaison à $g$** :\n"
                "$$\\frac{a}{g} = \\frac{8{,}64}{9{,}81} \\approx 0{,}88.$$\n\n"
                "L'accélération centripète est **88% de $g$** : les astronautes sont "
                "en état d'apesanteur apparente non pas parce qu'il n'y a plus de "
                "gravité (il y en a encore 88%), mais parce qu'ils sont en **chute "
                "libre permanente** autour de la Terre (état d'impesanteur)."
            ),
            MCQ(
                "Accélération en MCU",
                "Dans un mouvement circulaire uniforme, l'accélération est :",
                [
                    {"text": "Nulle (vitesse constante)", "correct": False, "feedback": "Le vecteur vitesse change de direction, donc $\\vec{a} \\neq \\vec{0}$."},
                    {"text": "Tangente à la trajectoire, vers l'avant", "correct": False, "feedback": "Ce serait le cas d'un mouvement accéléré."},
                    {"text": "Centripète, de norme $v^2/R$", "correct": True, "feedback": "Exact ! Dirigée vers le centre."},
                    {"text": "Centrifuge (vers l'extérieur)", "correct": False, "feedback": "La force centrifuge est une force fictive (référentiel non galiléen)."}
                ],
                explanation="$\\vec{a} = (v^2/R)\\,\\vec{N}$, dirigée vers le centre du cercle."
            ),
            MCQ(
                "Vitesse linéaire et angulaire",
                "Si $R$ est divisé par 2 et $\\omega$ maintenu constant, que devient $v$ ?",
                [
                    {"text": "Multipliée par 2", "correct": False, "feedback": "Non."},
                    {"text": "Divisée par 2", "correct": True, "feedback": "Oui : $v = \\omega R$."},
                    {"text": "Inchangée", "correct": False, "feedback": "Non."},
                    {"text": "Divisée par 4", "correct": False, "feedback": "Trop."}
                ],
                explanation="$v = \\omega R$ est proportionnelle à $R$ si $\\omega$ est fixé."
            ),
            FB(
                "Formules du MCU",
                "Dans un MCU : $v = \\omega \\times {{blank_1}}$ ; "
                "$a = \\dfrac{v^2}{R} = \\omega^2 \\times {{blank_2}}$ ; "
                "la période vaut $T = \\dfrac{2\\pi}{\\omega} = \\dfrac{1}{\\,{{blank_3}}\\,}$.",
                {"blank_1": ["R"], "blank_2": ["R"], "blank_3": ["f", "frequence", "fréquence"]},
                explanation="$v=\\omega R$, $a=\\omega^2 R$, et $T=1/f$."
            ),
            TF(
                "Vrai ou Faux ? MCU",
                [
                    {"statement": "En MCU, le vecteur vitesse change de direction.",
                     "is_true": True},
                    {"statement": "L'accélération est tangente à la trajectoire.",
                     "is_true": False, "statement_note": "Elle est perpendiculaire (centripète)."},
                    {"statement": "Si $v$ double, l'accélération centripète quadruple.",
                     "is_true": True},
                    {"statement": "La période $T$ s'exprime en hertz (Hz).",
                     "is_true": False, "statement_note": "En secondes ; $f$ est en Hz."},
                    {"statement": "$\\omega = 2\\pi f$.",
                     "is_true": True}
                ]
            )
        ]},
    ]},


    # =====================================================================
    # MODULE 1 — DYNAMIQUE
    # =====================================================================
    {"order": 1, "title": "Dynamique · Les lois de Newton",
     "description": "Les trois lois de Newton, forces usuelles, plan incliné, "
                    "frottement, applications aux virages et aux loopings.",
     "lessons": [

        # -----------------------------------------------------------------
        # Lesson 1.1 — Les trois lois de Newton
        # -----------------------------------------------------------------
        {"order": 0, "title": "Les trois lois de Newton",
         "slug": "trois-lois-newton", "minutes": 35, "blocks": [
            T(
                "# Les trois lois de Newton\n\n"
                "## 1. Première loi (principe d'inertie)\n\n"
                "**« Tout corps persévère dans son état de repos ou de mouvement "
                "rectiligne uniforme si les forces qui s'exercent sur lui se "
                "compensent. »**\n\n"
                "$$\\text{Si } \\sum \\vec{F}_{ext} = \\vec{0} \\;\\Rightarrow\\; "
                "\\vec{v} = \\text{constante}$$\n\n"
                "Cela définit les **référentiels galiléens**.\n\n"
                "## 2. Deuxième loi (PFD)\n\n"
                "Principe Fondamental de la Dynamique (relation de Newton) :\n"
                "$$\\sum \\vec{F}_{ext} = m\\, \\vec{a} = \\frac{d\\vec{p}}{dt}$$\n\n"
                "où $\\vec{p} = m\\vec{v}$ est la **quantité de mouvement**.\n\n"
                "## 3. Troisième loi (action-réaction)\n\n"
                "**« À toute action, il existe une réaction opposée de même norme. »**\n"
                "$$\\vec{F}_{A\\to B} = -\\vec{F}_{B\\to A}$$\n\n"
                "Les deux forces agissent sur **deux corps différents**, elles ne "
                "se compensent donc jamais !\n\n"
                "## 4. Bilan des forces — méthode\n\n"
                "1. Système étudié ;\n"
                "2. Référentiel (galiléen) ;\n"
                "3. Bilan des forces (poids, réaction, tension, frottement…) ;\n"
                "4. Choix du repère ;\n"
                "5. Projection du PFD sur les axes ;\n"
                "6. Résolution.\n\n"
                "> 💡 **Astuce** : La 1ère loi est un cas particulier de la 2ème "
                "(quand $\\sum\\vec{F}=\\vec{0}$). Ne pas confondre 1ère et 3ème loi : "
                "la 1ère parle des forces sur le **même** corps ; la 3ème loi relie "
                "deux forces sur **deux corps différents**."
            ),
            S(
                "Schéma des 3 lois de Newton",
                "import matplotlib.pyplot as plt\n"
                "import numpy as np\n"
                "from matplotlib.patches import FancyArrowPatch, Circle\n"
                "\n"
                "fig, axes = plt.subplots(1, 3, figsize=(14, 5))\n"
                "\n"
                "# Loi 1 : inertie (pas de force -> MRU)\n"
                "ax = axes[0]\n"
                "ax.add_patch(Circle((1, 1), 0.3, color='blue'))\n"
                "ax.add_patch(FancyArrowPatch((1.3, 1), (4, 1), arrowstyle='->', mutation_scale=20, color='red', lw=2))\n"
                "ax.text(2.5, 1.4, r'$\\vec{v}$ const.', fontsize=12, color='red')\n"
                "ax.text(2.5, 0.3, r'$\\sum \\vec{F}=\\vec{0}$', fontsize=12)\n"
                "ax.set_xlim(0,5); ax.set_ylim(0,2); ax.set_aspect('equal')\n"
                "ax.set_title('1ère loi : Inertie\\n' + r'(MRU si $\\sum \\vec{F}=\\vec{0}$)', fontsize=10)\n"
                "\n"
                "# Loi 2 : PFD\n"
                "ax = axes[1]\n"
                "ax.add_patch(Circle((2, 1), 0.3, color='blue'))\n"
                "ax.add_patch(FancyArrowPatch((2.3, 1), (4, 1), arrowstyle='->', mutation_scale=20, color='red', lw=2))\n"
                "ax.text(3, 1.4, r'$m\\vec{a}$', fontsize=14, color='red')\n"
                "ax.set_xlim(0,5); ax.set_ylim(0,2); ax.set_aspect('equal')\n"
                "ax.set_title('2ème loi : PFD\\n' + r'$\\sum \\vec{F}=m\\vec{a}$', fontsize=10)\n"
                "\n"
                "# Loi 3 : action-reaction\n"
                "ax = axes[2]\n"
                "ax.add_patch(Circle((1.5, 1), 0.3, color='blue'))\n"
                "ax.add_patch(Circle((3.5, 1), 0.3, color='green'))\n"
                "ax.add_patch(FancyArrowPatch((1.8, 1), (3.2, 1), arrowstyle='->', mutation_scale=18, color='red', lw=2))\n"
                "ax.add_patch(FancyArrowPatch((3.2, 1), (1.8, 1), arrowstyle='->', mutation_scale=18, color='orange', lw=2))\n"
                "ax.text(2.5, 1.5, r'$\\vec{F}_{A\\to B}$', fontsize=11, color='red')\n"
                "ax.text(2.5, 0.4, r'$\\vec{F}_{B\\to A}$', fontsize=11, color='orange')\n"
                "ax.set_xlim(0,5); ax.set_ylim(0,2); ax.set_aspect('equal')\n"
                "ax.set_title('3ème loi : Action-Réaction\\n' + r'$\\vec{F}_{A\\to B}=-\\vec{F}_{B\\to A}$', fontsize=10)\n"
                "\n"
                "for ax in axes:\n"
                "    ax.grid(True, alpha=0.3); ax.set_xticks([]); ax.set_yticks([])\n"
                "plt.tight_layout(); plt.savefig('plot.png')\n"
                "print('3 lois de Newton tracees.')\n"
            ),
            APP(
                "Ascenseur et poids apparent",
                "Une personne de masse $m=70$ kg se tient dans un ascenseur. "
                "Calcule la force normale (poids apparent) exercée par le sol sur la "
                "personne lorsque l'ascenseur : (a) monte à vitesse constante ; "
                "(b) monte avec une accélération vers le haut de $a=2$ m/s² ; "
                "(c) descend avec une accélération vers le bas de $a=2$ m/s².",
                "On note $N$ la force normale du sol sur la personne (vers le haut), "
                "et $P=mg$ son poids (vers le bas). On prend $g=9{,}81$ m/s².\n\n"
                "**(a) Vitesse constante** ($a=0$) :\n"
                "PFD : $N - P = 0 \\Rightarrow N = mg = 70 \\times 9{,}81 \\approx 687$ N. "
                "Le poids apparent est égal au poids réel.\n\n"
                "**(b) Accélération vers le haut** ($a = +2$ m/s²) :\n"
                "PFD : $N - P = ma \\Rightarrow N = m(g+a) = 70 \\times 11{,}81 \\approx 827$ N. "
                "On se sent **plus lourd**.\n\n"
                "**(c) Accélération vers le bas** ($a = -2$ m/s²) :\n"
                "PFD : $N - P = ma \\Rightarrow N = m(g-|a|) = 70 \\times 7{,}81 \\approx 547$ N. "
                "On se sent **plus léger**.\n\n"
                "Si l'ascenseur était en chute libre ($a = -g$), on aurait $N=0$ : "
                "c'est l'**impesanteur** !"
            ),
            MCQ(
                "PFD — ascenseur",
                "Dans un ascenseur qui accélère vers le haut, comment évolue le "
                "poids apparent par rapport au poids réel ?",
                [
                    {"text": "Plus petit", "correct": False, "feedback": "Non, c'est le cas d'une accélération vers le bas."},
                    {"text": "Égal", "correct": False, "feedback": "Seulement si la vitesse est constante."},
                    {"text": "Plus grand", "correct": True, "feedback": "Exact : $N = m(g+a) > mg$."},
                    {"text": "Nul", "correct": False, "feedback": "Cela arriverait en chute libre."}
                ],
                explanation="$N - mg = ma \\Rightarrow N = m(g+a)$ avec $a > 0$, donc $N > mg$."
            ),
            MCQ(
                "Action-réaction",
                "Si A pousse B avec une force de 50 N, quelle force B exerce-t-il sur A ?",
                [
                    {"text": "0 N (les forces se compensent)", "correct": False, "feedback": "Les forces ne s'appliquent pas au même corps."},
                    {"text": "50 N dans le même sens", "correct": False, "feedback": "Non, la réaction est opposée."},
                    {"text": "50 N dans le sens opposé", "correct": True, "feedback": "Exact ! Loi de l'action-réaction."},
                    {"text": "Dépend des masses", "correct": False, "feedback": "Non, les forces sont toujours égales et opposées."}
                ],
                explanation="$\\vec{F}_{A\\to B} = -\\vec{F}_{B\\to A}$, indépendamment des masses."
            ),
            FB(
                "Compléter le PFD",
                "Le PFD s'écrit : $\\sum {{blank_1}} = m \\times {{blank_2}}$. "
                "Si la somme des forces extérieures est nulle, l'objet est en "
                "{{blank_3}} (repos ou MRU).",
                {"blank_1": ["\\vec{F}", "F", "\\vec{F}_{ext}", "F_{ext}", "forces"],
                 "blank_2": ["\\vec{a}", "a"],
                 "blank_3": ["inertie", "mouvement rectiligne uniforme", "MRU"]},
                explanation="Le PFD relie la somme des forces extérieures à l'accélération ; "
                            "si la somme est nulle, on a inertie (1ère loi)."
            ),
            TF(
                "Vrai ou Faux ? Lois de Newton",
                [
                    {"statement": "La 1ère loi est un cas particulier de la 2ème.",
                     "is_true": True},
                    {"statement": "Les forces d'action et de réaction se compensent sur un même corps.",
                     "is_true": False, "statement_note": "Elles s'appliquent à deux corps différents."},
                    {"statement": "Le PFD n'est valable que dans un référentiel galiléen.",
                     "is_true": True},
                    {"statement": "Si $\\sum\\vec{F}=\\vec{0}$, l'objet est forcément au repos.",
                     "is_true": False, "statement_note": "Il peut aussi être en MRU."},
                    {"statement": "Le poids est une force d'attraction gravitationnelle.",
                     "is_true": True}
                ]
            )
        ]},

        # -----------------------------------------------------------------
        # Lesson 1.2 — Forces usuelles
        # -----------------------------------------------------------------
        {"order": 1, "title": "Forces usuelles",
         "slug": "forces-usuelles", "minutes": 30, "blocks": [
            T(
                "# Les forces usuelles en mécanique\n\n"
                "## 1. Poids\n\n"
                "$$\\vec{P} = m\\,\\vec{g}, \\quad |\\vec{P}| = mg, \\quad "
                "g \\approx 9{,}81\\;\\text{m/s}^2$$\n\n"
                "Direction : verticale, vers le bas (vers le centre de la Terre).\n\n"
                "## 2. Force de réaction normale\n\n"
                "Force exercée par un support sur l'objet, **perpendiculaire** au "
                "support :\n"
                "$$\\vec{N} \\perp \\text{support}$$\n\n"
                "## 3. Tension d'un fil\n\n"
                "Force exercée par un fil tendu, le long du fil, dirigée vers le "
                "point d'attache. Sur une poulie idéale (sans masse, sans frottement), "
                "la tension est la même des deux côtés.\n\n"
                "## 4. Force de frottement solide\n\n"
                "Deux composantes :\n"
                "- **statique** : $f_s \\leq \\mu_s\\, N$ (empêche le mouvement) ;\n"
                "- **cinétique** : $f_k = \\mu_k\\, N$ (s'oppose au mouvement, "
                "toujours en sens opposé à $\\vec{v}$).\n\n"
                "On a généralement $\\mu_s > \\mu_k$.\n\n"
                "## 5. Force de rappel d'un ressort\n\n"
                "**Loi de Hooke** :\n"
                "$$\\vec{F} = -k\\,(x - x_0)\\,\\vec{i}$$\n\n"
                "où $k$ est la constante de raideur (N/m), $x-x_0$ l'allongement.\n\n"
                "## 6. Poussée d'Archimède\n\n"
                "$$\\vec{\\Pi} = -\\rho\\, V\\, \\vec{g}$$\n\n"
                "dirigée vers le haut, de norme égale au poids du fluide déplacé.\n\n"
                "> 💡 **Astuce** : Pour un bilan de forces, liste d'abord les forces "
                "à distance (poids, attraction magnétique) puis les forces de contact "
                "(réaction, tension, frottement). N'oublie jamais qu'une force de "
                "contact ne peut exister que s'il y a contact !"
            ),
            S(
                "Bilan des forces sur un bloc sur plan horizontal",
                "import matplotlib.pyplot as plt\n"
                "import numpy as np\n"
                "from matplotlib.patches import FancyArrowPatch, Rectangle\n"
                "\n"
                "fig, ax = plt.subplots(figsize=(8, 5))\n"
                "ax.add_patch(Rectangle((0, 0), 8, 0.3, color='lightgray'))  # sol\n"
                "ax.add_patch(Rectangle((3, 0.3), 1.5, 1.2, color='steelblue'))  # bloc\n"
                "cx, cy = 3.75, 0.9\n"
                "# Poids (vers le bas)\n"
                "ax.add_patch(FancyArrowPatch((cx, cy), (cx, cy-1.5), arrowstyle='->', mutation_scale=20, color='red', lw=2.5))\n"
                "ax.text(cx+0.1, cy-1.2, r'$\\vec{P}=m\\vec{g}$', fontsize=13, color='red')\n"
                "# Normale (vers le haut)\n"
                "ax.add_patch(FancyArrowPatch((cx, cy), (cx, cy+1.5), arrowstyle='->', mutation_scale=20, color='green', lw=2.5))\n"
                "ax.text(cx+0.1, cy+1.2, r'$\\vec{N}$', fontsize=13, color='green')\n"
                "# Force appliquee (vers la droite)\n"
                "ax.add_patch(FancyArrowPatch((cx, cy), (cx+1.8, cy), arrowstyle='->', mutation_scale=20, color='blue', lw=2.5))\n"
                "ax.text(cx+1.0, cy+0.2, r'$\\vec{F}$', fontsize=13, color='blue')\n"
                "# Frottement (vers la gauche, oppose a v)\n"
                "ax.add_patch(FancyArrowPatch((cx, cy), (cx-1.2, cy), arrowstyle='->', mutation_scale=20, color='orange', lw=2.5))\n"
                "ax.text(cx-1.5, cy+0.2, r'$\\vec{f}$', fontsize=13, color='orange')\n"
                "ax.set_xlim(0, 8); ax.set_ylim(-1, 3)\n"
                "ax.set_aspect('equal'); ax.grid(True, alpha=0.3)\n"
                "ax.set_title('Bilan des forces sur un bloc', fontsize=12)\n"
                "ax.axis('off')\n"
                "plt.tight_layout(); plt.savefig('plot.png')\n"
                "print('Si v = cste : F = f et N = P')\n"
            ),
            APP(
                "Bloc tiré à vitesse constante",
                "Un bloc de masse $m=5$ kg est tiré sur une surface horizontale à "
                "vitesse constante par une force $F=15$ N. Le coefficient de "
                "frottement cinétique vaut $\\mu_k$. (a) Détermine $\\mu_k$. "
                "(b) Que vaut la force normale $N$ ? (c) Quelle force faudrait-il "
                "appliquer pour faire accélérer le bloc à $a=1$ m/s² ?",
                "On prend $g = 9{,}81$ m/s².\n\n"
                "**Bilan des forces** (vertical) : $N - mg = 0 \\Rightarrow N = mg = "
                "5 \\times 9{,}81 = 49{,}05$ N.\n\n"
                "**(a) Puisque $v$ est constante, $a=0$ donc $\\sum F_x = 0$ : "
                "$F - f = 0 \\Rightarrow f = F = 15$ N.\n"
                "Or $f = \\mu_k N$, donc :\n"
                "$$\\mu_k = \\frac{f}{N} = \\frac{15}{49{,}05} \\approx 0{,}306.$$\n\n"
                "**(b) $N = 49{,}05$ N** (cf. ci-dessus).\n\n"
                "**(c) Pour accélérer à $a=1$ m/s²** : PFD selon $x$\n"
                "$$F' - f = ma \\Rightarrow F' = ma + f = 5 \\times 1 + 15 = 20\\;\\text{N}.$$\n\n"
                "Il faut donc augmenter la force de 33% (de 15 à 20 N) pour obtenir "
                "une accélération de 1 m/s²."
            ),
            MCQ(
                "Force de frottement cinétique",
                "La force de frottement cinétique $f_k$ vaut :",
                [
                    {"text": "$\\mu_s N$", "correct": False, "feedback": "C'est le frottement statique (max)."},
                    {"text": "$\\mu_k N$", "correct": True, "feedback": "Exact ! $f_k = \\mu_k N$."},
                    {"text": "$\\mu_k mg$", "correct": False, "feedback": "Seulement si $N=mg$ (plan horizontal sans autre force verticale)."},
                    {"text": "$\\mu_k v$", "correct": False, "feedback": "Non, indépendant de $v$."}
                ],
                explanation="$f_k = \\mu_k N$, indépendant de la vitesse et de la surface apparente."
            ),
            MCQ(
                "Réaction normale",
                "Sur un plan horizontal, si le bloc ne subit que son poids et la "
                "réaction, alors :",
                [
                    {"text": "$N > mg$", "correct": False, "feedback": "Non, le bloc ne décolle pas."},
                    {"text": "$N = mg$", "correct": True, "feedback": "Exact ! PFD vertical : $N - mg = 0$."},
                    {"text": "$N < mg$", "correct": False, "feedback": "Non."},
                    {"text": "$N = 0$", "correct": False, "feedback": "Non, le support pousse le bloc."}
                ],
                explanation="Sans accélération verticale, $N - mg = 0$, donc $N = mg$."
            ),
            FB(
                "Loi de Hooke et forces",
                "La force de rappel d'un ressort vaut $\\vec{F} = -{{blank_1}}\\,(x-x_0)\\,\\vec{i}$. "
                "La force de frottement cinétique vaut $f_k = \\mu_k \\times {{blank_2}}$. "
                "La poussée d'Archimède vaut $\\Pi = \\rho \\times V \\times {{blank_3}}$.",
                {"blank_1": ["k"], "blank_2": ["N", "normale"], "blank_3": ["g", "g"]},
                explanation="Raideur $k$ pour Hooke, force normale $N$ pour le frottement, "
                            "gravité $g$ pour Archimède."
            ),
            TF(
                "Vrai ou Faux ? Forces usuelles",
                [
                    {"statement": "Le poids est toujours vertical vers le bas.",
                     "is_true": True},
                    {"statement": "La réaction normale est toujours verticale vers le haut.",
                     "is_true": False, "statement_note": "Elle est perpendiculaire au support (incliné par exemple)."},
                    {"statement": "$\\mu_s > \\mu_k$ en général.",
                     "is_true": True},
                    {"statement": "La tension est identique des deux côtés d'une poulie idéale.",
                     "is_true": True},
                    {"statement": "La poussée d'Archimède dépend de la profondeur.",
                     "is_true": False, "statement_note": "Elle ne dépend que du volume immergé."}
                ]
            )
        ]},

        # -----------------------------------------------------------------
        # Lesson 1.3 — Plan incliné et frottement
        # -----------------------------------------------------------------
        {"order": 2, "title": "Plan incliné et frottement",
         "slug": "plan-incline-frottement", "minutes": 35, "blocks": [
            T(
                "# Plan incliné et frottement\n\n"
                "## 1. Configuration\n\n"
                "Un bloc de masse $m$ descend un plan incliné d'angle $\\alpha$. "
                "On choisit le repère $(\\vec{T}, \\vec{N})$ tangent / normal au plan.\n\n"
                "## 2. Bilan des forces (projection)\n\n"
                "**Poids** : $\\vec{P} = m\\vec{g}$, à décomposer en :\n"
                "- tangentielle : $P_t = mg\\sin\\alpha$ (vers le bas du plan) ;\n"
                "- normale : $P_n = mg\\cos\\alpha$ (vers le support).\n\n"
                "**Réaction normale** : $N = mg\\cos\\alpha$ (pas d'accélération normale).\n\n"
                "**Frottement** : $f = \\mu N = \\mu\\, mg\\cos\\alpha$, dirigé vers le "
                "haut du plan (s'oppose au mouvement).\n\n"
                "## 3. Accélération\n\n"
                "PFD selon l'axe tangentiel :\n"
                "$$a = g(\\sin\\alpha - \\mu\\cos\\alpha)$$\n\n"
                "- Si $\\sin\\alpha > \\mu\\cos\\alpha$ : le bloc accélère vers le bas.\n"
                "- Si $\\sin\\alpha < \\mu\\cos\\alpha$ : le bloc reste immobile (frottement statique suffisant).\n\n"
                "## 4. Angle critique\n\n"
                "L'angle limite de glissement (bloc à la limite de bouger) :\n"
                "$$\\tan\\alpha_c = \\mu_s$$\n\n"
                "> 💡 **Astuce** : Pour un plan incliné sans frottement ($\\mu = 0$), "
                "$a = g\\sin\\alpha$. À $\\alpha=30°$, $a \\approx 4{,}9$ m/s² : la "
                "moitié de $g$."
            ),
            S(
                "Bilan des forces sur plan incliné",
                "import matplotlib.pyplot as plt\n"
                "import numpy as np\n"
                "from matplotlib.patches import FancyArrowPatch, Polygon\n"
                "\n"
                "alpha = np.radians(30)\n"
                "fig, ax = plt.subplots(figsize=(8, 6))\n"
                "# Plan incline\n"
                "ax.add_patch(Polygon([[0,0],[6,0],[6,6*np.tan(alpha)]], color='lightgray'))\n"
                "# Bloc\n"
                "cx, cy = 3, 3*np.tan(alpha)\n"
                "w, h = 0.8, 0.5\n"
                "ax.add_patch(Polygon([[cx-w/2,cy],[cx+w/2,cy],[cx+w/2,cy+h],[cx-w/2,cy+h]], color='steelblue'))\n"
                "# Centre du bloc\n"
                "px, py = cx, cy + h/2\n"
                "# Tangent (T) et normale (N)\n"
                "tx, ty = np.cos(alpha), np.sin(alpha)   # vers le bas du plan\n"
                "nx, ny = -np.sin(alpha), np.cos(alpha)  # vers le haut (hors plan)\n"
                "# Poids (vertical vers le bas)\n"
                "ax.add_patch(FancyArrowPatch((px,py), (px, py-1.5), arrowstyle='->', mutation_scale=20, color='red', lw=2.5))\n"
                "ax.text(px+0.1, py-1.2, r'$\\vec{P}$', fontsize=13, color='red')\n"
                "# Normale N (perpendiculaire au plan, sortant)\n"
                "ax.add_patch(FancyArrowPatch((px,py), (px+nx*1.2, py+ny*1.2), arrowstyle='->', mutation_scale=20, color='green', lw=2.5))\n"
                "ax.text(px+nx*1.3+0.1, py+ny*1.3, r'$\\vec{N}$', fontsize=13, color='green')\n"
                "# Frottement f (vers le haut du plan, oppose a v)\n"
                "ax.add_patch(FancyArrowPatch((px,py), (px-tx*1.0, py-ty*1.0), arrowstyle='->', mutation_scale=20, color='orange', lw=2.5))\n"
                "ax.text(px-tx*1.2-0.2, py-ty*1.2, r'$\\vec{f}$', fontsize=13, color='orange')\n"
                "ax.set_xlim(-0.5, 7); ax.set_ylim(-0.5, 5)\n"
                "ax.set_aspect('equal'); ax.grid(True, alpha=0.3)\n"
                "ax.set_title(rf'Plan incliné $\\alpha=30°$ : bilan des forces', fontsize=12)\n"
                "ax.axis('off')\n"
                "plt.tight_layout(); plt.savefig('plot.png')\n"
                "print('Projection : P_t = mg sin(a), P_n = mg cos(a)')\n"
            ),
            S(
                "Accélération vs angle d'inclinaison",
                "import matplotlib.pyplot as plt\n"
                "import numpy as np\n"
                "\n"
                "g = 9.81\n"
                "mu = 0.3   # coefficient de frottement\n"
                "alpha = np.linspace(0, 60, 200)\n"
                "rad = np.radians(alpha)\n"
                "a = g * (np.sin(rad) - mu*np.cos(rad))\n"
                "a = np.maximum(a, 0)  # si negatif, le bloc ne bouge pas\n"
                "alpha_c = np.degrees(np.arctan(mu))\n"
                "\n"
                "fig, ax = plt.subplots(figsize=(8, 5))\n"
                "ax.plot(alpha, a, 'b-', lw=2)\n"
                "ax.axvline(alpha_c, color='r', ls='--', label=r'$\\alpha_c = \\arctan(\\mu) \\approx %.1f°$' % alpha_c)\n"
                "ax.set_xlabel(r'Angle $\\alpha$ [deg]')\n"
                "ax.set_ylabel(r'Accélération $a$ [m/s$^2$]')\n"
                "ax.set_title(r'$a = g(\\sin\\alpha - \\mu\\cos\\alpha)$, $\\mu=0{,}3$')\n"
                "ax.legend(); ax.grid(True, alpha=0.3)\n"
                "plt.tight_layout(); plt.savefig('plot.png')\n"
                "print(f'Angle critique : {alpha_c:.2f} deg')\n"
                "print(f'A 45 deg : a = {g*(np.sin(np.radians(45))-mu*np.cos(np.radians(45))):.2f} m/s^2')\n"
            ),
            APP(
                "Bloc qui descend un plan incliné",
                "Un bloc de masse $m=2$ kg descend un plan incliné à $\\alpha=25°$ "
                "avec un coefficient de frottement cinétique $\\mu_k = 0{,}15$. "
                "Partant du repos, quelle distance parcourt-il en $t=3$ s ? "
                "Quelle est sa vitesse finale ?",
                "PFD le long du plan (orienté vers le bas) :\n"
                "$$a = g(\\sin\\alpha - \\mu_k\\cos\\alpha).$$\n\n"
                "Avec $\\sin 25° \\approx 0{,}423$ et $\\cos 25° \\approx 0{,}906$ :\n"
                "$$a = 9{,}81 \\times (0{,}423 - 0{,}15 \\times 0{,}906) = 9{,}81 \\times "
                "(0{,}423 - 0{,}136) = 9{,}81 \\times 0{,}287 \\approx 2{,}81\\;\\text{m/s}^2.$$\n\n"
                "Le bloc accélère bien vers le bas ($a > 0$).\n\n"
                "**Distance parcourue** (MRUA partant du repos) :\n"
                "$$x = \\tfrac12 a t^2 = \\tfrac12 \\times 2{,}81 \\times 9 \\approx 12{,}6\\;\\text{m}.$$\n\n"
                "**Vitesse finale** :\n"
                "$$v = a t = 2{,}81 \\times 3 \\approx 8{,}44\\;\\text{m/s} \\approx "
                "30{,}4\\;\\text{km/h}.$$\n\n"
                "Vérification : $v^2 = 2ax \\Rightarrow v = \\sqrt{2\\times 2{,}81\\times 12{,}6} "
                "\\approx 8{,}42$ m/s ✓."
            ),
            MCQ(
                "Accélération sans frottement",
                "Sur un plan incliné sans frottement à $\\alpha=30°$, l'accélération du bloc vaut :",
                [
                    {"text": "$g$", "correct": False, "feedback": "Trop, ce serait la chute libre."},
                    {"text": "$g/2 \\approx 4{,}9$ m/s²", "correct": True, "feedback": "Exact ! $a = g\\sin 30° = g/2$."},
                    {"text": "$g\\sin 60°$", "correct": False, "feedback": "Confusion d'angle."},
                    {"text": "0 (pas de mouvement)", "correct": False, "feedback": "Sans frottement, le bloc glisse."}
                ],
                explanation="$a = g\\sin\\alpha = g\\sin 30° = g/2 \\approx 4{,}9$ m/s²."
            ),
            MCQ(
                "Angle critique",
                "Si $\\mu_s = 0{,}4$, l'angle critique $\\alpha_c$ au-delà duquel le bloc "
                "commence à glisser est :",
                [
                    {"text": "$\\arctan(0{,}4) \\approx 21{,}8°$", "correct": True, "feedback": "Exact ! $\\tan\\alpha_c = \\mu_s$."},
                    {"text": "$\\arcsin(0{,}4) \\approx 23{,}6°$", "correct": False, "feedback": "C'est tangente, pas sinus."},
                    {"text": "$0{,}4$ radians $\\approx 22{,}9°$", "correct": False, "feedback": "Mauvaise fonction."},
                    {"text": "45°", "correct": False, "feedback": "C'est l'angle de portée max d'un projectile."}
                ],
                explanation="$\\tan\\alpha_c = \\mu_s \\Rightarrow \\alpha_c = \\arctan(\\mu_s) \\approx 21{,}8°$."
            ),
            FB(
                "Composantes du poids sur plan incliné",
                "Sur un plan incliné d'angle $\\alpha$, la composante tangentielle du "
                "poids vaut $mg\\,{{blank_1}}\\,\\alpha$ et la composante normale vaut "
                "$mg\\,{{blank_2}}\\,\\alpha$. L'angle critique vérifie "
                "$\\tan\\alpha_c = {{blank_3}}$.",
                {"blank_1": ["\\sin", "sin"], "blank_2": ["\\cos", "cos"], "blank_3": ["\\mu_s", "mu_s", "mu"]},
                explanation="Tangentielle = $mg\\sin\\alpha$, normale = $mg\\cos\\alpha$, "
                            "et l'angle critique vérifie $\\tan\\alpha_c = \\mu_s$."
            ),
            TF(
                "Vrai ou Faux ? Plan incliné",
                [
                    {"statement": "Sans frottement, l'accélération vaut $g\\sin\\alpha$.",
                     "is_true": True},
                    {"statement": "La force normale vaut $mg$ (comme sur un plan horizontal).",
                     "is_true": False, "statement_note": "Elle vaut $mg\\cos\\alpha$."},
                    {"statement": "Si $\\mu$ augmente, l'angle critique augmente.",
                     "is_true": True},
                    {"statement": "Pour $\\alpha = 0$, le bloc ne peut jamais bouger.",
                     "is_true": False, "statement_note": "Une force extérieure peut le mettre en mouvement."},
                    {"statement": "Le frottement s'oppose toujours au mouvement (ou à sa tendance).",
                     "is_true": True}
                ]
            )
        ]},

        # -----------------------------------------------------------------
        # Lesson 1.4 — Applications : virages, loop
        # -----------------------------------------------------------------
        {"order": 3, "title": "Applications : virages, loop",
         "slug": "applications-virages-loop", "minutes": 35, "blocks": [
            T(
                "# Applications : virages et loopings\n\n"
                "## 1. Virage sur route horizontale\n\n"
                "Une voiture de masse $m$ prend un virage de rayon $R$ à la vitesse "
                "constante $v$. Le frottement des pneus fournit la force centripète :\n"
                "$$f = m\\,\\frac{v^2}{R}$$\n\n"
                "Vitesse maximale (avant dérapage) :\n"
                "$$v_{max} = \\sqrt{\\mu_s\\, g\\, R}$$\n\n"
                "## 2. Virage en relèvement (banking)\n\n"
                "Pour éviter toute force de frottement, on incline la route d'un "
                "angle $\\theta$ tel que :\n"
                "$$\\tan\\theta = \\frac{v^2}{gR}$$\n\n"
                "C'est le **virage idéalement relevé**. La réaction normale seule "
                "fournit alors la force centripète.\n\n"
                "## 3. Looping vertical\n\n"
                "Une voiture (ou un wagon) fait un looping vertical de rayon $R$. "
                "Au sommet du looping (position haute), PFD selon l'axe vertical "
                "(orienté vers le bas, vers le centre) :\n"
                "$$mg + N = m\\frac{v^2}{R}$$\n\n"
                "où $N$ est la réaction du rail. La **vitesse minimale** pour "
                "ne pas tomber correspond à $N = 0$ :\n"
                "$$v_{min} = \\sqrt{gR}$$\n\n"
                "C'est la **condition de contact** au sommet du looping.\n\n"
                "> 💡 **Astuce** : Pour un looping de $R=5$ m, $v_{min} = \\sqrt{9{,}81 \\times 5} "
                "\\approx 7$ m/s $\\approx 25$ km/h. Insuffisant en pratique car il faut "
                "aussi compenser les frottements !"
            ),
            S(
                "Vitesse max dans un virage vs rayon",
                "import matplotlib.pyplot as plt\n"
                "import numpy as np\n"
                "\n"
                "g = 9.81\n"
                "R = np.linspace(10, 200, 200)\n"
                "for mu, col in [(0.3, 'r'), (0.5, 'b'), (0.8, 'g')]:\n"
                "    vmax = np.sqrt(mu*g*R) * 3.6  # km/h\n"
                "    plt.plot(R, vmax, lw=2, color=col, label=r'$\\mu_s=%.1f$' % mu)\n"
                "plt.xlabel(r'Rayon du virage $R$ [m]')\n"
                "plt.ylabel(r'Vitesse max $v_{max}$ [km/h]')\n"
                "plt.title(r'Vitesse max dans un virage : $v_{max}=\\sqrt{\\mu_s g R}$')\n"
                "plt.legend(); plt.grid(True, alpha=0.3)\n"
                "plt.tight_layout(); plt.savefig('plot.png')\n"
                "print(f'A R=50 m, mu=0.5 : vmax = {np.sqrt(0.5*9.81*50)*3.6:.1f} km/h')\n"
            ),
            S(
                "Looping vertical : forces au sommet",
                "import matplotlib.pyplot as plt\n"
                "import numpy as np\n"
                "from matplotlib.patches import FancyArrowPatch, Circle\n"
                "\n"
                "R = 1.0\n"
                "fig, ax = plt.subplots(figsize=(6, 7))\n"
                "theta = np.linspace(0, 2*np.pi, 200)\n"
                "ax.plot(R*np.cos(theta), R*np.sin(theta), 'b-', lw=2)\n"
                "# Sommet\n"
                "px, py = 0, R\n"
                "ax.add_patch(Circle((px, py), 0.03, color='k'))\n"
                "# Poids (vers le bas)\n"
                "ax.add_patch(FancyArrowPatch((px, py), (px, py-0.4), arrowstyle='->', mutation_scale=20, color='red', lw=2.5))\n"
                "ax.text(0.05, py-0.3, r'$\\vec{P}=m\\vec{g}$', fontsize=12, color='red')\n"
                "# Normale N (vers le centre, donc vers le bas au sommet)\n"
                "ax.add_patch(FancyArrowPatch((px, py), (px, py-0.25), arrowstyle='->', mutation_scale=18, color='green', lw=2.5))\n"
                "ax.text(-0.35, py-0.2, r'$\\vec{N}$', fontsize=12, color='green')\n"
                "# Vitesse (tangente, vers la droite au sommet)\n"
                "ax.add_patch(FancyArrowPatch((px, py), (px+0.5, py), arrowstyle='->', mutation_scale=20, color='blue', lw=2.5))\n"
                "ax.text(0.25, py+0.05, r'$\\vec{v}$', fontsize=12, color='blue')\n"
                "ax.set_xlim(-1.5, 1.5); ax.set_ylim(-1.3, 1.3)\n"
                "ax.set_aspect('equal'); ax.grid(True, alpha=0.3)\n"
                "ax.set_title(r'Looping au sommet : $mg+N = m v^2/R$', fontsize=12)\n"
                "plt.tight_layout(); plt.savefig('plot.png')\n"
                "print(f'Vitesse min (N=0) : v_min = sqrt(gR) = {np.sqrt(9.81*R):.2f} m/s')\n"
            ),
            APP(
                "Virage relevé à 130 km/h",
                "Sur une autoroute, on souhaite qu'un virage de rayon $R=400$ m puisse "
                "être pris à $v=130$ km/h sans aucune force de frottement latéral, "
                "grâce à un relevement (banking) de la route. (a) Calcule l'angle "
                "$\\theta$ de relèvement idéal. (b) Si la route est plate ($\\theta=0$) "
                "et $\\mu_s=0{,}5$, la voiture peut-elle prendre ce virage à 130 km/h ?",
                "On a $v = 130/3{,}6 \\approx 36{,}1$ m/s, $R=400$ m, $g=9{,}81$ m/s².\n\n"
                "**(a) Angle idéal** :\n"
                "$$\\tan\\theta = \\frac{v^2}{gR} = \\frac{36{,}1^2}{9{,}81 \\times 400} "
                "= \\frac{1303}{3924} \\approx 0{,}332$$\n"
                "$$\\theta = \\arctan(0{,}332) \\approx 18{,}4°.$$\n\n"
                "C'est un angle important — en pratique, les routes sont relevées "
                "à 4–8° seulement, le reste étant assuré par les pneus.\n\n"
                "**(b) Route plate, $\\mu_s = 0{,}5$** :\n"
                "$$v_{max} = \\sqrt{\\mu_s g R} = \\sqrt{0{,}5 \\times 9{,}81 \\times 400} "
                "\\approx 44{,}3\\;\\text{m/s} \\approx 159\\;\\text{km/h}.$$\n\n"
                "Puisque $130 < 159$ km/h, la voiture peut prendre ce virage sur "
                "route plate avec un coefficient de frottement de 0,5. Mais sur "
                "route mouillée ($\\mu_s \\approx 0{,}25$), $v_{max}$ tombe à 113 km/h "
                "et le virage devient dangereux à 130 km/h."
            ),
            MCQ(
                "Vitesse min au sommet d'un looping",
                "Pour un looping de rayon $R=5$ m, la vitesse minimale au sommet pour "
                "ne pas perdre le contact vaut environ :",
                [
                    {"text": "$\\sqrt{gR} \\approx 7$ m/s", "correct": True, "feedback": "Exact ! Condition $N=0$."},
                    {"text": "$\\sqrt{2gR} \\approx 10$ m/s", "correct": False, "feedback": "Trop élevé."},
                    {"text": "$gR \\approx 49$ m/s", "correct": False, "feedback": "Tu as oublié la racine."},
                    {"text": "0 m/s", "correct": False, "feedback": "Non, la voiture tomberait."}
                ],
                explanation="$v_{min} = \\sqrt{gR} = \\sqrt{9{,}81\\times 5} \\approx 7$ m/s."
            ),
            MCQ(
                "Virage relevé",
                "Pour un virage idéalement relevé d'angle $\\theta$, $R$ et $v$, "
                "quelle relation est vérifiée ?",
                [
                    {"text": "$\\sin\\theta = v^2/(gR)$", "correct": False, "feedback": "C'est tangente, pas sinus."},
                    {"text": "$\\tan\\theta = v^2/(gR)$", "correct": True, "feedback": "Exact !"},
                    {"text": "$\\tan\\theta = gR/v^2$", "correct": False, "feedback": "C'est l'inverse."},
                    {"text": "$\\cos\\theta = v^2/(gR)$", "correct": False, "feedback": "Non, c'est tangente."}
                ],
                explanation="PFD vertical : $N\\cos\\theta = mg$ ; radial : $N\\sin\\theta = mv^2/R$, "
                            "donc $\\tan\\theta = v^2/(gR)$."
            ),
            FB(
                "Formules virages et loopings",
                "Virage à plat : $v_{max} = \\sqrt{\\mu_s \\times g \\times {{blank_1}}}$. "
                "Virage idéalement relevé : $\\tan\\theta = \\dfrac{v^2}{g \\times {{blank_2}}}$. "
                "Au sommet du looping, $v_{min} = \\sqrt{{{blank_3}}}$ (si $R$ est le rayon).",
                {"blank_1": ["R"], "blank_2": ["R"], "blank_3": ["gR", "g*R", "g\\,R"]},
                explanation="Les trois formules clés des applications circulaires."
            ),
            TF(
                "Vrai ou Faux ? Virages et loopings",
                [
                    {"statement": "Dans un virage, l'accélération est centripète.",
                     "is_true": True},
                    {"statement": "Plus le rayon du virage est grand, plus la vitesse max est élevée.",
                     "is_true": True},
                    {"statement": "Au sommet d'un looping, le poids et la normale sont dirigés vers le bas.",
                     "is_true": True},
                    {"statement": "Si $v < \\sqrt{gR}$ au sommet du looping, la voiture reste collée au rail.",
                     "is_true": False, "statement_note": "Elle perd le contact (N=0 imposé)."},
                    {"statement": "Un virage idéalement relevé ne nécessite aucun frottement latéral.",
                     "is_true": True}
                ]
            )
        ]},
    ]},


    # =====================================================================
    # MODULE 2 — TRAVAIL ET ÉNERGIE
    # =====================================================================
    {"order": 2, "title": "Travail et énergie",
     "description": "Travail d'une force, énergie cinétique, énergie potentielle, "
                    "énergie mécanique, conservation, oscillations.",
     "lessons": [

        # -----------------------------------------------------------------
        # Lesson 2.1 — Travail d'une force
        # -----------------------------------------------------------------
        {"order": 0, "title": "Travail d'une force", "slug": "travail-force",
         "minutes": 30, "blocks": [
            T(
                "# Travail d'une force\n\n"
                "## 1. Définition\n\n"
                "Le **travail** d'une force $\\vec{F}$ constante le long d'un "
                "déplacement $\\vec{AB}$ est :\n"
                "$$W_{AB}(\\vec{F}) = \\vec{F} \\cdot \\vec{AB} = F \\cdot AB \\cdot "
                "\\cos\\alpha$$\n\n"
                "où $\\alpha$ est l'angle entre $\\vec{F}$ et $\\vec{AB}$. Unité : "
                "le **joule** (J) = N·m.\n\n"
                "## 2. Travail moteur / résistant\n\n"
                "- $0 \\leq \\alpha < 90°$ : $W > 0$ (**moteur**) ;\n"
                "- $\\alpha = 90°$ : $W = 0$ (**nul**, par exemple la force normale) ;\n"
                "- $90° < \\alpha \\leq 180°$ : $W < 0$ (**résistant**, par exemple "
                "les frottements).\n\n"
                "## 3. Travail du poids\n\n"
                "Le poids est une force **conservative**. Son travail ne dépend que "
                "des altitudes initiale et finale :\n"
                "$$W_{AB}(\\vec{P}) = mg(z_A - z_B)$$\n\n"
                "Indépendant du chemin suivi !\n\n"
                "## 4. Travail d'une force de frottement\n\n"
                "Les frottements sont des forces **non conservatives** (dissipatives). "
                "Leur travail dépend du chemin et est toujours **négatif** :\n"
                "$$W(\\vec{f}) = -f \\cdot L < 0$$\n\n"
                "où $L$ est la longueur du trajet.\n\n"
                "## 5. Puissance\n\n"
                "$$P = \\frac{W}{\\Delta t} = \\vec{F} \\cdot \\vec{v}$$\n\n"
                "Unité : le **watt** (W) = J/s.\n\n"
                "> 💡 **Astuce** : Reconnaître une force conservative en se demandant : "
                "« le travail dépend-il du chemin ? ». Si non, c'est conservative "
                "(poids, force de rappel, force électrique). Si oui, c'est "
                "non conservative (frottements, forces magnétiques sur particules "
                "chargées…)."
            ),
            S(
                "Travail du poids selon 3 chemins",
                "import matplotlib.pyplot as plt\n"
                "import numpy as np\n"
                "from matplotlib.patches import FancyArrowPatch\n"
                "\n"
                "fig, ax = plt.subplots(figsize=(8, 6))\n"
                "# 3 chemins de A(0,0) a B(2,-3)\n"
                "# Chemin 1 : direct\n"
                "ax.plot([0, 2], [0, -3], 'r-', lw=2, label='Direct')\n"
                "# Chemin 2 : horizontal puis vertical\n"
                "ax.plot([0, 2, 2], [0, 0, -3], 'b--', lw=2, label='Horiz. puis vert.')\n"
                "# Chemin 3 : courbe\n"
                "x = np.linspace(0, 2, 50)\n"
                "y = -3*np.sin(x*np.pi/4)\n"
                "ax.plot(x, y, 'g-.', lw=2, label='Sinusoïde')\n"
                "ax.plot(0, 0, 'ko', ms=8); ax.text(0.1, 0.2, 'A', fontsize=14)\n"
                "ax.plot(2, -3, 'ko', ms=8); ax.text(2.1, -3, 'B', fontsize=14)\n"
                "ax.set_xlim(-0.5, 3); ax.set_ylim(-3.5, 1)\n"
                "ax.set_aspect('equal'); ax.grid(True, alpha=0.3)\n"
                "ax.set_title(r'Travail du poids : $W=mg(z_A-z_B)$, même valeur pour tous les chemins', fontsize=11)\n"
                "ax.legend()\n"
                "plt.tight_layout(); plt.savefig('plot.png')\n"
                "print('Tous les chemins donnent W(P) = mg*(z_A - z_B) = mg*3')\n"
            ),
            APP(
                "Cycliste en descente",
                "Un cycliste de masse totale $m=80$ kg (vélo inclus) descend une "
                "pente de $h=30$ m de dénivelé. Il arrive en bas avec une vitesse "
                "$v_f=15$ m/s. (a) Calcule le travail du poids. (b) Calcule la "
                "variation d'énergie cinétique. (c) En déduire le travail des "
                "forces de frottement (air + route).",
                "On prend $g = 9{,}81$ m/s².\n\n"
                "**(a) Travail du poids** :\n"
                "$$W(\\vec{P}) = mg(z_A - z_B) = 80 \\times 9{,}81 \\times 30 \\approx "
                "23 544\\;\\text{J} \\approx 23{,}5\\;\\text{kJ}.$$\n\n"
                "**(b) Variation d'énergie cinétique** (en supposant $v_0=0$ en haut) :\n"
                "$$\\Delta E_c = \\tfrac12 m v_f^2 - 0 = \\tfrac12 \\times 80 \\times 15^2 "
                "= 9 000\\;\\text{J}.$$\n\n"
                "**(c) Bilan énergétique** (théorème de l'énergie cinétique) :\n"
                "$$\\Delta E_c = W(\\vec{P}) + W(\\vec{f})$$\n"
                "$$W(\\vec{f}) = \\Delta E_c - W(\\vec{P}) = 9000 - 23544 \\approx "
                "-14 544\\;\\text{J}.$$\n\n"
                "Les forces de frottement ont dissipé environ **14,5 kJ** d'énergie "
                "(62% du travail du poids). Cette énergie part en chaleur dans les "
                "pneus et en échauffement de l'air."
            ),
            MCQ(
                "Travail et angle",
                "Le travail d'une force $F$ sur un déplacement $AB$ vaut $W = F\\cdot AB\\cos\\alpha$. "
                "Pour $\\alpha=180°$ (force opposée au déplacement) :",
                [
                    {"text": "$W = F\\cdot AB$ (moteur max)", "correct": False, "feedback": "Non."},
                    {"text": "$W = 0$", "correct": False, "feedback": "C'est pour $\\alpha = 90°$."},
                    {"text": "$W = -F\\cdot AB$ (résistant max)", "correct": True, "feedback": "Exact ! $\\cos 180° = -1$."},
                    {"text": "Indéfini", "correct": False, "feedback": "Non, $\\cos 180°$ est bien défini."}
                ],
                explanation="$\\cos 180° = -1$, donc $W = -F\\cdot AB$."
            ),
            MCQ(
                "Force conservative",
                "Laquelle de ces forces est conservative ?",
                [
                    {"text": "Force de frottement cinétique", "correct": False, "feedback": "Non, son travail dépend du chemin."},
                    {"text": "Force de frottement visqueux $-k\\vec{v}$", "correct": False, "feedback": "Non, dissipative."},
                    {"text": "Poids", "correct": True, "feedback": "Exact ! $W = mg(z_A-z_B)$ indépendant du chemin."},
                    {"text": "Poussée d'Archimède", "correct": False, "feedback": "Elle aussi conservative en général, mais le poids est la réponse canonique."}
                ],
                explanation="Le poids est l'archétype de la force conservative."
            ),
            FB(
                "Compléter les formules du travail",
                "Travail d'une force constante : $W = \\vec{F} \\cdot {{blank_1}}$. "
                "Travail du poids : $W(\\vec{P}) = mg\\,{{blank_2}}$. "
                "Puissance moyenne : $P = W / {{blank_3}}$.",
                {"blank_1": ["\\vec{AB}", "AB"], "blank_2": ["(z_A - z_B)", "z_A - z_B", "(z_A-z_B)"],
                 "blank_3": ["\\Delta t", "Dt", "t"]},
                explanation="Produit scalaire avec le déplacement ; différence d'altitude ; "
                            "puissance = travail sur temps."
            ),
            TF(
                "Vrai ou Faux ? Travail",
                [
                    {"statement": "Le travail d'une force peut être négatif.",
                     "is_true": True},
                    {"statement": "Le travail du poids dépend du chemin suivi.",
                     "is_true": False, "statement_note": "Il ne dépend que des altitudes."},
                    {"statement": "1 J = 1 N·m.",
                     "is_true": True},
                    {"statement": "La force normale fait un travail non nul en général.",
                     "is_true": False, "statement_note": "Perpendiculaire au déplacement, $W=0$."},
                    {"statement": "Le travail des forces de frottement est toujours négatif.",
                     "is_true": True}
                ]
            )
        ]},

        # -----------------------------------------------------------------
        # Lesson 2.2 — Énergie cinétique et TEC
        # -----------------------------------------------------------------
        {"order": 1, "title": "Énergie cinétique et théorème de l'énergie cinétique",
         "slug": "energie-cinetique-tec", "minutes": 30, "blocks": [
            T(
                "# Énergie cinétique et TEC\n\n"
                "## 1. Définition\n\n"
                "L'**énergie cinétique** d'un point matériel de masse $m$ animé d'une "
                "vitesse $v$ est :\n"
                "$$E_c = \\tfrac12 m v^2$$\n\n"
                "C'est une grandeur **scalaire** et **positive**, en joules (J).\n\n"
                "## 2. Théorème de l'Énergie Cinétique (TEC)\n\n"
                "Dans un référentiel galiléen, la **variation d'énergie cinétique** "
                "d'un système entre deux instants est égale à la **somme des travaux "
                "des forces extérieures** appliquées :\n"
                "$$\\Delta E_c = \\sum W(\\vec{F}_{ext})$$\n\n"
                "## 3. Cas particulier : forces conservatives seulement\n\n"
                "Si toutes les forces sont conservatives, l'énergie **mécanique** "
                "se conserve (voir leçon suivante).\n\n"
                "## 4. Application : freinage\n\n"
                "Une voiture qui freine avec une force $F$ constante sur une distance "
                "$d$ : $\\Delta E_c = -F d$. Donc $\\tfrac12 m v_0^2 = F d$ :\n"
                "$$d = \\frac{m v_0^2}{2F}$$\n\n"
                "## 5. Énergie cinétique et mouvement de rotation\n\n"
                "Pour un solide en rotation autour d'un axe fixe :\n"
                "$$E_c = \\tfrac12 J\\, \\omega^2$$\n\n"
                "où $J$ est le **moment d'inertie** et $\\omega$ la vitesse angulaire.\n\n"
                "> 💡 **Astuce** : Le TEC est souvent **plus rapide** que le PFD pour "
                "trouver une vitesse en fonction d'une position, car il élimine le "
                "temps et projette directement sur la trajectoire."
            ),
            S(
                "Énergie cinétique d'une voiture vs vitesse",
                "import matplotlib.pyplot as plt\n"
                "import numpy as np\n"
                "\n"
                "v = np.linspace(0, 50, 200)   # m/s (= 0 a 180 km/h)\n"
                "m = 1000.0  # 1 tonne\n"
                "Ec = 0.5 * m * v**2 / 1000    # en kJ\n"
                "\n"
                "fig, ax = plt.subplots(figsize=(8, 5))\n"
                "ax.plot(v*3.6, Ec, 'b-', lw=2)\n"
                "ax.set_xlabel(r'$v$ [km/h]')\n"
                "ax.set_ylabel(r'$E_c$ [kJ]')\n"
                "ax.set_title(r'Énergie cinétique d\\'une voiture de 1000 kg : $E_c=\\frac12 m v^2$')\n"
                "ax.grid(True, alpha=0.3)\n"
                "plt.tight_layout(); plt.savefig('plot.png')\n"
                "print(f'A 50 km/h : Ec = {0.5*1000*(50/3.6)**2/1000:.1f} kJ')\n"
                "print(f'A 100 km/h : Ec = {0.5*1000*(100/3.6)**2/1000:.1f} kJ')\n"
                "print(f'A 130 km/h : Ec = {0.5*1000*(130/3.6)**2/1000:.1f} kJ')\n"
                "print('Doubler la vitesse -> x4 sur Ec !')\n"
            ),
            APP(
                "Voiture qui freine",
                "Une voiture de masse $m=1200$ kg roule à $v_0=90$ km/h. Le conducteur "
                "freine avec une force totale $F=6000$ N. (a) Calcule l'énergie "
                "cinétique initiale. (b) Quelle distance de freinage est nécessaire "
                "pour s'arrêter ? (c) Même question si la vitesse est $v_0=130$ km/h.",
                "On a $v_0 = 90/3{,}6 = 25$ m/s.\n\n"
                "**(a) Énergie cinétique initiale** :\n"
                "$$E_c = \\tfrac12 m v_0^2 = \\tfrac12 \\times 1200 \\times 25^2 = "
                "375 000\\;\\text{J} = 375\\;\\text{kJ}.$$\n\n"
                "**(b) Distance de freinage** (TEC, $\\Delta E_c = -F d$) :\n"
                "$$d = \\frac{E_c}{F} = \\frac{375 000}{6000} \\approx 62{,}5\\;\\text{m}.$$\n\n"
                "**(c) À $v_0=130$ km/h $= 36{,}1$ m/s** :\n"
                "$$E_c' = \\tfrac12 \\times 1200 \\times 36{,}1^2 \\approx 782\\;\\text{kJ}$$\n"
                "$$d' = \\frac{782 000}{6000} \\approx 130{,}4\\;\\text{m}.$$\n\n"
                "On retrouve la **loi en $v_0^2$** : la vitesse a augmenté de 44% "
                "($130/90 \\approx 1{,}44$), mais la distance de freinage a augmenté "
                "de **108%** ($130/62 \\approx 2{,}08$). Ce n'est pas exactement le "
                "double car le rapport de vitesse n'est pas exactement 2."
            ),
            MCQ(
                "Énergie cinétique et vitesse",
                "Si la vitesse est multipliée par 3, l'énergie cinétique est multipliée par :",
                [
                    {"text": "3", "correct": False, "feedback": "Non, $E_c \\propto v^2$."},
                    {"text": "6", "correct": False, "feedback": "Trop peu."},
                    {"text": "9", "correct": True, "feedback": "Exact ! $E_c \\propto v^2$."},
                    {"text": "27", "correct": False, "feedback": "Trop, ce serait $v^3$."}
                ],
                explanation="$E_c = \\tfrac12 m v^2$, donc $\\times 3$ sur $v$ $\\Rightarrow$ $\\times 9$ sur $E_c$."
            ),
            MCQ(
                "Théorème de l'énergie cinétique",
                "Le TEC dit que $\\Delta E_c$ est égale à :",
                [
                    {"text": "La somme des forces extérieures", "correct": False, "feedback": "C'est le PFD."},
                    {"text": "La somme des travaux des forces extérieures", "correct": True, "feedback": "Exact !"},
                    {"text": "La somme des énergies potentielles", "correct": False, "feedback": "Non."},
                    {"text": "L'énergie mécanique", "correct": False, "feedback": "L'énergie mécanique est $E_c + E_p$."}
                ],
                explanation="$\\Delta E_c = \\sum W(\\vec{F}_{ext})$."
            ),
            FB(
                "Formules de l'énergie cinétique",
                "Énergie cinétique de translation : $E_c = \\dfrac12 m \\times {{blank_1}}$. "
                "Énergie cinétique de rotation : $E_c = \\dfrac12 J \\times {{blank_2}}$. "
                "Théorème : $\\Delta E_c = \\sum {{blank_3}}(\\vec{F}_{ext})$.",
                {"blank_1": ["v^2", "v**2"], "blank_2": ["\\omega^2", "omega^2", "w^2"],
                 "blank_3": ["W", "travaux", "W"]},
                explanation="Translation avec $v^2$, rotation avec $\\omega^2$, et la somme des travaux."
            ),
            TF(
                "Vrai ou Faux ? Énergie cinétique",
                [
                    {"statement": "L'énergie cinétique est toujours positive.",
                     "is_true": True},
                    {"statement": "Le TEC est valable même avec des forces non conservatives.",
                     "is_true": True},
                    {"statement": "Pour un freinage, $\\Delta E_c > 0$.",
                     "is_true": False, "statement_note": "$\\Delta E_c < 0$ (la voiture ralentit)."},
                    {"statement": "Pour un solide en rotation, $E_c = \\tfrac12 J\\omega^2$.",
                     "is_true": True},
                    {"statement": "$E_c$ s'exprime en newton (N).",
                     "is_true": False, "statement_note": "En joule (J)."}
                ]
            )
        ]},

        # -----------------------------------------------------------------
        # Lesson 2.3 — Énergie potentielle et mécanique
        # -----------------------------------------------------------------
        {"order": 2, "title": "Énergie potentielle et énergie mécanique",
         "slug": "energie-potentielle-mecanique", "minutes": 35, "blocks": [
            T(
                "# Énergie potentielle et énergie mécanique\n\n"
                "## 1. Énergie potentielle\n\n"
                "L'**énergie potentielle** $E_p$ est associée à une force "
                "conservative. La force dérive d'un potentiel :\n"
                "$$\\vec{F} = -\\vec{\\nabla} E_p$$\n\n"
                "### Énergie potentielle de pesanteur\n"
                "$$E_p = mgz + \\text{cste}$$\n\n"
                "### Énergie potentielle élastique (ressort)\n"
                "$$E_p = \\tfrac12 k (x-x_0)^2$$\n\n"
                "## 2. Énergie mécanique\n\n"
                "$$E_m = E_c + E_p$$\n\n"
                "## 3. Conservation de l'énergie mécanique\n\n"
                "Si toutes les forces sont conservatives (pas de frottement), "
                "l'énergie mécanique se conserve :\n"
                "$$E_m = \\text{constante} \\;\\Leftrightarrow\\; \\Delta E_m = 0$$\n\n"
                "## 4. Cas avec frottement\n\n"
                "S'il y a des frottements, l'énergie mécanique **décroît** :\n"
                "$$\\Delta E_m = W(\\vec{f}_{nc}) \\leq 0$$\n\n"
                "où $\\vec{f}_{nc}$ sont les forces **non conservatives**.\n\n"
                "## 5. Diagramme d'énergie — puits de potentiel\n\n"
                "Pour un oscillateur harmonique ($E_p = \\tfrac12 k x^2$), on a un "
                "**puits de potentiel parabolique**. Les points de retournement "
                "vérifient $E_p = E_m$ (donc $E_c=0$).\n\n"
                "> 💡 **Astuce** : L'énergie potentielle est **définie à une constante "
                "près** : seule sa variation a un sens physique. On choisit souvent "
                "$E_p = 0$ au niveau du sol, ou à l'infini (gravitation)."
            ),
            S(
                "Diagramme d'énergie — oscillateur harmonique",
                "import matplotlib.pyplot as plt\n"
                "import numpy as np\n"
                "\n"
                "k = 1.0\n"
                "m = 1.0\n"
                "A = 2.0   # amplitude\n"
                "x = np.linspace(-3, 3, 300)\n"
                "Ep = 0.5 * k * x**2\n"
                "Em = 0.5 * k * A**2   # energie mecanique totale\n"
                "Ec = Em - Ep\n"
                "\n"
                "fig, ax = plt.subplots(figsize=(9, 6))\n"
                "ax.plot(x, Ep, 'r-', lw=2, label=r'$E_p(x)=\\frac12 k x^2$')\n"
                "ax.axhline(Em, color='b', ls='--', lw=1.5, label=r'$E_m$ = cste')\n"
                "ax.fill_between(x, 0, Ep, where=(np.abs(x)<=A), color='red', alpha=0.2)\n"
                "ax.fill_between(x, Ep, Em, where=(np.abs(x)<=A), color='blue', alpha=0.2, label=r'$E_c$ (zone bleue)')\n"
                "ax.axvline(A, color='g', ls=':', label=r'Points de retournement $\\pm A$')\n"
                "ax.axvline(-A, color='g', ls=':')\n"
                "ax.set_xlabel(r'$x$'); ax.set_ylabel(r'Énergie [J]')\n"
                "ax.set_title('Puits de potentiel harmonique')\n"
                "ax.legend(); ax.grid(True, alpha=0.3)\n"
                "ax.set_ylim(-0.5, 6)\n"
                "plt.tight_layout(); plt.savefig('plot.png')\n"
                "print(f'Em = {Em:.2f} J, amplitude A = {A:.2f} m')\n"
                "print(f'A x=0 : Ep=0, Ec=Em (vitesse max)')\n"
                "print(f'A x=±A : Ep=Em, Ec=0 (points de retournement)')\n"
            ),
            APP(
                "Bille qui dévale une rampe",
                "Une bille de masse $m=0{,}1$ kg part du repos en haut d'une rampe "
                "parfaite (sans frottement) à $h=1{,}5$ m au-dessus du sol. "
                "(a) Quelle est sa vitesse en bas de la rampe ? (b) Si la rampe "
                "présente des frottements qui dissipent 30% de l'énergie initiale, "
                "quelle est la nouvelle vitesse en bas ?",
                "On prend $g=9{,}81$ m/s².\n\n"
                "**(a) Sans frottement — conservation de $E_m$** :\n"
                "Au départ : $E_m = E_p = mgh$ (car $v_0=0$).\n"
                "En bas : $E_m = E_c = \\tfrac12 m v^2$ (car $z=0$).\n\n"
                "Conservation : $\\tfrac12 m v^2 = mgh \\Rightarrow$\n"
                "$$v = \\sqrt{2gh} = \\sqrt{2 \\times 9{,}81 \\times 1{,}5} \\approx "
                "5{,}43\\;\\text{m/s}.$$\n\n"
                "Remarque : la masse se simplifie — tous les corps tombent à la même "
                "vitesse (Galilée).\n\n"
                "**(b) Avec frottements (30% d'énergie dissipée)** :\n"
                "L'énergie finale est 70% de l'énergie initiale :\n"
                "$$\\tfrac12 m v'^2 = 0{,}70 \\times mgh$$\n"
                "$$v' = \\sqrt{2 \\times 0{,}70 \\times 9{,}81 \\times 1{,}5} "
                "\\approx 4{,}55\\;\\text{m/s}.$$\n\n"
                "On vérifie : $v'/v = \\sqrt{0{,}70} \\approx 0{,}837$, soit 16% de "
                "perte de vitesse pour 30% de perte d'énergie (toujours à cause de "
                "la racine carrée)."
            ),
            MCQ(
                "Conservation de l'énergie mécanique",
                "L'énergie mécanique se conserve si et seulement si :",
                [
                    {"text": "Toutes les forces sont conservatives", "correct": True, "feedback": "Exact !"},
                    {"text": "Il n'y a aucune force", "correct": False, "feedback": "Trop restrictif."},
                    {"text": "Le mouvement est uniforme", "correct": False, "feedback": "Non suffisant."},
                    {"text": "L'objet est au repos", "correct": False, "feedback": "Pas nécessaire."}
                ],
                explanation="L'absence de forces non conservatives (frottements) est la condition."
            ),
            MCQ(
                "Énergie potentielle de pesanteur",
                "L'énergie potentielle de pesanteur vaut :",
                [
                    {"text": "$mgv$", "correct": False, "feedback": "Vitesse n'apparaît pas dans $E_p$."},
                    {"text": "$\\tfrac12 m v^2$", "correct": False, "feedback": "C'est $E_c$, pas $E_p$."},
                    {"text": "$mgz$", "correct": True, "feedback": "Exact !"},
                    {"text": "$\\tfrac12 k x^2$", "correct": False, "feedback": "C'est l'énergie potentielle élastique."}
                ],
                explanation="$E_p = mgz$ (à une constante additive près)."
            ),
            FB(
                "Compléter les formules d'énergie",
                "Énergie mécanique : $E_m = E_c + {{blank_1}}$. "
                "Énergie potentielle élastique : $E_p = \\dfrac12 {{blank_2}} x^2$. "
                "Vitesse par conservation : $v = \\sqrt{2 g {{blank_3}}}$ (hauteur $h$).",
                {"blank_1": ["E_p", "Ep"], "blank_2": ["k"], "blank_3": ["h"]},
                explanation="$E_m = E_c + E_p$ ; ressort : $\\tfrac12 k x^2$ ; chute libre : $v=\\sqrt{2gh}$."
            ),
            TF(
                "Vrai ou Faux ? Énergie mécanique",
                [
                    {"statement": "$E_p$ est définie à une constante près.",
                     "is_true": True},
                    {"statement": "En présence de frottements, $E_m$ augmente.",
                     "is_true": False, "statement_note": "Elle diminue."},
                    {"statement": "Pour un oscillateur harmonique, $E_p$ est parabolique.",
                     "is_true": True},
                    {"statement": "Aux points de retournement, $E_c = 0$.",
                     "is_true": True},
                    {"statement": "$E_m$ est une grandeur vectorielle.",
                     "is_true": False, "statement_note": "C'est un scalaire."}
                ]
            )
        ]},

        # -----------------------------------------------------------------
        # Lesson 2.4 — Conservation de l'énergie
        # -----------------------------------------------------------------
        {"order": 3, "title": "Conservation de l'énergie — applications",
         "slug": "conservation-energie", "minutes": 30, "blocks": [
            T(
                "# Conservation de l'énergie — applications\n\n"
                "## 1. Méthode générale\n\n"
                "Pour résoudre un problème avec conservation de l'énergie :\n"
                "1. Vérifier que les forces sont conservatives (sinon $E_m$ diminue) ;\n"
                "2. Choisir l'origine des $E_p$ ;\n"
                "3. Écrire $E_m = E_c + E_p$ à deux instants ;\n"
                "4. Égaliser et résoudre.\n\n"
                "## 2. Looping avec énergie\n\n"
                "Pour qu'une voiture (partant du repos à hauteur $h$) réussisse un "
                "looping de rayon $R$ :\n"
                "- Au départ : $E_m = mgh$ ;\n"
                "- Au sommet : $E_m = \\tfrac12 m v^2 + mg(2R)$.\n\n"
                "Condition de contact au sommet : $v^2 \\geq gR$.\n\n"
                "En combinant avec la conservation de l'énergie :\n"
                "$$mgh \\geq \\tfrac12 m(gR) + 2mgR = \\tfrac52 mgR$$\n"
                "$$\\boxed{h \\geq \\tfrac52 R}$$\n\n"
                "## 3. Pendule\n\n"
                "Pour un pendule de longueur $L$ lâché d'un angle $\\theta_0$, la "
                "vitesse au point bas vaut :\n"
                "$$v = \\sqrt{2 g L (1 - \\cos\\theta_0)}$$\n\n"
                "## 4. Plan incliné sans frottement\n\n"
                "Vitesse au bas d'un plan incliné de hauteur $h$ :\n"
                "$$v = \\sqrt{2gh}$$\n\n"
                "Indépendante de l'angle et de la masse !\n\n"
                "> 💡 **Astuce** : L'approche énergétique est souvent **beaucoup plus "
                "rapide** que le PFD quand on cherche une vitesse à une position "
                "donnée. Elle évite d'intégrer $a(t)$ sur le temps."
            ),
            S(
                "Looping : hauteur min vs rayon",
                "import matplotlib.pyplot as plt\n"
                "import numpy as np\n"
                "\n"
                "R = np.linspace(1, 10, 100)\n"
                "h_min = 2.5 * R  # sans frottement\n"
                "\n"
                "fig, ax = plt.subplots(figsize=(8, 5))\n"
                "ax.plot(R, h_min, 'b-', lw=2, label=r'$h_{min}=\\frac{5}{2}R$ (sans frottement)')\n"
                "ax.plot(R, 3.0*R, 'r--', lw=2, label=r'avec 20% de pertes ($\\approx 3R$)')\n"
                "ax.set_xlabel(r'Rayon du looping $R$ [m]')\n"
                "ax.set_ylabel(r'Hauteur de départ min $h$ [m]')\n"
                "ax.set_title('Hauteur minimale pour réussir un looping')\n"
                "ax.legend(); ax.grid(True, alpha=0.3)\n"
                "plt.tight_layout(); plt.savefig('plot.png')\n"
                "print(f'R=5 m -> h_min = {2.5*5:.1f} m (ideal)')\n"
                "print(f'Avec frottements, h_min augmente (souvent ~3R ou plus).')\n"
            ),
            APP(
                "Pendule simple — vitesse au point bas",
                "Un pendule simple de longueur $L=1{,}0$ m est lâché sans vitesse "
                "initiale depuis un angle $\\theta_0 = 60°$. (a) Calcule la vitesse "
                "au point bas. (b) Même question si $\\theta_0 = 90°$. (c) Quelle "
                "vitesse faudrait-il donner au pendule au point bas pour qu'il fasse "
                "un tour complet ?",
                "On prend $g = 9{,}81$ m/s².\n\n"
                "**Méthode** : conservation de $E_m$ entre le point de départ (haut) "
                "et le point bas.\n"
                "Hauteur initiale : $h = L(1 - \\cos\\theta_0)$.\n"
                "Au point bas : $\\tfrac12 m v^2 = mgh \\Rightarrow v = \\sqrt{2 g L (1 - \\cos\\theta_0)}$.\n\n"
                "**(a) $\\theta_0 = 60°$** ($\\cos 60° = 0{,}5$) :\n"
                "$$v = \\sqrt{2 \\times 9{,}81 \\times 1 \\times 0{,}5} = \\sqrt{9{,}81} "
                "\\approx 3{,}13\\;\\text{m/s}.$$\n\n"
                "**(b) $\\theta_0 = 90°$** ($\\cos 90° = 0$) :\n"
                "$$v = \\sqrt{2 \\times 9{,}81 \\times 1 \\times 1} \\approx 4{,}43\\;\\text{m/s}.$$\n\n"
                "**(c) Tour complet** : il faut que le fil reste tendu au sommet, "
                "c'est-à-dire $v_{sommet}^2 \\geq gL$.\n"
                "Conservation de $E_m$ entre le point bas et le sommet :\n"
                "$$\\tfrac12 m v_{bas}^2 = \\tfrac12 m v_{sommet}^2 + mg(2L)$$\n"
                "Avec $v_{sommet}^2 = gL$ :\n"
                "$$v_{bas}^2 = gL + 4gL = 5gL \\quad\\Rightarrow\\quad v_{bas} = \\sqrt{5gL} "
                "= \\sqrt{5 \\times 9{,}81 \\times 1} \\approx 7{,}0\\;\\text{m/s}.$$\n\n"
                "C'est la **vitesse minimale** pour faire un tour complet (boucle)."
            ),
            MCQ(
                "Hauteur min pour un looping",
                "Sans frottement, la hauteur minimale pour réussir un looping de rayon $R$ vaut :",
                [
                    {"text": "$2R$", "correct": False, "feedback": "Trop bas, on perd le contact."},
                    {"text": "$\\tfrac52 R$", "correct": True, "feedback": "Exact ! Démontré via conservation de $E_m$."},
                    {"text": "$3R$", "correct": False, "feedback": "Trop, c'est avec marge de sécurité."},
                    {"text": "$\\pi R$", "correct": False, "feedback": "Non, $\\pi$ n'a rien à voir ici."}
                ],
                explanation="On combine $mgh = \\tfrac12 m v^2 + 2mgR$ avec $v^2 \\geq gR$ au sommet, d'où $h \\geq \\tfrac52 R$."
            ),
            MCQ(
                "Vitesse au bas d'un plan incliné sans frottement",
                "Un objet part du repos en haut d'un plan de hauteur $h$. Sa vitesse "
                "en bas vaut :",
                [
                    {"text": "$\\sqrt{gh}$", "correct": False, "feedback": "Manque un facteur 2."},
                    {"text": "$\\sqrt{2gh}$", "correct": True, "feedback": "Exact ! Indépendant de la masse et de l'angle."},
                    {"text": "$2gh$", "correct": False, "feedback": "Tu as oublié la racine."},
                    {"text": "$gh$", "correct": False, "feedback": "Non."}
                ],
                explanation="$mgh = \\tfrac12 m v^2 \\Rightarrow v = \\sqrt{2gh}$."
            ),
            FB(
                "Vitesse et conservation",
                "Vitesse au bas d'une chute de hauteur $h$ : $v = \\sqrt{{{blank_1}}}$. "
                "Vitesse au point bas d'un pendule : $v = \\sqrt{2 g L (1 - {{blank_2}})}$. "
                "Tour complet de looping : $v_{bas} \\geq \\sqrt{{{blank_3}}}$.",
                {"blank_1": ["2gh", "2 g h", "2\\,g\\,h"],
                 "blank_2": ["\\cos\\theta_0", "cos(theta_0)", "cos(\\theta_0)"],
                 "blank_3": ["5gL", "5 g L", "5\\,g\\,L"]},
                explanation="Chute libre : $\\sqrt{2gh}$ ; pendule : avec $\\cos\\theta_0$ ; "
                            "looping complet : $\\sqrt{5gL}$."
            ),
            TF(
                "Vrai ou Faux ? Conservation de l'énergie",
                [
                    {"statement": "Sans frottement, $E_m$ se conserve.",
                     "is_true": True},
                    {"statement": "La vitesse au bas d'un plan incliné sans frottement dépend de l'angle.",
                     "is_true": False, "statement_note": "Elle ne dépend que de $h$."},
                    {"statement": "Pour un looping sans frottement, $h_{min}=\\tfrac52 R$.",
                     "is_true": True},
                    {"statement": "Plus l'amplitude du pendule est grande, plus la vitesse au bas est grande.",
                     "is_true": True},
                    {"statement": "L'approche énergétique évite d'intégrer $a(t)$.",
                     "is_true": True}
                ]
            )
        ]},
    ]},


    # =====================================================================
    # MODULE 3 — COLLISIONS
    # =====================================================================
    {"order": 3, "title": "Collisions et quantité de mouvement",
     "description": "Quantité de mouvement, impulsion, collisions élastiques "
                    "et inélastiques, applications.",
     "lessons": [

        # -----------------------------------------------------------------
        # Lesson 3.1 — Quantité de mouvement et impulsion
        # -----------------------------------------------------------------
        {"order": 0, "title": "Quantité de mouvement et impulsion",
         "slug": "quantite-mouvement-impulsion", "minutes": 30, "blocks": [
            T(
                "# Quantité de mouvement et impulsion\n\n"
                "## 1. Quantité de mouvement\n\n"
                "La **quantité de mouvement** d'un point matériel de masse $m$ et "
                "de vitesse $\\vec{v}$ est :\n"
                "$$\\vec{p} = m\\, \\vec{v}$$\n\n"
                "C'est un vecteur, en kg·m/s.\n\n"
                "## 2. Impulsion\n\n"
                "L'**impulsion** d'une force $\\vec{F}$ sur l'intervalle $[t_1, t_2]$ est :\n"
                "$$\\vec{J} = \\int_{t_1}^{t_2} \\vec{F}(t)\\, dt$$\n\n"
                "Pour une force constante : $\\vec{J} = \\vec{F}\\, \\Delta t$.\n\n"
                "## 3. Théorème de l'impulsion\n\n"
                "$$\\Delta \\vec{p} = \\vec{J}$$\n\n"
                "La variation de la quantité de mouvement égale l'impulsion reçue.\n\n"
                "## 4. Conservation de $\\vec{p}$\n\n"
                "Pour un système **isolé** (aucune force extérieure), la quantité de "
                "mouvement totale se conserve :\n"
                "$$\\sum \\vec{p}_i = \\text{constante}$$\n\n"
                "## 5. Application : recul d'une arme\n\n"
                "Une arme de masse $M$ tire une balle de masse $m$ à la vitesse $v$. "
                "Avant : $\\vec{p}=0$. Après : $m v_{balle} + M V_{arme} = 0$, donc :\n"
                "$$V_{arme} = -\\frac{m}{M} v_{balle}$$\n\n"
                "> 💡 **Astuce** : La conservation de $\\vec{p}$ est utile dans toutes "
                "les **interactions brèves** (chocs, explosions) où les forces "
                "intérieures dominent largement les forces extérieures."
            ),
            S(
                "Recul d'une arme — conservation de p",
                "import matplotlib.pyplot as plt\n"
                "import numpy as np\n"
                "from matplotlib.patches import FancyArrowPatch, Rectangle, Circle\n"
                "\n"
                "fig, ax = plt.subplots(figsize=(10, 4))\n"
                "M, m = 4.0, 0.01       # masse arme, masse balle\n"
                "v_balle = 400.0        # m/s\n"
                "V_arme = -m/M * v_balle\n"
                "# Avant\n"
                "ax.add_patch(Rectangle((1, 1.5), 2, 0.6, color='steelblue'))\n"
                "ax.text(2, 2.4, 'AVANT\\n$p=0$', ha='center', fontsize=11)\n"
                "# Fleche nulle\n"
                "# Apres\n"
                "ax.add_patch(Rectangle((5-V_arme*0.005, 1.5), 2, 0.6, color='steelblue'))\n"
                "ax.text(6, 2.4, 'APRÈS', ha='center', fontsize=11)\n"
                "# Balle (vers la droite)\n"
                "ax.add_patch(Circle((7.5+v_balle*0.003, 1.8), 0.1, color='red'))\n"
                "ax.add_patch(FancyArrowPatch((7.5, 1.8), (8.5, 1.8), arrowstyle='->', mutation_scale=18, color='red', lw=2))\n"
                "ax.text(8, 2.1, r'$m v_{balle}$', color='red', fontsize=11)\n"
                "# Arme recule (vers la gauche)\n"
                "ax.add_patch(FancyArrowPatch((5, 1.4), (4, 1.4), arrowstyle='->', mutation_scale=18, color='blue', lw=2))\n"
                "ax.text(4.2, 0.9, r'$M V_{arme}$', color='blue', fontsize=11)\n"
                "ax.set_xlim(0, 10); ax.set_ylim(0, 3)\n"
                "ax.set_aspect('equal'); ax.grid(True, alpha=0.3)\n"
                "ax.set_title(rf'Conservation de $\\vec{{p}}$ : $m v_{{balle}} + M V_{{arme}} = 0$', fontsize=12)\n"
                "ax.axis('off')\n"
                "plt.tight_layout(); plt.savefig('plot.png')\n"
                "print(f'Vitesse de recul : V_arme = {V_arme:.2f} m/s')\n"
                "print(f'Quantite de mouvement : m*v = {m*v_balle:.2f} kg.m/s')\n"
                "print(f'                      : M*V = {M*V_arme:.2f} kg.m/s (oppose)')\n"
            ),
            APP(
                "Saut d'un plongeur",
                "Un plongeur de masse $m=70$ kg se tient sur une barque de masse "
                "$M=200$ kg, initialement immobile. Il saute horizontalement à la "
                "vitesse $v=3$ m/s (par rapport à la barque avant le saut). "
                "(a) Calcule la vitesse de la barque après le saut (par rapport à l'eau). "
                "(b) Quelle est la vitesse réelle du plongeur par rapport à l'eau ?",
                "**Système** : plongeur + barque (isolé horizontalement, frottements "
                "de l'eau négligés pendant le saut).\n\n"
                "Soit $V$ la vitesse de la barque par rapport à l'eau (vers l'arrière, "
                "donc négative si le plongeur saute vers l'avant). La vitesse du "
                "plongeur par rapport à l'eau est $v_{rel} = v + V$ (composition des "
                "vitesses, valable en mécanique newtonienne).\n\n"
                "Conservation de $p$ (initialement nulle) :\n"
                "$$m(v + V) + M V = 0$$\n"
                "$$m v + (m+M) V = 0 \\quad\\Rightarrow\\quad V = -\\frac{m v}{m+M}$$\n\n"
                "**(a) Vitesse de la barque** :\n"
                "$$V = -\\frac{70 \\times 3}{70 + 200} = -\\frac{210}{270} \\approx -0{,}778\\;\\text{m/s}.$$\n\n"
                "La barque recule à $\\approx 0{,}78$ m/s.\n\n"
                "**(b) Vitesse du plongeur par rapport à l'eau** :\n"
                "$$v_{rel} = v + V = 3 - 0{,}778 \\approx 2{,}22\\;\\text{m/s}.$$\n\n"
                "Vérification : $m v_{rel} + M V = 70 \\times 2{,}22 + 200 \\times (-0{,}778) "
                "\\approx 155{,}4 - 155{,}6 \\approx 0$ ✓ (conservation vérifiée)."
            ),
            MCQ(
                "Impulsion et variation de p",
                "Le théorème de l'impulsion dit :",
                [
                    {"text": "$\\Delta \\vec{p} = \\vec{F}$", "correct": False, "feedback": "Il manque l'intégration sur le temps."},
                    {"text": "$\\Delta \\vec{p} = \\vec{J}$", "correct": True, "feedback": "Exact !"},
                    {"text": "$\\Delta \\vec{p} = \\vec{0}$", "correct": False, "feedback": "Seulement pour un système isolé."},
                    {"text": "$\\vec{p} = m\\vec{a}$", "correct": False, "feedback": "C'est plutôt $\\vec{F}=m\\vec{a}$."}
                ],
                explanation="$\\Delta\\vec{p} = \\vec{J} = \\int \\vec{F}\\, dt$."
            ),
            MCQ(
                "Conservation de p",
                "La quantité de mouvement totale d'un système se conserve :",
                [
                    {"text": "Toujours", "correct": False, "feedback": "Non, seulement si le système est isolé."},
                    {"text": "Si le système est isolé (pas de force extérieure)", "correct": True, "feedback": "Exact !"},
                    {"text": "Si les forces intérieures sont nulles", "correct": False, "feedback": "Non pertinent."},
                    {"text": "Jamais", "correct": False, "feedback": "Si, pour un système isolé."}
                ],
                explanation="Système isolé $\\Leftrightarrow$ aucune force extérieure nette $\\Rightarrow$ $\\sum \\vec{p}$ constante."
            ),
            FB(
                "Quantité de mouvement",
                "Quantité de mouvement : $\\vec{p} = m \\times {{blank_1}}$. "
                "Impulsion (force constante) : $\\vec{J} = \\vec{F} \\times {{blank_2}}$. "
                "Théorème : $\\Delta \\vec{p} = {{blank_3}}$.",
                {"blank_1": ["\\vec{v}", "v"], "blank_2": ["\\Delta t", "Dt", "t"],
                 "blank_3": ["\\vec{J}", "J", "impulsion"]},
                explanation="$\\vec{p}=m\\vec{v}$, $\\vec{J}=\\vec{F}\\,\\Delta t$, $\\Delta\\vec{p}=\\vec{J}$."
            ),
            TF(
                "Vrai ou Faux ? Quantité de mouvement",
                [
                    {"statement": "$\\vec{p}$ est un vecteur.",
                     "is_true": True},
                    {"statement": "L'impulsion s'exprime en N·s.",
                     "is_true": True},
                    {"statement": "Pour un système isolé, $\\sum \\vec{p}$ reste constant même lors d'un choc.",
                     "is_true": True},
                    {"statement": "Les forces intérieures modifient $\\sum \\vec{p}$ du système.",
                     "is_true": False, "statement_note": "Elles se compensent (3ème loi)."},
                    {"statement": "$\\vec{p}$ a la même dimension qu'une impulsion.",
                     "is_true": True}
                ]
            )
        ]},

        # -----------------------------------------------------------------
        # Lesson 3.2 — Collisions élastiques et inélastiques
        # -----------------------------------------------------------------
        {"order": 1, "title": "Collisions élastiques et inélastiques",
         "slug": "collisions-elastiques-inelastiques", "minutes": 35, "blocks": [
            T(
                "# Collisions élastiques et inélastiques\n\n"
                "## 1. Types de collisions\n\n"
                "- **Élastique** : conservation de $\\vec{p}$ ET de $E_c$ (ex : "
                "boules de billard idéales, particules).\n"
                "- **Inélastique** : conservation de $\\vec{p}$ mais pas de $E_c$ "
                "(une partie part en chaleur/déformation).\n"
                "- **Parfaitement inélastique** : les deux objets restent accrochés "
                "après le choc (perte max d'$E_c$).\n\n"
                "## 2. Collision 1D parfaitement inélastique\n\n"
                "Deux objets de masses $m_1, m_2$ et vitesses $v_1, v_2$ s'accrochent. "
                "Vitesse finale commune :\n"
                "$$v_f = \\frac{m_1 v_1 + m_2 v_2}{m_1 + m_2}$$\n\n"
                "## 3. Collision 1D élastique\n\n"
                "Conservation de $\\vec{p}$ et de $E_c$ donnent :\n"
                "$$v_1' = \\frac{(m_1-m_2)v_1 + 2 m_2 v_2}{m_1+m_2}$$\n"
                "$$v_2' = \\frac{(m_2-m_1)v_2 + 2 m_1 v_1}{m_1+m_2}$$\n\n"
                "## 4. Cas particuliers remarquables\n\n"
                "- **Masses égales** ($m_1=m_2$) : $v_1'=v_2$ et $v_2'=v_1$ "
                "(échange des vitesses).\n"
                "- **Cible immobile** ($v_2=0$) et $m_1 \\ll m_2$ : la particule "
                "légère **rebondit** ($v_1' \\approx -v_1$) et la lourde bouge à "
                "peu ($v_2' \\approx 0$).\n"
                "- **Cible immobile** et $m_1 \\gg m_2$ : la particule lourde "
                "continue presque à la même vitesse.\n\n"
                "> 💡 **Astuce** : Dans une collision élastique 1D entre masses "
                "égales, les deux objets **échangent leurs vitesses**. C'est "
                "spectaculaire au billard !"
            ),
            S(
                "Collision 1D élastique — masses égales",
                "import matplotlib.pyplot as plt\n"
                "import numpy as np\n"
                "\n"
                "m1, m2 = 1.0, 1.0\n"
                "v1, v2 = 4.0, 0.0     # cible immobile\n"
                "# Formules de collision elastique 1D\n"
                "v1p = ((m1-m2)*v1 + 2*m2*v2)/(m1+m2)\n"
                "v2p = ((m2-m1)*v2 + 2*m1*v1)/(m1+m2)\n"
                "\n"
                "t = np.linspace(0, 2, 100)\n"
                "x1_avant = v1*t\n"
                "x2_avant = v2*t + 5\n"
                "t_choc = 5 / (v1 - v2)\n"
                "t_apres = t[t >= t_choc] - t_choc\n"
                "x1_apres = v1*t_choc + v1p*t_apres\n"
                "x2_apres = 5 + v2p*t_apres\n"
                "\n"
                "fig, ax = plt.subplots(figsize=(9, 5))\n"
                "ax.plot(t[t<t_choc], x1_avant[t<t_choc], 'b-', lw=2, label=r'$m_1$ (avant)')\n"
                "ax.plot(t[t<t_choc], x2_avant[t<t_choc], 'r-', lw=2, label=r'$m_2$ (avant)')\n"
                "ax.plot(t[t>=t_choc], x1_apres, 'b--', lw=2, label=r\"$m_1$ (après)\")\n"
                "ax.plot(t[t>=t_choc], x2_apres, 'r--', lw=2, label=r\"$m_2$ (après)\")\n"
                "ax.axvline(t_choc, color='k', ls=':', alpha=0.5)\n"
                "ax.text(t_choc, 8, r'Choc $\\to$ échange des vitesses', fontsize=10)\n"
                "ax.set_xlabel(r'$t$ [s]'); ax.set_ylabel(r'$x$ [m]')\n"
                "ax.set_title(r'Collision élastique 1D, masses égales : $v_1=4, v_2=0$')\n"
                "ax.legend(); ax.grid(True, alpha=0.3)\n"
                "plt.tight_layout(); plt.savefig('plot.png')\n"
                "print(f'Avant : v1={v1}, v2={v2}')\n"
                "print(f'Apres : v1p={v1p:.2f}, v2p={v2p:.2f}')\n"
                "print(f'Verification p : {m1*v1+m2*v2:.2f} = {m1*v1p+m2*v2p:.2f}')\n"
                "print(f'Verification Ec : {0.5*m1*v1**2+0.5*m2*v2**2:.2f} = {0.5*m1*v1p**2+0.5*m2*v2p**2:.2f}')\n"
            ),
            APP(
                "Collision élastique avec cible immobile",
                "Une boule de billard de masse $m_1=200$ g se déplace à $v_1=2$ m/s "
                "et heurte une autre boule de masse $m_2=200$ g initialement "
                "immobile. (a) Calcule les vitesses après le choc (supposé élastique "
                "et 1D). (b) Reprends la question si $m_2 = 400$ g.",
                "**(a) Masses égales** : $m_1 = m_2 = m$.\n"
                "D'après les formules de collision 1D élastique :\n"
                "$$v_1' = \\frac{(m-m)v_1 + 2 m \\cdot 0}{2m} = 0$$\n"
                "$$v_2' = \\frac{(m-m)\\cdot 0 + 2 m v_1}{2m} = v_1 = 2\\;\\text{m/s}.$$\n\n"
                "Il y a **échange des vitesses** : la boule 1 s'arrête, la boule 2 "
                "part à 2 m/s. C'est le comportement classique du billard.\n\n"
                "Vérification : $E_c$ avant $= \\tfrac12 \\times 0{,}2 \\times 4 = 0{,}4$ J ; "
                "$E_c$ après $= \\tfrac12 \\times 0{,}2 \\times 4 = 0{,}4$ J ✓.\n\n"
                "**(b) $m_2 = 400$ g** :\n"
                "$$v_1' = \\frac{(200-400)\\times 2 + 2\\times 400 \\times 0}{600} "
                "= \\frac{-400}{600} \\approx -0{,}67\\;\\text{m/s},$$\n"
                "$$v_2' = \\frac{(400-200)\\times 0 + 2\\times 200 \\times 2}{600} "
                "= \\frac{800}{600} \\approx 1{,}33\\;\\text{m/s}.$$\n\n"
                "La boule 1 **rebondit** (vitesse négative) à 0,67 m/s, tandis que "
                "la boule 2 part à 1,33 m/s. Vérification $E_c$ : avant = 0,4 J ; "
                "après = $\\tfrac12 \\times 0{,}2 \\times 0{,}67^2 + \\tfrac12 \\times 0{,}4 "
                "\\times 1{,}33^2 \\approx 0{,}045 + 0{,}355 = 0{,}4$ J ✓."
            ),
            MCQ(
                "Collision parfaitement inélastique",
                "Deux objets de masses $m_1$ et $m_2$ en collision parfaitement "
                "inélastique ont, après le choc :",
                [
                    {"text": "Chacun sa propre vitesse", "correct": False, "feedback": "Non, ils restent accrochés."},
                    {"text": "Une vitesse commune $v_f = (m_1 v_1 + m_2 v_2)/(m_1+m_2)$", "correct": True, "feedback": "Exact !"},
                    {"text": "Une énergie cinétique conservée", "correct": False, "feedback": "Non, il y a perte d'$E_c$."},
                    {"text": "Une quantité de mouvement nulle", "correct": False, "feedback": "Seulement si elle était nulle avant."}
                ],
                explanation="Vitesse commune $v_f = (m_1 v_1 + m_2 v_2)/(m_1+m_2)$."
            ),
            MCQ(
                "Collision élastique masses égales",
                "Lors d'une collision élastique 1D entre deux masses égales, où "
                "l'une est immobile, on observe :",
                [
                    {"text": "Les deux boules s'arrêtent", "correct": False, "feedback": "Non, $\\vec{p}$ ne serait pas conservé."},
                    {"text": "Échange des vitesses", "correct": True, "feedback": "Exact ! La boule incidente s'arrête, la cible part à $v_1$."},
                    {"text": "Elles rebondissent toutes deux", "correct": False, "feedback": "Non."},
                    {"text": "Les vitesses sont divisées par 2", "correct": False, "feedback": "Non."}
                ],
                explanation="Pour $m_1=m_2$, on a $v_1' = v_2$ et $v_2' = v_1$ : échange total."
            ),
            FB(
                "Formules des collisions",
                "Collision parfaitement inélastique : $v_f = \\dfrac{m_1 v_1 + {{blank_1}}}{m_1 + m_2}$. "
                "Collision élastique : $\\vec{p}$ et ${{blank_2}}$ sont conservés. "
                "Collision inélastique : une partie de $E_c$ est dissipée en {{blank_3}}.",
                {"blank_1": ["m_2 v_2"], "blank_2": ["E_c", "Ec", "énergie cinétique"],
                 "blank_3": ["chaleur", "déformation", "chaleur et déformation"]},
                explanation="$v_f$ est la moyenne pondérée ; collision élastique conserve $E_c$ ; "
                            "le reste part en chaleur/déformation."
            ),
            TF(
                "Vrai ou Faux ? Collisions",
                [
                    {"statement": "Dans toute collision, $\\vec{p}$ totale est conservée (système isolé).",
                     "is_true": True},
                    {"statement": "Une collision parfaitement inélastique conserve $E_c$.",
                     "is_true": False, "statement_note": "C'est la collision qui dissipe le plus d'$E_c$."},
                    {"statement": "Une collision élastique conserve $E_c$.",
                     "is_true": True},
                    {"statement": "Pour des masses égales en collision élastique 1D, il y a échange des vitesses.",
                     "is_true": True},
                    {"statement": "Une collision inélastique ne conserve pas $\\vec{p}$.",
                     "is_true": False, "statement_note": "Elle conserve $\\vec{p}$ mais pas $E_c$."}
                ]
            )
        ]},
    ]},


    # =====================================================================
    # MODULE 4 — OSCILLATEURS
    # =====================================================================
    {"order": 4, "title": "Oscillateurs et ondes",
     "description": "Oscillateur harmonique, pendule simple, oscillations "
                    "amorties et forcées, résonance.",
     "lessons": [

        # -----------------------------------------------------------------
        # Lesson 4.1 — Oscillateur harmonique
        # -----------------------------------------------------------------
        {"order": 0, "title": "Oscillateur harmonique",
         "slug": "oscillateur-harmonique", "minutes": 35, "blocks": [
            T(
                "# Oscillateur harmonique\n\n"
                "## 1. Définition\n\n"
                "Un **oscillateur harmonique** est un système soumis à une force de "
                "rappel proportionnelle à l'écartement : $\\vec{F} = -k\\, x\\, \\vec{i}$.\n"
                "Le PFD donne :\n"
                "$$m\\ddot{x} = -k x \\quad\\Leftrightarrow\\quad \\ddot{x} + \\omega_0^2 x = 0$$\n\n"
                "avec la **pulsation propre** $\\omega_0 = \\sqrt{k/m}$.\n\n"
                "## 2. Solution\n\n"
                "$$x(t) = A\\cos(\\omega_0 t) + B\\sin(\\omega_0 t) = X_{max}\\cos(\\omega_0 t + \\varphi)$$\n\n"
                "avec $X_{max}$ l'amplitude, $\\varphi$ la phase.\n\n"
                "## 3. Période et fréquence\n\n"
                "$$T = \\frac{2\\pi}{\\omega_0} = 2\\pi\\sqrt{\\frac{m}{k}}, \\quad "
                "f = \\frac{1}{T}$$\n\n"
                "## 4. Énergie\n\n"
                "$$E_c = \\tfrac12 m \\dot{x}^2, \\quad E_p = \\tfrac12 k x^2, \\quad "
                "E_m = \\tfrac12 k X_{max}^2 = \\text{cste}$$\n\n"
                "## 5. Portrait de phase\n\n"
                "Dans le plan $(x, \\dot{x})$, la trajectoire est une **ellipse** :\n"
                "$$\\frac{x^2}{X_{max}^2} + \\frac{\\dot{x}^2}{\\omega_0^2 X_{max}^2} = 1$$\n\n"
                "> 💡 **Astuce** : La période ne dépend **pas** de l'amplitude (pour "
                "un oscillateur harmonique idéal). C'est la propriété d'**isochronisme** "
                "des oscillations, exploitée dans les horloges à pendule."
            ),
            S(
                "Oscillateur harmonique : x(t), v(t), a(t)",
                "import matplotlib.pyplot as plt\n"
                "import numpy as np\n"
                "\n"
                "m, k = 1.0, 16.0\n"
                "omega0 = np.sqrt(k/m)\n"
                "T = 2*np.pi/omega0\n"
                "t = np.linspace(0, 2*T, 500)\n"
                "X = 1.0\n"
                "x = X*np.cos(omega0*t)\n"
                "v = -X*omega0*np.sin(omega0*t)\n"
                "a = -omega0**2 * x\n"
                "\n"
                "fig, axes = plt.subplots(3, 1, figsize=(9, 9), sharex=True)\n"
                "axes[0].plot(t, x, 'b-', lw=2)\n"
                "axes[0].set_ylabel(r'$x(t)$ [m]')\n"
                "axes[0].set_title(rf'$\\omega_0={omega0:.2f}$ rad/s, $T={T:.3f}$ s')\n"
                "axes[0].grid(True, alpha=0.3)\n"
                "axes[1].plot(t, v, 'r-', lw=2)\n"
                "axes[1].set_ylabel(r'$v(t)$ [m/s]')\n"
                "axes[1].grid(True, alpha=0.3)\n"
                "axes[2].plot(t, a, 'g-', lw=2)\n"
                "axes[2].set_ylabel(r'$a(t)$ [m/s$^2$]')\n"
                "axes[2].set_xlabel(r'$t$ [s]')\n"
                "axes[2].grid(True, alpha=0.3)\n"
                "plt.tight_layout(); plt.savefig('plot.png')\n"
                "print(f'omega_0 = {omega0:.2f} rad/s')\n"
                "print(f'T = {T:.3f} s, f = {1/T:.2f} Hz')\n"
                "print(f'E_m = 0.5*k*X^2 = {0.5*k*X**2:.2f} J')\n"
            ),
            S(
                "Portrait de phase (x, v)",
                "import matplotlib.pyplot as plt\n"
                "import numpy as np\n"
                "\n"
                "omega0 = 4.0\n"
                "t = np.linspace(0, 5*2*np.pi/omega0, 500)\n"
                "fig, ax = plt.subplots(figsize=(7, 7))\n"
                "for A in [0.5, 1.0, 1.5]:\n"
                "    x = A*np.cos(omega0*t)\n"
                "    v = -A*omega0*np.sin(omega0*t)\n"
                "    ax.plot(x, v, lw=2, label=r'$A=%.1f$' % A)\n"
                "ax.set_xlabel(r'$x$ [m]'); ax.set_ylabel(r'$\\dot{x}$ [m/s]')\n"
                "ax.set_title(r'Portraits de phase : ellipses $\\frac{x^2}{A^2}+\\frac{\\dot{x}^2}{A^2\\omega_0^2}=1$')\n"
                "ax.legend(); ax.grid(True, alpha=0.3)\n"
                "ax.set_aspect('equal')\n"
                "plt.tight_layout(); plt.savefig('plot.png')\n"
                "print('Plus A est grand, plus lellipse est large, mais la forme reste elliptique.')\n"
            ),
            APP(
                "Ressort et masse",
                "Un ressort de constante de raideur $k=50$ N/m est accroché à une "
                "masse $m=0{,}2$ kg. On écarte la masse de $X_{max}=5$ cm de sa "
                "position d'équilibre et on la lâche sans vitesse initiale. "
                "(a) Calcule $\\omega_0$, $T$ et $f$. (b) Écris $x(t)$. "
                "(c) Calcule l'énergie mécanique et la vitesse maximale.",
                "**(a) Grandeurs caractéristiques** :\n"
                "$$\\omega_0 = \\sqrt{\\frac{k}{m}} = \\sqrt{\\frac{50}{0{,}2}} = \\sqrt{250} \\approx 15{,}81\\;\\text{rad/s}$$\n"
                "$$T = \\frac{2\\pi}{\\omega_0} \\approx \\frac{6{,}283}{15{,}81} \\approx 0{,}397\\;\\text{s}$$\n"
                "$$f = \\frac{1}{T} \\approx 2{,}52\\;\\text{Hz}$$\n\n"
                "**(b) Solution $x(t)$** : conditions initiales $x(0)=X_{max}$ et "
                "$\\dot{x}(0)=0$, donc $x(t) = X_{max}\\cos(\\omega_0 t)$ :\n"
                "$$x(t) = 0{,}05\\, \\cos(15{,}81\\, t)\\;\\text{[m]}.$$\n\n"
                "**(c) Énergie mécanique et vitesse max** :\n"
                "$$E_m = \\tfrac12 k X_{max}^2 = \\tfrac12 \\times 50 \\times 0{,}05^2 = 0{,}0625\\;\\text{J} = 62{,}5\\;\\text{mJ}.$$\n\n"
                "Vitesse maximale (au passage à $x=0$) : $E_m = \\tfrac12 m v_{max}^2$ :\n"
                "$$v_{max} = X_{max}\\, \\omega_0 = 0{,}05 \\times 15{,}81 \\approx 0{,}79\\;\\text{m/s}.$$\n\n"
                "Vérification : $\\tfrac12 \\times 0{,}2 \\times 0{,}79^2 \\approx 0{,}062$ J ✓."
            ),
            MCQ(
                "Période d'un oscillateur",
                "La période d'un oscillateur harmonique ($m$, $k$) vaut :",
                [
                    {"text": "$2\\pi\\sqrt{m/k}$", "correct": True, "feedback": "Exact !"},
                    {"text": "$2\\pi\\sqrt{k/m}$", "correct": False, "feedback": "Tu as inversé."},
                    {"text": "$\\sqrt{m/k}$", "correct": False, "feedback": "Il manque le $2\\pi$."},
                    {"text": "$2\\pi m k$", "correct": False, "feedback": "Non."}
                ],
                explanation="$T = 2\\pi/\\omega_0 = 2\\pi\\sqrt{m/k}$."
            ),
            MCQ(
                "Isochronisme",
                "Pour un oscillateur harmonique idéal, si on multiplie l'amplitude par 2, "
                "la période est :",
                [
                    {"text": "Multipliée par 2", "correct": False, "feedback": "Non."},
                    {"text": "Inchangée", "correct": True, "feedback": "Exact ! Propriété d'isochronisme."},
                    {"text": "Divisée par 2", "correct": False, "feedback": "Non."},
                    {"text": "Multipliée par 4", "correct": False, "feedback": "Non."}
                ],
                explanation="$T$ ne dépend que de $m$ et $k$, pas de l'amplitude."
            ),
            FB(
                "Compléter l'oscillateur harmonique",
                "Pulsation propre : $\\omega_0 = \\sqrt{{{blank_1}}}$. "
                "Période : $T = 2\\pi \\sqrt{m/{{blank_2}}}$. "
                "Énergie mécanique : $E_m = \\tfrac12 k \\times {{blank_3}}^2$.",
                {"blank_1": ["k/m"], "blank_2": ["k"], "blank_3": ["X", "X_{max}", "A"]},
                explanation="$\\omega_0=\\sqrt{k/m}$, $T=2\\pi\\sqrt{m/k}$, $E_m=\\tfrac12 k X_{max}^2$."
            ),
            TF(
                "Vrai ou Faux ? Oscillateur harmonique",
                [
                    {"statement": "La force de rappel est proportionnelle à l'écartement.",
                     "is_true": True},
                    {"statement": "La période dépend de l'amplitude.",
                     "is_true": False, "statement_note": "Isochronisme : elle n'en dépend pas."},
                    {"statement": "Le portrait de phase est une ellipse.",
                     "is_true": True},
                    {"statement": "L'énergie mécanique se conserve (sans frottement).",
                     "is_true": True},
                    {"statement": "$\\omega_0 = 2\\pi f$.",
                     "is_true": True}
                ]
            )
        ]},

        # -----------------------------------------------------------------
        # Lesson 4.2 — Pendule simple
        # -----------------------------------------------------------------
        {"order": 1, "title": "Pendule simple", "slug": "pendule-simple",
         "minutes": 30, "blocks": [
            T(
                "# Pendule simple\n\n"
                "## 1. Modèle\n\n"
                "Un **pendule simple** est une masse ponctuelle $m$ suspendue à un "
                "fil de longueur $L$, sans masse, dans un champ de pesanteur $g$.\n\n"
                "## 2. Équation du mouvement\n\n"
                "PFD en projection tangentielle :\n"
                "$$\\ddot{\\theta} + \\frac{g}{L}\\sin\\theta = 0$$\n\n"
                "## 3. Approximation harmonique\n\n"
                "Pour **petites oscillations** ($\\theta \\ll 1$ rad), $\\sin\\theta \\approx \\theta$ :\n"
                "$$\\ddot{\\theta} + \\omega_0^2 \\theta = 0, \\quad \\omega_0 = \\sqrt{\\frac{g}{L}}$$\n"
                "$$T = 2\\pi\\sqrt{\\frac{L}{g}}$$\n\n"
                "Indépendant de la masse et (aux petites oscillations) de l'amplitude.\n\n"
                "## 4. Grandes amplitudes\n\n"
                "Pour $\\theta_{max}$ quelconque, la période augmente : \n"
                "$$T = T_0 \\left(1 + \\frac{1}{16}\\theta_{max}^2 + \\frac{11}{3072}\\theta_{max}^4 + \\dots\\right)$$\n\n"
                "(développement asymptotique).\n\n"
                "## 5. Application historique\n\n"
                "Galilée a observé l'isochronisme des petites oscillations du pendule "
                "(1583), ce qui a permis la conception des horloges à pendule par "
                "Huygens (1656).\n\n"
                "> 💡 **Astuce** : Un pendule de $L = 1$ m a une période "
                "$T = 2\\pi\\sqrt{1/9{,}81} \\approx 2{,}0$ s — soit **1 s par demi-oscillation**, "
                "idéal pour les horloges."
            ),
            S(
                "Pendule : petite vs grande amplitude",
                "import matplotlib.pyplot as plt\n"
                "import numpy as np\n"
                "from scipy.integrate import odeint\n"
                "\n"
                "g, L = 9.81, 1.0\n"
                "omega0 = np.sqrt(g/L)\n"
                "T0 = 2*np.pi/omega0\n"
                "\n"
                "def pend(y, t):\n"
                "    theta, dtheta = y\n"
                "    return [dtheta, -(g/L)*np.sin(theta)]\n"
                "\n"
                "t = np.linspace(0, 5*T0, 1000)\n"
                "fig, ax = plt.subplots(figsize=(9, 5))\n"
                "for amp_deg in [5, 30, 90, 150]:\n"
                "    amp = np.radians(amp_deg)\n"
                "    sol = odeint(pend, [amp, 0], t)\n"
                "    ax.plot(t/T0, np.degrees(sol[:,0]), lw=2, label=r'$\\theta_0=%d°$' % amp_deg)\n"
                "ax.axhline(0, color='k', lw=0.5)\n"
                "ax.set_xlabel(r'$t/T_0$')\n"
                "ax.set_ylabel(r'$\\theta$ [deg]')\n"
                "ax.set_title(r'Pendule : $\\ddot{\\theta}+(g/L)\\sin\\theta=0$, période dépend de $\\theta_0$')\n"
                "ax.legend(); ax.grid(True, alpha=0.3)\n"
                "plt.tight_layout(); plt.savefig('plot.png')\n"
                "print(f'T0 (petites oscillations) = {T0:.3f} s')\n"
                "print('Pour theta_0=150 deg, la periode reelle est ~1.5*T0 (anharmonique).')\n"
            ),
            APP(
                "Horloge à pendule",
                "On veut construire une horloge à pendule dont la période est "
                "exactement $T = 2{,}0$ s (1 s par demi-oscillation). "
                "(a) Calcule la longueur $L$ du pendule. (b) Si $g$ diminue légèrement "
                "(par exemple en altitude), la période change-t-elle ? De combien "
                "pour $g' = 9{,}79$ m/s² (au sommet du Mont Blanc) vs $g = 9{,}81$ m/s² ?",
                "**(a) Longueur du pendule** :\n"
                "$$T = 2\\pi\\sqrt{\\frac{L}{g}} \\Rightarrow L = g\\left(\\frac{T}{2\\pi}\\right)^2$$\n"
                "$$L = 9{,}81 \\times \\left(\\frac{2}{2\\pi}\\right)^2 = 9{,}81 \\times \\frac{1}{\\pi^2} "
                "\\approx 0{,}994\\;\\text{m}.$$\n\n"
                "Une longueur d'environ **99,4 cm** donne une période de 2 s.\n\n"
                "**(b) Variation de période avec $g$** :\n"
                "$$\\frac{\\Delta T}{T} = \\frac12 \\frac{\\Delta g}{g}$$\n"
                "(en différentiant $T = 2\\pi\\sqrt{L/g}$).\n\n"
                "Avec $g' = 9{,}79$ m/s², $\\Delta g / g = -0{,}002/9{,}81 \\approx -2{,}04 \\times 10^{-4}$ :\n"
                "$$\\frac{\\Delta T}{T} \\approx \\frac12 \\times (-2{,}04 \\times 10^{-4}) \\approx -1{,}02 \\times 10^{-4}.$$\n\n"
                "Sur une journée de $86 400$ s, cela représente un retard de "
                "$\\Delta t \\approx 86400 \\times 1{,}02 \\times 10^{-4} \\approx 8{,}8$ s. "
                "C'est pourquoi les horloges à pendule doivent être réglées selon "
                "l'altitude et la latitude (la valeur de $g$ varie légèrement)."
            ),
            MCQ(
                "Période d'un pendule",
                "Pour un pendule simple aux petites oscillations :",
                [
                    {"text": "$T = 2\\pi\\sqrt{L/g}$", "correct": True, "feedback": "Exact !"},
                    {"text": "$T = 2\\pi\\sqrt{g/L}$", "correct": False, "feedback": "Tu as inversé."},
                    {"text": "$T = 2\\pi\\sqrt{m/g}$", "correct": False, "feedback": "La masse n'intervient pas."},
                    {"text": "$T = 2\\pi L/g$", "correct": False, "feedback": "Pas de racine carrée ?"}
                ],
                explanation="$T = 2\\pi\\sqrt{L/g}$."
            ),
            MCQ(
                "Grandes amplitudes",
                "Pour un pendule simple, si $\\theta_{max}$ augmente (en restant < 180°), "
                "la période réelle :",
                [
                    {"text": "Augmente", "correct": True, "feedback": "Exact ! Le pendule devient anharmonique."},
                    {"text": "Diminue", "correct": False, "feedback": "Non, c'est l'inverse."},
                    {"text": "Reste constante", "correct": False, "feedback": "Seulement aux petites oscillations."},
                    {"text": "Devient nulle", "correct": False, "feedback": "Évidemment non."}
                ],
                explanation="Aux grandes amplitudes, $T > T_0$ (le développement fait apparaître un terme en $\\theta_{max}^2$)."
            ),
            FB(
                "Compléter le pendule",
                "Équation : $\\ddot{\\theta} + \\dfrac{g}{L}{{blank_1}} = 0$. "
                "Aux petites oscillations : $T = 2\\pi\\sqrt{{{blank_2}}}$. "
                "Indépendant de la {{blank_3}}.",
                {"blank_1": ["\\sin\\theta", "sin(theta)", "sin\\theta"],
                 "blank_2": ["L/g", "L / g"], "blank_3": ["masse", "m"]},
                explanation="Équation $\\ddot\\theta+(g/L)\\sin\\theta=0$ ; $T=2\\pi\\sqrt{L/g}$ ; indépendante de $m$."
            ),
            TF(
                "Vrai ou Faux ? Pendule",
                [
                    {"statement": "Aux petites oscillations, $T$ ne dépend pas de $m$.",
                     "is_true": True},
                    {"statement": "Aux petites oscillations, $T$ ne dépend pas de $\\theta_{max}$.",
                     "is_true": True},
                    {"statement": "Aux grandes amplitudes, $T$ augmente.",
                     "is_true": True},
                    {"statement": "$\\sin\\theta \\approx \\theta$ pour $\\theta$ petit.",
                     "is_true": True},
                    {"statement": "Un pendule de $L=1$ m a une période d'environ 2 s sur Terre.",
                     "is_true": True}
                ]
            )
        ]},

        # -----------------------------------------------------------------
        # Lesson 4.3 — Oscillations amorties et forcées
        # -----------------------------------------------------------------
        {"order": 2, "title": "Oscillations amorties et forcées",
         "slug": "oscillations-amorties-forcees", "minutes": 35, "blocks": [
            T(
                "# Oscillations amorties et forcées\n\n"
                "## 1. Oscillation amortie\n\n"
                "Avec un frottement visqueux $-\\lambda \\dot{x}$, l'équation devient :\n"
                "$$m\\ddot{x} + \\lambda \\dot{x} + k x = 0 \\;\\Leftrightarrow\\; "
                "\\ddot{x} + 2\\gamma\\dot{x} + \\omega_0^2 x = 0$$\n\n"
                "avec $\\gamma = \\lambda/(2m)$ et $\\omega_0^2 = k/m$.\n\n"
                "## 2. Régimes\n\n"
                "- **Pseudo-périodique** ($\\gamma < \\omega_0$) : oscillations "
                "amorties exponentiellement :\n"
                "$$x(t) = X_0\\, e^{-\\gamma t}\\cos(\\Omega t + \\varphi), \\quad "
                "\\Omega = \\sqrt{\\omega_0^2 - \\gamma^2}$$\n"
                "- **Critique** ($\\gamma = \\omega_0$) : retour à l'équilibre le "
                "plus rapide sans oscillation.\n"
                "- **Apériodique** ($\\gamma > \\omega_0$) : retour exponentiel "
                "sans oscillation.\n\n"
                "## 3. Oscillation forcée et résonance\n\n"
                "On applique une force sinusoïdale $F_0\\cos(\\omega t)$ :\n"
                "$$\\ddot{x} + 2\\gamma\\dot{x} + \\omega_0^2 x = \\frac{F_0}{m}\\cos(\\omega t)$$\n\n"
                "En régime permanent : $x(t) = A(\\omega)\\cos(\\omega t - \\varphi)$ avec :\n"
                "$$A(\\omega) = \\frac{F_0/m}{\\sqrt{(\\omega_0^2 - \\omega^2)^2 + 4\\gamma^2 \\omega^2}}$$\n\n"
                "## 4. Résonance\n\n"
                "L'amplitude est maximale pour $\\omega_r \\approx \\omega_0$ (quand $\\gamma \\ll \\omega_0$).\n\n"
                "> 💡 **Astuce** : Le **régime critique** est utilisé dans les "
                "amortisseurs de voiture et les galvanomètres : il permet un retour "
                "à l'équilibre **sans oscillation** et **le plus rapidement possible**."
            ),
            S(
                "Trois régimes d'amortissement",
                "import matplotlib.pyplot as plt\n"
                "import numpy as np\n"
                "from scipy.integrate import odeint\n"
                "\n"
                "omega0 = 4.0\n"
                "t = np.linspace(0, 6, 1000)\n"
                "\n"
                "def osc(y, t, gamma):\n"
                "    x, v = y\n"
                "    return [v, -2*gamma*v - omega0**2 * x]\n"
                "\n"
                "fig, ax = plt.subplots(figsize=(9, 5))\n"
                "for gamma, lbl, col in [(0.5, 'Pseudo-périodique ($\\gamma < \\omega_0$)', 'b'),\n"
                "                        (4.0, 'Critique ($\\gamma = \\omega_0$)', 'r'),\n"
                "                        (8.0, 'Apériodique ($\\gamma > \\omega_0$)', 'g')]:\n"
                "    sol = odeint(osc, [1.0, 0], t, args=(gamma,))\n"
                "    ax.plot(t, sol[:,0], lw=2, color=col, label=lbl)\n"
                "ax.axhline(0, color='k', lw=0.5)\n"
                "ax.set_xlabel(r'$t$ [s]'); ax.set_ylabel(r'$x(t)$ [m]')\n"
                "ax.set_title(rf'Trois régimes damortissement ($\\omega_0={omega0}$ rad/s)')\n"
                "ax.legend(); ax.grid(True, alpha=0.3)\n"
                "plt.tight_layout(); plt.savefig('plot.png')\n"
                "print('Le regime critique revient a lequilibre le plus vite sans osciller.')\n"
            ),
            S(
                "Résonance : amplitude vs fréquence",
                "import matplotlib.pyplot as plt\n"
                "import numpy as np\n"
                "\n"
                "omega0 = 4.0\n"
                "F0_m = 1.0\n"
                "omega = np.linspace(0, 8, 500)\n"
                "\n"
                "fig, ax = plt.subplots(figsize=(9, 5))\n"
                "for gamma in [0.3, 0.8, 2.0]:\n"
                "    A = F0_m / np.sqrt((omega0**2 - omega**2)**2 + 4*gamma**2*omega**2)\n"
                "    ax.plot(omega, A, lw=2, label=r'$\\gamma=%.1f$' % gamma)\n"
                "ax.axvline(omega0, color='k', ls=':', label=r'$\\omega_0$')\n"
                "ax.set_xlabel(r'Pulsation excitatrice $\\omega$')\n"
                "ax.set_ylabel(r'Amplitude $A(\\omega)$')\n"
                "ax.set_title(r'Résonance : pic plus étroit quand $\\gamma$ diminue')\n"
                "ax.legend(); ax.grid(True, alpha=0.3)\n"
                "ax.set_ylim(0, 5)\n"
                "plt.tight_layout(); plt.savefig('plot.png')\n"
                "print('Plus gamma est petit, plus le pic de resonance est haut et étroit.')\n"
                "print(f'Pulsation propre : omega_0 = {omega0} rad/s')\n"
            ),
            APP(
                "Amortisseur critique d'une voiture",
                "Une roue de voiture de masse $m=300$ kg est suspendue à un ressort "
                "de raideur $k=12 000$ N/m. On veut un amortissement **critique** "
                "pour éviter les oscillations. (a) Calcule $\\omega_0$. (b) Quelle "
                "valeur de $\\lambda$ (coefficient de frottement visqueux) faut-il ? "
                "(c) Si l'amortisseur est usé et $\\lambda$ est divisé par 2, "
                "décris le comportement.",
                "**(a) Pulsation propre** :\n"
                "$$\\omega_0 = \\sqrt{\\frac{k}{m}} = \\sqrt{\\frac{12 000}{300}} = "
                "\\sqrt{40} \\approx 6{,}32\\;\\text{rad/s}.$$\n\n"
                "Période propre : $T_0 = 2\\pi/\\omega_0 \\approx 0{,}99$ s.\n\n"
                "**(b) Amortissement critique** : $\\gamma = \\omega_0$, et "
                "$\\gamma = \\lambda/(2m)$, donc :\n"
                "$$\\lambda_c = 2m\\, \\omega_0 = 2 \\times 300 \\times 6{,}32 \\approx "
                "3 795\\;\\text{N·s/m}.$$\n\n"
                "C'est la valeur idéale des amortisseurs pour ce réglage.\n\n"
                "**(c) Si $\\lambda = \\lambda_c/2$** : on a $\\gamma = \\omega_0/2 < \\omega_0$, "
                "donc le régime devient **pseudo-périodique**. La voiture va osciller "
                "après chaque bosse, avec une pseudo-pulsation :\n"
                "$$\\Omega = \\sqrt{\\omega_0^2 - \\gamma^2} = \\sqrt{40 - 10} = \\sqrt{30} "
                "\\approx 5{,}48\\;\\text{rad/s}.$$\n\n"
                "Le temps de relaxation est $\\tau = 1/\\gamma = 2/\\omega_0 \\approx 0{,}32$ s. "
                "La voiture va osciller significativement pendant ~1 s après chaque "
                "bosse, ce qui est inconfortable et dangereux."
            ),
            MCQ(
                "Régime critique",
                "Le régime critique correspond à :",
                [
                    {"text": "$\\gamma > \\omega_0$ (oscillations très amorties)", "correct": False, "feedback": "C'est le régime apériodique."},
                    {"text": "$\\gamma = \\omega_0$ (retour le plus rapide sans oscillation)", "correct": True, "feedback": "Exact !"},
                    {"text": "$\\gamma < \\omega_0$ (oscillations amorties)", "correct": False, "feedback": "C'est le régime pseudo-périodique."},
                    {"text": "$\\gamma = 0$ (oscillations perpétuelles)", "correct": False, "feedback": "Pas d'amortissement."}
                ],
                explanation="Régime critique : $\\gamma = \\omega_0$."
            ),
            MCQ(
                "Résonance",
                "L'amplitude d'un oscillateur forcé est maximale pour une pulsation "
                "d'excitation proche de :",
                [
                    {"text": "$\\omega_0$ (pulsation propre)", "correct": True, "feedback": "Exact !"},
                    {"text": "0", "correct": False, "feedback": "Non."},
                    {"text": "$\\gamma$ (coefficient d'amortissement)", "correct": False, "feedback": "Non."},
                    {"text": "$2\\omega_0$", "correct": False, "feedback": "Non."}
                ],
                explanation="Pour $\\gamma \\ll \\omega_0$, la résonance a lieu à $\\omega_r \\approx \\omega_0$."
            ),
            FB(
                "Compléter les oscillations amorties",
                "Équation : $\\ddot{x} + 2{{blank_1}}\\dot{x} + \\omega_0^2 x = 0$. "
                "Pseudo-pulsation : $\\Omega = \\sqrt{\\omega_0^2 - {{blank_2}}^2}$. "
                "Régime critique : $\\gamma = {{blank_3}}$.",
                {"blank_1": ["\\gamma", "gamma"], "blank_2": ["\\gamma", "gamma"],
                 "blank_3": ["\\omega_0", "omega_0"]},
                explanation="$2\\gamma\\dot x$ pour l'amortissement ; $\\Omega=\\sqrt{\\omega_0^2-\\gamma^2}$ ; "
                            "régime critique : $\\gamma=\\omega_0$."
            ),
            TF(
                "Vrai ou Faux ? Oscillations amorties",
                [
                    {"statement": "En régime pseudo-périodique, l'amplitude décroît exponentiellement.",
                     "is_true": True},
                    {"statement": "Le régime critique est le plus rapide pour revenir à l'équilibre.",
                     "is_true": True},
                    {"statement": "À la résonance, l'amplitude diverge toujours vers l'infini.",
                     "is_true": False, "statement_note": "Pas avec un amortissement non nul."},
                    {"statement": "Plus $\\gamma$ est petit, plus le pic de résonance est étroit.",
                     "is_true": True},
                    {"statement": "Le facteur de qualité $Q$ mesure la sélectivité de la résonance.",
                     "is_true": True}
                ]
            )
        ]},
    ]},


    # =====================================================================
    # MODULE 5 — GRAVITATION
    # =====================================================================
    {"order": 5, "title": "Gravitation universelle",
     "description": "Loi de Newton, champ gravitationnel, lois de Kepler, "
                    "orbites, satellites.",
     "lessons": [

        # -----------------------------------------------------------------
        # Lesson 5.1 — Loi de gravitation universelle
        # -----------------------------------------------------------------
        {"order": 0, "title": "Loi de gravitation universelle",
         "slug": "gravitation-universelle", "minutes": 35, "blocks": [
            T(
                "# Loi de gravitation universelle\n\n"
                "## 1. Énoncé (Newton, 1687)\n\n"
                "Deux masses ponctuelles $m_1$ et $m_2$ séparées d'une distance $r$ "
                "s'attirent avec une force :\n"
                "$$\\vec{F}_{1\\to 2} = -G\\, \\frac{m_1 m_2}{r^2}\\, \\vec{u}_{12}$$\n\n"
                "où $G \\approx 6{,}674\\times 10^{-11}$ N·m²/kg² est la **constante "
                "de gravitation universelle**.\n\n"
                "## 2. Champ gravitationnel\n\n"
                "Une masse $M$ crée un champ $\\vec{g}$ à la distance $r$ :\n"
                "$$\\vec{g}(r) = -\\frac{GM}{r^2}\\, \\vec{u}_r, \\quad "
                "|\\vec{g}| = \\frac{GM}{r^2}$$\n\n"
                "Une masse $m$ placée dans ce champ subit la force $\\vec{F} = m\\,\\vec{g}$.\n\n"
                "## 3. À la surface de la Terre\n\n"
                "$$g = \\frac{GM_T}{R_T^2} \\approx 9{,}81\\;\\text{m/s}^2$$\n\n"
                "avec $M_T \\approx 5{,}97\\times 10^{24}$ kg, $R_T \\approx 6 371$ km.\n\n"
                "## 4. Variation avec l'altitude\n\n"
                "À l'altitude $h$ :\n"
                "$$g(h) = \\frac{GM_T}{(R_T + h)^2} = g_0 \\left(\\frac{R_T}{R_T + h}\\right)^2$$\n\n"
                "## 5. Satellite en orbite circulaire\n\n"
                "Vitesse orbitale : $v = \\sqrt{GM/r}$\n\n"
                "Période (3ème loi de Kepler) : $T^2 = \\dfrac{4\\pi^2}{GM} r^3$\n\n"
                "> 💡 **Astuce** : La loi de gravitation explique **tout** : la "
                "chute des pommes, les marées, les orbites des planètes, le mouvement "
                "des galaxies… C'est l'une des plus grandes unifications de la physique."
            ),
            S(
                "Champ g vs altitude",
                "import matplotlib.pyplot as plt\n"
                "import numpy as np\n"
                "\n"
                "G = 6.674e-11\n"
                "MT = 5.97e24\n"
                "RT = 6.371e6\n"
                "g0 = G*MT/RT**2\n"
                "h = np.linspace(0, 5e6, 200)  # altitude de 0 a 5000 km\n"
                "g = G*MT/(RT+h)**2\n"
                "\n"
                "fig, ax = plt.subplots(figsize=(9, 5))\n"
                "ax.plot(h/1e3, g, 'b-', lw=2)\n"
                "ax.axhline(g0, color='r', ls='--', label=r'$g_0=9{,}81$ m/s$^2$ (sol)')\n"
                "ax.set_xlabel(r'Altitude $h$ [km]')\n"
                "ax.set_ylabel(r'$g(h)$ [m/s$^2$]')\n"
                "ax.set_title(r'Champ gravitationnel terrestre : $g(h)=g_0\\left(\\frac{R_T}{R_T+h}\\right)^2$')\n"
                "ax.legend(); ax.grid(True, alpha=0.3)\n"
                "plt.tight_layout(); plt.savefig('plot.png')\n"
                "print(f'g(0) = {g[0]:.3f} m/s^2')\n"
                "print(f'g(h=400km, ISS) = {G*MT/(RT+400e3)**2:.3f} m/s^2')\n"
                "print(f'g(h=2000km) = {G*MT/(RT+2000e3)**2:.3f} m/s^2')\n"
            ),
            APP(
                "Vitesse orbitale de l'ISS",
                "L'ISS orbite à $h=400$ km d'altitude. (a) Calcule le rayon de "
                "l'orbite, le champ gravitationnel à cette altitude, la vitesse "
                "orbitale et la période. (b) Compare la période à une journée "
                "terrestre (24 h).",
                "Données : $G = 6{,}674\\times 10^{-11}$ SI, $M_T = 5{,}97\\times 10^{24}$ kg, "
                "$R_T = 6{,}371\\times 10^6$ m.\n\n"
                "**Rayon orbital** : $r = R_T + h = 6{,}371\\times 10^6 + 4{,}00\\times 10^5 "
                "\\approx 6{,}77\\times 10^6$ m.\n\n"
                "**Champ gravitationnel** :\n"
                "$$g = \\frac{GM_T}{r^2} = \\frac{6{,}674\\times 10^{-11} \\times 5{,}97\\times 10^{24}}"
                "{(6{,}77\\times 10^6)^2} \\approx 8{,}68\\;\\text{m/s}^2.$$\n\n"
                "**Vitesse orbitale** : $g = v^2/r \\Rightarrow v = \\sqrt{gr}$\n"
                "$$v = \\sqrt{8{,}68 \\times 6{,}77\\times 10^6} \\approx 7 668\\;\\text{m/s} "
                "\\approx 27 600\\;\\text{km/h}.$$\n\n"
                "**Période** : $T = 2\\pi r / v$\n"
                "$$T = \\frac{2\\pi \\times 6{,}77\\times 10^6}{7 668} \\approx 5 550\\;\\text{s} "
                "\\approx 92{,}5\\;\\text{min}.$$\n\n"
                "L'ISS fait **environ 16 tours de la Terre par jour**. C'est "
                "pourquoi les astronautes voient 16 lever de soleil par 24 h !"
            ),
            MCQ(
                "Loi de gravitation",
                "La force gravitationnelle entre deux masses $m_1$ et $m_2$ distantes de $r$ vaut :",
                [
                    {"text": "$G\\, m_1 m_2 / r$", "correct": False, "feedback": "Ce serait en $1/r$, pas en $1/r^2$."},
                    {"text": "$G\\, m_1 m_2 / r^2$", "correct": True, "feedback": "Exact !"},
                    {"text": "$G\\, (m_1 + m_2) / r^2$", "correct": False, "feedback": "C'est le produit, pas la somme."},
                    {"text": "$G\\, m_1 m_2 r^2$", "correct": False, "feedback": "Mauvaise dépendance en $r$."}
                ],
                explanation="$F = G m_1 m_2 / r^2$."
            ),
            MCQ(
                "Champ gravitationnel à l'altitude h",
                "À l'altitude $h$, le champ $g(h)$ vaut :",
                [
                    {"text": "$g_0$", "correct": False, "feedback": "Non, il diminue avec l'altitude."},
                    {"text": "$g_0 (R_T/(R_T+h))$", "correct": False, "feedback": "Ce serait en $1/r$, pas $1/r^2$."},
                    {"text": "$g_0 (R_T/(R_T+h))^2$", "correct": True, "feedback": "Exact !"},
                    {"text": "0", "correct": False, "feedback": "Seulement à l'infini."}
                ],
                explanation="$g(h) = GM/(R_T+h)^2 = g_0 (R_T/(R_T+h))^2$."
            ),
            FB(
                "Formules de gravitation",
                "Force : $F = G \\, m_1 m_2 / {{blank_1}}$. "
                "Champ créé par $M$ à distance $r$ : $g = GM/{{blank_2}}$. "
                "Vitesse orbitale circulaire : $v = \\sqrt{{{blank_3}}}$.",
                {"blank_1": ["r^2", "r**2"], "blank_2": ["r^2", "r**2"],
                 "blank_3": ["GM/r", "GM/r", "\\frac{GM}{r}"]},
                explanation="$F$ en $1/r^2$, champ aussi, et $v=\\sqrt{GM/r}$."
            ),
            TF(
                "Vrai ou Faux ? Gravitation",
                [
                    {"statement": "$G \\approx 6{,}67\\times 10^{-11}$ SI.",
                     "is_true": True},
                    {"statement": "La force gravitationnelle est toujours attractive.",
                     "is_true": True},
                    {"statement": "$g$ diminue avec l'altitude.",
                     "is_true": True},
                    {"statement": "La Lune subit la gravité de la Terre mais ne l'exerce pas sur la Terre.",
                     "is_true": False, "statement_note": "Action-réaction : la Terre attire la Lune autant que la Lune attire la Terre."},
                    {"statement": "La période orbitale augmente avec le rayon de l'orbite.",
                     "is_true": True}
                ]
            )
        ]},

        # -----------------------------------------------------------------
        # Lesson 5.2 — Lois de Kepler
        # -----------------------------------------------------------------
        {"order": 1, "title": "Lois de Kepler", "slug": "lois-kepler",
         "minutes": 35, "blocks": [
            T(
                "# Les trois lois de Kepler\n\n"
                "Johannes Kepler (1571–1630) a énoncé trois lois empiriques "
                "(déduites des observations de Tycho Brahe) sur le mouvement des "
                "planètes autour du Soleil.\n\n"
                "## 1. Première loi (loi des orbites)\n\n"
                "**« Les planètes décrivent des ellipses dont le Soleil occupe l'un "
                "des foyers. »**\n\n"
                "Pour un cercle (cas particulier d'ellipse), le Soleil est au centre.\n\n"
                "## 2. Deuxième loi (loi des aires)\n\n"
                "**« Le rayon vecteur Soleil-planète balaie des aires égales en des "
                "temps égaux. »**\n\n"
                "Conséquence : la planète va **plus vite** près du Soleil (périhélie) "
                "que loin (aphélie). C'est la **conservation du moment cinétique**.\n\n"
                "## 3. Troisième loi (loi des périodes)\n\n"
                "**« Le carré de la période est proportionnel au cube du demi-grand axe. »**\n"
                "$$\\frac{T^2}{a^3} = \\frac{4\\pi^2}{GM}$$\n\n"
                "où $M$ est la masse de l'astre central.\n\n"
                "## 4. Vitesses au périhélie et à l'aphélie\n\n"
                "Pour une orbite elliptique d'excentricité $e$ :\n"
                "$$v_{per} = \\sqrt{\\frac{GM(1+e)}{a(1-e)}}, \\quad "
                "v_{aph} = \\sqrt{\\frac{GM(1-e)}{a(1+e)}}$$\n\n"
                "## 5. Application : satellites géostationnaires\n\n"
                "Pour être géostationnaire, il faut $T = 24$ h. On en déduit le "
                "rayon orbital :\n"
                "$$r_{geo} = \\left(\\frac{GMT^2}{4\\pi^2}\\right)^{1/3} \\approx 42 164\\;\\text{km}$$\n\n"
                "soit $h \\approx 35 786$ km d'altitude.\n\n"
                "> 💡 **Astuce** : La 3ème loi de Kepler permet de **peser les "
                "astres** ! En mesurant $T$ et $a$ d'un satellite, on remonte à la "
                "masse $M$ de l'astre central."
            ),
            S(
                "Orbite elliptique et loi des aires",
                "import matplotlib.pyplot as plt\n"
                "import numpy as np\n"
                "\n"
                "a = 1.0          # demi-grand axe (UA)\n"
                "e = 0.6          # excentricite\n"
                "b = a*np.sqrt(1-e**2)\n"
                "theta = np.linspace(0, 2*np.pi, 200)\n"
                "x = a*np.cos(theta) - a*e   # Soleil au foyer\n"
                "y = b*np.sin(theta)\n"
                "\n"
                "fig, ax = plt.subplots(figsize=(8, 6))\n"
                "ax.plot(x, y, 'b-', lw=2)\n"
                "ax.plot(0, 0, 'yo', ms=15)  # Soleil (foyer)\n"
                "ax.text(0.1, 0.1, 'Soleil', fontsize=11)\n"
                "# Aire balayee en temps egal : secteur a proximite du perihelie (rapide) et aphelie (lent)\n"
                "for t0 in [0, np.pi]:\n"
                "    theta1 = np.linspace(t0, t0+0.3, 30)\n"
                "    x1 = a*np.cos(theta1) - a*e\n"
                "    y1 = b*np.sin(theta1)\n"
                "    ax.fill_between(np.concatenate([[0], x1, [0]]), np.concatenate([[0], y1, [0]]), 0, color='red', alpha=0.3)\n"
                "ax.set_aspect('equal'); ax.grid(True, alpha=0.3)\n"
                "ax.set_xlabel(r'$x$ [UA]'); ax.set_ylabel(r'$y$ [UA]')\n"
                "ax.set_title(rf'Orbite elliptique ($a=1$, $e={e}$) et loi des aires')\n"
                "plt.tight_layout(); plt.savefig('plot.png')\n"
                "print(f'Perihelie : r = a(1-e) = {a*(1-e):.2f} UA')\n"
                "print(f'Aphelie : r = a(1+e) = {a*(1+e):.2f} UA')\n"
                "print('Les 2 secteurs rouges ont la MEME aire (balayee en des temps egaux).')\n"
            ),
            S(
                "3ème loi de Kepler : T² vs a³",
                "import matplotlib.pyplot as plt\n"
                "import numpy as np\n"
                "\n"
                "# Planetes du systeme solaire (a en UA, T en annees)\n"
                "planetes = ['Mercure', 'Venus', 'Terre', 'Mars', 'Jupiter', 'Saturne']\n"
                "a = np.array([0.387, 0.723, 1.000, 1.524, 5.203, 9.537])\n"
                "T = np.array([0.241, 0.615, 1.000, 1.881, 11.862, 29.457])\n"
                "\n"
                "fig, axes = plt.subplots(1, 2, figsize=(13, 5))\n"
                "axes[0].plot(a, T, 'bo', ms=8)\n"
                "for i, p in enumerate(planetes):\n"
                "    axes[0].annotate(p, (a[i], T[i]), fontsize=9, xytext=(5,5), textcoords='offset points')\n"
                "axes[0].set_xlabel(r'$a$ [UA]'); axes[0].set_ylabel(r'$T$ [annees]')\n"
                "axes[0].set_title(r'T vs a'); axes[0].grid(True, alpha=0.3)\n"
                "\n"
                "axes[1].plot(a**3, T**2, 'ro', ms=8)\n"
                "a_th = np.linspace(0, 10, 100)\n"
                "axes[1].plot(a_th**3, a_th**3, 'b--', lw=1, label=r'$T^2 = a^3$ (theorie)')\n"
                "for i, p in enumerate(planetes):\n"
                "    axes[1].annotate(p, (a[i]**3, T[i]**2), fontsize=9, xytext=(5,5), textcoords='offset points')\n"
                "axes[1].set_xlabel(r'$a^3$ [UA$^3$]'); axes[1].set_ylabel(r'$T^2$ [annees$^2$]')\n"
                "axes[1].set_title(r'3ème loi : $T^2/a^3 = 1$ (UA, annees)')\n"
                "axes[1].legend(); axes[1].grid(True, alpha=0.3)\n"
                "plt.tight_layout(); plt.savefig('plot.png')\n"
                "print('Dans les unites UA et annees : T^2/a^3 ~ 1 pour toutes les planetes.')\n"
                "print(f'Terre : T^2/a^3 = {1.0**2/1.0**3:.4f}')\n"
                "print(f'Jupiter : T^2/a^3 = {11.862**2/5.203**3:.4f}')\n"
            ),
            APP(
                "Satellite géostationnaire",
                "Calcule l'altitude à laquelle doit orbiter un satellite pour être "
                "**géostationnaire** (période $T = 24$ h, dans le plan équatorial, "
                "dans le sens de rotation de la Terre). On prend "
                "$GM_T = 3{,}986\\times 10^{14}$ m³/s².",
                "Un satellite géostationnaire a la même période que la rotation "
                "de la Terre : $T = 24$ h $= 86 400$ s.\n\n"
                "**3ème loi de Kepler** : $T^2 = \\dfrac{4\\pi^2}{GM_T} r^3$, soit :\n"
                "$$r = \\left(\\frac{GM_T T^2}{4\\pi^2}\\right)^{1/3}.$$\n\n"
                "**Application numérique** :\n"
                "$$r = \\left(\\frac{3{,}986\\times 10^{14} \\times 86 400^2}{4\\pi^2}\\right)^{1/3}$$\n"
                "$$= \\left(\\frac{3{,}986\\times 10^{14} \\times 7{,}46\\times 10^9}{39{,}48}\\right)^{1/3}$$\n"
                "$$\\approx \\left(7{,}54\\times 10^{22}\\right)^{1/3} \\approx 4{,}22\\times 10^7\\;\\text{m}.$$\n\n"
                "Soit $r \\approx 42 164$ km. **Altitude** :\n"
                "$$h = r - R_T = 42 164 - 6 371 \\approx 35 793\\;\\text{km}.$$\n\n"
                "**Vitesse orbitale** : $v = 2\\pi r / T = \\dfrac{2\\pi \\times 42 164\\,000}{86 400} "
                "\\approx 3 070$ m/s $\\approx 11 050$ km/h.\n\n"
                "Cette orbite géostationnaire est très utilisée pour les satellites "
                "de télécommunications (le satellite paraît immobile depuis le sol)."
            ),
            MCQ(
                "1ère loi de Kepler",
                "La 1ère loi de Kepler dit que les planètes décrivent :",
                [
                    {"text": "Des cercles dont le Soleil est au centre", "correct": False, "feedback": "C'est l'approximation circulaire, pas la loi générale."},
                    {"text": "Des ellipses dont le Soleil occupe un foyer", "correct": True, "feedback": "Exact !"},
                    {"text": "Des paraboles", "correct": False, "feedback": "Ce sont les comètes non périodiques."},
                    {"text": "Des spirales", "correct": False, "feedback": "Non."}
                ],
                explanation="Première loi : orbites elliptiques avec le Soleil à un foyer."
            ),
            MCQ(
                "3ème loi de Kepler",
                "La 3ème loi dit que $T^2/a^3$ est :",
                [
                    {"text": "Constant pour tous les satellites d'un même astre", "correct": True, "feedback": "Exact ! Constante $= 4\\pi^2/(GM)$."},
                    {"text": "Constant pour tout l'univers", "correct": False, "feedback": "Non, dépend de $M$ de l'astre central."},
                    {"text": "Nul", "correct": False, "feedback": "Non."},
                    {"text": "Égal à 1 (en unités SI)", "correct": False, "feedback": "Seulement dans les unités UA et années pour le Soleil."}
                ],
                explanation="$T^2/a^3 = 4\\pi^2/(GM)$, dépend de l'astre central."
            ),
            FB(
                "Compléter les lois de Kepler",
                "1ère loi : les orbites sont des {{blank_1}} dont le Soleil est un foyer. "
                "2ème loi : conservation du {{blank_2}} (loi des aires). "
                "3ème loi : $T^2/a^3 = 4\\pi^2/(G\\,{{blank_3}})$.",
                {"blank_1": ["ellipses", "ellipse"], "blank_2": ["moment cinétique", "moment cinetique"],
                 "blank_3": ["M", "M"]},
                explanation="Ellipses ; conservation du moment cinétique ; $M$ est la masse de l'astre central."
            ),
            TF(
                "Vrai ou Faux ? Kepler",
                [
                    {"statement": "La Terre va plus vite au périhélie qu'à l'aphélie.",
                     "is_true": True},
                    {"statement": "Les orbites réelles sont parfaitement circulaires.",
                     "is_true": False, "statement_note": "Elles sont elliptiques (excentricité faible pour les planètes)."},
                    {"statement": "La 3ème loi permet de déterminer la masse de l'astre central.",
                     "is_true": True},
                    {"statement": "Un satellite géostationnaire a une période de 24 h.",
                     "is_true": True},
                    {"statement": "La 2ème loi de Kepler découle de la conservation de l'énergie cinétique.",
                     "is_true": False, "statement_note": "C'est la conservation du moment cinétique."}
                ]
            )
        ]},
    ]},


    # =====================================================================
    # MODULE 6 — MÉCANIQUE AVANCÉE
    # =====================================================================
    {"order": 6, "title": "Mécanique avancée · Moment cinétique et Lagrange",
     "description": "Moment cinétique, rotation, conservation du moment "
                    "cinétique, introduction au formalisme de Lagrange.",
     "lessons": [

        # -----------------------------------------------------------------
        # Lesson 6.1 — Moment cinétique et rotation
        # -----------------------------------------------------------------
        {"order": 0, "title": "Moment cinétique et rotation",
         "slug": "moment-cinetique-rotation", "minutes": 35, "blocks": [
            T(
                "# Moment cinétique et rotation\n\n"
                "## 1. Moment cinétique d'un point matériel\n\n"
                "Le **moment cinétique** par rapport à un point $O$ est :\n"
                "$$\\vec{L}_O = \\vec{r} \\wedge \\vec{p} = m\\, (\\vec{r} \\wedge \\vec{v})$$\n\n"
                "C'est un vecteur axial, en kg·m²/s.\n\n"
                "## 2. Théorème du moment cinétique\n\n"
                "$$\\frac{d\\vec{L}_O}{dt} = \\sum \\vec{M}_O(\\vec{F}_{ext})$$\n\n"
                "où $\\vec{M}_O(\\vec{F}) = \\vec{r} \\wedge \\vec{F}$ est le **moment** "
                "de la force $\\vec{F}$ par rapport à $O$.\n\n"
                "## 3. Conservation du moment cinétique\n\n"
                "Si $\\sum \\vec{M}_O(\\vec{F}_{ext}) = \\vec{0}$, alors $\\vec{L}_O$ est "
                "**conservé**. C'est le principe du **patineur qui tourne** : en "
                "ramenant ses bras, il diminue son moment d'inertie $J$ et augmente "
                "donc sa vitesse angulaire $\\omega$ (car $L = J\\omega$ = cste).\n\n"
                "## 4. Solide en rotation autour d'un axe fixe\n\n"
                "$$L = J\\, \\omega, \\quad E_c = \\tfrac12 J\\omega^2$$\n\n"
                "où $J$ est le **moment d'inertie** par rapport à l'axe.\n\n"
                "## 5. Moments d'inertie usuels\n\n"
                "- Tige de longueur $L$ (centre) : $J = \\tfrac{1}{12} m L^2$ ;\n"
                "- Cercle/anneau mince (centre) : $J = m R^2$ ;\n"
                "- Disque plein (centre) : $J = \\tfrac{1}{2} m R^2$ ;\n"
                "- Sphère pleine (centre) : $J = \\tfrac{2}{5} m R^2$.\n\n"
                "> 💡 **Astuce** : Le théorème de Huygens permet de calculer $J$ "
                "par rapport à un axe parallèle : $J_{\\Delta} = J_G + m\\, d^2$ où $d$ "
                "est la distance entre les deux axes."
            ),
            S(
                "Patineuse : conservation de L",
                "import matplotlib.pyplot as plt\n"
                "import numpy as np\n"
                "\n"
                "# J1 = 2 kg.m^2 (bras etendus), J2 = 0.6 kg.m^2 (bras serres)\n"
                "J1, J2 = 2.0, 0.6\n"
                "omega1 = 2.0   # rad/s initial\n"
                "L = J1 * omega1  # conserve\n"
                "omega2 = L / J2\n"
                "\n"
                "t = np.linspace(0, 10, 500)\n"
                "omega = np.where(t < 5, omega1, omega1 + (omega2-omega1)*(t-5)/0.5)\n"
                "omega = np.where(t > 5.5, omega2, omega)\n"
                "J_t = np.where(t < 5, J1, np.where(t > 5.5, J2, J1 + (J2-J1)*(t-5)/0.5))\n"
                "L_t = J_t * omega\n"
                "\n"
                "fig, axes = plt.subplots(3, 1, figsize=(9, 9), sharex=True)\n"
                "axes[0].plot(t, J_t, 'b-', lw=2); axes[0].set_ylabel(r'$J$ [kg m$^2$]')\n"
                "axes[1].plot(t, omega, 'r-', lw=2); axes[1].set_ylabel(r'$\\omega$ [rad/s]')\n"
                "axes[2].plot(t, L_t, 'g-', lw=2); axes[2].set_ylabel(r'$L=J\\omega$ [kg m$^2$/s]')\n"
                "axes[2].set_xlabel(r'$t$ [s]')\n"
                "axes[0].axvline(5, color='k', ls=':', alpha=0.5); axes[1].axvline(5, color='k', ls=':', alpha=0.5)\n"
                "axes[2].axvline(5, color='k', ls=':', alpha=0.5)\n"
                "axes[0].set_title(r'Patineuse : $J$ diminue, $\\omega$ augmente, $L=J\\omega$ conservé')\n"
                "for ax in axes: ax.grid(True, alpha=0.3)\n"
                "plt.tight_layout(); plt.savefig('plot.png')\n"
                "print(f'Avant : J={J1}, omega={omega1}, L={L}')\n"
                "print(f'Apres : J={J2}, omega={omega2:.2f}, L={J2*omega2:.2f}')\n"
                "print(f'L conserve ! (a t=5 la patineuse ramene ses bras)')\n"
            ),
            APP(
                "Patineuse qui ramène ses bras",
                "Une patineuse tourne à $\\omega_1 = 2$ rad/s avec les bras écartés "
                "($J_1 = 2{,}0$ kg·m²). En ramenant les bras le long du corps, son "
                "moment d'inertie devient $J_2 = 0{,}6$ kg·m². "
                "(a) Calcule sa nouvelle vitesse angulaire $\\omega_2$. "
                "(b) Calcule les énergies cinétiques avant et après. "
                "(c) D'où vient l'énergie supplémentaire ?",
                "**(a) Conservation de $L$** (pas de moment extérieur selon l'axe "
                "vertical) :\n"
                "$$L = J_1 \\omega_1 = J_2 \\omega_2 \\;\\Rightarrow\\; "
                "\\omega_2 = \\omega_1 \\frac{J_1}{J_2} = 2 \\times \\frac{2{,}0}{0{,}6} "
                "\\approx 6{,}67\\;\\text{rad/s}.$$\n\n"
                "La vitesse angulaire est **multipliée par 3,33**.\n\n"
                "**(b) Énergies cinétiques** :\n"
                "$$E_{c,1} = \\tfrac12 J_1 \\omega_1^2 = \\tfrac12 \\times 2{,}0 \\times 4 = 4{,}0\\;\\text{J},$$\n"
                "$$E_{c,2} = \\tfrac12 J_2 \\omega_2^2 = \\tfrac12 \\times 0{,}6 \\times 6{,}67^2 \\approx 13{,}3\\;\\text{J}.$$\n\n"
                "L'énergie cinétique a **plus que triplé** !\n\n"
                "**(c) Origine de l'énergie** : La conservation de $L$ ne dit pas "
                "que $E_c$ se conserve. En ramenant ses bras, la patineuse fournit "
                "un **travail** (elle tire ses bras vers l'intérieur, contre la "
                "force centrifuge). Ce travail est converti en énergie cinétique "
                "de rotation. La différence $\\Delta E_c \\approx 9{,}3$ J provient "
                "du travail musculaire de la patineuse."
            ),
            MCQ(
                "Moment cinétique et patineuse",
                "Une patineuse ramène ses bras (son $J$ diminue). Sa vitesse angulaire :",
                [
                    {"text": "Diminue", "correct": False, "feedback": "C'est l'inverse."},
                    {"text": "Reste constante", "correct": False, "feedback": "Non, $L = J\\omega$ se conserve mais pas $\\omega$."},
                    {"text": "Augmente", "correct": True, "feedback": "Exact ! $\\omega = L/J$ augmente quand $J$ diminue."},
                    {"text": "S'annule", "correct": False, "feedback": "Non."}
                ],
                explanation="$L=J\\omega$ conservé $\\Rightarrow \\omega$ augmente quand $J$ diminue."
            ),
            MCQ(
                "Moment d'inertie d'un disque plein",
                "Le moment d'inertie d'un disque plein de masse $m$ et rayon $R$ "
                "autour de son axe est :",
                [
                    {"text": "$m R^2$", "correct": False, "feedback": "C'est un anneau mince."},
                    {"text": "$\\tfrac12 m R^2$", "correct": True, "feedback": "Exact !"},
                    {"text": "$\\tfrac12 m R$", "correct": False, "feedback": "Mauvaise dimension."},
                    {"text": "$\\tfrac{2}{5} m R^2$", "correct": False, "feedback": "C'est une sphère pleine."}
                ],
                explanation="Disque plein : $J = \\tfrac12 m R^2$."
            ),
            FB(
                "Compléter le moment cinétique",
                "Moment cinétique : $\\vec{L} = \\vec{r} \\wedge {{blank_1}}$. "
                "Solide en rotation : $L = J \\times {{blank_2}}$. "
                "Théorème : $\\dfrac{d\\vec{L}}{dt} = \\sum \\vec{{{blank_3}}}_O(\\vec{F}_{ext})$.",
                {"blank_1": ["\\vec{p}", "p", "m\\vec{v}"], "blank_2": ["\\omega", "omega"],
                 "blank_3": ["M", "moments"]},
                explanation="$\\vec{L}=\\vec{r}\\wedge\\vec{p}$ ; $L=J\\omega$ ; "
                            "théorème du moment cinétique avec les moments des forces."
            ),
            TF(
                "Vrai ou Faux ? Moment cinétique",
                [
                    {"statement": "Le moment cinétique se conserve si $\\sum\\vec{M}_{ext}=\\vec{0}$.",
                     "is_true": True},
                    {"statement": "Le patineur qui ramène ses bras augmente son $\\omega$.",
                     "is_true": True},
                    {"statement": "Pour une masse ponctuelle, $L = mrv$ (mouvement circulaire).",
                     "is_true": True},
                    {"statement": "Le moment d'inertie s'exprime en kg/m².",
                     "is_true": False, "statement_note": "En kg·m²."},
                    {"statement": "Le théorème de Huygens relie $J$ pour des axes parallèles.",
                     "is_true": True}
                ]
            )
        ]},

        # -----------------------------------------------------------------
        # Lesson 6.2 — Introduction à Lagrange
        # -----------------------------------------------------------------
        {"order": 1, "title": "Introduction au formalisme de Lagrange",
         "slug": "introduction-lagrange", "minutes": 40, "blocks": [
            T(
                "# Introduction au formalisme de Lagrange\n\n"
                "## 1. Pourquoi Lagrange ?\n\n"
                "Le formalisme newtonien (PFD) devient lourd pour les systèmes "
                "contraints (pendule, pendule double, perle sur cerceau…). "
                "Le **formalisme de Lagrange** (1788) reformule la mécanique à partir "
                "d'un **principe d'optimisation** (principe de moindre action) et "
                "fonctionne dans n'importe quel système de coordonnées.\n\n"
                "## 2. Coordonnées généralisées\n\n"
                "On choisit des variables $q_i$ (angles, positions…) qui décrivent "
                "complètement le système, en tenant compte des contraintes. "
                "Exemples :\n"
                "- pendule simple : $q = \\theta$ ;\n"
                "- pendule double : $q_1 = \\theta_1$, $q_2 = \\theta_2$ ;\n"
                "- perle sur cerceau : $q = \\theta$.\n\n"
                "## 3. Lagrangien\n\n"
                "$$\\mathcal{L}(q, \\dot{q}, t) = E_c(q, \\dot{q}, t) - E_p(q, t)$$\n\n"
                "Différence entre énergie cinétique et énergie potentielle.\n\n"
                "## 4. Équations d'Euler-Lagrange\n\n"
                "$$\\frac{d}{dt}\\left(\\frac{\\partial \\mathcal{L}}{\\partial \\dot{q}_i}\\right) "
                "- \\frac{\\partial \\mathcal{L}}{\\partial q_i} = 0$$\n\n"
                "## 5. Application : pendule simple\n\n"
                "Coordonnée $q=\\theta$. Énergies :\n"
                "$$E_c = \\tfrac12 m L^2 \\dot{\\theta}^2, \\quad E_p = mgL(1-\\cos\\theta)$$\n"
                "$$\\mathcal{L} = \\tfrac12 m L^2 \\dot{\\theta}^2 - mgL(1-\\cos\\theta)$$\n\n"
                "Euler-Lagrange redonne bien :\n"
                "$$\\ddot{\\theta} + \\frac{g}{L}\\sin\\theta = 0$$\n\n"
                "## 6. Pendule double — chaos\n\n"
                "Le pendule double (deux tiges articulées) est un système "
                "**chaotique** : il exhibe une sensibilité extrême aux conditions "
                "initiales. C'est l'exemple paradigmatique de la mécanique "
                "non-linéaire.\n\n"
                "> 💡 **Astuce** : Le formalisme lagrangien est à la base de toute "
                "la physique moderne : mécanique quantique, théorie des champs, "
                "relativité générale. Maîtriser Lagrange, c'est ouvrir la porte de "
                "la physique théorique."
            ),
            S(
                "Pendule double chaotique",
                "import matplotlib.pyplot as plt\n"
                "import numpy as np\n"
                "from scipy.integrate import odeint\n"
                "\n"
                "g = 9.81\n"
                "L1, L2 = 1.0, 1.0\n"
                "m1, m2 = 1.0, 1.0\n"
                "\n"
                "def double_pendule(y, t):\n"
                "    th1, om1, th2, om2 = y\n"
                "    delta = th1 - th2\n"
                "    den = 2*m1 + m2 - m2*np.cos(2*delta)\n"
                "    dth1 = om1\n"
                "    dth2 = om2\n"
                "    dom1 = (-g*(2*m1+m2)*np.sin(th1) - m2*g*np.sin(th1-2*th2)\n"
                "            - 2*np.sin(delta)*m2*(om2**2*L2 + om1**2*L1*np.cos(delta))) / (L1*den)\n"
                "    dom2 = (2*np.sin(delta)*(om1**2*L1*(m1+m2)\n"
                "            + g*(m1+m2)*np.cos(th1) + om2**2*L2*m2*np.cos(delta))) / (L2*den)\n"
                "    return [dth1, dom1, dth2, dom2]\n"
                "\n"
                "t = np.linspace(0, 10, 2000)\n"
                "y0 = [np.radians(120), 0, np.radians(-10), 0]\n"
                "sol = odeint(double_pendule, y0, t)\n"
                "th1, th2 = sol[:,0], sol[:,2]\n"
                "x1 = L1*np.sin(th1); y1 = -L1*np.cos(th1)\n"
                "x2 = x1 + L2*np.sin(th2); y2 = y1 - L2*np.cos(th2)\n"
                "\n"
                "fig, ax = plt.subplots(figsize=(7, 7))\n"
                "ax.plot(x2, y2, 'b-', lw=0.6, alpha=0.7)\n"
                "ax.plot([0, x1[0], x2[0]], [0, y1[0], y2[0]], 'k-o', lw=2, ms=6)\n"
                "ax.plot([0], [0], 'ko', ms=8)\n"
                "ax.set_aspect('equal'); ax.grid(True, alpha=0.3)\n"
                "ax.set_title('Trajectoire du 2ème pendule (chaotique)')\n"
                "ax.set_xlabel(r'$x$'); ax.set_ylabel(r'$y$')\n"
                "plt.tight_layout(); plt.savefig('plot.png')\n"
                "print('Trajectoire chaotique : ne se répète jamais (sensibilité aux CI)')\n"
                "print(f'Periode propre (small angle) du premier pendule : T = {2*np.pi*np.sqrt(L1/g):.2f} s')\n"
            ),
            APP(
                "Lagrangien du pendule simple",
                "Retrouve l'équation du mouvement du pendule simple à partir du "
                "formalisme de Lagrange. On note $\\theta$ l'angle avec la verticale, "
                "$L$ la longueur, $m$ la masse.",
                "**Étape 1 — Coordonnée généralisée** : $q = \\theta$.\n\n"
                "**Étape 2 — Position et vitesse de la masse** :\n"
                "$$x = L\\sin\\theta, \\quad z = -L\\cos\\theta$$\n"
                "$$\\dot{x} = L\\cos\\theta\\, \\dot{\\theta}, \\quad "
                "\\dot{z} = L\\sin\\theta\\, \\dot{\\theta}$$\n\n"
                "**Étape 3 — Énergies** :\n"
                "$$E_c = \\tfrac12 m (\\dot{x}^2 + \\dot{z}^2) = \\tfrac12 m L^2 \\dot{\\theta}^2 "
                "(\\cos^2\\theta + \\sin^2\\theta) = \\tfrac12 m L^2 \\dot{\\theta}^2.$$\n"
                "$$E_p = mgz = -mgL\\cos\\theta \\quad (\\text{en choisissant } E_p=0 \\text{ en } \\theta=\\pi/2).$$\n\n"
                "**Étape 4 — Lagrangien** :\n"
                "$$\\mathcal{L} = \\tfrac12 m L^2 \\dot{\\theta}^2 + mgL\\cos\\theta.$$\n\n"
                "**Étape 5 — Équation d'Euler-Lagrange** :\n"
                "$$\\frac{\\partial \\mathcal{L}}{\\partial \\dot{\\theta}} = m L^2 \\dot{\\theta}, "
                "\\quad \\frac{d}{dt}(\\cdot) = m L^2 \\ddot{\\theta}, \\quad "
                "\\frac{\\partial \\mathcal{L}}{\\partial \\theta} = -mgL\\sin\\theta.$$\n\n"
                "Donc :\n"
                "$$m L^2 \\ddot{\\theta} - (-mgL\\sin\\theta) = 0 \\;\\Leftrightarrow\\; "
                "\\boxed{\\ddot{\\theta} + \\frac{g}{L}\\sin\\theta = 0}.$$\n\n"
                "On retrouve bien l'équation du pendule simple. Aux petites "
                "oscillations, $\\sin\\theta \\approx \\theta$ donne l'oscillateur "
                "harmonique de pulsation $\\omega_0 = \\sqrt{g/L}$."
            ),
            MCQ(
                "Lagrangien",
                "Le lagrangien $\\mathcal{L}$ d'un système mécanique vaut :",
                [
                    {"text": "$E_c + E_p$", "correct": False, "feedback": "C'est l'énergie mécanique."},
                    {"text": "$E_c - E_p$", "correct": True, "feedback": "Exact !"},
                    {"text": "$E_c \\times E_p$", "correct": False, "feedback": "Pas un produit."},
                    {"text": "$E_p - E_c$", "correct": False, "feedback": "C'est l'opposé."}
                ],
                explanation="$\\mathcal{L} = E_c - E_p$."
            ),
            MCQ(
                "Équations d'Euler-Lagrange",
                "Les équations d'Euler-Lagrange s'écrivent :",
                [
                    {"text": "$\\frac{d}{dt}\\frac{\\partial \\mathcal{L}}{\\partial \\dot{q}} - \\frac{\\partial \\mathcal{L}}{\\partial q} = 0$", "correct": True, "feedback": "Exact !"},
                    {"text": "$\\frac{\\partial \\mathcal{L}}{\\partial q} = 0$", "correct": False, "feedback": "Il manque le terme en $\\dot{q}$."},
                    {"text": "$\\frac{d\\mathcal{L}}{dt} = 0$", "correct": False, "feedback": "Ce n'est pas la bonne équation."},
                    {"text": "$\\mathcal{L} = \\text{constante}$", "correct": False, "feedback": "Non, le lagrangien n'est pas constant en général."}
                ],
                explanation="Équation d'Euler-Lagrange : $\\frac{d}{dt}\\frac{\\partial\\mathcal{L}}{\\partial\\dot q} - \\frac{\\partial\\mathcal{L}}{\\partial q} = 0$."
            ),
            FB(
                "Compléter Lagrange",
                "Lagrangien : $\\mathcal{L} = E_c - {{blank_1}}$. "
                "Équation d'Euler-Lagrange : $\\dfrac{d}{dt}\\dfrac{\\partial \\mathcal{L}}{\\partial \\dot{q}} - \\dfrac{\\partial \\mathcal{L}}{\\partial {{blank_2}}} = 0$. "
                "Le pendule double est un exemple de système {{blank_3}}.",
                {"blank_1": ["E_p", "Ep"], "blank_2": ["q"], "blank_3": ["chaotique", "non-linéaire"]},
                explanation="$\\mathcal{L}=E_c-E_p$ ; dérivée par rapport à $q$ ; "
                            "le pendule double est chaotique."
            ),
            TF(
                "Vrai ou Faux ? Lagrange",
                [
                    {"statement": "Le formalisme de Lagrange fonctionne en coordonnées quelconques.",
                     "is_true": True},
                    {"statement": "Le lagrangien est $\\mathcal{L} = E_c - E_p$.",
                     "is_true": True},
                    {"statement": "Le pendule double est un système chaotique.",
                     "is_true": True},
                    {"statement": "Les équations d'Euler-Lagrange redonnent le PFD dans les cas simples.",
                     "is_true": True},
                    {"statement": "Le formalisme lagrangien n'est valable que pour les forces conservatives.",
                     "is_true": False, "statement_note": "Il peut être étendu aux forces non conservatives via les forces généralisées."}
                ]
            )
        ]},
    ]},

]  # end of COURSE_STRUCTURE
