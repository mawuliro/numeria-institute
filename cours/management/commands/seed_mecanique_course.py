"""
Management command: seed_mecanique_course
Creates a complete Classical Mechanics course with Python simulations.
All strings containing apostrophes use double quotes.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from cours.models import (Course, CourseModule, CourseLesson, LessonBlock,
    CodeExercise, MCQExercise, MCQChoice, FillBlankExercise, TrueFalseExercise)

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
            if d: self.stdout.write(self.style.WARNING(f"Deleted ({d} rows)."))
        course, created = Course.objects.get_or_create(slug=slug, defaults={
            "title": "Mecanique Classique · De Newton a Lagrange",
            "description": "Un cours complet de mecanique classique avec simulations Python interactives. Couvre la cinematique, la dynamique, l energie, les collisions, les oscillateurs et la gravitation.",
            "short_description": "Maitrise la mecanique: cinematique, forces, energie, collisions, oscillateurs, gravitation.",
            "category": "physique", "level": "debutant", "language": "fr",
            "price": 0, "is_free": True, "status": status, "estimated_hours": 40})
        if not created: self.stdout.write(self.style.WARNING("Course exists - updating."))
        for md in COURSE_STRUCTURE:
            mod = self._mod(course, md)
            for ld in md["lessons"]:
                les = self._les(course, mod, ld)
                self._blocks(les, ld["blocks"])
        self.stdout.write(self.style.SUCCESS(
            f"\n✓ Seeded: {course.title}\n  Modules: {CourseModule.objects.filter(course=course).count()}\n"
            f"  Lessons: {CourseLesson.objects.filter(course=course).count()}\n"
            f"  Blocks: {LessonBlock.objects.filter(course_lesson__course=course).count()}\n"))
    def _mod(self, course, d):
        m, _ = CourseModule.objects.get_or_create(course=course, title=d["title"],
            defaults={"description": d.get("description",""), "order": d["order"], "is_active": True})
        return m
    def _les(self, course, mod, d):
        s = d.get("slug") or d["title"].lower().replace(" ","-").replace("'","-")
        l, _ = CourseLesson.objects.get_or_create(course=course, module=mod, title=d["title"],
            defaults={"slug": s, "order": d["order"], "estimated_minutes": d.get("minutes",25),
                      "is_free_preview": True, "is_active": True})
        return l
    def _blocks(self, lesson, blocks):
        LessonBlock.objects.filter(course_lesson=lesson).delete()
        for i, bd in enumerate(blocks): self._blk(lesson, bd, i)
    def _blk(self, lesson, data, idx):
        t = data["type"]; b = LessonBlock(course_lesson=lesson, block_type=t, order=idx)
        if t == "text": b.text_content = data["content"]; b.save()
        elif t == "sandbox": b.sandbox_title = data.get("title","Simulation"); b.sandbox_initial_code = data.get("code",""); b.save()
        elif t == "mcq":
            ex = MCQExercise.objects.create(course_lesson=lesson, title=data["title"], question=data["question"],
                instructions=data.get("instructions",""), difficulty=data.get("difficulty","easy"), points=data.get("points",5),
                hint=data.get("hint",""), explanation=data.get("explanation",""), allow_multiple_correct=data.get("multiple",False), shuffle_choices=True)
            for i, c in enumerate(data["choices"]): MCQChoice.objects.create(exercise=ex, text=c["text"], is_correct=c["correct"], feedback=c.get("feedback",""), order=i)
            b.mcq_exercise = ex; b.save()
        elif t == "fill_blank":
            ex = FillBlankExercise.objects.create(course_lesson=lesson, title=data["title"], instructions=data.get("instructions",""),
                difficulty=data.get("difficulty","easy"), points=data.get("points",5), hint=data.get("hint",""), explanation=data.get("explanation",""),
                text_with_blanks=data["text_with_blanks"], answers=data["answers"], case_sensitive=False)
            b.fill_blank = ex; b.save()
        elif t == "true_false":
            ex = TrueFalseExercise.objects.create(course_lesson=lesson, title=data["title"], instructions=data.get("instructions",""),
                difficulty=data.get("difficulty","easy"), points=data.get("points",6), hint=data.get("hint",""), explanation=data.get("explanation",""),
                statements=data["statements"], points_per_statement=2)
            b.true_false = ex; b.save()

COURSE_STRUCTURE = [
    {"order":0, "title":"Cinematique · Decrire le mouvement", "description":"Position, vitesse, acceleration et types de mouvements.", "lessons":[
        {"order":0, "title":"Vecteurs et reperes", "slug":"vecteurs-reperes", "minutes":25, "blocks":[
            {"type":"text", "content":"# Vecteurs et reperes en physique\n\n## Qu'est-ce qu'un vecteur ?\n\nEn physique, un **vecteur** est une grandeur qui possede :\n- une **direction** (orientation dans l'espace)\n- un **sens** (vers ou on va)\n- une **norme** (la valeur numerique, en unites physiques)\n- un **point d'application**\n\nExemples de grandeurs vectorielles : la force $\\vec{F}$, la vitesse $\\vec{v}$, l'acceleration $\\vec{a}$, la position $\\vec{r}$.\n\n## Repere cartesien\n\nUn **repere** est un systeme d'axes qui permet de reperer un point dans l'espace. Le plus courant est le **repere cartesien** $(O, \\vec{i}, \\vec{j}, \\vec{k})$ :\n\n- $O$ : origine\n- $\\vec{i}$ : axe horizontal (x)\n- $\\vec{j}$ : axe vertical (y)\n- $\\vec{k}$ : axe profondeur (z)\n\nUn vecteur position s'ecrit : $$\\vec{r} = x\\,\\vec{i} + y\\,\\vec{j} + z\\,\\vec{k}$$\n\n## Norme d'un vecteur\n\nLa norme (longueur) d'un vecteur $\\vec{v} = (v_x, v_y, v_z)$ est :\n\n$$|\\vec{v}| = \\sqrt{v_x^2 + v_y^2 + v_z^2}$$\n\n## Operations sur les vecteurs\n\n### Addition\n$$\\vec{A} + \\vec{B} = (A_x + B_x,\\; A_y + B_y,\\; A_z + B_z)$$\n\n### Multiplication par un scalaire\n$$k \\cdot \\vec{A} = (kA_x,\\; kA_y,\\; kA_z)$$\n\n### Produit scalaire\n$$\\vec{A} \\cdot \\vec{B} = A_x B_x + A_y B_y + A_z B_z = |\\vec{A}||\\vec{B}|\\cos\\theta$$\n\n> 💡 **Astuce** : Le produit scalaire est nul si les vecteurs sont perpendiculaires ($\\theta = 90$°)."},
            {"type":"sandbox", "title":"Visualiser des vecteurs 2D avec matplotlib", "code":"import matplotlib.pyplot as plt\nimport numpy as np\n\nA = np.array([3, 1])\nB = np.array([1, 2])\nC = A + B\n\nfig, ax = plt.subplots(1, 1, figsize=(8, 6))\nax.quiver(0, 0, A[0], A[1], angles='xy', scale_units='xy', scale=1, color='blue', width=0.02, label='A = (3,1)')\nax.quiver(0, 0, B[0], B[1], angles='xy', scale_units='xy', scale=1, color='red', width=0.02, label='B = (1,2)')\nax.quiver(0, 0, C[0], C[1], angles='xy', scale_units='xy', scale=1, color='green', width=0.02, label='A+B = (4,3)')\n\nax.set_xlim(-1, 6)\nax.set_ylim(-1, 5)\nax.set_xlabel('x')\nax.set_ylabel('y')\nax.set_title('Vecteurs et leur somme')\nax.legend()\nax.grid(True)\nax.set_aspect('equal')\nplt.tight_layout()\nplt.savefig('plot.png')\nprint(f'|A| = {np.linalg.norm(A):.2f}')\nprint(f'|B| = {np.linalg.norm(B):.2f}')\nprint(f'|A+B| = {np.linalg.norm(C):.2f}')\nprint(f'A.B = {np.dot(A, B)}')\n"},
            {"type":"mcq", "title":"Norme d'un vecteur", "question":"Quelle est la norme du vecteur $\\vec{v} = (3, 4)$ ?", "explanation":"$|v| = \\sqrt{3^2 + 4^2} = \\sqrt{9+16} = \\sqrt{25} = 5$", "choices":[
                {"text":"7", "correct":False, "feedback":"3+4=7 mais ce n'est pas comme ca qu'on calcule une norme."},
                {"text":"5", "correct":True, "feedback":"Exact ! racine(9+16) = 5"},
                {"text":"25", "correct":False, "feedback":"C'est le carre de la norme, pas la norme."},
                {"text":"12", "correct":False, "feedback":"3x4=12 mais ce n'est pas la norme."}]},
            {"type":"true_false", "title":"Vrai ou Faux ? Vecteurs", "statements":[
                {"statement":"La vitesse est une grandeur vectorielle.", "is_true":True},
                {"statement":"La norme d'un vecteur peut etre negative.", "is_true":False},
                {"statement":"Si le produit scalaire de deux vecteurs est nul, ils sont perpendiculaires.", "is_true":True},
                {"statement":"La masse est une grandeur vectorielle.", "is_true":False}]},
        ]},
        {"order":1, "title":"Position, vitesse et acceleration", "slug":"position-vitesse-acceleration", "minutes":30, "blocks":[
            {"type":"text", "content":"# Position, vitesse et acceleration\n\n## Position\n\nLa **position** d'un objet est donnee par le vecteur position $\\vec{r}(t)$ qui depend du temps :\n\n$$\\vec{r}(t) = x(t)\\,\\vec{i} + y(t)\\,\\vec{j} + z(t)\\,\\vec{k}$$\n\n## Vitesse\n\nLa **vitesse** est la derivee de la position par rapport au temps :\n\n$$\\vec{v}(t) = \\frac{d\\vec{r}}{dt} = \\dot{\\vec{r}}$$\n\nLa **vitesse scalaire** (norme) est : $$v = |\\vec{v}| = \\sqrt{v_x^2 + v_y^2 + v_z^2}$$\n\n## Acceleration\n\nL'**acceleration** est la derivee de la vitesse (derivee seconde de la position) :\n\n$$\\vec{a}(t) = \\frac{d\\vec{v}}{dt} = \\frac{d^2\\vec{r}}{dt^2}$$\n\n## Cas particulier: MRUA\n\nPour un **Mouvement Rectiligne Uniformement Acceler** :\n\n$$x(t) = x_0 + v_0 t + \\frac{1}{2}at^2$$\n$$v(t) = v_0 + at$$\n\nou $x_0$ est la position initiale, $v_0$ la vitesse initiale, et $a$ l'acceleration constante."},
            {"type":"sandbox", "title":"Tracer position, vitesse et acceleration", "code":"import matplotlib.pyplot as plt\nimport numpy as np\n\nt = np.linspace(0, 10, 100)\nx0, v0, a = 0, 5, 2\n\nx = x0 + v0 * t + 0.5 * a * t**2\nv = v0 + a * t\nacc = np.full_like(t, a)\n\nfig, axes = plt.subplots(3, 1, figsize=(8, 10), sharex=True)\n\naxes[0].plot(t, x, 'b-', linewidth=2)\naxes[0].set_ylabel('Position x (m)')\naxes[0].set_title('MRUA: x(t) = x0 + v0*t + 0.5*a*t^2')\naxes[0].grid(True)\n\naxes[1].plot(t, v, 'r-', linewidth=2)\naxes[1].set_ylabel('Vitesse v (m/s)')\naxes[1].grid(True)\n\naxes[2].plot(t, acc, 'g-', linewidth=2)\naxes[2].set_ylabel('Acceleration a (m/s^2)')\naxes[2].set_xlabel('Temps t (s)')\naxes[2].grid(True)\n\nplt.tight_layout()\nplt.savefig('plot.png')\nprint(f'A t=10s: x={x[-1]:.1f}m, v={v[-1]:.1f}m/s, a={a}m/s^2')\n"},
            {"type":"mcq", "title":"Vitesse et derivee", "question":"La vitesse est la derivee de ___ par rapport au temps.", "explanation":"v = dr/dt - la vitesse est la derivee de la position.", "choices":[
                {"text":"L'acceleration", "correct":False},
                {"text":"La position", "correct":True, "feedback":"Exact ! v = dr/dt"},
                {"text":"La force", "correct":False},
                {"text":"L'energie", "correct":False}]},
            {"type":"fill_blank", "title":"Complete les equations du MRUA", "text_with_blanks":"x(t) = x0 + v0*t + {{blank_1}}*a*t^2\nv(t) = {{blank_2}} + a*t\nL'acceleration est la derivee de la {{blank_3}} par rapport au temps.", "answers":{"blank_1":["0.5","1/2"], "blank_2":["v0"], "blank_3":["vitesse","vitesse v"]}, "explanation":"0.5 pour le terme quadratique, v0 pour la vitesse initiale, la vitesse pour la derivee."},
            {"type":"true_false", "title":"Vrai ou Faux ? Cinematique", "statements":[
                {"statement":"L'acceleration est la derivee seconde de la position.", "is_true":True},
                {"statement":"La norme de la vitesse peut etre negative.", "is_true":False},
                {"statement":"Dans un MRUA, l'acceleration est constante.", "is_true":True},
                {"statement":"L'unite de l'acceleration est m/s.", "is_true":False}]},
        ]},
        {"order":2, "title":"Mouvement de projectile", "slug":"mouvement-projectile", "minutes":30, "blocks":[
            {"type":"text", "content":"# Mouvement de projectile\n\n## Equations du mouvement\n\nUn projectile lance avec une vitesse initiale $v_0$ a un angle $\\theta$ suit une **trajectoire parabolique** :\n\n$$x(t) = v_0 \\cos\\theta \\cdot t$$\n$$y(t) = v_0 \\sin\\theta \\cdot t - \\frac{1}{2}gt^2$$\n\nou $g = 9{,}81$ m/s².\n\n## Portee (distance horizontale maximale)\n$$R = \\frac{v_0^2 \\sin(2\\theta)}{g}$$\n\n> 💡 **Astuce** : La portee est maximale pour $\\theta = 45$°.\n\n## Hauteur maximale\n$$h_{max} = \\frac{v_0^2 \\sin^2\\theta}{2g}$$\n\n## Temps de vol\n$$t_{vol} = \\frac{2v_0 \\sin\\theta}{g}$$"},
            {"type":"sandbox", "title":"Simulation: tir parabolique", "code":"import matplotlib.pyplot as plt\nimport numpy as np\n\nv0 = 20\ntheta = 45\ng = 9.81\n\ntheta_rad = np.radians(theta)\nt_vol = 2 * v0 * np.sin(theta_rad) / g\nt = np.linspace(0, t_vol, 100)\n\nx = v0 * np.cos(theta_rad) * t\ny = v0 * np.sin(theta_rad) * t - 0.5 * g * t**2\n\nR = v0**2 * np.sin(2 * theta_rad) / g\nh_max = (v0 * np.sin(theta_rad))**2 / (2 * g)\n\nfig, ax = plt.subplots(figsize=(10, 5))\nax.plot(x, y, 'b-', linewidth=2, label=f'Trajectoire (theta={theta}deg)')\nax.plot(R, 0, 'ro', markersize=8, label=f'Portee R={R:.1f}m')\nax.plot(R/2, h_max, 'g^', markersize=10, label=f'Hauteur max={h_max:.1f}m')\nax.axhline(y=0, color='k', linewidth=0.5)\nax.set_xlabel('Distance x (m)')\nax.set_ylabel('Hauteur y (m)')\nax.set_title(f'Tir parabolique: v0={v0} m/s, theta={theta}deg')\nax.legend()\nax.grid(True)\nax.set_aspect('equal')\nplt.tight_layout()\nplt.savefig('plot.png')\nprint(f'Portee: {R:.2f} m')\nprint(f'Hauteur max: {h_max:.2f} m')\nprint(f'Temps de vol: {t_vol:.2f} s')\n"},
            {"type":"mcq", "title":"Portee maximale", "question":"Pour quel angle la portee d'un projectile est-elle maximale ?", "explanation":"R = v0^2 sin(2theta)/g est maximal quand sin(2theta)=1, donc theta=45 deg.", "choices":[
                {"text":"30 deg", "correct":False},
                {"text":"45 deg", "correct":True, "feedback":"Exact ! sin(2x45) = sin(90) = 1"},
                {"text":"60 deg", "correct":False},
                {"text":"90 deg", "correct":False, "feedback":"A 90 deg la portee est nulle (tir vertical)."}]},
            {"type":"true_false", "title":"Vrai ou Faux ? Projectiles", "statements":[
                {"statement":"La trajectoire d'un projectile est une parabole.", "is_true":True},
                {"statement":"L'acceleration horizontale d'un projectile est g.", "is_true":False},
                {"statement":"Le temps de vol depend de l'angle de tir.", "is_true":True},
                {"statement":"A 45 deg la portee est maximale.", "is_true":True}]},
        ]},
    ]},
    {"order":1, "title":"Dynamique · Les forces", "description":"Les lois de Newton et les forces qui regissent le mouvement.", "lessons":[
        {"order":0, "title":"Les trois lois de Newton", "slug":"lois-newton", "minutes":35, "blocks":[
            {"type":"text", "content":"# Les trois lois de Newton\n\n## Premiere loi · Principe d'inertie\n\n> Tout corps persevere dans son etat de repos ou de mouvement rectiligne uniforme si aucune force n'agit sur lui.\n\n$$\\sum \\vec{F} = \\vec{0} \\implies \\vec{v} = \\text{constante}$$\n\n## Deuxieme loi · Principe fondamental de la dynamique (PFD)\n\n> La somme des forces appliquees a un corps est egale au produit de sa masse par son acceleration.\n\n$$\\boxed{\\sum \\vec{F} = m\\,\\vec{a}}$$\n\nC'est l'equation la plus importante de la mecanique classique !\n\n## Troisieme loi · Action-reaction\n\n> A toute action, il existe une reaction egale et opposee.\n\n$$\\vec{F}_{A \\to B} = -\\vec{F}_{B \\to A}$$\n\n> 💡 **Astuce** : Les forces d'action et de reaction agissent sur des **corps differents**. Elles ne s'annulent donc pas sur un meme corps !"},
            {"type":"sandbox", "title":"Simulation: F=ma interactif", "code":"import matplotlib.pyplot as plt\nimport numpy as np\n\nm = 2.0\nF = 10.0\na = F / m\nv0 = 0\n\nt = np.linspace(0, 5, 100)\nv = v0 + a * t\nx = v0 * t + 0.5 * a * t**2\n\nfig, axes = plt.subplots(1, 2, figsize=(12, 5))\n\naxes[0].plot(t, v, 'b-', linewidth=2)\naxes[0].set_xlabel('Temps (s)')\naxes[0].set_ylabel('Vitesse (m/s)')\naxes[0].set_title(f'F={F}N, m={m}kg => a={a}m/s^2')\naxes[0].grid(True)\n\naxes[1].plot(t, x, 'r-', linewidth=2)\naxes[1].set_xlabel('Temps (s)')\naxes[1].set_ylabel('Position (m)')\naxes[1].set_title('Position x(t)')\naxes[1].grid(True)\n\nplt.tight_layout()\nplt.savefig('plot.png')\nprint(f'Force: {F} N')\nprint(f'Masse: {m} kg')\nprint(f'Acceleration: {a} m/s^2')\nprint(f'Vitesse a t=5s: {v[-1]:.1f} m/s')\n"},
            {"type":"mcq", "title":"Deuxieme loi de Newton", "question":"Si une force de 20 N s'applique sur une masse de 4 kg, quelle est l'acceleration ?", "explanation":"a = F/m = 20/4 = 5 m/s²", "choices":[
                {"text":"2 m/s²", "correct":False, "feedback":"4/20 ? Non, c'est F/m pas m/F."},
                {"text":"5 m/s²", "correct":True, "feedback":"Exact ! a = F/m = 20/4 = 5"},
                {"text":"16 m/s²", "correct":False, "feedback":"20x4 ? Non."},
                {"text":"80 m/s²", "correct":False}]},
            {"type":"fill_blank", "title":"Complete les lois de Newton", "text_with_blanks":"1ere loi: Si la somme des forces est nulle, la {{blank_1}} est constante.\n2eme loi: Somme des forces = masse x {{blank_2}}\n3eme loi: Action = -{{blank_3}}", "answers":{"blank_1":["vitesse","vitesse v"], "blank_2":["acceleration","acceleration a","a"], "blank_3":["reaction"]}, "explanation":"1ere: vitesse constante. 2eme: F=ma. 3eme: action=-reaction."},
            {"type":"true_false", "title":"Vrai ou Faux ? Lois de Newton", "statements":[
                {"statement":"La 1ere loi de Newton s'applique quand la somme des forces est nulle.", "is_true":True},
                {"statement":"Les forces d'action et de reaction s'annulent sur un meme corps.", "is_true":False},
                {"statement":"L'unite de force est le Newton (N).", "is_true":True},
                {"statement":"Si la masse double, l'acceleration double aussi (a force constante).", "is_true":False}]},
        ]},
        {"order":1, "title":"Forces usuelles et plan incline", "slug":"forces-plan-incline", "minutes":30, "blocks":[
            {"type":"text", "content":"# Forces usuelles et plan incline\n\n## Le poids\n\n$$\\vec{P} = m\\vec{g}$$\n\nou $g \\approx 9{,}81$ m/s² (sur Terre). Le poids est toujours dirige vers le bas.\n\n## Force de frottement\n\n$$\\vec{f} = -\\mu\\,|\\vec{N}|\\,\\hat{v}$$\n\nou $\\mu$ est le coefficient de frottement, $\\vec{N}$ la force normale.\n\n## Le plan incline\n\nSur un plan incline d'angle $\\alpha$, le poids se decompose en :\n\n- Composante parallele au plan : $mg\\sin\\alpha$ (fait glisser)\n- Composante perpendiculaire : $mg\\cos\\alpha$ (equilibree par la normale)\n\nL'acceleration (sans frottement) est :\n$$a = g\\sin\\alpha$$\n\nAvec frottement :\n$$a = g(\\sin\\alpha - \\mu\\cos\\alpha)$$\n\n> 💡 **Astuce** : L'angle critique ou l'objet commence a glisser est $\\tan\\alpha_c = \\mu$."},
            {"type":"sandbox", "title":"Simulation: bloc sur plan incline", "code":"import matplotlib.pyplot as plt\nimport numpy as np\n\nalpha = 30\ng = 9.81\nmu = 0.2\nm = 5\n\nalpha_rad = np.radians(alpha)\nP = m * g\nN = P * np.cos(alpha_rad)\nf_parallele = P * np.sin(alpha_rad)\nf_frottement = mu * N\na = g * (np.sin(alpha_rad) - mu * np.cos(alpha_rad))\n\nt = np.linspace(0, 3, 50)\nx = 0.5 * a * t**2\n\nfig, axes = plt.subplots(1, 2, figsize=(12, 5))\n\nlabels = ['Poids mg', 'Normale N', 'Parallele mg sin(a)', 'Frottement']\nvalues = [P, N, f_parallele, f_frottement]\ncolors = ['red', 'blue', 'green', 'orange']\naxes[0].barh(labels, values, color=colors)\naxes[0].set_xlabel('Force (N)')\naxes[0].set_title(f'Forces sur plan incline (alpha={alpha}deg, mu={mu})')\naxes[0].grid(True, axis='x')\n\naxes[1].plot(t, x, 'b-', linewidth=2)\naxes[1].set_xlabel('Temps (s)')\naxes[1].set_ylabel('Distance sur le plan (m)')\naxes[1].set_title(f'Position (a={a:.2f} m/s^2)')\naxes[1].grid(True)\n\nplt.tight_layout()\nplt.savefig('plot.png')\nprint(f'Poids: {P:.1f} N')\nprint(f'Normale: {N:.1f} N')\nprint(f'Acceleration: {a:.2f} m/s^2')\nprint(f'Distance a t=3s: {x[-1]:.2f} m')\n"},
            {"type":"mcq", "title":"Plan incline sans frottement", "question":"Sur un plan incline a 30 deg sans frottement, l'acceleration est :", "explanation":"a = g sin(alpha) = 9.81 x sin(30) = 9.81 x 0.5 = 4.905 m/s²", "choices":[
                {"text":"9.81 m/s²", "correct":False, "feedback":"C'est g, pas a. a = g sin(alpha)."},
                {"text":"4.9 m/s²", "correct":True, "feedback":"Exact ! g x sin(30) = 9.81 x 0.5"},
                {"text":"2.45 m/s²", "correct":False, "feedback":"C'est g x sin²(30), pas correct."},
                {"text":"0 m/s²", "correct":False, "feedback":"L'objet accelere sur un plan incline."}]},
            {"type":"true_false", "title":"Vrai ou Faux ? Forces", "statements":[
                {"statement":"Le poids est toujours dirige vers le bas.", "is_true":True},
                {"statement":"Sur un plan horizontal, la force normale vaut N = mg.", "is_true":True},
                {"statement":"Le frottement augmente l'acceleration sur un plan incline.", "is_true":False},
                {"statement":"L'angle critique de glissement verifie tan(alpha) = mu.", "is_true":True}]},
        ]},
    ]},
    {"order":2, "title":"Energie et travail", "description":"Travail, energie cinetique, energie potentielle et conservation.", "lessons":[
        {"order":0, "title":"Travail et energie cinetique", "slug":"travail-energie-cinetique", "minutes":30, "blocks":[
            {"type":"text", "content":"# Travail et energie cinetique\n\n## Travail d'une force\n\nLe **travail** d'une force $\\vec{F}$ sur un deplacement $\\vec{d}$ est :\n\n$$W = \\vec{F} \\cdot \\vec{d} = Fd\\cos\\theta$$\n\nou $\\theta$ est l'angle entre la force et le deplacement.\n\n## Energie cinetique\n\nL'**energie cinetique** d'un objet de masse $m$ allant a la vitesse $v$ :\n\n$$E_c = \\frac{1}{2}mv^2$$\n\n## Theoreme de l'energie cinetique\n\n> La variation d'energie cinetique est egale au travail des forces :\n\n$$\\Delta E_c = \\sum W$$\n\n$$\\frac{1}{2}mv_B^2 - \\frac{1}{2}mv_A^2 = \\sum W_{A \\to B}$$"},
            {"type":"sandbox", "title":"Energie cinetique vs vitesse", "code":"import matplotlib.pyplot as plt\nimport numpy as np\n\nm = 2\nv = np.linspace(0, 20, 100)\nEc = 0.5 * m * v**2\n\nfig, ax = plt.subplots(figsize=(8, 5))\nax.plot(v, Ec, 'b-', linewidth=2)\nax.set_xlabel('Vitesse v (m/s)')\nax.set_ylabel('Energie cinetique Ec (J)')\nax.set_title(f'Energie cinetique: Ec = 0.5*m*v^2 (m={m} kg)')\nax.grid(True)\nax.annotate(f'v=10 m/s => Ec={0.5*m*100:.0f} J', xy=(10, 0.5*m*100), xytext=(12, 200),\n            arrowprops=dict(arrowstyle='->', color='red'), fontsize=11, color='red')\nplt.tight_layout()\nplt.savefig('plot.png')\nprint(f'A v=10 m/s: Ec = {0.5*m*100:.0f} J')\nprint(f'A v=20 m/s: Ec = {0.5*m*400:.0f} J')\nprint(f'Rapport: Ec(20)/Ec(10) = {400/100:.1f}x (v double => Ec x4)')\n"},
            {"type":"mcq", "title":"Energie cinetique", "question":"Si la vitesse double, l'energie cinetique est multipliee par :", "explanation":"Ec = 0.5mv². Si v->2v, Ec->0.5m(2v)² = 4 x 0.5mv² = 4Ec", "choices":[
                {"text":"2", "correct":False},
                {"text":"4", "correct":True, "feedback":"Exact ! Ec proportionnelle a v²."},
                {"text":"8", "correct":False},
                {"text":"16", "correct":False}]},
            {"type":"fill_blank", "title":"Complete les formules", "text_with_blanks":"Travail: W = F x d x cos({{blank_1}})\nEnergie cinetique: Ec = {{blank_2}} x m x v^2\nTheoreme: Delta Ec = somme des {{blank_3}}", "answers":{"blank_1":["theta","angle"], "blank_2":["0.5","1/2"], "blank_3":["travaux","W","travaux W"]}, "explanation":"cos(theta) pour le travail, 0.5 pour Ec, somme des travaux pour le theoreme."},
            {"type":"true_false", "title":"Vrai ou Faux ? Energie", "statements":[
                {"statement":"Le travail d'une force perpendiculaire au deplacement est nul.", "is_true":True},
                {"statement":"L'energie cinetique est proportionnelle a la vitesse (pas v²).", "is_true":False},
                {"statement":"Le theoreme de l'energie cinetique lie Delta Ec au travail des forces.", "is_true":True},
                {"statement":"L'unite d'energie est le Joule (J).", "is_true":True}]},
        ]},
        {"order":1, "title":"Conservation de l'energie", "slug":"conservation-energie", "minutes":30, "blocks":[
            {"type":"text", "content":"# Conservation de l'energie\n\n## Energie potentielle de pesanteur\n\n$$E_p = mgh$$\n\nou $h$ est la hauteur par rapport a une reference.\n\n## Energie mecanique\n\nL'**energie mecanique** est la somme de l'energie cinetique et potentielle :\n\n$$E_m = E_c + E_p = \\frac{1}{2}mv^2 + mgh$$\n\n## Principe de conservation\n\n> En l'absence de frottements, l'energie mecanique se conserve :\n\n$$E_m = \\text{constante}$$\n\n## Application: chute libre\n\nUn objet tombant d'une hauteur $h$ sans vitesse initiale :\n- En haut : $E_c = 0$, $E_p = mgh$\n- En bas : $E_c = \\frac{1}{2}mv^2$, $E_p = 0$\n- Conservation : $\\frac{1}{2}mv^2 = mgh \\implies v = \\sqrt{2gh}$\n\n> 💡 **Astuce** : La vitesse a l'arrivee ne depend pas de la masse !"},
            {"type":"sandbox", "title":"Simulation: conservation d'energie (chute libre)", "code":"import matplotlib.pyplot as plt\nimport numpy as np\n\nm = 1.0\nh0 = 20\ng = 9.81\n\nt_chute = np.sqrt(2 * h0 / g)\nt = np.linspace(0, t_chute, 100)\n\nh = h0 - 0.5 * g * t**2\nv = g * t\n\nEc = 0.5 * m * v**2\nEp = m * g * h\nEm = Ec + Ep\n\nfig, axes = plt.subplots(1, 2, figsize=(12, 5))\n\naxes[0].plot(t, Ec, 'b-', linewidth=2, label='Ec (cinetique)')\naxes[0].plot(t, Ep, 'r-', linewidth=2, label='Ep (potentielle)')\naxes[0].plot(t, Em, 'g--', linewidth=2, label='Em (totale)')\naxes[0].set_xlabel('Temps (s)')\naxes[0].set_ylabel('Energie (J)')\naxes[0].set_title(\"Conservation de l'energie\")\naxes[0].legend()\naxes[0].grid(True)\n\naxes[1].plot(t, h, 'k-', linewidth=2)\naxes[1].set_xlabel('Temps (s)')\naxes[1].set_ylabel('Hauteur (m)')\naxes[1].set_title('Chute libre')\naxes[1].grid(True)\n\nplt.tight_layout()\nplt.savefig('plot.png')\nprint(f'Hauteur initiale: {h0} m')\nprint(f'Temps de chute: {t_chute:.2f} s')\nprint(f'Vitesse finale: {g*t_chute:.2f} m/s')\nprint(f'Energie mecanique: {m*g*h0:.1f} J (constant)')\n"},
            {"type":"mcq", "title":"Vitesse de chute", "question":"Un objet tombe de 20 m sans vitesse initiale. Quelle est sa vitesse finale ?", "explanation":"v = racine(2gh) = racine(2 x 9.81 x 20) = 19.8 m/s", "choices":[
                {"text":"9.9 m/s", "correct":False, "feedback":"v = racine(gh) ? Non, c'est racine(2gh)."},
                {"text":"19.8 m/s", "correct":True, "feedback":"Exact ! v = racine(2gh)"},
                {"text":"39.2 m/s", "correct":False, "feedback":"v = 2gh ? Non, c'est racine(2gh)."},
                {"text":"196 m/s", "correct":False}]},
            {"type":"true_false", "title":"Vrai ou Faux ? Conservation", "statements":[
                {"statement":"Sans frottement, l'energie mecanique se conserve.", "is_true":True},
                {"statement":"La vitesse de chute depend de la masse.", "is_true":False},
                {"statement":"L'energie potentielle diminue quand l'objet descend.", "is_true":True},
                {"statement":"Au point le plus bas, toute l'energie est potentielle.", "is_true":False}]},
        ]},
    ]},
    {"order":3, "title":"Collisions et quantite de mouvement", "description":"Impulsion, quantite de mouvement et types de collisions.", "lessons":[
        {"order":0, "title":"Quantite de mouvement et collisions", "slug":"quantite-mouvement-collisions", "minutes":35, "blocks":[
            {"type":"text", "content":"# Quantite de mouvement et collisions\n\n## Quantite de mouvement\n\nLa **quantite de mouvement** (ou impulsion) d'un objet de masse $m$ allant a la vitesse $\\vec{v}$ :\n\n$$\\vec{p} = m\\vec{v}$$\n\nUnite: kg·m/s\n\n## Conservation de la quantite de mouvement\n\n> En l'absence de forces exterieures, la quantite de mouvement totale se conserve :\n\n$$m_1\\vec{v}_{1i} + m_2\\vec{v}_{2i} = m_1\\vec{v}_{1f} + m_2\\vec{v}_{2f}$$\n\n## Types de collisions\n\n| Type | Energie cinetique | Quantite de mouvement |\n|------|------------------|----------------------|\n| **Elastique** | Conservee | Conservee |\n| **Inelastique** | Non conservee | Conservee |\n| **Parfaitement inelastique** | Perte maximale | Conservee (objets colles) |"},
            {"type":"sandbox", "title":"Simulation: collision elastique 1D", "code":"import matplotlib.pyplot as plt\nimport numpy as np\n\nm1, m2 = 2.0, 3.0\nv1i, v2i = 5.0, -2.0\n\nv1f = ((m1 - m2) * v1i + 2 * m2 * v2i) / (m1 + m2)\nv2f = (2 * m1 * v1i + (m2 - m1) * v2i) / (m1 + m2)\n\np_before = m1 * v1i + m2 * v2i\np_after = m1 * v1f + m2 * v2f\n\nEc_before = 0.5 * m1 * v1i**2 + 0.5 * m2 * v2i**2\nEc_after = 0.5 * m1 * v1f**2 + 0.5 * m2 * v2f**2\n\nfig, axes = plt.subplots(1, 2, figsize=(12, 5))\n\naxes[0].barh(['Objet 1', 'Objet 2'], [v1i, v2i], color=['blue', 'red'])\naxes[0].set_xlabel('Vitesse (m/s)')\naxes[0].set_title(f'AVANT collision\\np={p_before:.1f} kg.m/s, Ec={Ec_before:.1f} J')\naxes[0].grid(True, axis='x')\n\naxes[1].barh(['Objet 1', 'Objet 2'], [v1f, v2f], color=['blue', 'red'])\naxes[1].set_xlabel('Vitesse (m/s)')\naxes[1].set_title(f'APRES collision\\np={p_after:.1f} kg.m/s, Ec={Ec_after:.1f} J')\naxes[1].grid(True, axis='x')\n\nplt.tight_layout()\nplt.savefig('plot.png')\nprint(f'AVANT: v1={v1i} m/s, v2={v2i} m/s')\nprint(f'APRES: v1={v1f:.2f} m/s, v2={v2f:.2f} m/s')\nprint(f'Quantite de mouvement: {p_before:.1f} -> {p_after:.1f} (conservee)')\nprint(f'Energie cinetique: {Ec_before:.1f} -> {Ec_after:.1f} (conservee)')\n"},
            {"type":"mcq", "title":"Conservation", "question":"Qu'est-ce qui se conserve dans TOUTES les collisions ?", "explanation":"La quantite de mouvement se conserve toujours (sans forces exterieures).", "choices":[
                {"text":"L'energie cinetique", "correct":False, "feedback":"Pas dans les collisions inelastiques."},
                {"text":"La quantite de mouvement", "correct":True, "feedback":"Exact ! Toujours conservee."},
                {"text":"La vitesse", "correct":False},
                {"text":"La masse", "correct":False}]},
            {"type":"true_false", "title":"Vrai ou Faux ? Collisions", "statements":[
                {"statement":"Dans une collision elastique, l'energie cinetique est conservee.", "is_true":True},
                {"statement":"Dans une collision parfaitement inelastique, les objets restent colles.", "is_true":True},
                {"statement":"La quantite de mouvement ne se conserve que dans les collisions elastiques.", "is_true":False},
                {"statement":"L'unite de la quantite de mouvement est kg m/s.", "is_true":True}]},
        ]},
    ]},
    {"order":4, "title":"Mouvements particuliers", "description":"Oscillateurs, pendules et gravitation.", "lessons":[
        {"order":0, "title":"Oscillateur harmonique", "slug":"oscillateur-harmonique", "minutes":30, "blocks":[
            {"type":"text", "content":"# L'oscillateur harmonique\n\n## Le ressort\n\nUn ressort de constante de raideur $k$ exerce une force de rappel :\n\n$$\\vec{F} = -k\\vec{x}$$\n\n## Equation du mouvement\n\n$$m\\ddot{x} = -kx$$\n\n$$\\ddot{x} + \\omega^2 x = 0 \\quad \\text{ou} \\quad \\omega = \\sqrt{\\frac{k}{m}}$$\n\n## Solution\n\n$$x(t) = A\\cos(\\omega t + \\phi)$$\n\n## Periode et frequence\n\n$$T = \\frac{2\\pi}{\\omega} = 2\\pi\\sqrt{\\frac{m}{k}}$$\n\n$$f = \\frac{1}{T} = \\frac{1}{2\\pi}\\sqrt{\\frac{k}{m}}$$\n\n## Energie\n\n$$E = \\frac{1}{2}kA^2 = E_c + E_p = \\frac{1}{2}mv^2 + \\frac{1}{2}kx^2$$\n\n> 💡 **Astuce** : La periode ne depend pas de l'amplitude ! Un petit ou un grand mouvement ont la meme periode."},
            {"type":"sandbox", "title":"Simulation: oscillateur harmonique", "code":"import matplotlib.pyplot as plt\nimport numpy as np\n\nk = 10\nm = 1.0\nA = 0.5\nomega = np.sqrt(k / m)\nT = 2 * np.pi / omega\n\nt = np.linspace(0, 3*T, 300)\n\nx = A * np.cos(omega * t)\nv = -A * omega * np.sin(omega * t)\n\nEc = 0.5 * m * v**2\nEp = 0.5 * k * x**2\nEm = Ec + Ep\n\nfig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)\n\naxes[0].plot(t, x, 'b-', linewidth=2, label='Position x(t)')\naxes[0].plot(t, v, 'r-', linewidth=2, label='Vitesse v(t)')\naxes[0].set_ylabel('x (m), v (m/s)')\naxes[0].set_title(f'Oscillateur harmonique (k={k}N/m, m={m}kg, T={T:.2f}s)')\naxes[0].legend()\naxes[0].grid(True)\n\naxes[1].plot(t, Ec, 'b-', linewidth=2, label='Ec')\naxes[1].plot(t, Ep, 'r-', linewidth=2, label='Ep')\naxes[1].plot(t, Em, 'g--', linewidth=2, label='Em (total)')\naxes[1].set_xlabel('Temps (s)')\naxes[1].set_ylabel('Energie (J)')\naxes[1].legend()\naxes[1].grid(True)\n\nplt.tight_layout()\nplt.savefig('plot.png')\nprint(f'Pulsation: omega = {omega:.2f} rad/s')\nprint(f'Periode: T = {T:.2f} s')\nprint(f'Frequence: f = {1/T:.2f} Hz')\nprint(f'Energie totale: {0.5*k*A**2:.2f} J')\n"},
            {"type":"mcq", "title":"Periode du ressort", "question":"La periode d'un oscillateur harmonique depend de :", "explanation":"T = 2pi racine(m/k) - depend de m et k, pas de A.", "choices":[
                {"text":"L'amplitude A", "correct":False, "feedback":"Non ! La periode est independante de l'amplitude."},
                {"text":"La masse m et la raideur k", "correct":True, "feedback":"Exact ! T = 2pi racine(m/k)"},
                {"text":"Seulement la masse m", "correct":False},
                {"text":"Seulement la raideur k", "correct":False}]},
            {"type":"true_false", "title":"Vrai ou Faux ? Oscillateur", "statements":[
                {"statement":"La force de rappel d'un ressort est F = -kx.", "is_true":True},
                {"statement":"La periode augmente avec la raideur k.", "is_true":False},
                {"statement":"L'energie mecanique d'un oscillateur se conserve.", "is_true":True},
                {"statement":"La periode depend de l'amplitude.", "is_true":False}]},
        ]},
        {"order":1, "title":"Pendule simple", "slug":"pendule-simple", "minutes":30, "blocks":[
            {"type":"text", "content":"# Le pendule simple\n\n## Definition\n\nUn pendule simple est constitue d'une masse $m$ suspendue a un fil de longueur $\\ell$, oscillant sous l'effet de la gravite.\n\n## Equation du mouvement\n\nPour de petits angles ($\\theta < 15$ deg) :\n\n$$\\ddot{\\theta} + \\frac{g}{\\ell}\\theta = 0$$\n\n## Periode (petites oscillations)\n\n$$T = 2\\pi\\sqrt{\\frac{\\ell}{g}}$$\n\n> 💡 **Astuce** : La periode ne depend **pas** de la masse ni de l'amplitude (pour petits angles) !\n\n## Application: mesure de g\n\nEn mesurant $T$ et $\\ell$ :\n\n$$g = \\frac{4\\pi^2\\ell}{T^2}$$"},
            {"type":"sandbox", "title":"Simulation: pendule simple", "code":"import matplotlib.pyplot as plt\nimport numpy as np\n\nL = 1.0\ng = 9.81\ntheta0 = 0.3\nomega = np.sqrt(g / L)\nT = 2 * np.pi / omega\n\nt = np.linspace(0, 4*T, 400)\ntheta = theta0 * np.cos(omega * t)\n\nx = L * np.sin(theta)\ny = -L * np.cos(theta)\n\nfig, axes = plt.subplots(1, 2, figsize=(12, 5))\n\naxes[0].plot(t, np.degrees(theta), 'b-', linewidth=2)\naxes[0].set_xlabel('Temps (s)')\naxes[0].set_ylabel('Angle (degres)')\naxes[0].set_title(f'Pendule simple (L={L}m, T={T:.2f}s)')\naxes[0].grid(True)\n\naxes[1].plot(x, y, 'b-', linewidth=2)\naxes[1].plot(0, 0, 'ko', markersize=5)\naxes[1].plot(x[0], y[0], 'ro', markersize=10, label=f'theta0={np.degrees(theta0):.0f}deg')\naxes[1].set_xlabel('x (m)')\naxes[1].set_ylabel('y (m)')\naxes[1].set_title('Trajectoire du pendule')\naxes[1].set_aspect('equal')\naxes[1].legend()\naxes[1].grid(True)\n\nplt.tight_layout()\nplt.savefig('plot.png')\nprint(f'Longueur: {L} m')\nprint(f'Periode: {T:.3f} s')\nprint(f'Frequence: {1/T:.3f} Hz')\nprint(f'g mesure: {4*np.pi**2*L/T**2:.2f} m/s^2')\n"},
            {"type":"mcq", "title":"Periode du pendule", "question":"La periode d'un pendule simple depend de :", "explanation":"T = 2pi racine(L/g) - depend de la longueur et de g.", "choices":[
                {"text":"La masse m", "correct":False, "feedback":"Non ! La masse n'intervient pas."},
                {"text":"La longueur L et g", "correct":True, "feedback":"Exact ! T = 2pi racine(L/g)"},
                {"text":"L'amplitude", "correct":False, "feedback":"Pas pour les petits angles."},
                {"text":"La masse et l'amplitude", "correct":False}]},
            {"type":"fill_blank", "title":"Complete les formules du pendule", "text_with_blanks":"Periode: T = 2*pi*sqrt({{blank_1}}/g)\nLa periode ne depend pas de la {{blank_2}}\nPour mesurer g: g = 4*pi^2*{{blank_3}}/T^2", "answers":{"blank_1":["L","l","longueur"], "blank_2":["masse","masse m","m"], "blank_3":["L","l","longueur"]}, "explanation":"T = 2pi racine(L/g), independant de la masse, g = 4pi²L/T²."},
            {"type":"true_false", "title":"Vrai ou Faux ? Pendule", "statements":[
                {"statement":"La periode d'un pendule ne depend pas de sa masse.", "is_true":True},
                {"statement":"Un pendule plus long a une periode plus courte.", "is_true":False},
                {"statement":"L'approximation des petits angles est valable pour theta < 15 deg.", "is_true":True},
                {"statement":"On peut mesurer g avec un pendule.", "is_true":True}]},
        ]},
        {"order":2, "title":"Gravitation universelle", "slug":"gravitation-universelle", "minutes":30, "blocks":[
            {"type":"text", "content":"# Loi de la gravitation universelle\n\n## La loi de Newton\n\n> Deux corps de masses $m_1$ et $m_2$ separes d'une distance $r$ s'attirent avec une force :\n\n$$F = G\\frac{m_1 m_2}{r^2}$$\n\nou $G = 6{,}674 \\times 10^{-11}$ N·m²/kg² est la **constante de gravitation**.\n\n## Vitesse de liberation\n\n$$v_{lib} = \\sqrt{\\frac{2GM}{R}}$$\n\nPour la Terre : $v_{lib} \\approx 11{,}2$ km/s\n\n## Orbites circulaires\n\n$$v_{orbite} = \\sqrt{\\frac{GM}{r}}$$\n\n$$T_{orbite} = 2\\pi\\sqrt{\\frac{r^3}{GM}}$$\n\n> 💡 **Astuce** : C'est la **troisieme loi de Kepler** : $T^2 \\propto r^3$."},
            {"type":"sandbox", "title":"Simulation: orbites planetaires", "code":"import matplotlib.pyplot as plt\nimport numpy as np\n\nG = 6.674e-11\nM_terre = 5.972e24\nR_terre = 6.371e6\n\naltitudes = [400e3, 2000e3, 35786e3]\nlabels = ['ISS (400km)', 'GPS (2000km)', 'Geostat (35786km)']\ncolors = ['red', 'green', 'blue']\n\nfig, ax = plt.subplots(figsize=(8, 8))\n\ncercle = plt.Circle((0, 0), R_terre, color='cyan', label='Terre')\nax.add_patch(cercle)\n\nfor alt, label, color in zip(altitudes, labels, colors):\n    r = R_terre + alt\n    v = np.sqrt(G * M_terre / r)\n    T = 2 * np.pi * np.sqrt(r**3 / (G * M_terre))\n    theta = np.linspace(0, 2*np.pi, 100)\n    x = r * np.cos(theta)\n    y = r * np.sin(theta)\n    ax.plot(x, y, '-', color=color, linewidth=2, label=f'{label}\\nv={v/1000:.1f}km/s, T={T/3600:.1f}h')\n\nax.set_xlim(-5e7, 5e7)\nax.set_ylim(-5e7, 5e7)\nax.set_xlabel('x (m)')\nax.set_ylabel('y (m)')\nax.set_title('Orbites terrestres')\nax.set_aspect('equal')\nax.legend(loc='upper right')\nax.grid(True)\nplt.tight_layout()\nplt.savefig('plot.png')\nprint('Orbites terrestres:')\nfor alt, label in zip(altitudes, labels):\n    r = R_terre + alt\n    v = np.sqrt(G * M_terre / r)\n    T = 2 * np.pi * np.sqrt(r**3 / (G * M_terre))\n    print(f'  {label}: v={v:.0f} m/s, T={T/3600:.1f} h')\n"},
            {"type":"mcq", "title":"Loi de gravitation", "question":"La force gravitationnelle entre deux corps est proportionnelle a :", "explanation":"F = G m1 m2 / r² - proportionnelle au produit des masses, inversement proportionnelle a r².", "choices":[
                {"text":"1/r", "correct":False},
                {"text":"1/r²", "correct":True, "feedback":"Exact ! F proportionnelle a 1/r²"},
                {"text":"1/r³", "correct":False},
                {"text":"r²", "correct":False}]},
            {"type":"true_false", "title":"Vrai ou Faux ? Gravitation", "statements":[
                {"statement":"La constante G vaut environ 6.674e-11 N m²/kg².", "is_true":True},
                {"statement":"La vitesse de liberation de la Terre est d'environ 11.2 km/s.", "is_true":True},
                {"statement":"La troisieme loi de Kepler dit que T² proportionnel a r³.", "is_true":True},
                {"statement":"La force gravitationnelle augmente avec la distance.", "is_true":False}]},
        ]},
    ]},
    {"order":5, "title":"Mecanique avancee", "description":"Moment cinetique et introduction a Lagrange.", "lessons":[
        {"order":0, "title":"Moment cinetique et couple", "slug":"moment-cinetique", "minutes":30, "blocks":[
            {"type":"text", "content":"# Moment cinetique et couple\n\n## Moment cinetique\n\nLe **moment cinetique** d'une particule de quantite de mouvement $\\vec{p}$ par rapport a un point O :\n\n$$\\vec{L} = \\vec{r} \\times \\vec{p} = m(\\vec{r} \\times \\vec{v})$$\n\nPour un mouvement circulaire : $$L = mvr$$\n\n## Conservation du moment cinetique\n\n> En l'absence de couple exterieur, le moment cinetique se conserve :\n\n$$\\frac{d\\vec{L}}{dt} = \\vec{\\tau}_{ext}$$\n\nSi $\\vec{\\tau}_{ext} = 0$, alors $\\vec{L} = \\text{constante}$.\n\n## Couple (moment de force)\n\nLe **couple** exerce par une force $\\vec{F}$ par rapport a O :\n\n$$\\vec{\\tau} = \\vec{r} \\times \\vec{F}$$\n\n## Application: patineuse qui tourne\n\nQuand une patineuse rapproche ses bras, $r$ diminue. Puisque $L = mvr$ est constant, $v$ augmente : elle tourne plus vite !\n\n> 💡 C'est la conservation du moment cinetique, utilisee aussi par les etoiles qui s'effondrent en pulsars."},
            {"type":"mcq", "title":"Moment cinetique", "question":"Le moment cinetique L pour un mouvement circulaire est :", "explanation":"L = mvr pour un mouvement circulaire.", "choices":[
                {"text":"L = mvr", "correct":True, "feedback":"Exact !"},
                {"text":"L = mv/r", "correct":False},
                {"text":"L = m v² r", "correct":False},
                {"text":"L = mgr", "correct":False}]},
            {"type":"true_false", "title":"Vrai ou Faux ? Moment cinetique", "statements":[
                {"statement":"Le moment cinetique se conserve sans couple exterieur.", "is_true":True},
                {"statement":"Une patineuse qui rapproche ses bras tourne plus lentement.", "is_true":False},
                {"statement":"Le couple est le produit vectoriel r x F.", "is_true":True},
                {"statement":"L'unite du moment cinetique est kg m²/s.", "is_true":True}]},
        ]},
        {"order":1, "title":"Introduction aux equations de Lagrange", "slug":"lagrange-introduction", "minutes":30, "blocks":[
            {"type":"text", "content":"# Introduction aux equations de Lagrange\n\n## Pourquoi Lagrange ?\n\nLa mecanique de Newton ($\\vec{F} = m\\vec{a}$) fonctionne bien pour des systemes simples. Mais pour des systemes complexes (pendules doubles, systemes contraints), les equations de **Lagrange** sont beaucoup plus puissantes.\n\n## Le Lagrangien\n\nLe **Lagrangien** est defini par :\n\n$$\\mathcal{L} = E_c - E_p$$\n\n(energie cinetique moins energie potentielle)\n\n## Equation de Lagrange\n\nPour une coordonnee generalisee $q$ :\n\n$$\\frac{d}{dt}\\left(\\frac{\\partial \\mathcal{L}}{\\partial \\dot{q}}\\right) - \\frac{\\partial \\mathcal{L}}{\\partial q} = 0$$\n\n## Exemple: le pendule\n\nPour un pendule de longueur $\\ell$ :\n\n- $E_c = \\frac{1}{2}m\\ell^2\\dot{\\theta}^2$\n- $E_p = mg\\ell(1 - \\cos\\theta)$\n\nEn appliquant l'equation de Lagrange :\n\n$$\\ddot{\\theta} + \\frac{g}{\\ell}\\sin\\theta = 0$$\n\nOn retrouve l'equation du pendule ! 🎉\n\n## Avantages de Lagrange\n\n1. **Pas besoin de forces de contrainte** (le fil du pendule n'apparait pas)\n2. **Travaille avec n'importe quelles coordonnees** (pas seulement cartesienne)\n3. **Systematique** : on calcule L, on derive, on a l'equation\n4. **Generalisable** a la mecanique quantique et relativiste\n\n> 💡 **Astuce** : Lagrange = meme resultat que Newton, mais avec moins de travail pour les systemes complexes."},
            {"type":"mcq", "title":"Le Lagrangien", "question":"Comment definit-on le Lagrangien ?", "explanation":"L = Ec - Ep (energie cinetique moins energie potentielle).", "choices":[
                {"text":"L = Ec + Ep", "correct":False, "feedback":"Non, c'est Ec - Ep."},
                {"text":"L = Ec - Ep", "correct":True, "feedback":"Exact !"},
                {"text":"L = Ep - Ec", "correct":False},
                {"text":"L = Ec x Ep", "correct":False}]},
            {"type":"true_false", "title":"Vrai ou Faux ? Lagrange", "statements":[
                {"statement":"Le Lagrangien est L = Ec - Ep.", "is_true":True},
                {"statement":"Lagrange necessite de calculer les forces de contrainte.", "is_true":False},
                {"statement":"L'equation de Lagrange redonne les memes resultats que Newton.", "is_true":True},
                {"statement":"Les equations de Lagrange utilisent des coordonnees generalisees.", "is_true":True}]},
        ]},
    ]},
]
