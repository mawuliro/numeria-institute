"""
Management command: seed_python_course

Creates a complete Python course "De l'Algorithmique à la POO" with:
  - 5 modules
  - 15 lessons
  - ~50 text blocks (Markdown + LaTeX)
  - ~15 sandboxes (Python code)
  - ~20 MCQ exercises (3-4 choices each)
  - ~15 code exercises (with starter code, expected output, tests)
  - ~10 fill-in-the-blank exercises
  - ~10 true/false exercises

Idempotent: if the course already exists (matched by slug), it is updated
in place rather than duplicated. Run with:

    python manage.py seed_python_course

The course is created in 'published' status so it's immediately visible
on the catalogue. Set --draft to keep it as a draft instead.
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
    help = 'Seed a complete Python course (Algorithmique → POO) with lessons, blocks, and exercises.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--draft', action='store_true',
            help='Create the course in draft status (default: published).',
        )
        parser.add_argument(
            '--clean', action='store_true',
            help='Delete the existing course (and all its children) before re-creating.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        slug = 'python-algorithmique-poo'
        status = 'draft' if options['draft'] else 'published'

        if options['clean']:
            deleted, _ = Course.objects.filter(slug=slug).delete()
            if deleted:
                self.stdout.write(self.style.WARNING(f'Deleted existing course ({deleted} related rows).'))

        course, created = Course.objects.get_or_create(
            slug=slug,
            defaults={
                'title': 'Python : de l\'Algorithmique à la POO',
                'description': (
                    "Un parcours complet pour apprendre Python depuis les premiers "
                    "concepts algorithmiques jusqu'à la programmation orientée objet. "
                    "Pensé pour les apprenants africains et francophones : exemples "
                    "concrets, exercices interactifs, et sandbox Python intégrée."
                ),
                'short_description': (
                    "Apprends Python de zéro à la POO : algorithmique, structures de "
                    "données, récursivité, tri, classes, héritage."
                ),
                'category': 'python',
                'level': 'debutant',
                'language': 'fr',
                'price': 0,
                'is_free': True,
                'status': status,
                'estimated_hours': 40,
            },
        )
        if not created:
            self.stdout.write(self.style.WARNING(f'Course "{course.title}" already exists — updating.'))
            course.status = status
            course.save(update_fields=['status'])
        else:
            self.stdout.write(self.style.SUCCESS(f'Created course "{course.title}".'))

        # Build each module + lessons + blocks
        for module_data in COURSE_STRUCTURE:
            module = self.upsert_module(course, module_data)
            for lesson_data in module_data['lessons']:
                lesson = self.upsert_lesson(module, lesson_data)
                self.upsert_blocks(lesson, lesson_data['blocks'])

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Course seeded: {course.title}\n'
            f'  Modules: {CourseModule.objects.filter(course=course).count()}\n'
            f'  Lessons: {CourseLesson.objects.filter(course=course).count()}\n'
            f'  Blocks:  {LessonBlock.objects.filter(course_lesson__course=course).count()}\n'
            f'  Status:  {course.status}\n'
            f'  URL:     /cours/{course.id}/'
        ))

    def upsert_module(self, course, data):
        module, _ = CourseModule.objects.get_or_create(
            course=course, title=data['title'],
            defaults={'description': data.get('description', ''), 'order': data['order'], 'is_active': True},
        )
        return module

    def upsert_lesson(self, module, data):
        slug = data.get('slug') or data['title'].lower().replace(' ', '-').replace('é', 'e').replace('à', 'a').replace('è', 'e').replace('û', 'u').replace("'", '-')
        lesson, _ = CourseLesson.objects.get_or_create(
            module=module, title=data['title'],
            defaults={
                'slug': slug,
                'order': data['order'],
                'estimated_minutes': data.get('minutes', 20),
                'is_free_preview': data.get('free_preview', True),
                'is_active': True,
            },
        )
        return lesson

    def upsert_blocks(self, lesson, blocks_data):
        # Clear existing blocks for this lesson (so re-running updates content cleanly)
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
            block.sandbox_initial_code = data.get('code', '# Écris ton code ici\n')
            block.save()
        elif btype == 'mcq':
            ex = self.create_mcq(lesson, data)
            block.mcq_exercise = ex
            block.save()
        elif btype == 'code_exercise':
            ex = self.create_code_exercise(lesson, data)
            block.code_exercise = ex
            block.save()
        elif btype == 'fill_blank':
            ex = self.create_fill_blank(lesson, data)
            block.fill_blank = ex
            block.save()
        elif btype == 'true_false':
            ex = self.create_true_false(lesson, data)
            block.true_false = ex
            block.save()
        else:
            # Unsupported type for this seeder — skip silently
            return

    # ---------- Exercise factories ----------

    def create_mcq(self, lesson, data):
        ex = MCQExercise.objects.create(
            course_lesson=lesson,
            title=data['title'],
            question=data['question'],
            instructions=data.get('instructions', ''),
            difficulty=data.get('difficulty', 'easy'),
            points=data.get('points', 5),
            hint=data.get('hint', ''),
            explanation=data.get('explanation', ''),
            order=data.get('order', 0),
            allow_multiple_correct=data.get('multiple', False),
            shuffle_choices=True,
        )
        for i, choice in enumerate(data['choices']):
            MCQChoice.objects.create(
                exercise=ex,
                text=choice['text'],
                is_correct=choice['correct'],
                feedback=choice.get('feedback', ''),
                order=i,
            )
        return ex

    def create_code_exercise(self, lesson, data):
        return CodeExercise.objects.create(
            course_lesson=lesson,
            title=data['title'],
            instructions=data.get('instructions', ''),
            difficulty=data.get('difficulty', 'easy'),
            points=data.get('points', 10),
            hint=data.get('hint', ''),
            explanation=data.get('explanation', ''),
            order=data.get('order', 0),
            starter_code=data.get('starter', '# Écris ton code ici\n'),
            solution_code=data.get('solution', ''),
            expected_output=data.get('expected_output', ''),
            test_code=data.get('test_code', ''),
            evaluation_mode=data.get('eval_mode', 'exact'),
        )

    def create_fill_blank(self, lesson, data):
        return FillBlankExercise.objects.create(
            course_lesson=lesson,
            title=data['title'],
            instructions=data.get('instructions', ''),
            difficulty=data.get('difficulty', 'easy'),
            points=data.get('points', 5),
            hint=data.get('hint', ''),
            explanation=data.get('explanation', ''),
            order=data.get('order', 0),
            text_with_blanks=data['text_with_blanks'],
            answers=data['answers'],
            case_sensitive=data.get('case_sensitive', False),
        )

    def create_true_false(self, lesson, data):
        return TrueFalseExercise.objects.create(
            course_lesson=lesson,
            title=data['title'],
            instructions=data.get('instructions', ''),
            difficulty=data.get('difficulty', 'easy'),
            points=data.get('points', 6),
            hint=data.get('hint', ''),
            explanation=data.get('explanation', ''),
            order=data.get('order', 0),
            statements=data['statements'],
            points_per_statement=data.get('points_per_statement', 2),
        )


# =============================================================================
# COURSE STRUCTURE — all content in French
# =============================================================================

COURSE_STRUCTURE = [
    # ──────────────────────────────────────────────────────────────────────
    # MODULE 1 — Introduction à Python
    # ──────────────────────────────────────────────────────────────────────
    {
        'order': 0,
        'title': 'Introduction à Python',
        'description': "Découvre Python, installe ton environnement et écris tes premiers programmes.",
        'lessons': [
            {
                'order': 0,
                'title': 'Bienvenue en Python',
                'slug': 'bienvenue-python',
                'minutes': 15,
                'free_preview': True,
                'blocks': [
                    {
                        'type': 'text',
                        'content': """# Bienvenue en Python ! 🐍

Python est un langage de programmation **simple, lisible et puissant**. Il est utilisé partout : intelligence artificielle, sites web, sciences, automatisation, jeux.

## Pourquoi apprendre Python ?

- **Syntaxe claire** : proche de l'anglais, facile à lire
- **Polyvalent** : web, data, IA, scripts, robotique
- **Communauté énorme** : des millions de tutoriels et de bibliothèques
- **Demande forte** sur le marché du travail en Afrique et à l'international

## Ton premier programme

Traditionnellement, le premier programme qu'on écrit dans un nouveau langage affiche « Hello, World! ». En Python, c'est une seule ligne :

```python
print("Hello, World!")
```

Le mot `print` est une **fonction**. Elle affiche à l'écran ce qu'on lui passe entre parenthèses. Les guillemets `"..."` délimitent une **chaîne de caractères** (du texte).

## Dans ce cours

Nous allons partir de zéro et arriver jusqu'à la **programmation orientée objet**. Le parcours :

1. **Module 1** — Introduction (variables, types, opérateurs)
2. **Module 2** — Algorithmique (conditions, boucles, fonctions)
3. **Module 3** — Structures de données (listes, tuples, dictionnaires)
4. **Module 4** — Algorithmique avancée (récursivité, tri, complexité)
5. **Module 5** — POO (classes, héritage, polymorphisme)

Chaque leçon contient :
- Un **cours théorique** avec des exemples
- Une **sandbox** pour tester le code en direct
- Des **exercices** (QCM, code à écrire, textes à trous)

Prêt ? C'est parti ! 🚀""",
                    },
                    {
                        'type': 'sandbox',
                        'title': 'Ton premier programme',
                        'code': '# Lance ce programme en cliquant sur Run\nprint("Hello, World!")\nprint("Je m\'appelle ...")\nprint("J\'apprends Python avec Numeria Institute")\n',
                    },
                    {
                        'type': 'mcq',
                        'title': 'Que fait la fonction print() ?',
                        'question': "Que fait l'instruction `print(\"Hello\")` en Python ?",
                        'explanation': "print() est une fonction intégrée qui affiche son argument dans la console.",
                        'choices': [
                            {'text': 'Elle affiche "Hello" à l\'écran', 'correct': True, 'feedback': 'Exact ! print() écrit dans la sortie standard.'},
                            {'text': 'Elle crée une variable nommée Hello', 'correct': False, 'feedback': 'Non, pour créer une variable on écrit juste `Hello = ...` sans print().'},
                            {'text': 'Elle demande à l\'utilisateur de taper Hello', 'correct': False, 'feedback': 'Non, c\'est input() qui demande à l\'utilisateur.'},
                            {'text': 'Elle efface l\'écran', 'correct': False, 'feedback': 'Non, print() n\'efface rien.'},
                        ],
                    },
                    {
                        'type': 'true_false',
                        'title': 'Vrai ou Faux ? Python',
                        'instructions': 'Indique si chaque affirmation est vraie ou fausse.',
                        'explanation': 'Python a été créé par Guido van Rossum en 1991. Il est gratuit et open-source.',
                        'statements': [
                            {'text': 'Python a été créé par Guido van Rossum.', 'is_correct': True},
                            {'text': 'Python est un langage payant.', 'is_correct': False},
                            {'text': 'Python est utilisé en intelligence artificielle.', 'is_correct': True},
                            {'text': 'Python ne peut fonctionner que sur Windows.', 'is_correct': False},
                        ],
                    },
                ],
            },
            {
                'order': 1,
                'title': 'Variables et types de base',
                'slug': 'variables-types',
                'minutes': 25,
                'free_preview': True,
                'blocks': [
                    {
                        'type': 'text',
                        'content': """# Variables et types de base

## Qu'est-ce qu'une variable ?

Une **variable** est une boîte nommée qui contient une valeur. En Python, on crée une variable en lui assignant une valeur avec le signe `=` :

```python
age = 25
nom = "Awa"
taille = 1.68
est_majeur = True
```

## Les types fondamentaux

Python possède quatre types de base que tu utiliseras tout le temps :

| Type | Exemple | Description |
|------|---------|-------------|
| `int` | `25`, `-7`, `0` | Nombres entiers |
| `float` | `1.68`, `3.14`, `-0.5` | Nombres à virgule |
| `str` | `"Awa"`, `'Bonjour'` | Chaînes de caractères (texte) |
| `bool` | `True`, `False` | Booléens (vrai / faux) |

## Connaître le type d'une valeur

La fonction `type()` renvoie le type d'une valeur :

```python
print(type(25))        # <class 'int'>
print(type("Awa"))     # <class 'str'>
print(type(1.68))      # <class 'float'>
print(type(True))      # <class 'bool'>
```

## Règles de nommage

- Une variable commence par une **lettre** ou un `_`
- Pas d'espaces, pas de caractères spéciaux (`+`, `-`, `@`...)
- Sensible à la casse : `age` ≠ `Age` ≠ `AGE`
- On utilise la convention **snake_case** : `mon_age`, `prix_total`

```python
# ✅ Bon
mon_age = 25
prix_total = 1500

# ❌ Mauvais
mon-age = 25      # tiret interdit
2e_variable = 5   # commence par un chiffre
```

## Affectation multiple

Python permet d'assigner plusieurs variables en une ligne :

```python
x, y, z = 1, 2, 3
print(x, y, z)   # 1 2 3

a = b = c = 0
print(a, b, c)   # 0 0 0
```

## Modification d'une variable

On peut modifier la valeur d'une variable en la réassignant :

```python
compteur = 0
compteur = 1
compteur = compteur + 1   # maintenant compteur = 2
compteur += 1             # raccourci : compteur = 3
```

Les opérateurs `+=`, `-=`, `*=`, `/=` sont des raccourcis très utiles.""",
                    },
                    {
                        'type': 'sandbox',
                        'title': 'Joue avec les variables',
                        'code': '# Crée des variables de différents types\nage = 20\nnom = "Kofi"\ntaille = 1.75\nest_etudiant = True\n\n# Affiche-les\nprint("Nom :", nom)\nprint("Age :", age)\nprint("Taille :", taille)\nprint("Etudiant ?", est_etudiant)\n\n# Vérifie leurs types\nprint(type(age))\nprint(type(nom))\nprint(type(taille))\nprint(type(est_etudiant))\n',
                    },
                    {
                        'type': 'mcq',
                        'title': 'Types de base',
                        'question': 'Quel est le type de la valeur `3.14` en Python ?',
                        'explanation': "Les nombres à virgule sont du type float (flottant).",
                        'choices': [
                            {'text': 'int', 'correct': False, 'feedback': 'int est pour les entiers (sans virgule).'},
                            {'text': 'float', 'correct': True, 'feedback': 'Bravo ! 3.14 est un nombre à virgule flottante.'},
                            {'text': 'str', 'correct': False, 'feedback': 'str est pour le texte. 3.14 sans guillemets est un nombre.'},
                            {'text': 'bool', 'correct': False, 'feedback': 'bool ne contient que True ou False.'},
                        ],
                    },
                    {
                        'type': 'mcq',
                        'title': 'Nommage de variables',
                        'question': "Lequel de ces noms de variable est VALIDE en Python ?",
                        'explanation': "Les noms de variables ne peuvent pas commencer par un chiffre, contenir un tiret ni un espace.",
                        'choices': [
                            {'text': '2e_variable', 'correct': False, 'feedback': 'Un nom ne peut pas commencer par un chiffre.'},
                            {'text': 'mon-age', 'correct': False, 'feedback': 'Le tiret - est interdit (utilise _).'},
                            {'text': 'prix_total', 'correct': True, 'feedback': 'Parfait ! snake_case est la convention Python.'},
                            {'text': 'mon age', 'correct': False, 'feedback': 'Pas d\'espaces dans un nom de variable.'},
                        ],
                    },
                    {
                        'type': 'fill_blank',
                        'title': 'Complète le code',
                        'instructions': 'Complète les parties manquantes du code.',
                        'text_with_blanks': "nom = {{blank_1}}\nage = {{blank_2}}\nprint({{blank_3}})",
                        'answers': {
                            'blank_1': ['"Awa"', "'Awa'"],
                            'blank_2': ['20'],
                            'blank_3': ['nom', 'age'],
                        },
                        'explanation': 'On utilise des guillemets pour le texte, un nombre sans guillemets pour age, et on affiche les variables.',
                    },
                    {
                        'type': 'code_exercise',
                        'title': 'Crée tes premières variables',
                        'instructions': """Crée trois variables :
- `nom` qui contient ton prénom (texte)
- `age` qui contient ton âge (entier)
- `taille` qui contient ta taille en mètres (flottant)

Puis affiche-les chacun sur une ligne avec `print()`.""",
                        'difficulty': 'easy',
                        'points': 10,
                        'hint': 'Utilise print() pour chaque variable.',
                        'explanation': 'On crée les trois variables avec leurs types, puis on les affiche.',
                        'starter': '# Crée tes variables ici\n\n\n# Affiche-les\n\n',
                        'solution': 'nom = "Awa"\nage = 20\ntaille = 1.70\nprint(nom)\nprint(age)\nprint(taille)\n',
                        'expected_output': 'Awa\n20\n1.7\n',
                        'eval_mode': 'contains',
                    },
                ],
            },
            {
                'order': 2,
                'title': 'Opérateurs et expressions',
                'slug': 'operateurs-expressions',
                'minutes': 25,
                'free_preview': True,
                'blocks': [
                    {
                        'type': 'text',
                        'content': """# Opérateurs et expressions

## Opérateurs arithmétiques

Python dispose des opérateurs mathématiques classiques :

| Opérateur | Description | Exemple | Résultat |
|-----------|-------------|---------|----------|
| `+` | Addition | `5 + 3` | `8` |
| `-` | Soustraction | `5 - 3` | `2` |
| `*` | Multiplication | `5 * 3` | `15` |
| `/` | Division (toujours float) | `10 / 3` | `3.333...` |
| `//` | Division entière | `10 // 3` | `3` |
| `%` | Modulo (reste) | `10 % 3` | `1` |
| `**` | Puissance | `2 ** 3` | `8` |

```python
print(7 + 2)    # 9
print(7 / 2)    # 3.5  (toujours un float)
print(7 // 2)   # 3    (quotient entier)
print(7 % 2)    # 1    (reste)
print(2 ** 10)  # 1024 (2 puissance 10)
```

## Opérateurs de comparaison

Ils renvoient un booléen `True` ou `False` :

| Opérateur | Signification | Exemple |
|-----------|---------------|---------|
| `==` | Égal à | `5 == 5` → `True` |
| `!=` | Différent de | `5 != 3` → `True` |
| `<` | Strictement inférieur | `3 < 5` → `True` |
| `>` | Strictement supérieur | `5 > 3` → `True` |
| `<=` | Inférieur ou égal | `5 <= 5` → `True` |
| `>=` | Supérieur ou égal | `4 >= 5` → `False` |

⚠ **Attention** : `=` (affectation) et `==` (comparaison) sont différents !

## Opérateurs logiques

Python possède trois opérateurs logiques :

| Opérateur | Description | Exemple |
|-----------|-------------|---------|
| `and` | ET (les deux vrais) | `True and False` → `False` |
| `or` | OU (au moins un vrai) | `True or False` → `True` |
| `not` | NON (inverse) | `not True` → `False` |

```python
age = 20
permis = True
print(age >= 18 and permis)   # True — peut conduire
print(age < 18 or not permis) # False
```

## Priorité des opérateurs

Comme en mathématiques, `*` est prioritaire sur `+` :

```python
print(2 + 3 * 4)   # 14, pas 20  (3*4=12, puis 2+12)
print((2 + 3) * 4) # 20  (parenthèses d'abord)
```

Quand tu as un doute, **mets des parenthèses** — c'est plus lisible et plus sûr.

## Opérateurs sur les chaînes

Le `+` concatène (assemble) deux chaînes, le `*` répète :

```python
prenom = "Awa"
nom = "Diallo"
print(prenom + " " + nom)   # "Awa Diallo"
print("Abc" * 3)             # "AbcAbcAbc"
```""",
                    },
                    {
                        'type': 'sandbox',
                        'title': 'Calcule en direct',
                        'code': '# Teste les différents opérateurs\nprint("Addition :", 5 + 3)\nprint("Division :", 10 / 3)\nprint("Division entiere :", 10 // 3)\nprint("Modulo :", 10 % 3)\nprint("Puissance :", 2 ** 8)\nprint()\n\n# Comparaisons\nprint("5 == 5 ?", 5 == 5)\nprint("5 > 7 ?", 5 > 7)\nprint()\n\n# Logique\nage = 20\nprint("Majeur ?", age >= 18)\nprint("Mineur ou 25 ans ?", age < 18 or age == 25)\n',
                    },
                    {
                        'type': 'mcq',
                        'title': 'Modulo',
                        'question': 'Que vaut `17 % 5` en Python ?',
                        'explanation': "Le modulo % renvoie le reste de la division entière. 17 = 5*3 + 2, donc 17 % 5 = 2.",
                        'choices': [
                            {'text': '3', 'correct': False, 'feedback': '3 est le quotient (17 // 5), pas le reste.'},
                            {'text': '2', 'correct': True, 'feedback': 'Bravo ! 17 = 5*3 + 2, le reste est 2.'},
                            {'text': '3.4', 'correct': False, 'feedback': 'C\'est le résultat de 17 / 5 (division normale).'},
                            {'text': '85', 'correct': False, 'feedback': 'C\'est 17 * 5.'},
                        ],
                    },
                    {
                        'type': 'mcq',
                        'title': 'Priorité des opérateurs',
                        'question': 'Que vaut `2 + 3 * 4` ?',
                        'explanation': "La multiplication est prioritaire sur l'addition : 3*4=12, puis 2+12=14.",
                        'choices': [
                            {'text': '20', 'correct': False, 'feedback': 'Tu as fait (2+3)*4 — mais * est prioritaire sans parenthèses.'},
                            {'text': '14', 'correct': True, 'feedback': 'Exact ! 3*4=12, puis 2+12=14.'},
                            {'text': '24', 'correct': False, 'feedback': 'Non, ce n\'est pas 2*3*4.'},
                            {'text': '11', 'correct': False, 'feedback': 'Tu as sans doute oublié la priorité de *.'},
                        ],
                    },
                    {
                        'type': 'code_exercise',
                        'title': 'Calcul de moyenne',
                        'instructions': """Trois élèves ont eu les notes suivantes :
- Awa : 14
- Kofi : 17
- Aya : 12

Calcule leur **moyenne** (somme divisée par 3) et affiche le résultat avec `print()`.""",
                        'difficulty': 'easy',
                        'points': 10,
                        'hint': 'moyenne = (14 + 17 + 12) / 3',
                        'explanation': 'On additionne les trois notes puis on divise par le nombre d\'élèves.',
                        'starter': '# Calcule la moyenne\n\n',
                        'solution': 'note1 = 14\nnote2 = 17\nnote3 = 12\nmoyenne = (note1 + note2 + note3) / 3\nprint(moyenne)\n',
                        'expected_output': '14.333333333333334\n',
                        'eval_mode': 'contains',
                    },
                    {
                        'type': 'true_false',
                        'title': 'Vrai ou Faux ? Opérateurs',
                        'instructions': 'Indique si chaque affirmation est vraie ou fausse.',
                        'explanation': "Le / donne toujours un float (même 6/2 = 3.0). Le // donne un entier.",
                        'statements': [
                            {'text': "L'expression 6 / 2 donne 3.0", 'is_correct': True},
                            {'text': "L'expression 7 // 2 donne 3.5", 'is_correct': False},
                            {'text': "L'expression 2 ** 3 donne 8", 'is_correct': True},
                            {'text': "L'expression 5 == 5 donne False", 'is_correct': False},
                        ],
                    },
                ],
            },
        ],
    },

    # ──────────────────────────────────────────────────────────────────────
    # MODULE 2 — Algorithmique : les bases
    # ──────────────────────────────────────────────────────────────────────
    {
        'order': 1,
        'title': 'Algorithmique : les bases',
        'description': "Conditions, boucles et fonctions : les fondations de tout programme.",
        'lessons': [
            {
                'order': 0,
                'title': 'Conditions (if / elif / else)',
                'slug': 'conditions-if-elif-else',
                'minutes': 30,
                'free_preview': True,
                'blocks': [
                    {
                        'type': 'text',
                        'content': """# Conditions : if / elif / else

## Qu'est-ce qu'une condition ?

Une **condition** permet à ton programme de prendre des décisions : exécuter un bloc de code seulement si une certaine situation est vraie.

## Syntaxe de base

```python
if condition:
    # code exécuté si la condition est True
    print("La condition est vraie")
```

⚠ **Trois choses importantes** :
1. La ligne `if` se termine par **`:`** (deux points)
2. Le bloc indenté (4 espaces) est exécuté si la condition est vraie
3. L'indentation est **obligatoire** en Python — c'est elle qui délimite les blocs

## if / else

```python
age = 20
if age >= 18:
    print("Tu es majeur")
else:
    print("Tu es mineur")
```

## if / elif / else

`elif` (= "else if") permet de tester plusieurs cas :

```python
note = 14

if note >= 16:
    print("Très bien")
elif note >= 14:
    print("Bien")
elif note >= 12:
    print("Assez bien")
elif note >= 10:
    print("Passable")
else:
    print("Insuffisant")
```

Les conditions sont évaluées **dans l'ordre**. Dès qu'une est vraie, le bloc correspondant est exécuté et on sort.

## Conditions composées

On combine avec `and`, `or`, `not` :

```python
age = 25
permis = True

if age >= 18 and permis:
    print("Tu peux conduire")
else:
    print("Tu ne peux pas conduire")
```

## Imbrication de conditions

On peut imbriquer les `if` :

```python
age = 20
permis = True

if age >= 18:
    if permis:
        print("Tu peux conduire")
    else:
        print("Passe ton permis d'abord")
else:
    print("Tu es trop jeune")
```

## Piège fréquent : `=` vs `==`

```python
# ❌ FAUX — c'est une affectation, pas une comparaison
if age = 18:  # SyntaxError

# ✅ CORRECT — == compare
if age == 18:
    print("Tu as pile 18 ans")
```""",
                    },
                    {
                        'type': 'sandbox',
                        'title': 'Joue avec les conditions',
                        'code': '# Modifie age et observe le résultat\nage = 17\n\nif age >= 18:\n    print("Tu es majeur")\n    print("Tu peux voter")\nelse:\n    print("Tu es mineur")\n    print("Attends encore", 18 - age, "ans")\n\nprint()  # ligne vide\n\n# Plusieurs cas\nnote = 13\nif note >= 16:\n    print("Très bien")\nelif note >= 14:\n    print("Bien")\nelif note >= 12:\n    print("Assez bien")\nelse:\n    print("À améliorer")\n',
                    },
                    {
                        'type': 'mcq',
                        'title': 'Indentation',
                        'question': "Que se passe-t-il si on oublie l'indentation après un `if` ?",
                        'explanation': "Python utilise l'indentation pour définir les blocs. Sans indentation, c'est une erreur de syntaxe.",
                        'choices': [
                            {'text': 'Le code marche quand même', 'correct': False, 'feedback': 'Non, Python refuse de lancer le programme.'},
                            {'text': 'Python lève une IndentationError', 'correct': True, 'feedback': 'Exact ! L\'indentation est obligatoire en Python.'},
                            {'text': 'Le if est ignoré', 'correct': False, 'feedback': 'Non, c\'est pire : le programme ne se lance pas.'},
                            {'text': 'Le code est exécuté deux fois', 'correct': False, 'feedback': 'Non, aucune raison.'},
                        ],
                    },
                    {
                        'type': 'mcq',
                        'title': 'elif vs if',
                        'question': "Quelle est la différence entre `if / elif / else` et plusieurs `if` successifs ?",
                        'explanation': "Avec if/elif/else, dès qu'une condition est vraie on sort. Avec plusieurs if, toutes les conditions sont testées.",
                        'choices': [
                            {'text': 'Aucune différence', 'correct': False, 'feedback': 'Si, il y en a une importante.'},
                            {'text': 'if/elif/else sort dès qu\'une condition est vraie ; plusieurs if testent tout', 'correct': True, 'feedback': 'Bravo ! C\'est la différence clé.'},
                            {'text': 'Plusieurs if sont plus rapides', 'correct': False, 'feedback': 'Non, et ce n\'est pas la bonne réponse.'},
                            {'text': 'elif ne peut être utilisé qu\'une fois', 'correct': False, 'feedback': 'On peut utiliser autant de elif qu\'on veut.'},
                        ],
                    },
                    {
                        'type': 'code_exercise',
                        'title': 'Majorité',
                        'instructions': """Demande l'âge de l'utilisateur avec `age = int(input("Ton âge ? "))` puis :
- Si `age >= 18` : affiche "Tu es majeur"
- Sinon : affiche "Tu es mineur, il te reste X ans" où X est le nombre d'années avant 18

(Pour tester, tu peux remplacer le `input()` par une valeur fixe comme `age = 15`.)""",
                        'difficulty': 'easy',
                        'points': 10,
                        'hint': 'Pense à utiliser 18 - age pour le nombre d\'années restantes.',
                        'explanation': 'On teste si age >= 18. Si oui, majeur. Sinon, mineur et on calcule 18 - age.',
                        'starter': 'age = 15  # modifie pour tester\n\n',
                        'solution': 'age = 15\nif age >= 18:\n    print("Tu es majeur")\nelse:\n    print("Tu es mineur, il te reste", 18 - age, "ans")\n',
                        'expected_output': 'Tu es mineur, il te reste 3 ans\n',
                        'eval_mode': 'exact',
                    },
                    {
                        'type': 'code_exercise',
                        'title': 'Calculatrice simple',
                        'instructions': """Crée deux variables `a = 10` et `b = 3`. Affiche :
- leur somme
- leur différence
- leur produit
- leur quotient entier (//)
- leur reste (%)

Chaque résultat sur une ligne.""",
                        'difficulty': 'easy',
                        'points': 10,
                        'hint': 'Utilise +, -, *, //, %.',
                        'explanation': 'On utilise les 5 opérateurs arithmétiques de base.',
                        'starter': 'a = 10\nb = 3\n\n',
                        'solution': 'a = 10\nb = 3\nprint(a + b)\nprint(a - b)\nprint(a * b)\nprint(a // b)\nprint(a % b)\n',
                        'expected_output': '13\n7\n30\n3\n1\n',
                        'eval_mode': 'exact',
                    },
                ],
            },
            {
                'order': 1,
                'title': 'Boucles (for / while)',
                'slug': 'boucles-for-while',
                'minutes': 35,
                'free_preview': True,
                'blocks': [
                    {
                        'type': 'text',
                        'content': """# Boucles : for et while

Les boucles permettent de **répéter** un bloc de code plusieurs fois.

## Boucle `for`

On l'utilise quand on connaît à l'avance le nombre d'itérations. En Python, `for` parcourt une séquence (liste, chaîne, `range`, etc.).

### `range(n)` — de 0 à n-1

```python
for i in range(5):
    print(i)
# Affiche : 0 1 2 3 4
```

### `range(a, b)` — de a à b-1

```python
for i in range(1, 6):
    print(i)
# Affiche : 1 2 3 4 5
```

### `range(a, b, pas)` — avec un pas

```python
for i in range(0, 10, 2):
    print(i)
# Affiche : 0 2 4 6 8
```

### Parcourir une chaîne

```python
for lettre in "Python":
    print(lettre)
# P y t h o n
```

## Boucle `while`

On l'utilise tant qu'une condition est vraie (on ne sait pas forcément combien d'itérations).

```python
n = 5
while n > 0:
    print(n)
    n -= 1
print("Décollage !")
# Affiche : 5 4 3 2 1 Décollage !
```

⚠ **Attention aux boucles infinies !** Si tu oublies de modifier la variable de condition, la boucle ne s'arrête jamais :

```python
# ❌ BOUCLE INFINIE — ne jamais faire ça
n = 5
while n > 0:
    print(n)
    # on a oublié n -= 1 → n reste 5 pour toujours
```

## `break` et `continue`

- `break` sort de la boucle immédiatement
- `continue` passe à l'itération suivante

```python
for i in range(10):
    if i == 5:
        break       # on sort à i = 5
    print(i)
# 0 1 2 3 4

for i in range(5):
    if i == 2:
        continue    # on saute i = 2
    print(i)
# 0 1 3 4
```

## `else` dans une boucle

Python permet un `else` après une boucle, exécuté si la boucle s'est terminée **sans `break`** :

```python
for i in range(5):
    print(i)
else:
    print("Boucle terminée normalement")
```

## Choisir entre `for` et `while`

| Situation | Boucle recommandée |
|-----------|--------------------|
| Nombre d'itérations connu | `for` |
| Parcourir une séquence | `for` |
| Condition d'arrêt complexe | `while` |
| Attendre un événement | `while` |""",
                    },
                    {
                        'type': 'sandbox',
                        'title': 'Expérimente les boucles',
                        'code': '# Boucle for classique\nprint("Compte de 1 à 5 :")\nfor i in range(1, 6):\n    print(i)\n\nprint()\n\n# Boucle for avec pas\nprint("Pairs de 0 à 10 :")\nfor i in range(0, 11, 2):\n    print(i)\n\nprint()\n\n# Boucle while\nprint("Compte à rebours :")\nn = 3\nwhile n > 0:\n    print(n)\n    n -= 1\nprint("Partez !")\n\nprint()\n\n# break\nprint("On s\'arrête à 3 :")\nfor i in range(10):\n    if i == 3:\n        break\n    print(i)\n',
                    },
                    {
                        'type': 'mcq',
                        'title': 'range()',
                        'question': 'Que vaut `list(range(1, 5))` ?',
                        'explanation': "range(1, 5) génère les nombres de 1 à 4 (5 est exclu).",
                        'choices': [
                            {'text': '[1, 2, 3, 4, 5]', 'correct': False, 'feedback': 'Non, 5 est exclu.'},
                            {'text': '[1, 2, 3, 4]', 'correct': True, 'feedback': 'Exact ! range(a, b) va de a à b-1.'},
                            {'text': '[0, 1, 2, 3, 4]', 'correct': False, 'feedback': 'Non, on commence à 1.'},
                            {'text': '[1, 2, 3, 4, 5, 6]', 'correct': False, 'feedback': 'Non, on s\'arrête avant 5.'},
                        ],
                    },
                    {
                        'type': 'mcq',
                        'title': 'Boucle infinie',
                        'question': "Lequel de ces codes crée une boucle infinie ?",
                        'explanation': "Si la condition de la boucle while ne devient jamais False, c'est une boucle infinie.",
                        'choices': [
                            {'text': 'while True:\\n    print("x")', 'correct': True, 'feedback': 'Exact ! True sera toujours vrai.'},
                            {'text': 'for i in range(10):\\n    print(i)', 'correct': False, 'feedback': 'Cette boucle s\'arrête à 10.'},
                            {'text': 'i = 0\\nwhile i < 5:\\n    print(i)\\n    i += 1', 'correct': False, 'feedback': 'i augmente, la boucle s\'arrête.'},
                            {'text': 'for c in "abc":\\n    print(c)', 'correct': False, 'feedback': 'Cette boucle s\'arrête après 3 lettres.'},
                        ],
                    },
                    {
                        'type': 'code_exercise',
                        'title': 'Somme de 1 à N',
                        'instructions': """Calcule la somme des entiers de 1 à 10 inclus (1 + 2 + 3 + ... + 10) avec une boucle `for`. Affiche le résultat final.

(Astuce mathématique : la réponse est 55.)""",
                        'difficulty': 'easy',
                        'points': 10,
                        'hint': 'Initialise une variable somme = 0, puis ajoute chaque i avec somme += i.',
                        'explanation': 'On initialise une variable à 0, puis on lui ajoute chaque entier de 1 à 10.',
                        'starter': 'somme = 0\n# complète la boucle\n\nprint(somme)\n',
                        'solution': 'somme = 0\nfor i in range(1, 11):\n    somme += i\nprint(somme)\n',
                        'expected_output': '55\n',
                        'eval_mode': 'exact',
                    },
                    {
                        'type': 'code_exercise',
                        'title': 'Table de multiplication',
                        'instructions': """Affiche la table de multiplication de 7, de 7×1 jusqu'à 7×10. Chaque ligne au format :
`7 x 1 = 7`
`7 x 2 = 14`
...
`7 x 10 = 70`""",
                        'difficulty': 'medium',
                        'points': 15,
                        'hint': 'Utilise une boucle for i in range(1, 11) et affiche 7, "x", i, "=", 7*i.',
                        'explanation': 'On boucle de 1 à 10, et on affiche le calcul et le résultat.',
                        'starter': '# Affiche la table de 7\n\n',
                        'solution': 'for i in range(1, 11):\n    print(7, "x", i, "=", 7 * i)\n',
                        'expected_output': '7 x 1 = 7\n7 x 2 = 14\n7 x 3 = 21\n7 x 4 = 28\n7 x 5 = 35\n7 x 6 = 42\n7 x 7 = 49\n7 x 8 = 56\n7 x 9 = 63\n7 x 10 = 70\n',
                        'eval_mode': 'exact',
                    },
                    {
                        'type': 'true_false',
                        'title': 'Vrai ou Faux ? Boucles',
                        'instructions': 'Indique si chaque affirmation est vraie ou fausse.',
                        'explanation': "range(5) va de 0 à 4 (5 exclu). break sort de la boucle, continue passe à l'itération suivante.",
                        'statements': [
                            {'text': 'range(5) génère 0, 1, 2, 3, 4', 'is_correct': True},
                            {'text': "break permet de passer à l'itération suivante", 'is_correct': False},
                            {'text': "continue permet de sortir d'une boucle", 'is_correct': False},
                            {'text': "Une boucle while peut ne jamais s'exécuter si la condition est fausse au départ", 'is_correct': True},
                        ],
                    },
                ],
            },
            {
                'order': 2,
                'title': 'Fonctions',
                'slug': 'fonctions',
                'minutes': 35,
                'free_preview': True,
                'blocks': [
                    {
                        'type': 'text',
                        'content': """# Fonctions

## Pourquoi des fonctions ?

Une **fonction** est un bloc de code réutilisable. Elle permet :
- d'**éviter la répétition** (DRY : Don't Repeat Yourself)
- de **structurer** le programme
- de **tester** chaque partie indépendamment

## Définir une fonction

On utilise le mot-clé `def` :

```python
def saluer():
    print("Bonjour !")

saluer()  # Appel de la fonction → affiche "Bonjour !"
```

## Fonction avec paramètres

```python
def saluer(nom):
    print("Bonjour", nom, "!")

saluer("Awa")    # Bonjour Awa !
saluer("Kofi")   # Bonjour Kofi !
```

## Valeur de retour : `return`

Une fonction peut **renvoyer** un résultat avec `return` :

```python
def carre(x):
    return x * x

resultat = carre(5)
print(resultat)   # 25
```

⚠ Une fois `return` exécuté, la fonction s'arrête. Le code après `return` n'est jamais exécuté.

## Plusieurs paramètres

```python
def addition(a, b):
    return a + b

print(addition(3, 5))   # 8
```

## Paramètres par défaut

On peut donner une valeur par défaut à un paramètre :

```python
def saluer(nom, message="Bonjour"):
    print(message, nom)

saluer("Awa")              # Bonjour Awa
saluer("Kofi", "Salut")    # Salut Kofi
```

⚠ Les paramètres avec valeur par défaut doivent être **en dernier**.

## Arguments nommés

On peut nommer les arguments lors de l'appel :

```python
def puissance(base, exposant):
    return base ** exposant

print(puissance(2, 10))             # 1024
print(puissance(exposant=10, base=2))  # 1024 (ordre inversé)
```

## Portée des variables

Une variable définie **dans** une fonction n'existe pas à l'extérieur :

```python
def ma_fonction():
    x = 10
    print(x)

ma_fonction()  # 10
print(x)       # ❌ NameError : x n'existe pas ici
```

## Docstring

Une bonne fonction est documentée avec une **docstring** :

```python
def aire_rectangle(longueur, largeur):
    '''Calcule l'aire d'un rectangle.

    Args:
        longueur (float): la longueur du rectangle
        largeur (float): la largeur du rectangle

    Returns:
        float: l'aire (longueur * largeur)
    '''
    return longueur * largeur
```

## Bonnes pratiques

- ✅ Nom clair (verbe + complément) : `calculer_moyenne`, `est_pair`
- ✅ Une fonction = une tâche
- ✅ Documenter avec une docstring
- ✅ Tester avec différents arguments
- ❌ Éviter les effets de bord (modifier des variables globales)""",
                    },
                    {
                        'type': 'sandbox',
                        'title': 'Écris tes propres fonctions',
                        'code': '# Définition de fonctions\ndef bonjour(nom):\n    print("Bonjour", nom + "!")\n\ndef carre(x):\n    return x * x\n\ndef est_pair(n):\n    return n % 2 == 0\n\n# Appels\nbonjour("Awa")\nbonjour("Kofi")\n\nprint(carre(5))\nprint(carre(7))\n\nprint(est_pair(4))\nprint(est_pair(7))\n',
                    },
                    {
                        'type': 'mcq',
                        'title': 'return vs print',
                        'question': "Quelle est la différence entre `return` et `print` ?",
                        'explanation': "return renvoie une valeur utilisable dans le reste du programme ; print affiche juste à l'écran.",
                        'choices': [
                            {'text': 'Aucune, ce sont des synonymes', 'correct': False, 'feedback': 'Faux, ils servent à des choses différentes.'},
                            {'text': 'return renvoie une valeur utilisable ; print affiche juste à l\'écran', 'correct': True, 'feedback': 'Exact ! return permet de récupérer le résultat.'},
                            {'text': 'print renvoie une valeur ; return affiche', 'correct': False, 'feedback': 'C\'est l\'inverse.'},
                            {'text': 'return ne marche que dans les boucles', 'correct': False, 'feedback': 'return s\'utilise dans les fonctions.'},
                        ],
                    },
                    {
                        'type': 'mcq',
                        'title': 'Paramètres par défaut',
                        'question': "Que se passe-t-il si on appelle `saluer()` avec la définition `def saluer(nom=\"Monde\"):` ?",
                        'explanation': "Quand on ne passe pas d'argument, le paramètre prend sa valeur par défaut.",
                        'choices': [
                            {'text': 'Erreur : argument manquant', 'correct': False, 'feedback': 'Non, il y a une valeur par défaut.'},
                            {'text': 'nom vaut "Monde"', 'correct': True, 'feedback': 'Bravo ! La valeur par défaut est utilisée.'},
                            {'text': 'nom vaut None', 'correct': False, 'feedback': 'Non, None ne serait utilisé que sans valeur par défaut.'},
                            {'text': 'nom vaut ""', 'correct': False, 'feedback': 'Non, la valeur par défaut est "Monde".'},
                        ],
                    },
                    {
                        'type': 'code_exercise',
                        'title': 'Fonction maximum',
                        'instructions': """Écris une fonction `maximum(a, b)` qui renvoie le plus grand des deux nombres `a` et `b`.

Teste-la avec `print(maximum(10, 20))` (doit afficher 20) et `print(maximum(50, 5))` (doit afficher 50).""",
                        'difficulty': 'easy',
                        'points': 10,
                        'hint': 'Utilise une condition if a > b: return a else: return b.',
                        'explanation': 'On compare a et b et on renvoie le plus grand.',
                        'starter': 'def maximum(a, b):\n    # complète ici\n    pass\n\nprint(maximum(10, 20))\nprint(maximum(50, 5))\n',
                        'solution': 'def maximum(a, b):\n    if a > b:\n        return a\n    else:\n        return b\n\nprint(maximum(10, 20))\nprint(maximum(50, 5))\n',
                        'expected_output': '20\n50\n',
                        'eval_mode': 'exact',
                    },
                    {
                        'type': 'code_exercise',
                        'title': 'Fonction factorielle',
                        'instructions': """Écris une fonction `factorielle(n)` qui calcule la factorielle de n (le produit 1 × 2 × 3 × ... × n).

Convention : factorielle(0) = 1.

Teste avec `print(factorielle(5))` qui doit afficher `120` (car 1×2×3×4×5 = 120).""",
                        'difficulty': 'medium',
                        'points': 15,
                        'hint': 'Initialise resultat = 1, puis multiplie par chaque i de 1 à n avec une boucle for.',
                        'explanation': 'On accumule le produit des entiers de 1 à n dans une variable.',
                        'starter': 'def factorielle(n):\n    # complète\n    pass\n\nprint(factorielle(5))\n',
                        'solution': 'def factorielle(n):\n    resultat = 1\n    for i in range(1, n + 1):\n        resultat *= i\n    return resultat\n\nprint(factorielle(5))\n',
                        'expected_output': '120\n',
                        'eval_mode': 'exact',
                    },
                    {
                        'type': 'fill_blank',
                        'title': 'Complète la fonction',
                        'instructions': 'Complète la fonction qui calcule le double.',
                        'text_with_blanks': "{{blank_1}} double(x):\n    {{blank_2}} x * 2",
                        'answers': {
                            'blank_1': ['def'],
                            'blank_2': ['return'],
                        },
                        'explanation': 'On définit la fonction avec def, puis on renvoie le résultat avec return.',
                    },
                ],
            },
        ],
    },

    # ──────────────────────────────────────────────────────────────────────
    # MODULE 3 — Structures de données
    # ──────────────────────────────────────────────────────────────────────
    {
        'order': 2,
        'title': 'Structures de données',
        'description': "Listes, tuples, dictionnaires et chaînes : organiser tes données.",
        'lessons': [
            {
                'order': 0,
                'title': 'Listes',
                'slug': 'listes',
                'minutes': 35,
                'free_preview': True,
                'blocks': [
                    {
                        'type': 'text',
                        'content': """# Listes

## Qu'est-ce qu'une liste ?

Une **liste** est une collection ordonnée et modifiable d'éléments. C'est la structure de données la plus utilisée en Python.

```python
fruits = ["pomme", "banane", "cerise"]
notes = [14, 17, 12, 19]
mixte = [1, "deux", 3.0, True]
vide = []
```

## Accès aux éléments

On accède à un élément par son **index** (commence à 0) :

```python
fruits = ["pomme", "banane", "cerise"]
print(fruits[0])   # "pomme"
print(fruits[1])   # "banane"
print(fruits[-1])  # "cerise" (dernier élément)
print(fruits[-2])  # "banane" (avant-dernier)
```

## Modification

Les listes sont **mutables** (modifiables) :

```python
fruits = ["pomme", "banane", "cerise"]
fruits[0] = "abricot"
print(fruits)  # ['abricot', 'banane', 'cerise']
```

## Tranchage (slicing)

On extrait une portion avec `[début:fin]` (fin exclu) :

```python
notes = [10, 12, 14, 16, 18, 20]
print(notes[1:4])    # [12, 14, 16]
print(notes[:3])     # [10, 12, 14]  (du début à 3)
print(notes[3:])     # [16, 18, 20]  (de 3 à la fin)
print(notes[:])      # toute la liste (copie)
print(notes[::2])    # [10, 14, 18]  (tous les 2 éléments)
```

## Méthodes courantes

```python
fruits = ["pomme", "banane"]

fruits.append("cerise")        # ajoute à la fin
print(fruits)                  # ['pomme', 'banane', 'cerise']

fruits.insert(1, "kiwi")       # insère à l'index 1
print(fruits)                  # ['pomme', 'kiwi', 'banane', 'cerise']

fruits.remove("kiwi")          # supprime la première occurrence
print(fruits)                  # ['pomme', 'banane', 'cerise']

dernier = fruits.pop()         # supprime et renvoie le dernier
print(dernier)                 # 'cerise'
print(fruits)                  # ['pomme', 'banane']

print(len(fruits))             # 2 (longueur)
print("pomme" in fruits)       # True (appartenance)

fruits.sort()                  # trie sur place
fruits.reverse()               # inverse
```

## Parcourir une liste

```python
fruits = ["pomme", "banane", "cerise"]

# Par les éléments
for fruit in fruits:
    print(fruit)

# Par les index
for i in range(len(fruits)):
    print(i, fruits[i])

# enumerate : index + élément
for i, fruit in enumerate(fruits):
    print(i, fruit)
```

## Listes de listes

Une liste peut contenir d'autres listes (matrice) :

```python
matrice = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9]
]
print(matrice[1][2])   # 6 (ligne 1, colonne 2)
```""",
                    },
                    {
                        'type': 'sandbox',
                        'title': 'Manipule les listes',
                        'code': '# Création\nfruits = ["pomme", "banane", "cerise"]\nprint(fruits)\n\n# Accès\nprint("Premier :", fruits[0])\nprint("Dernier :", fruits[-1])\n\n# Modification\nfruits[0] = "abricot"\nprint("Après modif :", fruits)\n\n# Ajout\nfruits.append("kiwi")\nprint("Après append :", fruits)\n\n# Longueur et appartenance\nprint("Longueur :", len(fruits))\nprint("banane dedans ?", "banane" in fruits)\n\n# Parcours\nfor i, f in enumerate(fruits):\n    print(i, f)\n',
                    },
                    {
                        'type': 'mcq',
                        'title': 'Index des listes',
                        'question': "Que vaut `liste[2]` si `liste = ['a', 'b', 'c', 'd']` ?",
                        'explanation': "Les index commencent à 0. Donc liste[0]='a', liste[1]='b', liste[2]='c'.",
                        'choices': [
                            {'text': "'a'", 'correct': False, 'feedback': 'Non, c\'est liste[0].'},
                            {'text': "'b'", 'correct': False, 'feedback': 'Non, c\'est liste[1].'},
                            {'text': "'c'", 'correct': True, 'feedback': 'Exact ! Index 2 = 3e élément.'},
                            {'text': "'d'", 'correct': False, 'feedback': 'Non, c\'est liste[3].'},
                        ],
                    },
                    {
                        'type': 'mcq',
                        'title': 'Slicing',
                        'question': "Que vaut `notes[1:4]` si `notes = [10, 12, 14, 16, 18, 20]` ?",
                        'explanation': "notes[1:4] prend les éléments d'index 1, 2, 3 (4 exclu).",
                        'choices': [
                            {'text': '[10, 12, 14]', 'correct': False, 'feedback': 'Non, on commence à l\'index 1, pas 0.'},
                            {'text': '[12, 14, 16]', 'correct': True, 'feedback': 'Bravo ! Index 1, 2, 3.'},
                            {'text': '[12, 14, 16, 18]', 'correct': False, 'feedback': 'Non, 4 est exclu.'},
                            {'text': '[14, 16, 18]', 'correct': False, 'feedback': 'Non, on commence à 1.'},
                        ],
                    },
                    {
                        'type': 'code_exercise',
                        'title': 'Somme d\'une liste',
                        'instructions': """Calcule la somme de la liste `notes = [12, 15, 8, 17, 14]` en utilisant une boucle `for`. Affiche le résultat.

(Réponse attendue : 66)""",
                        'difficulty': 'easy',
                        'points': 10,
                        'hint': 'Initialise somme = 0 puis ajoute chaque note avec somme += note.',
                        'explanation': 'On parcourt chaque élément et on l\'ajoute à un accumulateur.',
                        'starter': 'notes = [12, 15, 8, 17, 14]\n\n',
                        'solution': 'notes = [12, 15, 8, 17, 14]\nsomme = 0\nfor note in notes:\n    somme += note\nprint(somme)\n',
                        'expected_output': '66\n',
                        'eval_mode': 'exact',
                    },
                    {
                        'type': 'code_exercise',
                        'title': 'Maximum d\'une liste',
                        'instructions': """Écris une fonction `maximum(liste)` qui renvoie le plus grand élément d'une liste de nombres.

Teste avec `print(maximum([3, 7, 2, 9, 5]))` qui doit afficher `9`.""",
                        'difficulty': 'medium',
                        'points': 15,
                        'hint': 'Initialise max = liste[0], puis compare chaque élément.',
                        'explanation': 'On commence avec le premier élément comme max, puis on met à jour si on trouve plus grand.',
                        'starter': 'def maximum(liste):\n    # complète\n    pass\n\nprint(maximum([3, 7, 2, 9, 5]))\n',
                        'solution': 'def maximum(liste):\n    max_val = liste[0]\n    for x in liste:\n        if x > max_val:\n            max_val = x\n    return max_val\n\nprint(maximum([3, 7, 2, 9, 5]))\n',
                        'expected_output': '9\n',
                        'eval_mode': 'exact',
                    },
                    {
                        'type': 'true_false',
                        'title': 'Vrai ou Faux ? Listes',
                        'instructions': 'Indique si chaque affirmation est vraie ou fausse.',
                        'explanation': "Les listes sont mutables. append ajoute à la fin. len() donne la longueur.",
                        'statements': [
                            {'text': "Les listes sont mutables en Python", 'is_correct': True},
                            {'text': "append() ajoute un élément au début de la liste", 'is_correct': False},
                            {'text': "len([1, 2, 3]) renvoie 3", 'is_correct': True},
                            {'text': "liste[-1] accède au premier élément", 'is_correct': False},
                        ],
                    },
                ],
            },
            {
                'order': 1,
                'title': 'Tuples et dictionnaires',
                'slug': 'tuples-dictionnaires',
                'minutes': 30,
                'free_preview': True,
                'blocks': [
                    {
                        'type': 'text',
                        'content': """# Tuples et dictionnaires

## Tuples

Un **tuple** est comme une liste mais **immuable** (non modifiable). On l'écrit avec des parenthèses :

```python
point = (3, 5)
couleur = (255, 128, 0)
singleton = (42,)   # tuple à un élément (la virgule est obligatoire)
```

### Pourquoi utiliser un tuple ?

- **Protéger des données** qui ne doivent pas changer
- Plus **rapide** qu'une liste
- Sert souvent à **regrouper des valeurs liées** (coordonnées, RGB, date...)

### Opérations

```python
point = (3, 5)
print(point[0])     # 3
print(point[1])     # 5
print(len(point))   # 2

# ❌ Impossible de modifier
# point[0] = 10  → TypeError

# Déballage (unpacking)
x, y = point
print(x)   # 3
print(y)   # 5
```

### Échange de variables

Le tuple permet l'échange élégant :

```python
a, b = 1, 2
a, b = b, a   # a=2, b=1
```

## Dictionnaires

Un **dictionnaire** est une collection de paires **clé → valeur**. On l'écrit avec des accolades :

```python
etudiant = {
    "nom": "Awa",
    "age": 20,
    "notes": [14, 17, 12],
    "majeur": True
}
```

### Accès aux valeurs

```python
print(etudiant["nom"])    # "Awa"
print(etudiant["age"])    # 20

# Avec .get() — ne plante pas si la clé n'existe pas
print(etudiant.get("ville", "Inconnue"))   # "Inconnue"
```

### Modification

```python
etudiant["age"] = 21            # modifie une valeur
etudiant["ville"] = "Lomé"      # ajoute une nouvelle paire
del etudiant["majeur"]          # supprime une paire
```

### Parcours

```python
# Parcours des clés
for cle in etudiant:
    print(cle)

# Parcours des valeurs
for valeur in etudiant.values():
    print(valeur)

# Parcours des paires
for cle, valeur in etudiant.items():
    print(cle, "->", valeur)
```

### Méthodes utiles

```python
print(len(etudiant))           # nombre de paires
print("nom" in etudiant)       # True (clé présente)
etudiant.update({"pays": "Togo"})  # ajoute plusieurs paires
```

## Quand utiliser quoi ?

| Structure | Use case |
|-----------|----------|
| `list` | Collection ordonnée modifiable |
| `tuple` | Données liées immuables (coordonnées, RGB) |
| `dict` | Association clé → valeur""",
                    },
                    {
                        'type': 'sandbox',
                        'title': 'Tuples et dictionnaires',
                        'code': '# Tuple\npoint = (3, 5)\nprint("Point :", point)\nprint("x =", point[0], "y =", point[1])\nx, y = point  # unpacking\nprint("x =", x, "y =", y)\n\nprint()\n\n# Dictionnaire\netudiant = {\n    "nom": "Awa",\n    "age": 20,\n    "notes": [14, 17, 12]\n}\nprint("Nom :", etudiant["nom"])\nprint("Age :", etudiant["age"])\nprint("Ville :", etudiant.get("ville", "Non renseignée"))\n\n# Modification\netudiant["age"] = 21\netudiant["ville"] = "Lomé"\nprint("Après modif :", etudiant)\n\n# Parcours\nfor cle, valeur in etudiant.items():\n    print(cle, "->", valeur)\n',
                    },
                    {
                        'type': 'mcq',
                        'title': 'Tuples vs listes',
                        'question': "Quelle est la principale différence entre un tuple et une liste ?",
                        'explanation': "Un tuple est immuable (non modifiable après création), une liste est mutable.",
                        'choices': [
                            {'text': 'Un tuple est immuable, une liste est mutable', 'correct': True, 'feedback': 'Exact ! On ne peut pas modifier un tuple après sa création.'},
                            {'text': 'Un tuple est plus long', 'correct': False, 'feedback': 'Non, c\'est l\'inverse.'},
                            {'text': 'Un tuple ne contient que des nombres', 'correct': False, 'feedback': 'Faux, un tuple peut contenir n\'importe quel type.'},
                            {'text': 'Une liste ne peut pas être parcourue', 'correct': False, 'feedback': 'Faux.'},
                        ],
                    },
                    {
                        'type': 'mcq',
                        'title': 'Dictionnaires',
                        'question': "Comment accède-t-on à la valeur de la clé 'nom' dans `d = {'nom': 'Awa'}` ?",
                        'explanation': "On utilise la syntaxe d['nom'] ou d.get('nom').",
                        'choices': [
                            {'text': "d.nom", 'correct': False, 'feedback': 'Non, cette syntaxe marche pour les attributs d\'objet, pas les dict.'},
                            {'text': "d['nom']", 'correct': True, 'feedback': 'Bravo ! On utilise les crochets avec la clé.'},
                            {'text': "d->nom", 'correct': False, 'feedback': 'Cette syntaxe n\'existe pas en Python.'},
                            {'text': "d(nom)", 'correct': False, 'feedback': 'Les dict ne s\'appellent pas comme des fonctions.'},
                        ],
                    },
                    {
                        'type': 'code_exercise',
                        'title': 'Carnet de notes',
                        'instructions': """Crée un dictionnaire `notes` avec les clés suivantes :
- "Awa" : 14
- "Kofi" : 17
- "Aya" : 12

Affiche la note de Kofi (avec `print(notes["Kofi"])`).""",
                        'difficulty': 'easy',
                        'points': 10,
                        'hint': 'Définis le dict avec des accolades { }.',
                        'explanation': 'On crée le dictionnaire puis on accède à la valeur de la clé "Kofi".',
                        'starter': '# Crée le dictionnaire\n\n\n# Affiche la note de Kofi\n',
                        'solution': 'notes = {"Awa": 14, "Kofi": 17, "Aya": 12}\nprint(notes["Kofi"])\n',
                        'expected_output': '17\n',
                        'eval_mode': 'exact',
                    },
                    {
                        'type': 'fill_blank',
                        'title': 'Complète le dictionnaire',
                        'instructions': 'Complète pour accéder à la valeur de la clé "age".',
                        'text_with_blanks': "etudiant = {\"nom\": \"Awa\", \"age\": 20}\nprint(etudiant{{blank_1}})",
                        'answers': {
                            'blank_1': ['["age"]', "['age']"],
                        },
                        'explanation': 'On accède à une valeur de dict avec dict[cle] en utilisant des crochets.',
                    },
                ],
            },
            {
                'order': 2,
                'title': 'Chaînes de caractères',
                'slug': 'chaines-caracteres',
                'minutes': 25,
                'free_preview': True,
                'blocks': [
                    {
                        'type': 'text',
                        'content': """# Chaînes de caractères

Les **chaînes** (`str`) représentent du texte. Elles sont très puissantes en Python.

## Création

```python
# Plusieurs syntaxes équivalentes
a = "Bonjour"
b = 'Bonjour'
c = '''Plusieurs
lignes'''
d = 'L\'apostrophe'   # échappement avec \
```

## Concaténation et répétition

```python
print("Bonjour" + " " + "Awa")  # "Bonjour Awa"
print("Abc" * 3)                  # "AbcAbcAbc"
```

## Index et slicing

Comme les listes :

```python
s = "Python"
print(s[0])      # "P"
print(s[-1])     # "n"
print(s[1:4])    # "yth"
print(s[:3])     # "Pyt"
```

## Longueur

```python
print(len("Python"))   # 6
```

## Parcours

```python
for lettre in "Python":
    print(lettre)
# P y t h o n
```

## Méthodes utiles

```python
s = "  Bonjour Awa  "

print(s.upper())        # "  BONJOUR AWA  "
print(s.lower())        # "  bonjour awa  "
print(s.strip())        # "Bonjour Awa" (enlève les espaces au début/fin)
print(s.replace("Awa", "Kofi"))  # "  Bonjour Kofi  "
print(s.split())        # ["Bonjour", "Awa"] (découpe par espaces)
print("-".join(["a", "b", "c"]))  # "a-b-c"

print("Awa" in "Bonjour Awa")   # True (sous-chaîne)
print("awa".startswith("a"))    # True
print("awa".endswith("wa"))     # True
```

## Formatage : f-strings

La façon moderne de formater du texte :

```python
nom = "Awa"
age = 20
print(f"Je m'appelle {nom} et j'ai {age} ans.")
# "Je m'appelle Awa et j'ai 20 ans."

# Expressions dans les f-strings
print(f"Dans 5 ans j'aurai {age + 5} ans.")

# Formatage de nombres
pi = 3.14159
print(f"Pi vaut environ {pi:.2f}")   # "Pi vaut environ 3.14"
```

## Vérifier le type

```python
s = "123"
print(s.isdigit())   # True (que des chiffres)
print(s.isalpha())   # False (que des lettres ? non)
print("abc".isalpha())  # True
```""",
                    },
                    {
                        'type': 'sandbox',
                        'title': 'Joue avec les chaînes',
                        'code': 's = "Numeria Institute"\nprint(s.upper())\nprint(s.lower())\nprint(len(s))\nprint(s[0])           # premier caractère\nprint(s[-1])          # dernier\nprint(s[:7])          # "Numeria"\nprint(s.split())      # découpe\n\n# f-strings\nnom = "Awa"\nage = 20\nprint(f"Bonjour {nom}, tu as {age} ans")\n\n# Parcours\nfor lettre in "Python":\n    print(lettre, end=" ")\nprint()\n',
                    },
                    {
                        'type': 'mcq',
                        'title': 'f-strings',
                        'question': "Que produit `f\"{2 + 3}\"` ?",
                        'explanation': "Les f-strings évaluent les expressions entre {} et les convertissent en chaîne.",
                        'choices': [
                            {'text': '"{2 + 3}"', 'correct': False, 'feedback': 'Non, les {} sont évalués dans une f-string.'},
                            {'text': '"5"', 'correct': True, 'feedback': 'Exact ! 2+3=5, converti en chaîne.'},
                            {'text': '5 (entier)', 'correct': False, 'feedback': 'Non, c\'est une chaîne "5".'},
                            {'text': 'Erreur', 'correct': False, 'feedback': 'Non, c\'est valide.'},
                        ],
                    },
                    {
                        'type': 'code_exercise',
                        'title': 'Compte les voyelles',
                        'instructions': """Compte le nombre de voyelles (a, e, i, o, u, y) dans la chaîne `mot = "numeria"` et affiche le résultat.

(Réponse attendue : 4 — u, e, i, a)""",
                        'difficulty': 'medium',
                        'points': 15,
                        'hint': 'Parcours chaque lettre avec for lettre in mot: et teste si elle est dans "aeiouy".',
                        'explanation': 'On parcourt chaque lettre, on vérifie si c\'est une voyelle, on incrémente un compteur.',
                        'starter': 'mot = "numeria"\n# complète\n\n',
                        'solution': 'mot = "numeria"\ncompteur = 0\nfor lettre in mot:\n    if lettre in "aeiouyAEIOUY":\n        compteur += 1\nprint(compteur)\n',
                        'expected_output': '4\n',
                        'eval_mode': 'exact',
                    },
                ],
            },
        ],
    },

    # ──────────────────────────────────────────────────────────────────────
    # MODULE 4 — Algorithmique avancée
    # ──────────────────────────────────────────────────────────────────────
    {
        'order': 3,
        'title': 'Algorithmique avancée',
        'description': "Récursivité, algorithmes de tri et complexité : pense comme un informaticien.",
        'lessons': [
            {
                'order': 0,
                'title': 'Récursivité',
                'slug': 'recursivite',
                'minutes': 35,
                'free_preview': True,
                'blocks': [
                    {
                        'type': 'text',
                        'content': """# Récursivité

## Qu'est-ce que la récursivité ?

Une fonction **récursive** est une fonction qui **s'appelle elle-même**. C'est une façon élégante de résoudre certains problèmes.

## Anatomy d'une fonction récursive

Toute fonction récursive doit avoir :
1. Un **cas de base** : la condition d'arrêt (sinon → récursion infinie)
2. Un **cas récursif** : la fonction s'appelle avec un problème plus petit

```python
def compte_rebours(n):
    if n <= 0:                  # ← cas de base
        print("Partez !")
        return
    print(n)
    compte_rebours(n - 1)       # ← cas récursif (vers le cas de base)

compte_rebours(3)
# 3
# 2
# 1
# Partez !
```

## Exemple classique : factorielle

$$n! = n \\times (n-1) \\times (n-2) \\times \\ldots \\times 1$$

$$0! = 1 \\quad \\text{(cas de base)}$$

$$n! = n \\times (n-1)! \\quad \\text{(cas récursif)}$$

```python
def factorielle(n):
    if n == 0:                  # cas de base
        return 1
    return n * factorielle(n - 1)   # cas récursif

print(factorielle(5))   # 120 = 5 * 4 * 3 * 2 * 1
```

## Suite de Fibonacci

$$F_0 = 0, \\quad F_1 = 1, \\quad F_n = F_{n-1} + F_{n-2}$$

```python
def fibonacci(n):
    if n == 0: return 0
    if n == 1: return 1
    return fibonacci(n - 1) + fibonacci(n - 2)

print(fibonacci(10))   # 55
```

⚠ Cette version est **très lente** pour n grand (exponentielle). On peut l'optimiser avec de la **mémoïsation**.

## Puissance récursive

$$x^n = x \\times x^{n-1}$$

```python
def puissance(x, n):
    if n == 0:
        return 1
    return x * puissance(x, n - 1)

print(puissance(2, 10))   # 1024
```

## Pièges à éviter

1. **Oublier le cas de base** → `RecursionError` (récursion infinie)
2. **Cas récursif qui ne se rapproche pas du cas de base** → récursion infinie
3. **Trop de profondeur** → `RecursionError` (limite ~1000 par défaut en Python)

## Récursivité vs itération

Tout problème récursif peut être écrit itérativement (avec une boucle) :

```python
# Itératif
def factorielle_iter(n):
    resultat = 1
    for i in range(1, n + 1):
        resultat *= i
    return resultat

# Récursif
def factorielle_rec(n):
    if n == 0:
        return 1
    return n * factorielle_rec(n - 1)
```

| Critère | Récursif | Itératif |
|---------|----------|----------|
| Lisibilité | ✅ Souvent plus clair | Variable selon cas |
| Performance | ❌ Plus lent (pile) | ✅ Plus rapide |
| Mémoire | ❌ Pile d'appels | ✅ Constant |
| Limite | ❌ ~1000 appels | ✅ Aucune |

**Choisir la récursivité quand** : la structure du problème est naturellement récursive (arbres, fractales, diviser-pour-régner).""",
                    },
                    {
                        'type': 'sandbox',
                        'title': 'Teste la récursivité',
                        'code': '# Factorielle récursive\ndef factorielle(n):\n    if n == 0:\n        return 1\n    return n * factorielle(n - 1)\n\nprint("5! =", factorielle(5))\nprint("10! =", factorielle(10))\n\n# Fibonacci récursif\ndef fib(n):\n    if n == 0: return 0\n    if n == 1: return 1\n    return fib(n - 1) + fib(n - 2)\n\nfor i in range(10):\n    print(f"fib({i}) = {fib(i)}")\n',
                    },
                    {
                        'type': 'mcq',
                        'title': 'Cas de base',
                        'question': "Pourquoi une fonction récursive a-t-elle absolument besoin d'un cas de base ?",
                        'explanation': "Sans cas de base, la fonction s'appelle indéfiniment → RecursionError.",
                        'choices': [
                            {'text': 'Pour optimiser la vitesse', 'correct': False, 'feedback': 'Non, c\'est plus fondamental que ça.'},
                            {'text': 'Pour arrêter la récursion (sinon boucle infinie)', 'correct': True, 'feedback': 'Exact ! Sans cas de base, la fonction s\'appelle pour toujours.'},
                            {'text': 'Pour renvoyer une chaîne', 'correct': False, 'feedback': 'Non, le type de retour n\'a rien à voir.'},
                            {'text': 'Pour lire des fichiers', 'correct': False, 'feedback': 'Aucun rapport.'},
                        ],
                    },
                    {
                        'type': 'code_exercise',
                        'title': 'Factorielle récursive',
                        'instructions': """Écris une fonction récursive `factorielle(n)` qui calcule n!.

Cas de base : factorielle(0) = 1
Cas récursif : factorielle(n) = n × factorielle(n-1)

Teste avec `print(factorielle(6))` qui doit afficher `720`.""",
                        'difficulty': 'medium',
                        'points': 15,
                        'hint': 'Pense aux deux cas : if n == 0: return 1 ; else: return n * factorielle(n-1).',
                        'explanation': 'La récursivité imite la définition mathématique : 0! = 1, n! = n * (n-1)!.',
                        'starter': 'def factorielle(n):\n    # complète\n    pass\n\nprint(factorielle(6))\n',
                        'solution': 'def factorielle(n):\n    if n == 0:\n        return 1\n    return n * factorielle(n - 1)\n\nprint(factorielle(6))\n',
                        'expected_output': '720\n',
                        'eval_mode': 'exact',
                    },
                    {
                        'type': 'code_exercise',
                        'title': 'Somme récursive 1+2+...+n',
                        'instructions': """Écris une fonction récursive `somme(n)` qui calcule 1 + 2 + 3 + ... + n.

Cas de base : somme(0) = 0
Cas récursif : somme(n) = n + somme(n-1)

Teste avec `print(somme(100))` qui doit afficher `5050`.""",
                        'difficulty': 'medium',
                        'points': 15,
                        'hint': 'Même structure que factorielle, mais avec + au lieu de *.',
                        'explanation': 'somme(n) = n + somme(n-1) imite la définition mathématique.',
                        'starter': 'def somme(n):\n    # complète\n    pass\n\nprint(somme(100))\n',
                        'solution': 'def somme(n):\n    if n == 0:\n        return 0\n    return n + somme(n - 1)\n\nprint(somme(100))\n',
                        'expected_output': '5050\n',
                        'eval_mode': 'exact',
                    },
                    {
                        'type': 'true_false',
                        'title': 'Vrai ou Faux ? Récursivité',
                        'instructions': 'Indique si chaque affirmation est vraie ou fausse.',
                        'explanation': "Une fonction récursive doit avoir un cas de base. Python limite la profondeur à ~1000 appels.",
                        'statements': [
                            {'text': "Une fonction récursive doit toujours avoir un cas de base", 'is_correct': True},
                            {'text': "La récursivité est toujours plus rapide que l'itération", 'is_correct': False},
                            {'text': "Tout problème récursif peut être résolu itérativement", 'is_correct': True},
                            {'text': "factorielle(0) = 0", 'is_correct': False},
                        ],
                    },
                ],
            },
            {
                'order': 1,
                'title': 'Algorithmes de tri',
                'slug': 'algorithmes-tri',
                'minutes': 40,
                'free_preview': True,
                'blocks': [
                    {
                        'type': 'text',
                        'content': """# Algorithmes de tri

Trier des données est une opération fondamentale en informatique. On va découvrir trois algorithmes classiques.

## Tri par sélection

**Idée** : à chaque tour, on trouve le minimum et on l'échange avec l'élément courant.

```python
def tri_selection(liste):
    n = len(liste)
    for i in range(n):
        # Trouver le min dans liste[i:]
        min_idx = i
        for j in range(i + 1, n):
            if liste[j] < liste[min_idx]:
                min_idx = j
        # Échanger
        liste[i], liste[min_idx] = liste[min_idx], liste[i]
    return liste

print(tri_selection([5, 2, 8, 1, 9, 3]))
# [1, 2, 3, 5, 8, 9]
```

**Complexité** : $O(n^2)$ — lent sur de grandes listes.

## Tri à bulles

**Idée** : on compare les éléments adjacents et on les échange s'ils sont dans le mauvais ordre. Les plus grands "remontent" comme des bulles.

```python
def tri_bulles(liste):
    n = len(liste)
    for i in range(n):
        for j in range(0, n - i - 1):
            if liste[j] > liste[j + 1]:
                liste[j], liste[j + 1] = liste[j + 1], liste[j]
    return liste

print(tri_bulles([5, 2, 8, 1, 9, 3]))
```

**Complexité** : $O(n^2)$.

## Tri par insertion

**Idée** : comme quand on trie des cartes en main — on insère chaque nouvelle carte à sa place.

```python
def tri_insertion(liste):
    for i in range(1, len(liste)):
        cle = liste[i]
        j = i - 1
        while j >= 0 and liste[j] > cle:
            liste[j + 1] = liste[j]
            j -= 1
        liste[j + 1] = cle
    return liste

print(tri_insertion([5, 2, 8, 1, 9, 3]))
```

**Complexité** : $O(n^2)$ dans le pire cas, $O(n)$ sur une liste déjà triée.

## Tri rapide (Quicksort) — diviser pour régner

**Idée** : choisir un **pivot**, partitionner la liste en deux (éléments ≤ pivot et > pivot), trier récursivement chaque moitié.

```python
def tri_rapide(liste):
    if len(liste) <= 1:
        return liste
    pivot = liste[0]
    gauche = [x for x in liste[1:] if x <= pivot]
    droite = [x for x in liste[1:] if x > pivot]
    return tri_rapide(gauche) + [pivot] + tri_rapide(droite)

print(tri_rapide([5, 2, 8, 1, 9, 3]))
```

**Complexité** : $O(n \\log n)$ en moyenne, $O(n^2)$ dans le pire cas.

## Python a déjà tout prévu

En pratique, on utilise `sorted()` ou `.sort()` :

```python
liste = [5, 2, 8, 1, 9, 3]
print(sorted(liste))      # [1, 2, 3, 5, 8, 9] — nouvelle liste
liste.sort()              # trie sur place
liste.sort(reverse=True)  # tri décroissant
```

Python utilise **Timsort**, un algorithme optimisé en $O(n \\log n)$.

## Tableau comparatif

| Algorithme | Complexité moyenne | Stable ? | En place ? |
|------------|--------------------|----------|------------|
| Sélection | $O(n^2)$ | Non | Oui |
| Bulles | $O(n^2)$ | Oui | Oui |
| Insertion | $O(n^2)$ | Oui | Oui |
| Rapide | $O(n \\log n)$ | Non | Oui |
| Timsort (Python) | $O(n \\log n)$ | Oui | Oui |

**Stable** : conserve l'ordre des éléments égaux.
**En place** : ne crée pas de copie.""",
                    },
                    {
                        'type': 'sandbox',
                        'title': 'Teste les tris',
                        'code': '# Tri par sélection\ndef tri_selection(liste):\n    n = len(liste)\n    for i in range(n):\n        min_idx = i\n        for j in range(i + 1, n):\n            if liste[j] < liste[min_idx]:\n                min_idx = j\n        liste[i], liste[min_idx] = liste[min_idx], liste[i]\n    return liste\n\n# Tri rapide\ndef tri_rapide(liste):\n    if len(liste) <= 1:\n        return liste\n    pivot = liste[0]\n    g = [x for x in liste[1:] if x <= pivot]\n    d = [x for x in liste[1:] if x > pivot]\n    return tri_rapide(g) + [pivot] + tri_rapide(d)\n\ndata = [5, 2, 8, 1, 9, 3, 7, 4, 6]\nprint("Sélection :", tri_selection(data[:]))\nprint("Rapide   :", tri_rapide(data[:]))\nprint("Python   :", sorted(data))\n',
                    },
                    {
                        'type': 'mcq',
                        'title': 'Tri par sélection',
                        'question': "Quelle est la complexité du tri par sélection ?",
                        'explanation': "Le tri par sélection a deux boucles imbriquées → complexité quadratique O(n²).",
                        'choices': [
                            {'text': 'O(n)', 'correct': False, 'feedback': 'Non, ce serait linéaire (un seul parcours).'},
                            {'text': 'O(n log n)', 'correct': False, 'feedback': 'Non, c\'est la complexité des tris rapides (Timsort, quicksort).'},
                            {'text': 'O(n²)', 'correct': True, 'feedback': 'Exact ! Deux boucles imbriquées.'},
                            {'text': 'O(2^n)', 'correct': False, 'feedback': 'Non, ce serait exponentiel.'},
                        ],
                    },
                    {
                        'type': 'mcq',
                        'title': 'sorted() vs .sort()',
                        'question': "Quelle est la différence entre `sorted(liste)` et `liste.sort()` ?",
                        'explanation': "sorted() renvoie une nouvelle liste triée ; .sort() trie la liste sur place (en la modifiant).",
                        'choices': [
                            {'text': 'Aucune différence', 'correct': False, 'feedback': 'Si, il y en a une.'},
                            {'text': 'sorted() renvoie une nouvelle liste ; .sort() modifie sur place', 'correct': True, 'feedback': 'Exact !'},
                            {'text': '.sort() est plus rapide', 'correct': False, 'feedback': 'Elles sont aussi rapides l\'une que l\'autre.'},
                            {'text': 'sorted() ne marche qu\'avec des nombres', 'correct': False, 'feedback': 'Faux, sorted() trie n\'importe quoi.'},
                        ],
                    },
                    {
                        'type': 'code_exercise',
                        'title': 'Tri par sélection',
                        'instructions': """Implémente le **tri par sélection** sur la liste `[5, 2, 8, 1, 9, 3]` et affiche le résultat trié.

Le principe : à chaque tour i, trouver le minimum dans `liste[i:]` et l'échanger avec `liste[i]`.""",
                        'difficulty': 'hard',
                        'points': 20,
                        'hint': 'Deux boucles : for i in range(n) ; for j in range(i+1, n) ; trouve min_idx et échange.',
                        'explanation': 'On parcourt la liste, à chaque position on trouve le min de la suite et on échange.',
                        'starter': 'def tri_selection(liste):\n    n = len(liste)\n    # complète\n    return liste\n\nprint(tri_selection([5, 2, 8, 1, 9, 3]))\n',
                        'solution': 'def tri_selection(liste):\n    n = len(liste)\n    for i in range(n):\n        min_idx = i\n        for j in range(i + 1, n):\n            if liste[j] < liste[min_idx]:\n                min_idx = j\n        liste[i], liste[min_idx] = liste[min_idx], liste[i]\n    return liste\n\nprint(tri_selection([5, 2, 8, 1, 9, 3]))\n',
                        'expected_output': '[1, 2, 3, 5, 8, 9]\n',
                        'eval_mode': 'exact',
                    },
                ],
            },
            {
                'order': 2,
                'title': 'Complexité algorithmique',
                'slug': 'complexite',
                'minutes': 30,
                'free_preview': True,
                'blocks': [
                    {
                        'type': 'text',
                        'content': """# Complexité algorithmique

## Pourquoi la complexité ?

Deux algorithmes peuvent résoudre le même problème, mais l'un peut être **1000 fois plus rapide** que l'autre sur de grandes données. La **complexité** mesure cette efficacité.

## Notation grand O

On note $O(f(n))$ la complexité, où $n$ est la taille des données.

| Complexité | Nom | Exemple |
|------------|-----|---------|
| $O(1)$ | Constant | Accès à un élément d'une liste |
| $O(\\log n)$ | Logarithmique | Recherche dichotomique |
| $O(n)$ | Linéaire | Parcourir une liste |
| $O(n \\log n)$ | Quasi-linéaire | Timsort, quicksort |
| $O(n^2)$ | Quadratique | Tri par sélection |
| $O(2^n)$ | Exponentielle | Fibonacci récursif naïf |
| $O(n!)$ | Factorielle | Voyageur de commerce |

## Comparaison visuelle

Pour $n = 1000$ :

| Complexité | Nombre d'opérations |
|------------|---------------------|
| $O(1)$ | 1 |
| $O(\\log n)$ | ~10 |
| $O(n)$ | 1 000 |
| $O(n \\log n)$ | ~10 000 |
| $O(n^2)$ | 1 000 000 |
| $O(2^n)$ | $\\approx 10^{301}$ (impossible à calculer) |

## Exemple : recherche dans une liste

### Recherche linéaire — $O(n)$

```python
def recherche_lineaire(liste, cible):
    for i, x in enumerate(liste):
        if x == cible:
            return i
    return -1
```

On parcourt chaque élément : $O(n)$.

### Recherche dichotomique — $O(\\log n)$

**Condition** : la liste doit être **triée**.

```python
def recherche_dichotomique(liste, cible):
    debut = 0
    fin = len(liste) - 1
    while debut <= fin:
        milieu = (debut + fin) // 2
        if liste[milieu] == cible:
            return milieu
        elif liste[milieu] < cible:
            debut = milieu + 1
        else:
            fin = milieu - 1
    return -1

print(recherche_dichotomique([1, 3, 5, 7, 9, 11, 13], 7))  # 3
```

À chaque étape, on divise la liste par 2 → $\\log_2(n)$ étapes.

Pour $n = 1\\,000\\,000$ :
- Linéaire : jusqu'à 1 000 000 d'opérations
- Dichotomique : ~20 opérations !

## Comment analyser son code ?

- Une boucle simple sur $n$ éléments → $O(n)$
- Deux boucles imbriquées → $O(n^2)$
- Une boucle qui divise par 2 à chaque tour → $O(\\log n)$
- Tri Python (Timsort) → $O(n \\log n)$

## Règle pratique

> Si ton algorithme doit traiter 10 000 éléments et qu'il est en $O(n^2)$, ça fait 100 millions d'opérations — ça commence à ramer. En $O(n)$, c'est instantané.

## Compromis temps / espace

Parfois on gagne du temps en utilisant plus de mémoire :

- **Recherche dichotomique** : $O(\\log n)$ temps, $O(1)$ mémoire
- **Table de hachage** (dict) : $O(1)$ temps, $O(n)$ mémoire

En Python, `in` sur un `dict` ou un `set` est en $O(1)$ — beaucoup plus rapide que sur une liste.

```python
# O(n) — lent sur une grande liste
if element in ma_liste: ...

# O(1) — instantané
if element in mon_set: ...
```""",
                    },
                    {
                        'type': 'sandbox',
                        'title': 'Compare les complexités',
                        'code': 'import time\n\n# Recherche linéaire\ndef recherche_lin(liste, cible):\n    for i, x in enumerate(liste):\n        if x == cible:\n            return i\n    return -1\n\n# Recherche dichotomique\ndef recherche_dicho(liste, cible):\n    debut, fin = 0, len(liste) - 1\n    while debut <= fin:\n        m = (debut + fin) // 2\n        if liste[m] == cible:\n            return m\n        elif liste[m] < cible:\n            debut = m + 1\n        else:\n            fin = m - 1\n    return -1\n\n# Test sur 1 000 000 d\'éléments\nN = 1_000_000\ndata = list(range(N))\n\nt0 = time.time()\nrecherche_lin(data, N - 1)\nt_lin = time.time() - t0\n\nt0 = time.time()\nrecherche_dicho(data, N - 1)\nt_dicho = time.time() - t0\n\nprint(f"Linéaire : {t_lin:.4f}s")\nprint(f"Dichotomique : {t_dicho:.6f}s")\nprint(f"Ratio : {t_lin / t_dicho:.0f}x plus rapide")\n',
                    },
                    {
                        'type': 'mcq',
                        'title': 'Recherche dichotomique',
                        'question': "Quelle est la complexité de la recherche dichotomique ?",
                        'explanation': "À chaque étape, on divise la liste par 2 → log₂(n) étapes → O(log n).",
                        'choices': [
                            {'text': 'O(n)', 'correct': False, 'feedback': 'Non, c\'est la recherche linéaire.'},
                            {'text': 'O(log n)', 'correct': True, 'feedback': 'Exact ! On divise par 2 à chaque étape.'},
                            {'text': 'O(n²)', 'correct': False, 'feedback': 'Non, ce serait quadratique.'},
                            {'text': 'O(1)', 'correct': False, 'feedback': 'Non, ce serait constant (accès direct).'},
                        ],
                    },
                    {
                        'type': 'mcq',
                        'title': 'Condition dichotomique',
                        'question': "Quelle condition est requise pour utiliser la recherche dichotomique ?",
                        'explanation': "La dichotomie ne fonctionne que sur une liste triée (sinon on ne sait pas quelle moitié explorer).",
                        'choices': [
                            {'text': 'La liste doit être triée', 'correct': True, 'feedback': 'Exact ! C\'est indispensable.'},
                            {'text': 'La liste doit avoir un nombre pair d\'éléments', 'correct': False, 'feedback': 'Non, peu importe.'},
                            {'text': 'La liste ne doit contenir que des nombres', 'correct': False, 'feedback': 'Non, on peut chercher des chaînes triées.'},
                            {'text': 'La liste doit être immuable', 'correct': False, 'feedback': 'Non, peu importe.'},
                        ],
                    },
                    {
                        'type': 'true_false',
                        'title': 'Vrai ou Faux ? Complexité',
                        'instructions': 'Indique si chaque affirmation est vraie ou fausse.',
                        'explanation': "O(1) est constant, O(n) linéaire, O(n²) quadratique. in sur un set est O(1).",
                        'statements': [
                            {'text': "O(1) signifie que le temps est constant quelle que soit la taille", 'is_correct': True},
                            {'text': "O(n) est plus lent que O(n²)", 'is_correct': False},
                            {'text': "Rechercher dans un set Python est O(1)", 'is_correct': True},
                            {'text': "Trier une liste avec sorted() est O(n)", 'is_correct': False},
                        ],
                    },
                ],
            },
        ],
    },

    # ──────────────────────────────────────────────────────────────────────
    # MODULE 5 — Programmation Orientée Objet (POO)
    # ──────────────────────────────────────────────────────────────────────
    {
        'order': 4,
        'title': 'Programmation Orientée Objet',
        'description': "Classes, objets, héritage, polymorphisme : organise ton code comme un pro.",
        'lessons': [
            {
                'order': 0,
                'title': 'Classes et objets',
                'slug': 'classes-objets',
                'minutes': 40,
                'free_preview': True,
                'blocks': [
                    {
                        'type': 'text',
                        'content': """# Classes et objets

## Pourquoi la POO ?

La **programmation orientée objet** (POO) est un paradigme qui consiste à regrouper données et comportements dans des **objets**. C'est la façon la plus courante de structurer un gros programme.

## Vocabulaire

- **Classe** : un modèle / plan de construction (comme le plan d'une maison)
- **Objet** : une instance concrète d'une classe (comme une maison construite)
- **Attribut** : une variable attachée à un objet (la couleur de la maison)
- **Méthode** : une fonction attachée à un objet (ouvrir la porte)

## Première classe

```python
class Chien:
    def __init__(self, nom, age):
        self.nom = nom
        self.age = age

    def aboyer(self):
        print(f"{self.nom} fait : Wouf !")

    def presenter(self):
        print(f"Je suis {self.nom}, j'ai {self.age} ans.")
```

### Explications

- `class Chien:` définit la classe
- `__init__` est le **constructeur** — appelé quand on crée un objet
- `self` représente l'objet lui-même (obligatoire comme premier paramètre)
- `self.nom` et `self.age` sont des **attributs d'instance**

## Créer des objets

```python
rex = Chien("Rex", 3)         # crée un objet Chien
medor = Chien("Médor", 5)     # un autre objet Chien

rex.aboyer()     # Rex fait : Wouf !
medor.presenter()  # Je suis Médor, j'ai 5 ans.

print(rex.nom)   # "Rex"
print(rex.age)   # 3
```

## Attributs vs variables locales

```python
class Compteur:
    def __init__(self):
        self.valeur = 0     # attribut — vit dans l'objet

    def incrementer(self):
        # self.valeur est accessible partout dans l'objet
        self.valeur += 1

    def afficher(self):
        print(self.valeur)
```

## Attributs de classe vs attributs d'instance

```python
class Etudiant:
    ecole = "Numeria Institute"   # attribut de classe (partagé)

    def __init__(self, nom):
        self.nom = nom   # attribut d'instance (unique)

awa = Etudiant("Awa")
kofi = Etudiant("Kofi")

print(awa.ecole)   # "Numeria Institute"
print(kofi.ecole)  # "Numeria Institute"
print(awa.nom)     # "Awa"
print(kofi.nom)    # "Kofi"

# Modifier l'attribut de classe
Etudiant.ecole = "Numeria"
print(awa.ecole)   # "Numeria" (modifié pour tous)
```

## Méthodes spéciales (dunder methods)

Python définit des méthodes spéciales entourées de `__` :

| Méthode | Rôle |
|---------|------|
| `__init__` | Constructeur |
| `__str__` | Représentation lisible (`print(obj)`) |
| `__repr__` | Représentation développeur |
| `__len__` | `len(obj)` |
| `__eq__` | `obj1 == obj2` |

```python
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __str__(self):
        return f"Point({self.x}, {self.y})"

    def __eq__(self, autre):
        return self.x == autre.x and self.y == autre.y

p1 = Point(3, 5)
p2 = Point(3, 5)
print(p1)         # Point(3, 5)  → utilise __str__
print(p1 == p2)   # True          → utilise __eq__
```""",
                    },
                    {
                        'type': 'sandbox',
                        'title': 'Crée tes premières classes',
                        'code': 'class Chien:\n    def __init__(self, nom, age):\n        self.nom = nom\n        self.age = age\n\n    def aboyer(self):\n        print(f"{self.nom} fait : Wouf !")\n\n    def presenter(self):\n        print(f"Je suis {self.nom}, j\'ai {self.age} ans.")\n\n# Création d\'objets\nrex = Chien("Rex", 3)\nmedor = Chien("Médor", 5)\n\nrex.aboyer()\nmedor.presenter()\nrex.presenter()\n\nprint()\n\n# Attributs publics\nprint(rex.nom, "a", rex.age, "ans")\n',
                    },
                    {
                        'type': 'mcq',
                        'title': 'Qu\'est-ce que self ?',
                        'question': "Que représente `self` dans une méthode Python ?",
                        'explanation': "self est une référence à l'instance courante — l'objet sur lequel la méthode est appelée.",
                        'choices': [
                            {'text': 'Un mot-clé pour déclarer une variable', 'correct': False, 'feedback': 'Non, c\'est juste un paramètre.'},
                            {'text': 'L\'objet sur lequel la méthode est appelée', 'correct': True, 'feedback': 'Exact ! self = l\'instance courante.'},
                            {'text': 'La classe parente', 'correct': False, 'feedback': 'Non, c\'est l\'instance, pas la classe.'},
                            {'text': 'Un paramètre optionnel', 'correct': False, 'feedback': 'Non, il est obligatoire en première position.'},
                        ],
                    },
                    {
                        'type': 'mcq',
                        'title': '__init__',
                        'question': "Quand est appelée la méthode `__init__` ?",
                        'explanation': "__init__ est le constructeur, appelé automatiquement quand on crée un objet avec ClassName(...).",
                        'choices': [
                            {'text': 'À chaque appel de méthode', 'correct': False, 'feedback': 'Non, seulement à la création.'},
                            {'text': 'Automatiquement quand on crée un objet avec ClassName(...)', 'correct': True, 'feedback': 'Exact ! C\'est le constructeur.'},
                            {'text': 'Manuellement avec obj.__init__()', 'correct': False, 'feedback': 'On peut, mais c\'est rare.'},
                            {'text': 'À la fin du programme', 'correct': False, 'feedback': 'Non, c\'est à la création.'},
                        ],
                    },
                    {
                        'type': 'code_exercise',
                        'title': 'Classe Etudiant',
                        'instructions': """Crée une classe `Etudiant` avec :
- un constructeur `__init__(self, nom, age)` qui crée les attributs `nom` et `age`
- une méthode `presenter(self)` qui affiche "Je suis {nom}, j'ai {age} ans."

Crée un étudiant `awa = Etudiant("Awa", 20)` et appelle `awa.presenter()`.

Affichage attendu : `Je suis Awa, j'ai 20 ans.`""",
                        'difficulty': 'medium',
                        'points': 15,
                        'hint': 'Utilise self.nom et self.age dans la méthode presenter, et une f-string.',
                        'explanation': 'Le constructeur stocke les attributs, la méthode les utilise.',
                        'starter': 'class Etudiant:\n    # complète\n    pass\n\nawa = Etudiant("Awa", 20)\nawa.presenter()\n',
                        'solution': 'class Etudiant:\n    def __init__(self, nom, age):\n        self.nom = nom\n        self.age = age\n\n    def presenter(self):\n        print(f"Je suis {self.nom}, j\'ai {self.age} ans.")\n\nawa = Etudiant("Awa", 20)\nawa.presenter()\n',
                        'expected_output': 'Je suis Awa, j\'ai 20 ans.\n',
                        'eval_mode': 'exact',
                    },
                    {
                        'type': 'code_exercise',
                        'title': 'Classe Rectangle',
                        'instructions': """Crée une classe `Rectangle` avec :
- un constructeur `__init__(self, largeur, hauteur)`
- une méthode `aire(self)` qui renvoie `largeur * hauteur`
- une méthode `perimetre(self)` qui renvoie `2 * (largeur + hauteur)`

Crée `r = Rectangle(5, 3)` et affiche son aire puis son périmètre (chacun sur une ligne).""",
                        'difficulty': 'medium',
                        'points': 15,
                        'hint': 'Stocke largeur et hauteur comme attributs dans __init__.',
                        'explanation': 'On stocke les dimensions, puis les méthodes utilisent self.largeur et self.hauteur.',
                        'starter': 'class Rectangle:\n    # complète\n    pass\n\nr = Rectangle(5, 3)\nprint(r.aire())\nprint(r.perimetre())\n',
                        'solution': 'class Rectangle:\n    def __init__(self, largeur, hauteur):\n        self.largeur = largeur\n        self.hauteur = hauteur\n\n    def aire(self):\n        return self.largeur * self.hauteur\n\n    def perimetre(self):\n        return 2 * (self.largeur + self.hauteur)\n\nr = Rectangle(5, 3)\nprint(r.aire())\nprint(r.perimetre())\n',
                        'expected_output': '15\n16\n',
                        'eval_mode': 'exact',
                    },
                    {
                        'type': 'fill_blank',
                        'title': 'Complète la classe',
                        'instructions': 'Complète les parties manquantes.',
                        'text_with_blanks': "{{blank_1}} Personne:\n    def __init__(self, nom):\n        self.{{blank_2}} = nom\n\n    def bonjour({{blank_3}}):\n        print(\"Bonjour\")",
                        'answers': {
                            'blank_1': ['class'],
                            'blank_2': ['nom'],
                            'blank_3': ['self'],
                        },
                        'explanation': 'On définit une classe avec class, on stocke l\'attribut avec self.nom, et self est le premier paramètre de toute méthode.',
                    },
                ],
            },
            {
                'order': 1,
                'title': 'Héritage',
                'slug': 'heritage',
                'minutes': 35,
                'free_preview': True,
                'blocks': [
                    {
                        'type': 'text',
                        'content': """# Héritage

## Principe

L'**héritage** permet à une classe (la **fille**) de récupérer les attributs et méthodes d'une autre classe (la **mère**). On évite ainsi la duplication de code.

## Syntaxe

```python
class Animal:                    # classe mère
    def __init__(self, nom):
        self.nom = nom

    def manger(self):
        print(f"{self.nom} mange.")

class Chien(Animal):             # classe fille — hérite d'Animal
    def aboyer(self):
        print(f"{self.nom} fait : Wouf !")

rex = Chien("Rex")
rex.manger()    # hérité d'Animal → "Rex mange."
rex.aboyer()    # propre à Chien → "Rex fait : Wouf !"
```

## Constructeur et `super()`

Si la classe fille a son propre `__init__`, elle doit appeler celui de la mère avec `super()` :

```python
class Animal:
    def __init__(self, nom, age):
        self.nom = nom
        self.age = age

class Chien(Animal):
    def __init__(self, nom, age, race):
        super().__init__(nom, age)   # appelle Animal.__init__
        self.race = race             # attribut spécifique à Chien

rex = Chien("Rex", 3, "Berger allemand")
print(rex.nom)    # "Rex"        (hérité)
print(rex.age)    # 3            (hérité)
print(rex.race)   # "Berger allemand"  (spécifique)
```

## Redéfinition (override)

Une classe fille peut **redéfinir** une méthode de la classe mère :

```python
class Animal:
    def __init__(self, nom):
        self.nom = nom

    def cri(self):
        print(f"{self.nom} fait un bruit.")

class Chien(Animal):
    def cri(self):                  # redéfinition
        print(f"{self.nom} fait : Wouf !")

class Chat(Animal):
    def cri(self):                  # redéfinition
        print(f"{self.nom} fait : Miaou !")

Animal("X").cri()    # X fait un bruit.
Chien("Rex").cri()   # Rex fait : Wouf !
Chat("Minou").cri()  # Minou fait : Miaou !
```

## Hiérarchie multi-niveaux

L'héritage peut s'enchaîner :

```python
class Vehicle:
    def rouler(self):
        print("Je roule.")

class Voiture(Vehicle):
    def klaxonner(self):
        print("Pouet !")

class VoitureDeCourse(Voiture):
    def turbo(self):
        print("VROUM !")

v = VoitureDeCourse()
v.rouler()     # hérité de Vehicle
v.klaxonner()  # hérité de Voiture
v.turbo()      # propre à VoitureDeCourse
```

## Vérifier les relations

```python
print(isinstance(rex, Chien))    # True
print(isinstance(rex, Animal))   # True (Chien hérite d'Animal)
print(issubclass(Chien, Animal)) # True
```

## Quand utiliser l'héritage ?

✅ **Bon usage** :
- `Chien` est un `Animal` → héritage naturel
- `Voiture` est un `Vehicle` → héritage naturel

❌ **Mauvais usage** :
- Éviter l'héritage profond (>3 niveaux)
- Préférer la **composition** quand la relation n'est pas "est un"

**Composition** : un objet contient un autre objet.
```python
class Moteur:
    def demarrer(self):
        print("Vroom")

class Voiture:
    def __init__(self):
        self.moteur = Moteur()   # composition

    def demarrer(self):
        self.moteur.demarrer()
```""",
                    },
                    {
                        'type': 'sandbox',
                        'title': 'Teste l\'héritage',
                        'code': 'class Animal:\n    def __init__(self, nom):\n        self.nom = nom\n\n    def cri(self):\n        print(f"{self.nom} fait un bruit.")\n\nclass Chien(Animal):\n    def cri(self):\n        print(f"{self.nom} fait : Wouf !")\n\nclass Chat(Animal):\n    def cri(self):\n        print(f"{self.nom} fait : Miaou !")\n\nanimaux = [Chien("Rex"), Chat("Minou"), Animal("Truc")]\nfor a in animaux:\n    a.cri()  # chaque objet appelle SA version de cri()\n\nprint()\n\n# isinstance\nprint("Rex est un Chien ?", isinstance(Chien("Rex"), Chien))\nprint("Rex est un Animal ?", isinstance(Chien("Rex"), Animal))\nprint("Chien sous-classe d\'Animal ?", issubclass(Chien, Animal))\n',
                    },
                    {
                        'type': 'mcq',
                        'title': 'Héritage — définition',
                        'question': "Qu'est-ce que l'héritage en POO ?",
                        'explanation': "L'héritage permet à une classe fille de récupérer attributs et méthodes d'une classe mère.",
                        'choices': [
                            {'text': 'Copier le code d\'une autre classe manuellement', 'correct': False, 'feedback': 'Non, c\'est automatique.'},
                            {'text': 'Une classe fille récupère attributs et méthodes d\'une classe mère', 'correct': True, 'feedback': 'Exact !'},
                            {'text': 'Cacher des attributs', 'correct': False, 'feedback': 'Non, ça c\'est l\'encapsulation.'},
                            {'text': 'Créer plusieurs objets en même temps', 'correct': False, 'feedback': 'Non.'},
                        ],
                    },
                    {
                        'type': 'mcq',
                        'title': 'super()',
                        'question': "À quoi sert `super().__init__()` dans une classe fille ?",
                        'explanation': "super() appelle la méthode __init__ de la classe mère, pour initialiser les attributs hérités.",
                        'choices': [
                            {'text': 'À appeler le constructeur de la classe mère', 'correct': True, 'feedback': 'Exact !'},
                            {'text': 'À créer un super objet', 'correct': False, 'feedback': 'Non.'},
                            {'text': 'À ignorer la classe mère', 'correct': False, 'feedback': 'C\'est l\'inverse.'},
                            {'text': 'À appeler n\'importe quelle méthode', 'correct': False, 'feedback': 'super() peut appeler n\'importe quelle méthode mère, mais __init__ est le plus courant.'},
                        ],
                    },
                    {
                        'type': 'code_exercise',
                        'title': 'Héritage Animal/Chien',
                        'instructions': """Crée deux classes :

1. `Animal` avec :
   - `__init__(self, nom)` qui crée `self.nom`
   - `cri(self)` qui affiche `{nom} fait un bruit.`

2. `Chien(Animal)` qui hérite d'Animal et redéfinit :
   - `cri(self)` qui affiche `{nom} fait : Wouf !`

Crée `rex = Chien("Rex")` et appelle `rex.cri()`.""",
                        'difficulty': 'medium',
                        'points': 15,
                        'hint': 'class Chien(Animal): définit l\'héritage. Redéfinis cri() dans Chien.',
                        'explanation': 'Chien hérite d\'Animal pour le constructeur, mais redéfinit la méthode cri().',
                        'starter': 'class Animal:\n    # complète\n    pass\n\nclass Chien(Animal):\n    # complète\n    pass\n\nrex = Chien("Rex")\nrex.cri()\n',
                        'solution': 'class Animal:\n    def __init__(self, nom):\n        self.nom = nom\n\n    def cri(self):\n        print(f"{self.nom} fait un bruit.")\n\nclass Chien(Animal):\n    def cri(self):\n        print(f"{self.nom} fait : Wouf !")\n\nrex = Chien("Rex")\nrex.cri()\n',
                        'expected_output': 'Rex fait : Wouf !\n',
                        'eval_mode': 'exact',
                    },
                    {
                        'type': 'true_false',
                        'title': 'Vrai ou Faux ? Héritage',
                        'instructions': 'Indique si chaque affirmation est vraie ou fausse.',
                        'explanation': "Une classe fille hérite des attributs et méthodes de la classe mère. isinstance vérifie la relation.",
                        'statements': [
                            {'text': "Une classe fille hérite automatiquement des méthodes de sa classe mère", 'is_correct': True},
                            {'text': "Une classe fille ne peut pas redéfinir une méthode de la classe mère", 'is_correct': False},
                            {'text': "isinstance(rex, Animal) renvoie True si rex est un Chien et Chien hérite d'Animal", 'is_correct': True},
                            {'text': "Une classe ne peut hériter que d'une seule autre classe", 'is_correct': False},
                        ],
                    },
                ],
            },
            {
                'order': 2,
                'title': 'Polymorphisme et encapsulation',
                'slug': 'polymorphisme-encapsulation',
                'minutes': 35,
                'free_preview': True,
                'blocks': [
                    {
                        'type': 'text',
                        'content': """# Polymorphisme et encapsulation

## Polymorphisme

Le **polymorphisme** (= "plusieurs formes") permet à des objets de classes différentes de répondre à la **même méthode** chacun à leur façon.

```python
class Chien:
    def crier(self):
        return "Wouf !"

class Chat:
    def crier(self):
        return "Miaou !"

class Vache:
    def crier(self):
        return "Meuh !"

animaux = [Chien(), Chat(), Vache()]
for animal in animaux:
    print(animal.crier())
# Wouf !
# Miaou !
# Meuh !
```

Python est **dynamiquement typé** : pas besoin d'héritage commun, il suffit que chaque objet ait la méthode `crier()`.

### Polymorphisme + héritage

```python
class Forme:
    def aire(self):
        return 0

class Carre(Forme):
    def __init__(self, cote):
        self.cote = cote
    def aire(self):
        return self.cote ** 2

class Cercle(Forme):
    def __init__(self, rayon):
        self.rayon = rayon
    def aire(self):
        return 3.14159 * self.rayon ** 2

formes = [Carre(4), Cercle(3), Forme()]
for f in formes:
    print(f.aire())
# 16
# 28.27431
# 0
```

Chaque objet appelle **sa propre version** de `aire()`.

## Encapsulation

L'**encapsulation** consiste à **protéger les données** internes d'un objet en contrôlant l'accès via des méthodes.

### Convention `_` et `__`

- `nom` : **public** (accès libre)
- `_nom` : **protégé** (convention — ne pas y toucher hors de la classe et des sous-classes)
- `__nom` : **privé** (Python modifie le nom pour le cacher — *name mangling*)

```python
class CompteBancaire:
    def __init__(self, solde_initial):
        self.__solde = solde_initial   # privé

    def deposer(self, montant):
        if montant > 0:
            self.__solde += montant

    def retirer(self, montant):
        if 0 < montant <= self.__solde:
            self.__solde -= montant
        else:
            print("Retrait impossible")

    def get_solde(self):
        return self.__solde

c = CompteBancaire(1000)
c.deposer(500)
c.retirer(200)
print(c.get_solde())   # 1300

# ❌ Interdit (convention + name mangling)
# print(c.__solde)      → AttributeError
# c.__solde = 999999    → ne modifie pas le vrai solde
```

### Pourquoi encapsuler ?

1. **Protéger l'intégrité** : impossible de mettre un solde négatif sans passer par `retirer()`
2. **Cacher l'implémentation** : l'utilisateur n'a pas besoin de savoir comment c'est stocké
3. **Faciliter les changements** : on peut changer le stockage interne sans casser le code des utilisateurs

### Propriétés (`@property`)

Python permet de définir des **getters/setters** élégants avec `@property` :

```python
class Temperature:
    def __init__(self, celsius):
        self._celsius = celsius

    @property
    def celsius(self):
        return self._celsius

    @celsius.setter
    def celsius(self, valeur):
        if valeur < -273.15:
            raise ValueError("Impossible : sous le zéro absolu")
        self._celsius = valeur

    @property
    def fahrenheit(self):
        return self._celsius * 9 / 5 + 32

t = Temperature(25)
print(t.celsius)      # 25     (appelle le getter)
print(t.fahrenheit)   # 77.0   (propriété calculée)

t.celsius = 30        # appelle le setter
print(t.celsius)      # 30

# t.celsius = -300    → ValueError (protégé par le setter)
```

## Les 4 piliers de la POO

| Pilier | Description |
|--------|-------------|
| **Encapsulation** | Protéger les données internes |
| **Héritage**      | Réutiliser du code via une hiérarchie |
| **Polymorphisme** | Une même méthode, plusieurs comportements |
| **Abstraction**   | Cacher la complexité, exposer une interface simple |

## Récapitulatif du cours

Tu as parcouru un long chemin ! 🎉

1. **Module 1** : variables, types, opérateurs
2. **Module 2** : conditions, boucles, fonctions
3. **Module 3** : listes, tuples, dictionnaires, chaînes
4. **Module 4** : récursivité, tri, complexité
5. **Module 5** : POO (classes, héritage, polymorphisme, encapsulation)

Tu peux maintenant :
- Écrire des programmes Python structurés
- Choisir la bonne structure de données
- Analyser la complexité d'un algorithme
- Modéliser un problème en objets

**Prochaines étapes** : exceptions, fichiers, modules, bibliothèques (NumPy, Pandas), framework web Django... Le voyage ne fait que commencer ! 🚀""",
                    },
                    {
                        'type': 'sandbox',
                        'title': 'Polymorphisme en action',
                        'code': 'class Forme:\n    def aire(self):\n        return 0\n\nclass Carre(Forme):\n    def __init__(self, cote):\n        self.cote = cote\n    def aire(self):\n        return self.cote ** 2\n\nclass Cercle(Forme):\n    def __init__(self, rayon):\n        self.rayon = rayon\n    def aire(self):\n        return 3.14159 * self.rayon ** 2\n\nformes = [Carre(4), Cercle(3), Forme()]\nfor f in formes:\n    print(f"aire = {f.aire()}")\n\nprint()\n\n# Encapsulation avec @property\nclass Temperature:\n    def __init__(self, c):\n        self._c = c\n\n    @property\n    def celsius(self):\n        return self._c\n\n    @celsius.setter\n    def celsius(self, val):\n        if val < -273.15:\n            raise ValueError("Trop froid !")\n        self._c = val\n\nt = Temperature(25)\nprint(t.celsius)\nt.celsius = 30\nprint(t.celsius)\n',
                    },
                    {
                        'type': 'mcq',
                        'title': 'Polymorphisme',
                        'question': "Qu'est-ce que le polymorphisme ?",
                        'explanation': "Le polymorphisme permet à des objets de classes différentes de répondre à la même méthode chacun à sa façon.",
                        'choices': [
                            {'text': 'Le fait d\'avoir plusieurs constructeurs', 'correct': False, 'feedback': 'Non.'},
                            {'text': 'La capacité d\'objets différents à répondre à la même méthode chacun à sa façon', 'correct': True, 'feedback': 'Exact !'},
                            {'text': 'Le fait de cacher des attributs', 'correct': False, 'feedback': 'Non, ça c\'est l\'encapsulation.'},
                            {'text': 'Le fait de créer plusieurs objets', 'correct': False, 'feedback': 'Non.'},
                        ],
                    },
                    {
                        'type': 'mcq',
                        'title': 'Encapsulation',
                        'question': "Comment nomme-t-on un attribut 'privé' en Python (par convention) ?",
                        'explanation': "Un attribut commençant par __ (double underscore) est 'privé' — Python applique le name mangling.",
                        'choices': [
                            {'text': '_attribut (un underscore)', 'correct': False, 'feedback': 'Un seul underscore = protégé, pas privé.'},
                            {'text': '__attribut (deux underscores)', 'correct': True, 'feedback': 'Exact ! Le double underscore déclenche le name mangling.'},
                            {'text': 'ATTRIBUT (majuscules)', 'correct': False, 'feedback': 'Convention pour les constantes, pas pour le privé.'},
                            {'text': 'attribut_ (underscore final)', 'correct': False, 'feedback': 'Utilisé pour éviter des conflits de noms, pas pour cacher.'},
                        ],
                    },
                    {
                        'type': 'mcq',
                        'title': 'Les 4 piliers',
                        'question': "Lequel n'est PAS un des 4 piliers de la POO ?",
                        'explanation': "Les 4 piliers sont : encapsulation, héritage, polymorphisme, abstraction. La compilation n'en fait pas partie.",
                        'choices': [
                            {'text': 'Encapsulation', 'correct': False, 'feedback': 'C\'est un pilier.'},
                            {'text': 'Héritage', 'correct': False, 'feedback': 'C\'est un pilier.'},
                            {'text': 'Compilation', 'correct': True, 'feedback': 'Exact ! Ce n\'est pas un pilier de la POO.'},
                            {'text': 'Polymorphisme', 'correct': False, 'feedback': 'C\'est un pilier.'},
                        ],
                    },
                    {
                        'type': 'code_exercise',
                        'title': 'Polymorphisme Forme',
                        'instructions': """Crée deux classes :
- `Carre` avec `__init__(self, cote)` et `aire(self)` qui renvoie `cote ** 2`
- `Cercle` avec `__init__(self, rayon)` et `aire(self)` qui renvoie `3.14 * rayon ** 2`

Crée une liste `formes = [Carre(4), Cercle(3)]` et affiche l'aire de chaque forme.""",
                        'difficulty': 'medium',
                        'points': 15,
                        'hint': 'Chaque classe a sa propre méthode aire() qui calcule différemment.',
                        'explanation': 'Deux classes indépendantes avec la même méthode aire() — polymorphisme.',
                        'starter': '# Crée les deux classes\n\n\n# Crée la liste et affiche les aires\nformes = [Carre(4), Cercle(3)]\nfor f in formes:\n    print(f.aire())\n',
                        'solution': 'class Carre:\n    def __init__(self, cote):\n        self.cote = cote\n    def aire(self):\n        return self.cote ** 2\n\nclass Cercle:\n    def __init__(self, rayon):\n        self.rayon = rayon\n    def aire(self):\n        return 3.14 * self.rayon ** 2\n\nformes = [Carre(4), Cercle(3)]\nfor f in formes:\n    print(f.aire())\n',
                        'expected_output': '16\n28.26\n',
                        'eval_mode': 'exact',
                    },
                    {
                        'type': 'code_exercise',
                        'title': 'Compte bancaire encapsulé',
                        'instructions': """Crée une classe `CompteBancaire` avec :
- un attribut **privé** `__solde` initialisé dans `__init__(self, solde_initial)`
- une méthode `deposer(self, montant)` qui ajoute au solde (si montant > 0)
- une méthode `get_solde(self)` qui renvoie le solde

Crée `c = CompteBancaire(1000)`, dépose 500, affiche le solde final (doit être 1500).""",
                        'difficulty': 'hard',
                        'points': 20,
                        'hint': 'L\'attribut privé s\'écrit self.__solde. La méthode get_solde renvoie self.__solde.',
                        'explanation': 'On protège le solde en l\'encapsulant avec __, et on y accède via get_solde().',
                        'starter': 'class CompteBancaire:\n    # complète\n    pass\n\nc = CompteBancaire(1000)\nc.deposer(500)\nprint(c.get_solde())\n',
                        'solution': 'class CompteBancaire:\n    def __init__(self, solde_initial):\n        self.__solde = solde_initial\n\n    def deposer(self, montant):\n        if montant > 0:\n            self.__solde += montant\n\n    def get_solde(self):\n        return self.__solde\n\nc = CompteBancaire(1000)\nc.deposer(500)\nprint(c.get_solde())\n',
                        'expected_output': '1500\n',
                        'eval_mode': 'exact',
                    },
                    {
                        'type': 'true_false',
                        'title': 'Vrai ou Faux ? POO avancée',
                        'instructions': 'Indique si chaque affirmation est vraie ou fausse.',
                        'explanation': "Le polymorphisme permet à des objets différents de répondre à la même méthode. @property définit un getter. L'encapsulation protège les données.",
                        'statements': [
                            {'text': "Le polymorphisme permet d'appeler la même méthode sur des objets de classes différentes", 'is_correct': True},
                            {'text': "Un attribut __solde est accessible directement avec objet.__solde", 'is_correct': False},
                            {'text': "@property permet de définir un getter élégant", 'is_correct': True},
                            {'text': "L'encapsulation sert à cacher l'implémentation et protéger les données", 'is_correct': True},
                        ],
                    },
                ],
            },
        ],
    },
]
