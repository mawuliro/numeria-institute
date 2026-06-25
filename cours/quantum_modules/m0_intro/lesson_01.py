"""
Leçon 01 — Module 0 (Introduction et limites de la physique classique)
Titre : Échelles quantiques et nécessité d'une nouvelle physique

Première leçon du cours de Mécanique Quantique I (Numeria Institute).
Couvre les échelles de longueur / énergie / temps, les constantes
fondamentales (h, ℏ, c) et les limites de validité de la physique
classique (action S ≫ ℏ, vitesse v ≪ c).

RÈGLES D'ÉCHAPPEMENT respectées :
- Source Python : `\\\\hbar` (2 backslashes) → DB `\\hbar` → MathJax rend OK
- Matplotlib : raw strings r'...' pour les labels LaTeX
"""

from cours.quantum_modules.helpers import T, S, APP, MCQ, FB, TF

LESSON = {
    "order": 0,
    "title": "Échelles quantiques et nécessité d'une nouvelle physique",
    "slug": "echelles-quantiques",
    "minutes": 40,
    "blocks": [
        T("""# Échelles quantiques et nécessité d'une nouvelle physique

Jusqu'à la fin du XIXe siècle, la mécanique de Newton et l'électromagnétisme de Maxwell semblaient capables de décrire l'ensemble du monde physique : trajectoires des planètes, chutes des corps, propagation de la lumière, circuits électriques. Pourtant, dès qu'on sonde la matière à l'échelle de l'atome, ces théories échouent. Cette leçon identifie les ordres de grandeur qui rendent indispensable une **nouvelle physique** : la mécanique quantique. Nous commencerons par cartographier ces échelles fondamentales avant de préciser les limites de validité des théories classiques et les seuils à partir desquels une description quantique s'impose.

## Échelles de longueur

L'échelle atomique se mesure en **ångströms** (Å). Le rayon typique d'un atome est :

$$a_0 \\approx 1~\\text{Å} = 10^{-10}~\\text{m}$$

Plus profondément, le **noyau** de l'atome occupe une région cent mille fois plus petite, de l'ordre du **femtomètre** (fm), encore appelé *fermi* :

$$R_{\\text{noyau}} \\approx 1~\\text{à}~7~\\text{fm} = 10^{-15}~\\text{m}$$

Entre les deux s'étend un grand vide peuplé d'électrons. Cette hiérarchie d'échelles, qui couvre cinq ordres de grandeur, explique pourquoi une description purement continue de la matière ne suffit pas : la matière est essentiellement vide, et l'essentiel de la masse est concentré dans un noyau minuscule.

## Échelles d'énergie

Aux échelles atomiques, l'énergie se mesure en **électrons-volts** (eV), l'énergie acquise par un électron accéléré sous une différence de potentiel de 1 volt :

$$1~\\text{eV} = 1{,}602 \\times 10^{-19}~\\text{J}$$

L'énergie de liaison d'un électron dans un atome vaut typiquement quelques eV. Pour le noyau, les énergies de liaison par nucléon sont mille à un million de fois plus grandes : de l'ordre du **MeV** ($10^6$ eV). On retiendra :

- **atome** : $E \\sim 1~\\text{eV}$
- **noyau** : $E \\sim 1~\\text{MeV}$

## Échelles de temps

À toute énergie $E$ correspond un temps caractéristique $\\tau \\sim \\hbar / E$. Pour un atome ($E \\sim 1~\\text{eV}$), on obtient $\\tau \\sim 10^{-15}~\\text{s}$, soit une femtoseconde. Pour un noyau ($E \\sim 1~\\text{MeV}$), $\\tau \\sim 10^{-21}~\\text{s}$. Ces durées ultracourtes expliquent pourquoi les phénomènes quantiques échappent à l'observation directe.

## Constantes fondamentales

Trois constantes structurent la physique quantique :

- La **constante de Planck** : $h = 6{,}626 \\times 10^{-34}~\\text{J}\\cdot\\text{s}$
- La **constante de Planck réduite** : $\\hbar = \\dfrac{h}{2\\pi} \\approx 1{,}055 \\times 10^{-34}~\\text{J}\\cdot\\text{s}$
- La **vitesse de la lumière** : $c = 2{,}998 \\times 10^{8}~\\text{m/s}$

$\\hbar$ joue le rôle d'**étalon quantique d'action**. Toute grandeur ayant la dimension d'une action (énergie × temps, ou moment cinétique) se mesure en multiples de $\\hbar$.

## Limite de validité de la physique classique

Une théorie classique reste valable tant que l'**action** $S$ du système étudié est très grande devant $\\hbar$ :

$$S \\gg \\hbar \\quad \\text{(régime classique)}$$

Quand $S \\sim \\hbar$, les effets quantiques deviennent dominants : trajectoires floues, énergies discrètes, interférences. De même, lorsque la vitesse $v$ d'une particule devient comparable à $c$, il faut remplacer la mécanique newtonienne par la **relativité restreinte**. Enfin, à ces échelles, certaines **incertitudes** deviennent intrinsèques : on ne peut plus attribuer simultanément une position et une vitesse parfaitement définies à une particule. Cette idée, formalisée plus tard par Heisenberg, sera étudiée au Module 1.
"""),
        S(
            "Cartographier les échelles de longueur et d'énergie",
            """import matplotlib.pyplot as plt

fig, axes = plt.subplots(2, 1, figsize=(11, 6.5))

def draw_scale(ax, items, unit, title, ranges):
    \"\"\"Trace une ligne graduée logarithmique avec marqueurs annotés.\"\"\"
    for i, (name, val) in enumerate(items):
        ax.plot(val, 0, 'o', color='#2c3e50', markersize=11, zorder=3)
        offset = 0.55 if (i % 2 == 0) else -0.85
        va = 'bottom' if offset > 0 else 'top'
        val_str = f'{val:.0e}'
        ax.annotate(name + '\\n' + val_str + ' ' + unit,
                    xy=(val, 0), xytext=(val, offset),
                    ha='center', va=va, fontsize=9, color='#2c3e50',
                    arrowprops=dict(arrowstyle='-', color='#7f8c8d', lw=0.8))
    ax.set_xscale('log')
    ax.set_ylim(-1.6, 1.6)
    ax.set_yticks([])
    ax.set_title(title, fontsize=12, fontweight='bold', pad=10)
    for (lo, hi, color, label) in ranges:
        ax.axvspan(lo, hi, alpha=0.15, color=color, label=label)
    ax.legend(loc='upper left', fontsize=9, framealpha=0.9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.tick_params(axis='x', labelsize=9)

# --- Échelle de longueur (m) ---
items_l = [
    ('Humain', 1e0),
    ('Cheveu', 1e-4),
    ('Cellule', 1e-6),
    ('Atome (1 Å)', 1e-10),
    ('Noyau (1 fm)', 1e-15),
]
draw_scale(axes[0], items_l, 'm',
           'Échelles de longueur (échelle log)',
           [(1e-11, 1e-9, 'orange', 'Atome'),
            (1e-16, 1e-14, 'red', 'Noyau')])
axes[0].set_xlim(1e-16, 1e1)
axes[0].set_xlabel(r'Longueur (m)', fontsize=11)

# --- Échelle d'énergie (eV) ---
items_e = [
    ('Photon visible', 2.5),
    ('Liaison atome', 1.0),
    ('Ionisation H', 13.6),
    ('Masse électron', 0.511e6),
    ('Liaison noyau', 8e6),
]
draw_scale(axes[1], items_e, 'eV',
           "Échelles d'énergie (échelle log)",
           [(0.5, 50, 'orange', 'Atome (eV)'),
            (1e5, 1e7, 'red', 'Noyau (MeV)')])
axes[1].set_xlim(1e-1, 1e8)
axes[1].set_xlabel(r'Énergie (eV)', fontsize=11)

plt.tight_layout()
plt.savefig('plot.png', dpi=100, bbox_inches='tight')
plt.close()
""",
        ),
        APP(
            "Énergie d'un électron dans un atome",
            "On considère un électron lié dans un atome d'hydrogène, dont la taille caractéristique est $a_0 \\approx 1~\\text{Å} = 10^{-10}~\\text{m}$. En utilisant l'idée intuitive qu'une particule confinée dans une région de taille $\\Delta x$ possède une quantité de mouvement minimale $\\Delta p \\sim \\hbar / \\Delta x$, estimer l'ordre de grandeur de son énergie cinétique $E_c$. On donne $m_e = 9{,}11 \\times 10^{-31}~\\text{kg}$ et $\\hbar = 1{,}055 \\times 10^{-34}~\\text{J}\\cdot\\text{s}$. Comparer au résultat expérimental $E_{\\text{ion}} \\approx 13{,}6~\\text{eV}$.",
            "1. **Quantité de mouvement minimale** : $\\Delta p \\sim \\dfrac{\\hbar}{a_0} = \\dfrac{1{,}055 \\times 10^{-34}}{10^{-10}} \\approx 10^{-24}~\\text{kg}\\cdot\\text{m/s}$.\n\n2. **Énergie cinétique** (non relativiste) : $E_c \\sim \\dfrac{(\\Delta p)^2}{2 m_e}$.\n\n3. **Numériquement** : $E_c \\approx \\dfrac{(10^{-24})^2}{2 \\times 9{,}11 \\times 10^{-31}} \\approx \\dfrac{10^{-48}}{1{,}8 \\times 10^{-30}} \\approx 6 \\times 10^{-19}~\\text{J}$.\n\n4. **Conversion en eV** : $E_c \\approx \\dfrac{6 \\times 10^{-19}}{1{,}6 \\times 10^{-19}} \\approx 4~\\text{eV}$.\n\n5. **Conclusion** : l'ordre de grandeur (quelques eV) est correct. La valeur exacte $13{,}6~\\text{eV}$ sera établie au Module 5 avec le traitement rigoureux de l'atome d'hydrogène ; le facteur $\\sim 3$ provient ici de l'estimation grossière $\\Delta p \\sim \\hbar/a_0$. Un électron atomique a donc typiquement une énergie de quelques eV, en accord avec l'échelle annoncée dans la leçon.",
        ),
        MCQ(
            "Ordres de grandeur",
            "Le rayon d'un noyau atomique est de l'ordre de :",
            [
                {"text": "1 nm = $10^{-9}$ m", "correct": False, "feedback": "Trop grand — c'est l'échelle des molécules et des nanostructures."},
                {"text": "1 Å = $10^{-10}$ m", "correct": False, "feedback": "C'est l'échelle de l'atome entier, pas du noyau."},
                {"text": "1 pm = $10^{-12}$ m", "correct": False, "feedback": "Encore trop grand — le noyau est bien plus petit."},
                {"text": "1 fm = $10^{-15}$ m", "correct": True, "feedback": "Exact ! Le noyau est environ $10^5$ fois plus petit que l'atome."},
            ],
            explanation="Le noyau atomique mesure environ 1 à 7 fm (femtomètres ou fermis), soit $10^{-15}$ m. L'atome complet, avec son cortège électronique, mesure ~1 Å = $10^{-10}$ m : le rapport est de $10^5$.",
        ),
        FB(
            "Constantes et échelles",
            "La constante de Planck vaut $h \\approx {{blank_1}} \\times 10^{-34}~\\text{J}\\cdot\\text{s}$, et la constante réduite $\\hbar = h/(2\\pi) \\approx {{blank_2}} \\times 10^{-34}~\\text{J}\\cdot\\text{s}$. À l'échelle atomique, les énergies se mesurent en {{blank_3}} (symbole eV), soit $1{,}602 \\times 10^{-19}~\\text{J}$.",
            {
                "blank_1": ["6.626", "6,626", "6,6"],
                "blank_2": ["1.055", "1,055", "1,05"],
                "blank_3": ["électrons-volts", "électron-volt", "electron-volts", "eV"],
            },
            explanation="$h \\approx 6{,}626 \\times 10^{-34}~\\text{J}\\cdot\\text{s}$ ; $\\hbar \\approx 1{,}055 \\times 10^{-34}~\\text{J}\\cdot\\text{s}$ ; l'unité d'énergie atomique est l'électron-volt (eV), qui vaut $1{,}602 \\times 10^{-19}$ J.",
        ),
        TF(
            "Limites de la physique classique",
            [
                {"statement": "La mécanique newtonienne reste valable tant que l'action $S$ du système est très grande devant $\\hbar$.", "is_true": True},
                {"statement": "Le noyau atomique est environ 10 fois plus petit que l'atome entier.", "is_true": False},
                {"statement": "$\\hbar = h/(2\\pi)$ est la constante de Planck réduite.", "is_true": True},
                {"statement": "L'énergie de liaison d'un électron dans un atome vaut typiquement quelques MeV.", "is_true": False},
                {"statement": "Lorsque la vitesse d'une particule devient comparable à $c$, la mécanique classique doit être remplacée par la relativité restreinte.", "is_true": True},
            ],
            explanation="L'écart entre l'atome (~1 Å) et le noyau (~1 fm) est de 5 ordres de grandeur, soit un facteur $10^5$ (et non 10). Les énergies atomiques sont de l'ordre de l'eV, pas du MeV (qui est l'échelle nucléaire). Le régime classique suppose $S \\gg \\hbar$, et le régime relativiste suppose $v \\ll c$.",
        ),
    ],
}
