"""
Management command: seed_latex_course

Creates a complete LaTeX typesetting course from beginner to advanced.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from cours.models import (
    Course, CourseModule, CourseLesson,
    LessonBlock,
    CodeExercise, MCQExercise, MCQChoice,
    FillBlankExercise, TrueFalseExercise,
)


class Command(BaseCommand):
    help = 'Seed a complete LaTeX course.'

    def add_arguments(self, parser):
        parser.add_argument('--draft', action='store_true')
        parser.add_argument('--clean', action='store_true')

    @transaction.atomic
    def handle(self, *args, **options):
        slug = 'latex-typographie-scientifique'
        status = 'draft' if options['draft'] else 'published'

        if options['clean']:
            deleted, _ = Course.objects.filter(slug=slug).delete()
            if deleted:
                self.stdout.write(self.style.WARNING(f'Deleted existing course ({deleted} rows).'))

        course, created = Course.objects.get_or_create(
            slug=slug,
            defaults={
                'title': "LaTeX : Typographie Scientifique",
                'description': (
                    "Un cours complet sur LaTeX, du débutant à l'avancé. "
                    "Apprends à rédiger des documents scientifiques impeccables : "
                    "rapports, articles, présentations, formules mathématiques."
                ),
                'short_description': "Maîtrise LaTeX : documents, mathématiques, tableaux, figures, présentations Beamer.",
                'category': 'informatique',
                'level': 'debutant',
                'language': 'fr',
                'price': 0,
                'is_free': True,
                'status': status,
                'estimated_hours': 30,
            },
        )
        if not created:
            self.stdout.write(self.style.WARNING(f'Course "{course.title}" already exists — updating.'))

        for module_data in COURSE_STRUCTURE:
            module = self.upsert_module(course, module_data)
            for lesson_data in module_data['lessons']:
                lesson = self.upsert_lesson(course, module, lesson_data)
                self.upsert_blocks(lesson, lesson_data['blocks'])

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Course seeded: {course.title}\n'
            f'  Modules: {CourseModule.objects.filter(course=course).count()}\n'
            f'  Lessons: {CourseLesson.objects.filter(course=course).count()}\n'
            f'  Blocks:  {LessonBlock.objects.filter(course_lesson__course=course).count()}\n'
        ))

    def upsert_module(self, course, data):
        module, _ = CourseModule.objects.get_or_create(
            course=course, title=data['title'],
            defaults={'description': data.get('description', ''), 'order': data['order'], 'is_active': True},
        )
        return module

    def upsert_lesson(self, course, module, data):
        s = data.get('slug') or data['title'].lower().replace(' ', '-').replace("'", '-')
        lesson, _ = CourseLesson.objects.get_or_create(
            course=course, module=module, title=data['title'],
            defaults={'slug': s, 'order': data['order'], 'estimated_minutes': data.get('minutes', 25),
                      'is_free_preview': data.get('free_preview', True), 'is_active': True},
        )
        return lesson

    def upsert_blocks(self, lesson, blocks_data):
        LessonBlock.objects.filter(course_lesson=lesson).delete()
        for idx, block_data in enumerate(blocks_data):
            self.create_block(lesson, block_data, idx)

    def create_block(self, lesson, data, idx):
        btype = data['type']
        block = LessonBlock(course_lesson=lesson, block_type=btype, order=idx)
        if btype == 'text':
            block.text_content = data['content']
            block.save()
        elif btype == 'sandbox':
            block.sandbox_title = data.get('title', 'Essaie toi-même')
            block.sandbox_initial_code = data.get('code', '# Code LaTeX\n')
            block.save()
        elif btype == 'mcq':
            ex = MCQExercise.objects.create(
                course_lesson=lesson, title=data['title'], question=data['question'],
                instructions=data.get('instructions', ''), difficulty=data.get('difficulty', 'easy'),
                points=data.get('points', 5), hint=data.get('hint', ''),
                explanation=data.get('explanation', ''), order=data.get('order', 0),
                allow_multiple_correct=data.get('multiple', False), shuffle_choices=True,
            )
            for i, choice in enumerate(data['choices']):
                MCQChoice.objects.create(exercise=ex, text=choice['text'], is_correct=choice['correct'],
                                         feedback=choice.get('feedback', ''), order=i)
            block.mcq_exercise = ex
            block.save()
        elif btype == 'fill_blank':
            ex = FillBlankExercise.objects.create(
                course_lesson=lesson, title=data['title'], instructions=data.get('instructions', ''),
                difficulty=data.get('difficulty', 'easy'), points=data.get('points', 5),
                hint=data.get('hint', ''), explanation=data.get('explanation', ''), order=data.get('order', 0),
                text_with_blanks=data['text_with_blanks'], answers=data['answers'],
                case_sensitive=data.get('case_sensitive', False),
            )
            block.fill_blank = ex
            block.save()
        elif btype == 'true_false':
            ex = TrueFalseExercise.objects.create(
                course_lesson=lesson, title=data['title'], instructions=data.get('instructions', ''),
                difficulty=data.get('difficulty', 'easy'), points=data.get('points', 6),
                hint=data.get('hint', ''), explanation=data.get('explanation', ''), order=data.get('order', 0),
                statements=data['statements'], points_per_statement=data.get('points_per_statement', 2),
            )
            block.true_false = ex
            block.save()


COURSE_STRUCTURE = [
    {
        'order': 0,
        'title': 'Introduction à LaTeX',
        'description': "Découvre LaTeX, installe ton environnement et écris ton premier document.",
        'lessons': [
            {
                'order': 0, 'title': 'Bienvenue en LaTeX', 'slug': 'bienvenue-latex',
                'minutes': 20, 'free_preview': True,
                'blocks': [
                    {'type': 'text', 'content': """# Bienvenue en LaTeX ! 📝

## Qu'est-ce que LaTeX ?

**LaTeX** (prononcé "la-tek") est un système de composition typographique de haute qualité, utilisé pour produire des documents scientifiques et techniques. Contrairement à Word, tu écris du **texte balisé** que LaTeX compile en un PDF parfait.

## Pourquoi utiliser LaTeX ?

- **Qualité typographique** inégalée (surtout pour les mathématiques)
- **Séparation contenu / mise en forme** : tu te concentres sur le contenu
- **Stabilité** : pas de mise en page qui saute quand tu modifies un paragraphe
- **Bibliographie automatique** avec BibTeX/BibLaTeX
- **Open source** et gratuit
- **Standard** dans le monde académique pour les articles, thèses, livres

## LaTeX vs traitement de texte

| Caractéristique | Word / LibreOffice | LaTeX |
|-----------------|--------------------|-------|
| Approche | WYSIWYG (tu vois le résultat) | WYSIWYM (tu écris la structure) |
| Mathématiques | Limité, difficile | Excellent, natif |
| Longs documents | Lent, instable | Rapide, stable |
| Bibliographie | Manuel | Automatique (BibTeX) |
| Versionning | Difficile | Facile (fichiers texte) |
| Courbe d'apprentissage | Facile | Plus raide au début |

## Comment ça marche ?

1. Tu écris un fichier `.tex` (texte brut avec des commandes)
2. Tu **compiles** le fichier avec un compilateur (pdflatex, xelatex, lualatex)
3. LaTeX produit un fichier **PDF**

```latex
\\documentclass{article}
\\begin{document}
Bonjour, monde !
\\end{document}
```

## Où écrire du LaTeX ?

| Outil | Type | Avantages |
|-------|------|-----------|
| **Overleaf** | En ligne | Pas d'installation, collaboration |
| **TeXstudio** | Bureau (Windows/Mac/Linux) | Riche, autocomplete |
| **VS Code + LaTeX Workshop** | Bureau | Intégré à ton éditeur de code |
| **Texmaker** | Bureau | Simple, léger |

> 💡 **Astuce** : Si tu débutes, utilise **Overleaf** (gratuit, en ligne, pas d'installation).

## Dans ce cours

1. **Module 1** · Introduction (installation, premier document, structure)
2. **Module 2** · Mise en forme (texte, listes, tableaux, figures)
3. **Module 3** · Mathématiques (formules, équations, symboles)
4. **Module 4** · Documents avancés (bibliographie, présentations Beamer)
5. **Module 5** · Bonnes pratiques (organisation, erreurs, tips)

C'est parti ! 🚀"""},
                    {'type': 'mcq', 'title': 'Qu\'est-ce que LaTeX ?', 'question': "LaTeX est un système de :",
                     'explanation': "LaTeX est un système de composition typographique, pas un éditeur WYSIWYG.",
                     'choices': [
                         {'text': 'Traitement de texte WYSIWYG', 'correct': False, 'feedback': 'Non, LaTeX est WYSIWYM.'},
                         {'text': 'Composition typographique', 'correct': True, 'feedback': 'Exact ! LaTeX produit des PDF de haute qualité.'},
                         {'text': 'Langage de programmation', 'correct': False, 'feedback': 'Pas vraiment, c\'est un langage de balisage.'},
                         {'text': 'Tableur', 'correct': False},
                     ]},
                    {'type': 'true_false', 'title': 'Vrai ou Faux ? LaTeX', 'statements': [
                        {'statement': "LaTeX est gratuit et open source.", 'is_true': True},
                        {'statement': "LaTeX est surtout connu pour ses mauvaises formules mathématiques.", 'is_true': False},
                        {'statement': "LaTeX sépare le contenu de la mise en forme.", 'is_true': True},
                        {'statement': "LaTeX ne peut produire que des fichiers Word.", 'is_true': False},
                    ]},
                ],
            },
            {
                'order': 1, 'title': 'Premier document LaTeX', 'slug': 'premier-document',
                'minutes': 30, 'free_preview': True,
                'blocks': [
                    {'type': 'text', 'content': """# Ton premier document LaTeX

## Structure de base

Tout document LaTeX a cette structure minimale :

```latex
\\documentclass{article}    % Type de document
\\begin{document}           % Début du contenu
                            % Ton texte ici
\\end{document}             % Fin du contenu
```

## Anatomie

| Élément | Rôle |
|---------|------|
| `\\documentclass{article}` | Définit le type de document (article, report, book, letter) |
| `\\begin{document}` | Début du contenu visible |
| `\\end{document}` | Fin du contenu (tout après est ignoré) |
| `%` | Commentaire (ignoré par LaTeX) |

## Le préambule

Entre `\\documentclass` et `\\begin{document}`, c'est le **préambule**. C'est là qu'on charge les packages et configure le document :

```latex
\\documentclass[12pt, a4paper]{article}

\\usepackage[utf8]{inputenc}   % Encodage UTF-8
\\usepackage[T1]{fontenc}      % Polices
\\usepackage[french]{babel}    % Langue française
\\usepackage{amsmath}           % Mathématiques avancées
\\usepackage{graphicx}          % Inclusion d'images

\\title{Mon premier document}
\\author{Awa Diallo}
\\date{\\today}

\\begin{document}
\\maketitle                    % Affiche titre, auteur, date

Bonjour, ceci est mon premier document LaTeX.

\\end{document}
```

## Classes de documents

| Classe | Usage |
|--------|-------|
| `article` | Articles courts, rapports (le plus courant) |
| `report` | Rapports plus longs avec chapitres |
| `book` | Livres (recto-verso, chapitres) |
| `letter` | Lettres |
| `beamer` | Présentations (diapositives) |
| `memoir` | Livres avancés (très flexible) |

## Options de classe

```latex
\\documentclass[12pt, a4paper, twocolumn]{article}
```

| Option | Effet |
|--------|-------|
| `10pt`, `11pt`, `12pt` | Taille de police de base |
| `a4paper`, `letterpaper` | Format de papier |
| `twocolumn` | Texte sur deux colonnes |
| `landscape` | Mode paysage |
| `twoside` | Recto-verso |

## Compilation

Pour produire le PDF, lance l'une de ces commandes :

```bash
pdflatex mondocument.tex    # Compilation standard
xelatex mondocument.tex     # Support Unicode natif
lualatex mondocument.tex    # Moteur moderne
```

> 💡 **Astuce** : Sur Overleaf, cliquez simplement sur "Recompile" — tout est automatique !

## Espaces et sauts de ligne

- **Espace simple** : un espace = un espace dans le PDF
- **Espaces multiples** : ignorés (un seul espace)
- **Saut de ligne** : ligne vide dans le `.tex` = nouveau paragraphe
- `\\\\` ou `\\newline` : force un saut de ligne sans nouveau paragraphe
- `\\par` : équivalent à une ligne vide"""},
                    {'type': 'fill_blank', 'title': 'Complète le code LaTeX', 'instructions': 'Complète les commandes LaTeX manquantes.',
                     'text_with_blanks': "{{blank_1}}{article}\n\n\\begin{document}\nBonjour !\n{{blank_2}}",
                     'answers': {'blank_1': ['\\documentclass'], 'blank_2': ['\\end{document}']},
                     'explanation': 'Tout document commence par \\documentclass et se termine par \\end{document}.'},
                    {'type': 'mcq', 'title': 'Le préambule', 'question': "Où place-t-on les \\usepackage ?",
                     'explanation': "Le préambule est entre \\documentclass et \\begin{document}.",
                     'choices': [
                         {'text': 'Avant \\documentclass', 'correct': False},
                         {'text': 'Entre \\documentclass et \\begin{document}', 'correct': True, 'feedback': 'Exact ! C\'est le préambule.'},
                         {'text': 'Après \\end{document}', 'correct': False},
                         {'text': "N'importe où", 'correct': False},
                     ]},
                    {'type': 'true_false', 'title': 'Vrai ou Faux ? Structure', 'statements': [
                        {'statement': "Le caractère % commence un commentaire en LaTeX.", 'is_true': True},
                        {'statement': "Plusieurs espaces consécutifs créent plusieurs espaces dans le PDF.", 'is_true': False},
                        {'statement': "Une ligne vide dans le .tex commence un nouveau paragraphe.", 'is_true': True},
                        {'statement': "La classe beamer sert à faire des présentations.", 'is_true': True},
                    ]},
                ],
            },
        ],
    },
    {
        'order': 1,
        'title': 'Mise en forme du texte',
        'description': "Apprends à formater ton texte : gras, italique, listes, tableaux, figures.",
        'lessons': [
            {
                'order': 0, 'title': 'Formatage du texte', 'slug': 'formatage-texte',
                'minutes': 25, 'free_preview': True,
                'blocks': [
                    {'type': 'text', 'content': """# Formatage du texte en LaTeX

## Styles de base

| Commande | Effet | Exemple |
|----------|-------|---------|
| `\\textbf{gras}` | **Gras** | `\\textbf{important}` |
| `\\textit{italique}` | *Italique* | `\\textit{note}` |
| `\\underline{souligné}` | Souligné | `\\underline{titre}` |
| `\\emph{emphase}` | *Emphase* (italique contextuel) | `\\emph{attention}` |
| `\\texttt{machine}` | `Machine à écrire` | `\\texttt{code}` |
| `\\textsc{majuscules}` | PETITES MAJUSCULES | `\\textsc{aucsi}` |
| `\\textbf{\\textit{mixte}}` | ***Gras + italique*** | combiné |

## Tailles de police

Du plus petit au plus grand :

```latex
{\\tiny minuscule}
{\\scriptsize très petit}
{\\footnotesize petit}
{\\small un peu petit}
{\\normalsize normal}
{\\large un peu grand}
{\\Large grand}
{\\LARGE très grand}
{\\huge énorme}
{\\Huge gigantesque}
```

> 💡 **Astuce** : Les tailles sont relatives à la taille de base (10pt, 11pt, ou 12pt définie dans `\\documentclass`).

## Couleurs

Nécessite le package `\\usepackage{xcolor}` :

```latex
\\textcolor{red}{texte rouge}
\\textcolor{blue}{texte bleu}
\\textcolor{green!50}{vert à 50%}
\\definecolor{monbleu}{RGB}{0, 100, 200}
\\textcolor{monbleu}{bleu personnalisé}
```

## Alignement

```latex
\\begin{center}
Texte centré
\\end{center}

\\begin{flushleft}
Texte aligné à gauche
\\end{flushleft}

\\begin{flushright}
Texte aligné à droite
\\end{flushright}
```

## Sections et hiérarchie

```latex
\\part{Partie}              % Niveau 0 (livres)
\\chapter{Chapitre}          % Niveau 1 (report, book)
\\section{Section}           % Niveau 2
\\subsection{Sous-section}   % Niveau 3
\\subsubsection{Sous-sous}   % Niveau 4
\\paragraph{Paragraphe}      % Niveau 5 (titre en ligne)
\\subparagraph{Sous-parag.}  % Niveau 6
```

La numérotation est automatique. Pour une section non numérotée, ajoute `*` :

```latex
\\section*{Introduction}    % Pas de numéro, pas dans la table des matières
```

## Table des matières

```latex
\\tableofcontents    % Génère la table des matières
```

> ⚠️ **Attention** : LaTeX a besoin de **deux compilations** pour la table des matières (la première collecte les sections, la seconde les affiche).

## Listes

### Liste à puces

```latex
\\begin{itemize}
    \\item Premier élément
    \\item Deuxième élément
    \\item Troisième élément
\\end{itemize}
```

### Liste numérotée

```latex
\\begin{enumerate}
    \\item Premier
    \\item Deuxième
    \\item Troisième
\\end{enumerate}
```

### Liste de description

```latex
\\begin{description}
    \\item[LaTeX] Système de composition typographique
    \\item[TeX] Le moteur sous-jacent
    \\item[BibTeX] Gestionnaire de bibliographie
\\end{description}
```"""},
                    {'type': 'mcq', 'title': 'Styles de texte', 'question': "Comment écrit-on du texte en gras en LaTeX ?",
                     'explanation': "La commande \\textbf{} met le texte en gras.",
                     'choices': [
                         {'text': '**gras**', 'correct': False, 'feedback': 'C\'est la syntaxe Markdown, pas LaTeX.'},
                         {'text': '\\textbf{gras}', 'correct': True, 'feedback': 'Exact !'},
                         {'text': '\\bold{gras}', 'correct': False},
                         {'text': '[b]gras[/b]', 'correct': False},
                     ]},
                    {'type': 'fill_blank', 'title': 'Complète les commandes', 'instructions': 'Complète les commandes LaTeX.',
                     'text_with_blanks': "{{blank_1}}{important} met en gras.\n{{blank_2}} commence une section.\n{{blank_3}} génère la table des matières.",
                     'answers': {'blank_1': ['\\textbf'], 'blank_2': ['\\section'], 'blank_3': ['\\tableofcontents']},
                     'explanation': '\\textbf pour le gras, \\section pour les sections, \\tableofcontents pour la table des matières.'},
                    {'type': 'true_false', 'title': 'Vrai ou Faux ? Formatage', 'statements': [
                        {'statement': "\\section*{Intro} crée une section non numérotée.", 'is_true': True},
                        {'statement': "LaTeX a besoin d'une seule compilation pour la table des matières.", 'is_true': False},
                        {'statement': "\\begin{itemize} crée une liste à puces.", 'is_true': True},
                        {'statement': "Les couleurs nécessitent le package xcolor.", 'is_true': True},
                    ]},
                ],
            },
            {
                'order': 1, 'title': 'Tableaux et figures', 'slug': 'tableaux-figures',
                'minutes': 30, 'free_preview': True,
                'blocks': [
                    {'type': 'text', 'content': """# Tableaux et figures en LaTeX

## Tableaux simples

LaTeX utilise l'environnement `tabular` pour les tableaux :

```latex
\\begin{table}[h]
    \\centering
    \\begin{tabular}{|l|c|r|}
        \\hline
        Nom & Âge & Note \\\\
        \\hline
        Awa & 20 & 15 \\\\
        Kofi & 22 & 17 \\\\
        Aya & 19 & 14 \\\\
        \\hline
    \\end{tabular}
    \\caption{Résultats des étudiants}
    \\label{tab:resultats}
\\end{table}
```

## Comprendre `{|l|c|r|}`

| Symbole | Alignement |
|---------|-----------|
| `l` | Left (gauche) |
| `c` | Center (centré) |
| `r` | Right (droite) |
| `|` | Ligne verticale |
| `p{3cm}` | Colonne de largeur fixée (texte justifié) |

## Commandes de tableau

| Commande | Effet |
|----------|-------|
| `\\hline` | Ligne horizontale |
| `\\cline{1-2}` | Ligne sur les colonnes 1 à 2 |
| `&` | Séparateur de colonne |
| `\\\\` | Nouvelle ligne |
| `\\multicolumn{2}{|c|}{Texte}` | Fusionner 2 colonnes |
| `\\multirow{2}{*}{Texte}` | Fusionner 2 lignes (package `multirow`) |

## Tableau professionnel (package `booktabs`)

```latex
\\usepackage{booktabs}

\\begin{tabular}{lcc}
    \\toprule
    Nom & Âge & Note \\\\
    \\midrule
    Awa & 20 & 15 \\\\
    Kofi & 22 & 17 \\\\
    \\bottomrule
\\end{tabular}
```

> 💡 **Astuce** : `booktabs` donne un look professionnel. Ne jamais utiliser de lignes verticales avec booktabs !

## Figures et images

Nécessite `\\usepackage{graphicx}` :

```latex
\\begin{figure}[h]
    \\centering
    \\includegraphics[width=0.8\\textwidth]{image.png}
    \\caption{Schéma de l'expérience}
    \\label{fig:experience}
\\end{figure}
```

## Options de placement

| Code | Signification |
|------|---------------|
| `h` | Here (ici, approximativement) |
| `t` | Top (en haut de la page) |
| `b` | Bottom (en bas de la page) |
| `p` | Page (page séparée) |
| `!` | Force (ignore certaines contraintes) |
| `H` | Here absolument (package `float`) |

## Références croisées

```latex
Comme le montre le tableau \\ref{tab:resultats} (page \\pageref{tab:resultats}),
et la figure \\ref{fig:experience}...
```

> ⚠️ **Attention** : Les références nécessitent **deux compilations** pour être résolues."""},
                    {'type': 'mcq', 'title': 'Alignement tabular', 'question': "Que signifie 'c' dans {lcr} ?",
                     'explanation': "c = center (centré), l = left, r = right.",
                     'choices': [
                         {'text': 'Column (colonne)', 'correct': False},
                         {'text': 'Center (centré)', 'correct': True, 'feedback': 'Exact !'},
                         {'text': 'Character (caractère)', 'correct': False},
                         {'text': 'Cut (couper)', 'correct': False},
                     ]},
                    {'type': 'mcq', 'title': 'Package booktabs', 'question': "Quelle commande du package booktabs crée la ligne du haut ?",
                     'explanation': "\\toprule crée la ligne supérieure épaisse.",
                     'choices': [
                         {'text': '\\topline', 'correct': False},
                         {'text': '\\toprule', 'correct': True, 'feedback': 'Exact !'},
                         {'text': '\\headrule', 'correct': False},
                         {'text': '\\hline', 'correct': False, 'feedback': '\\hline est la commande de base (sans booktabs).'},
                     ]},
                    {'type': 'true_false', 'title': 'Vrai ou Faux ? Tableaux', 'statements': [
                        {'statement': "& sépare les colonnes dans un tableau.", 'is_true': True},
                        {'statement': "\\\\ commence une nouvelle ligne dans un tableau.", 'is_true': True},
                        {'statement': "Les références croisées (\\ref) nécessitent une seule compilation.", 'is_true': False},
                        {'statement': "Le package graphicx est requis pour inclure des images.", 'is_true': True},
                    ]},
                ],
            },
        ],
    },
    {
        'order': 2,
        'title': 'Mathématiques en LaTeX',
        'description': "Maîtrise les formules mathématiques : symboles, équations, matrices, alignements.",
        'lessons': [
            {
                'order': 0, 'title': 'Notation mathématique de base', 'slug': 'maths-base',
                'minutes': 35, 'free_preview': True,
                'blocks': [
                    {'type': 'text', 'content': """# Notation mathématique en LaTeX

## Modes mathématiques

LaTeX propose plusieurs modes pour les maths :

| Mode | Syntaxe | Usage |
|------|---------|-------|
| **En ligne** | `$x^2$` ou `\\(x^2\\)` | Dans une phrase |
| **Hors ligne** | `$$x^2$$` ou `\\[x^2\\]` | Centré, sur sa propre ligne |
| **Équation** | `\\begin{equation}...\\end{equation}` | Numérotée |
| **Align** | `\\begin{align}...\\end{align}` | Multi-lignes alignées |

## Exposants, indices, fractions

```latex
$x^2$           % exposant
$x^{2n}$        % exposant composé
$x_i$           % indice
$x_{i+1}$       % indice composé
$\\frac{a}{b}$  % fraction
$\\sqrt{x}$     % racine carrée
$\\sqrt[n]{x}$  % racine n-ième
```

## Lettres grecques

```latex
$\\alpha$  $\\beta$  $\\gamma$  $\\delta$  $\\epsilon$
$\\pi$     $\\rho$   $\\sigma$  $\\tau$    $\\phi$
$\\omega$  $\\theta$  $\\lambda$  $\\mu$    $\\nu$
```

Majuscules : `$\\Gamma$  $\\Delta$  $\\Theta$  $\\Lambda$  $\\Sigma$  $\\Omega$`

## Opérateurs

| Commande | Résultat |
|----------|----------|
| `\\sum_{i=1}^{n}` | ∑ (somme) |
| `\\prod_{i=1}^{n}` | ∏ (produit) |
| `\\int_{a}^{b}` | ∫ (intégrale) |
| `\\lim_{x \\to 0}` | lim (limite) |
| `\\infty` | ∞ (infini) |
| `\\partial` | ∂ (dérivée partielle) |
| `\\nabla` | ∇ (nabla) |

## Symboles de relation

| Commande | Symbole |
|----------|---------|
| `\\leq` ou `\\leqslant` | ≤ |
| `\\geq` ou `\\geqslant` | ≥ |
| `\\neq` | ≠ |
| `\\approx` | ≈ |
| `\\equiv` | ≡ |
| `\\sim` | ~ |
| `\\propto` | ∝ |
| `\\perp` | ⊥ |
| `\\parallel` | ∥ |

## Ensembles

| Commande | Symbole |
|----------|---------|
| `\\mathbb{R}` | ℝ |
| `\\mathbb{N}` | ℕ |
| `\\mathbb{Z}` | ℤ |
| `\\mathbb{Q}` | ℚ |
| `\\mathbb{C}` | ℂ |
| `\\in` | ∈ |
| `\\notin` | ∉ |
| `\\subset` | ⊂ |
| `\\subseteq` | ⊆ |
| `\\cup` | ∪ |
| `\\cap` | ∩ |
| `\\emptyset` | ∅ |

> 💡 **Astuce** : `\\mathbb{}` nécessite `\\usepackage{amssymb}`.

## Exemple complet

```latex
\\begin{equation}
    \\int_{0}^{\\infty} e^{-x^2} \\, dx = \\frac{\\sqrt{\\pi}}{2}
    \\label{eq:gauss}
\\end{equation}
```

L'équation \\eqref{eq:gauss} est l'intégrale de Gauss.

## Points de suspension

| Commande | Usage |
|----------|-------|
| `\\dots` ou `\\ldots` | Points sur la ligne (a, b, \\dots, z) |
| `\\cdots` | Points centrés (a + b + \\cdots + z) |
| `\\vdots` | Points verticaux (dans une matrice) |
| `\\ddots` | Points diagonaux (dans une matrice) |"""},
                    {'type': 'mcq', 'title': 'Mode mathématique', 'question': "Comment écrit-on une formule mathématique en ligne (dans une phrase) ?",
                     'explanation': "Les symboles $...$ encadrent une formule en ligne.",
                     'choices': [
                         {'text': '#x^2#', 'correct': False},
                         {'text': '$x^2$', 'correct': True, 'feedback': 'Exact !'},
                         {'text': '{x^2}', 'correct': False},
                         {'text': '<m>x^2</m>', 'correct': False},
                     ]},
                    {'type': 'mcq', 'title': 'Lettres grecques', 'question': "Comment écrit-on la lettre grecque π en LaTeX ?",
                     'explanation': "Toutes les lettres grecques commencent par \\.",
                     'choices': [
                         {'text': '\\pi', 'correct': True, 'feedback': 'Exact !'},
                         {'text': '\\Pi', 'correct': False, 'feedback': 'C\'est Π (majuscule).'},
                         {'text': 'pi', 'correct': False},
                         {'text': '#pi#', 'correct': False},
                     ]},
                    {'type': 'fill_blank', 'title': 'Complète les formules', 'instructions': 'Complète les commandes LaTeX.',
                     'text_with_blanks': "Fraction : {{blank_1}}{a}{b}\nSomme : {{blank_2}}_{i=1}^{n}\nRacine : {{blank_3}}{x}",
                     'answers': {'blank_1': ['\\frac'], 'blank_2': ['\\sum'], 'blank_3': ['\\sqrt']},
                     'explanation': '\\frac pour les fractions, \\sum pour les sommes, \\sqrt pour les racines.'},
                    {'type': 'true_false', 'title': 'Vrai ou Faux ? Maths', 'statements': [
                        {'statement': "$$...$$ affiche une formule centrée sur sa propre ligne.", 'is_true': True},
                        {'statement': "\\mathbb{R} affiche le symbole des réels (R).", 'is_true': True},
                        {'statement': "\\int ne nécessite pas de bornes.", 'is_true': False},
                        {'statement': "L'environnement equation numérote automatiquement les équations.", 'is_true': True},
                    ]},
                ],
            },
            {
                'order': 1, 'title': 'Équations et alignements', 'slug': 'equations-alignements',
                'minutes': 30, 'free_preview': True,
                'blocks': [
                    {'type': 'text', 'content': """# Équations et alignements en LaTeX

## L'environnement equation

Numérote automatiquement :

```latex
\\begin{equation}
    E = mc^2
    \\label{eq:einstein}
\\end{equation}
```

Pour une équation **sans numéro**, utilise `equation*` :

```latex
\\begin{equation*}
    E = mc^2
\\end{equation*}
```

## L'environnement align (multi-lignes)

```latex
\\begin{align}
    f(x) &= (x + 1)^2 \\\\
         &= x^2 + 2x + 1 \\\\
         &= x(x + 2) + 1
\\end{align}
```

Le `&` indique où aligner. `\\\\` passe à la ligne suivante.

## L'environnement cases (systèmes)

```latex
\\begin{equation}
    |x| = \\begin{cases}
        x  & \\text{si } x \\geq 0 \\\\
        -x & \\text{si } x < 0
    \\end{cases}
\\end{equation}
```

## Matrices

| Environnement | Délimiteurs |
|---------------|-------------|
| `matrix` | Aucun |
| `pmatrix` | Parenthèses ( ) |
| `bmatrix` | Crochets [ ] |
| `Bmatrix` | Accolades { } |
| `vmatrix` | Barres | | |
| `Vmatrix` | Doubles barres ‖ ‖ |

```latex
\\begin{equation}
    A = \\begin{pmatrix}
        a_{11} & a_{12} \\\\
        a_{21} & a_{22}
    \\end{pmatrix}
\\end{equation}
```

## Texte dans les maths

```latex
$\\text{si } x > 0$
```

> ⚠️ **Attention** : N'utilise jamais de texte brut dans une formule. Utilise toujours `\\text{}` pour le texte normal dans une équation.

## Parenthèses ajustables

```latex
\\left( \\frac{a}{b} \\right)        % parenthèses auto-ajustées
\\left[ \\frac{a}{b} \\right]        % crochets
\\left\\{ \\frac{a}{b} \\right\\}     % accolades
\\left| \\frac{a}{b} \\right|        % valeur absolue
\\left. \\frac{a}{b} \\right|        % délimiteur invisible à gauche
```

> 💡 **Astuce** : `\\left` et `\\right` ajustent automatiquement la taille des délimiteurs au contenu.

## Exemples complets

### Théorème de Pythagore

```latex
\\begin{equation}
    a^2 + b^2 = c^2
\\end{equation}
```

### Formule quadratique

```latex
\\begin{equation}
    x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}
\\end{equation}
```

### Système d'équations

```latex
\\begin{align}
    2x + 3y &= 7 \\\\
    x - y   &= 1
\\end{align}
```

### Démonstration par étapes

```latex
\\begin{align*}
    (a+b)^2 &= (a+b)(a+b) \\\\
            &= a^2 + ab + ba + b^2 \\\\
            &= a^2 + 2ab + b^2
\\end{align*}
```"""},
                    {'type': 'mcq', 'title': 'Alignement', 'question': "À quoi sert le & dans l'environnement align ?",
                     'explanation': "Le & marque le point d'alignement entre les lignes.",
                     'choices': [
                         {'text': 'C\'est un séparateur de colonnes', 'correct': False},
                         {'text': 'C\'est le point d\'alignement', 'correct': True, 'feedback': 'Exact !'},
                         {'text': 'C\'est un commentaire', 'correct': False},
                         {'text': 'C\'est une erreur de syntaxe', 'correct': False},
                     ]},
                    {'type': 'mcq', 'title': 'Matrices', 'question': "Quel environnement utilise les parenthèses ( ) ?",
                     'explanation': "pmatrix = parenthesis matrix.",
                     'choices': [
                         {'text': 'bmatrix', 'correct': False, 'feedback': 'Crochets [ ].'},
                         {'text': 'pmatrix', 'correct': True, 'feedback': 'Exact ! pmatrix = parenthèses.'},
                         {'text': 'vmatrix', 'correct': False, 'feedback': 'Barres | |.'},
                         {'text': 'matrix', 'correct': False, 'feedback': 'Sans délimiteurs.'},
                     ]},
                    {'type': 'fill_blank', 'title': 'Complète les environnements',
                     'text_with_blanks': "{{blank_1}} numérote les équations.\n{{blank_2}} aligne plusieurs lignes.\n{{blank_3}} crée un système avec accolades.",
                     'answers': {'blank_1': ['equation', '\\begin{equation}'], 'blank_2': ['align', '\\begin{align}'], 'blank_3': ['cases', '\\begin{cases}']},
                     'explanation': 'equation pour numérotées, align pour multi-lignes, cases pour les systèmes.'},
                    {'type': 'true_false', 'title': 'Vrai ou Faux ? Équations', 'statements': [
                        {'statement': "equation* crée une équation sans numéro.", 'is_true': True},
                        {'statement': "\\\\ dans align passe à la ligne suivante.", 'is_true': True},
                        {'statement': "\\left et \\right sont obligatoires pour toutes les parenthèses.", 'is_true': False},
                        {'statement': "\\text{} permet d'insérer du texte normal dans une formule.", 'is_true': True},
                    ]},
                ],
            },
        ],
    },
    {
        'order': 3,
        'title': 'Documents avancés',
        'description': "Bibliographie, présentations Beamer, et documents longs.",
        'lessons': [
            {
                'order': 0, 'title': 'Bibliographie avec BibTeX', 'slug': 'bibtex',
                'minutes': 30, 'free_preview': True,
                'blocks': [
                    {'type': 'text', 'content': """# Bibliographie avec BibTeX

## Le fichier .bib

Crée un fichier `references.bib` contenant tes références :

```bibtex
@article{einstein1905,
    author  = {Albert Einstein},
    title   = {Zur Elektrodynamik bewegter K{"o}rper},
    journal = {Annalen der Physik},
    volume  = {322},
    number  = {10},
    pages   = {891--921},
    year    = {1905}
}

@book{knuth1984,
    author    = {Donald E. Knuth},
    title     = {The TeXbook},
    publisher = {Addison-Wesley},
    year      = {1984}
}

@online{overleaf,
    author = {Overleaf},
    title  = {Learn LaTeX in 30 Minutes},
    url    = {https://www.overleaf.com/learn},
    year   = {2023}
}
```

## Citer dans le document

```latex
\\usepackage{natbib}  % ou biblatex

\\begin{document}

Einstein a publié sa théorie de la relativité \\cite{einstein1905}.
Knuth a créé TeX \\citep{knuth1984}.

\\bibliographystyle{plainnat}   % Style de bibliographie
\\bibliography{references}       % Fichier .bib (sans extension)

\\end{document}
```

## Styles de citation

| Commande | Affichage |
|----------|-----------|
| `\\cite{key}` | [1] |
| `\\citep{key}` | (Knuth, 1984) |
| `\\citet{key}` | Knuth (1984) |
| `\\citeauthor{key}` | Knuth |
| `\\citeyear{key}` | 1984 |

## Types d'entrées BibTeX

| Type | Usage |
|------|-------|
| `@article` | Article de journal |
| `@book` | Livre |
| `@booklet` | Brochure (sans éditeur) |
| `@conference` | Actes de conférence |
| `@inbook` | Chapitre de livre |
| `@incollection` | Partie d'un recueil |
| `@inproceedings` | Article dans des actes |
| `@manual` | Manuel technique |
| `@mastersthesis` | Mémoire de master |
| `@misc` | Autre |
| `@phdthesis` | Thèse de doctorat |
| `@proceedings` | Actes de conférence |
| `@techreport` | Rapport technique |
| `@unpublished` | Non publié |
| `@online` | Ressource en ligne (avec `url`) |

## Compilation

```bash
pdflatex document
bibtex document        # Traite la bibliographie
pdflatex document      # Intègre les références
pdflatex document      # Résout les citations
```

> 💡 **Astuce** : Sur Overleaf, tout est automatique !"""},
                    {'type': 'mcq', 'title': 'Fichier .bib', 'question': "Quelle extension a le fichier de bibliographie ?",
                     'explanation': "Le fichier bibliographique a l'extension .bib.",
                     'choices': [
                         {'text': '.pdf', 'correct': False},
                         {'text': '.bib', 'correct': True, 'feedback': 'Exact !'},
                         {'text': '.tex', 'correct': False},
                         {'text': '.ref', 'correct': False},
                     ]},
                    {'type': 'mcq', 'title': 'Citation', 'question': "Quelle commande cite une référence ?",
                     'explanation': "\\cite{key} insère une citation.",
                     'choices': [
                         {'text': '\\ref{key}', 'correct': False, 'feedback': 'C\'est pour les références croisées.'},
                         {'text': '\\cite{key}', 'correct': True, 'feedback': 'Exact !'},
                         {'text': '\\bib{key}', 'correct': False},
                         {'text': '\\quote{key}', 'correct': False},
                     ]},
                    {'type': 'true_false', 'title': 'Vrai ou Faux ? BibTeX', 'statements': [
                        {'statement': "@article est utilisé pour les articles de journal.", 'is_true': True},
                        {'statement': "@phdthesis est utilisé pour les thèses de doctorat.", 'is_true': True},
                        {'statement': "BibTeX nécessite une seule compilation.", 'is_true': False},
                        {'statement': "Sur Overleaf, la bibliographie est gérée automatiquement.", 'is_true': True},
                    ]},
                ],
            },
            {
                'order': 1, 'title': 'Présentations avec Beamer', 'slug': 'beamer',
                'minutes': 30, 'free_preview': True,
                'blocks': [
                    {'type': 'text', 'content': """# Présentations avec Beamer

## Qu'est-ce que Beamer ?

**Beamer** est une classe LaTeX pour créer des **présentations** (diapositives). C'est l'outil standard pour les présentations scientifiques académiques.

## Structure de base

```latex
\\documentclass{beamer}

\\usetheme{Madrid}        % Thème
\\usecolortheme{default}   % Couleurs

\\title{Ma Présentation}
\\author{Awa Diallo}
\\institute{Numeria Institute}
\\date{\\today}

\\begin{document}

\\begin{frame}
    \\titlepage
\\end{frame}

\\begin{frame}{Plan}
    \\tableofcontents
\\end{frame}

\\section{Introduction}

\\begin{frame}{Introduction}
    Bonjour, ceci est ma première diapositive.
\\end{frame}

\\end{document}
```

## Thèmes populaires

| Thème | Style |
|-------|-------|
| `Madrid` | Classique, barre de navigation |
| `Berlin` | Avec sections en haut |
| `Warsaw` | Bleu, barre de navigation |
| `Singapore` | Minimaliste |
| `CambridgeUS` | Rouge et gris |
| `metropolis` | Moderne, épuré (à installer) |

```latex
\\usetheme{Madrid}           % Thème
\\usecolortheme{seahorse}    % Couleurs
```

## Contenu des diapositives

### Texte et listes

```latex
\\begin{frame}{Résultats}
    \\begin{itemize}
        \\item Premier résultat important
        \\item Deuxième résultat
        \\item Troisième résultat
    \\end{itemize}
\\end{frame}
```

### Mathématiques

```latex
\\begin{frame}{Formule}
    L'énergie est donnée par :
    \\begin{equation}
        E = mc^2
    \\end{equation}
\\end{frame}
```

### Colonnes

```latex
\\begin{frame}{Deux colonnes}
    \\begin{columns}
        \\begin{column}{0.5\\textwidth}
            Texte à gauche
        \\end{column}
        \\begin{column}{0.5\\textwidth}
            Texte à droite
        \\end{column}
    \\end{columns}
\\end{frame}
```

### Blocs colorés

```latex
\\begin{frame}{Blocs}
    \\begin{block}{Définition}
        Un nombre premier est divisible seulement par 1 et lui-même.
    \\end{block}
    
    \\begin{alertblock}{Attention}
        1 n'est pas premier !
    \\end{alertblock}
    
    \\begin{exampleblock}{Exemple}
        2, 3, 5, 7, 11 sont premiers.
    \\end{exampleblock}
\\end{frame}
```

## Animations (overlays)

```latex
\\begin{frame}{Animation}
    \\begin{itemize}
        \\item<1-> Premier point (apparait à la slide 1)
        \\item<2-> Deuxième point (apparait à la slide 2)
        \\item<3-> Troisième point (apparait à la slide 3)
    \\end{itemize}
\\end{frame}
```

## Conseils pour une bonne présentation

1. **Une idée par diapositive**
2. **Maximum 6 lignes** de texte
3. **Police ≥ 20pt** (LaTeX gère ça automatiquement)
4. **Peu de texte** : mots-clés, pas des paragraphes
5. **Images et figures** pour illustrer
6. **Numéroter les diapositives** : `\\setbeamertemplate{footline}[frame number]`
7. **Enlever la navigation** : `\\setbeamertemplate{navigation symbols}{}`

> 💡 **Astuce** : Ajoute `\\setbeamertemplate{navigation symbols}{}` dans le préambule pour enlever les icônes de navigation en bas."""},
                    {'type': 'mcq', 'title': 'Classe Beamer', 'question': "Quelle classe LaTeX utilise-t-on pour une présentation ?",
                     'explanation': "La classe beamer crée des diapositives.",
                     'choices': [
                         {'text': '\\documentclass{article}', 'correct': False},
                         {'text': '\\documentclass{beamer}', 'correct': True, 'feedback': 'Exact !'},
                         {'text': '\\documentclass{slides}', 'correct': False},
                         {'text': '\\documentclass{presentation}', 'correct': False},
                     ]},
                    {'type': 'mcq', 'title': 'Diapositive', 'question': "Quel environnement crée une diapositive ?",
                     'explanation': "\\begin{frame} crée une diapositive.",
                     'choices': [
                         {'text': '\\begin{slide}', 'correct': False},
                         {'text': '\\begin{frame}', 'correct': True, 'feedback': 'Exact !'},
                         {'text': '\\begin{page}', 'correct': False},
                         {'text': '\\begin{diapositive}', 'correct': False},
                     ]},
                    {'type': 'true_false', 'title': 'Vrai ou Faux ? Beamer', 'statements': [
                        {'statement': "\\usetheme{Madrid} définit le thème visuel.", 'is_true': True},
                        {'statement': "\\begin{block} crée un bloc coloré.", 'is_true': True},
                        {'statement': "Beamer ne supporte pas les mathématiques.", 'is_true': False},
                        {'statement': "\\item<2-> fait apparaître l'item à la 2e diapositive.", 'is_true': True},
                    ]},
                ],
            },
        ],
    },
    {
        'order': 4,
        'title': 'Bonnes pratiques et erreurs',
        'description': "Évite les erreurs courantes et organise tes projets LaTeX.",
        'lessons': [
            {
                'order': 0, 'title': 'Erreurs courantes et débogage', 'slug': 'erreurs-debogage',
                'minutes': 25, 'free_preview': True,
                'blocks': [
                    {'type': 'text', 'content': """# Erreurs courantes et débogage en LaTeX

## Erreurs fréquentes

### 1. Accolades non fermées

❌ `\\textbf{Important`
✅ `\\textbf{Important}`

### 2. Environnement non fermé

❌ `\\begin{itemize} \\item Un`
✅ `\\begin{itemize} \\item Un \\end{itemize}`

### 3. Caractères spéciaux non échappés

| Caractère | Commande |
|-----------|----------|
| `&` | `\\&` |
| `%` | `\\%` |
| `$` | `\\$` |
| `#` | `\\#` |
| `_` | `\\_` |
| `{` | `\\{` |
| `}` | `\\}` |
| `~` | `\\textasciitilde` |
| `^` | `\\textasciicircum` |
| `\\` | `\\textbackslash` |

### 4. Compilation manquante

LaTeX a parfois besoin de **plusieurs compilations** :
- **Table des matières** : 2 compilations
- **Références croisées** : 2 compilations
- **Bibliographie** : pdflatex → bibtex → pdflatex → pdflatex

### 5. Package manquant

❌ `! LaTeX Error: File 'xxx.sty' not found.`
→ Installe le package ou utilise `tlmgr install xxx`

### 6. Mode mathématique oublié

❌ `x^2` dans le texte → Erreur
✅ `$x^2$` → Correct

## Comprendre les messages d'erreur

### Erreur fatale
```
! Undefined control sequence.
l.15 \\masupercommande
```
→ La commande n'existe pas (paquet manquant ou faute de frappe)

### Avertissement (Warning)
```
LaTeX Warning: Reference `fig:test' on page 1 undefined
```
→ Recompile (la référence sera résolue à la 2e compilation)

### Overfull / Underfull hbox
```
Overfull \\hbox (12.3pt too wide) in paragraph
```
→ Une ligne déborde. Solution : `\\sloppy` ou reformuler le texte.

## Conseils de débogage

1. **Lis le message d'erreur** : LaTeX indique la ligne et le problème
2. **Commente des sections** avec `%` pour isoler l'erreur
3. **Compile souvent** : ne fais pas de gros changements avant de compiler
4. **Vérifie les accolades** : compte les `{` et `}`
5. **Vérifie les environnements** : chaque `\\begin` doit avoir un `\\end`
6. **Consulte les logs** : le fichier `.log` contient tous les détails

> ⚠️ **Attention** : Le caractère `_` (tiret bas) est réservé aux indices en mode math. Dans le texte, utilise `\\_`."""},
                    {'type': 'mcq', 'title': 'Caractères spéciaux', 'question': "Comment écrit-on le caractère % dans du texte LaTeX ?",
                     'explanation': "Le % est un commentaire en LaTeX. Pour l'afficher, utilise \\%.",
                     'choices': [
                         {'text': '%', 'correct': False, 'feedback': 'Ceci crée un commentaire.'},
                         {'text': '\\%', 'correct': True, 'feedback': 'Exact !'},
                         {'text': '/%', 'correct': False},
                         {'text': '[[%]]', 'correct': False},
                     ]},
                    {'type': 'mcq', 'title': 'Erreur de compilation', 'question': "Que faire si la table des matières est vide ?",
                     'explanation': "LaTeX a besoin de 2 compilations pour la table des matières.",
                     'choices': [
                         {'text': 'Recompiler une deuxième fois', 'correct': True, 'feedback': 'Exact !'},
                         {'text': 'Supprimer \\tableofcontents', 'correct': False},
                         {'text': 'Changer de documentclass', 'correct': False},
                         {'text': 'Ajouter \\usepackage{toc}', 'correct': False},
                     ]},
                    {'type': 'fill_blank', 'title': 'Échapper les caractères', 'instructions': 'Complète pour afficher ces caractères.',
                     'text_with_blanks': "Pourcent : {{blank_1}}\nEsperluette : {{blank_2}}\nDollar : {{blank_3}}",
                     'answers': {'blank_1': ['\\%'], 'blank_2': ['\\&'], 'blank_3': ['\\$']},
                     'explanation': 'Tous les caractères spéciaux se préfixent avec \\ en LaTeX.'},
                    {'type': 'true_false', 'title': 'Vrai ou Faux ? Erreurs', 'statements': [
                        {'statement': "Le caractère & doit être échappé avec \\& dans le texte.", 'is_true': True},
                        {'statement': "Les références croisées nécessitent 2 compilations.", 'is_true': True},
                        {'statement': "Le _ peut être utilisé tel quel dans le texte.", 'is_true': False},
                        {'statement': "Un Overfull hbox indique qu'une ligne déborde.", 'is_true': True},
                    ]},
                ],
            },
            {
                'order': 1, 'title': 'Organiser un projet LaTeX', 'slug': 'organisation-projet',
                'minutes': 20, 'free_preview': True,
                'blocks': [
                    {'type': 'text', 'content': """# Organiser un projet LaTeX

## Structure de fichiers recommandée

```
mon-projet/
├── main.tex              % Fichier principal
├── preamble.tex          % Préambule (packages, configurations)
├── chapters/
│   ├── introduction.tex   % Chapitre 1
│   ├── methodes.tex       % Chapitre 2
│   ├── resultats.tex      % Chapitre 3
│   └── conclusion.tex     % Chapitre 4
├── figures/
│   ├── schema.png
│   ├── graphique.pdf
│   └── logo.png
├── references.bib         % Bibliographie
├── .gitignore             % Pour Git
└── Makefile               % Compilation automatique (optionnel)
```

## Inclure des fichiers

Dans `main.tex` :

```latex
\\input{preamble}           % Inclut le préambule
\\input{chapters/introduction}
\\input{chapters/methodes}
\\input{chapters/resultats}
\\input{chapters/conclusion}
```

> 💡 **Astuce** : `\\input` n'inclut pas de saut de page, contrairement à `\\include` qui en ajoute un et utilise `\\clearpage`.

## Le fichier .gitignore

Si tu utilises Git, ignore les fichiers de compilation :

```gitignore
*.aux
*.log
*.out
*.toc
*.bbl
*.blg
*.fls
*.fdb_latexmk
*.synctex.gz
*.fdb_latexmk
```

## Makefile pour compilation automatique

```makefile
DOC = main

all: $(DOC).pdf

$(DOC).pdf: $(DOC).tex
    pdflatex $(DOC)
    bibtex $(DOC)
    pdflatex $(DOC)
    pdflatex $(DOC)

clean:
    rm -f *.aux *.log *.out *.toc *.bbl *.blg

view: $(DOC).pdf
    evince $(DOC).pdf &
```

## Bonnes pratiques

1. **Un fichier par chapitre** : facilite la navigation
2. **Commenter** : utilise `%` pour expliquer ton code
3. **Noms de labels explicites** : `\\label{fig:experience-chaleur}` pas `\\label{fig:1}`
4. **Préambule séparé** : réutilisable entre projets
5. **Figures en PDF** : préfère le PDF au PNG (vectoriel = net à toute taille)
6. **Git** : versionne ton code LaTeX (fichiers texte = parfait pour Git)

## Labels : conventions de nommage

| Préfixe | Usage | Exemple |
|---------|-------|---------|
| `fig:` | Figures | `\\label{fig:graphique}` |
| `tab:` | Tableaux | `\\label{tab:resultats}` |
| `eq:` | Équations | `\\label{eq:gauss}` |
| `sec:` | Sections | `\\label{sec:introduction}` |
| `chap:` | Chapitres | `\\label{chap:methodes}` |
| `alg:` | Algorithmes | `\\label{alg:trifusion}` |

> ⚠️ **Attention** : Les labels doivent être **uniques** dans tout le document."""},
                    {'type': 'mcq', 'title': 'Inclure un fichier', 'question': "Quelle commande inclut un fichier .tex sans saut de page ?",
                     'explanation': "\\input inclut le fichier tel quel, sans saut de page.",
                     'choices': [
                         {'text': '\\include{fichier}', 'correct': False, 'feedback': '\\include ajoute un saut de page.'},
                         {'text': '\\input{fichier}', 'correct': True, 'feedback': 'Exact !'},
                         {'text': '\\import{fichier}', 'correct': False},
                         {'text': '\\load{fichier}', 'correct': False},
                     ]},
                    {'type': 'mcq', 'title': 'Conventions de labels', 'question': "Quel préfixe pour une figure ?",
                     'explanation': "fig: est la convention pour les figures.",
                     'choices': [
                         {'text': 'fig:', 'correct': True, 'feedback': 'Exact !'},
                         {'text': 'image:', 'correct': False},
                         {'text': 'picture:', 'correct': False},
                         {'text': 'img:', 'correct': False},
                     ]},
                    {'type': 'true_false', 'title': 'Vrai ou Faux ? Organisation', 'statements': [
                        {'statement': "Il est recommandé de mettre un chapitre par fichier.", 'is_true': True},
                        {'statement': "\\input ajoute automatiquement un saut de page.", 'is_true': False},
                        {'statement': "Les labels doivent être uniques dans tout le document.", 'is_true': True},
                        {'statement': "Le format PDF est préférable au PNG pour les figures.", 'is_true': True},
                    ]},
                ],
            },
        ],
    },
]
