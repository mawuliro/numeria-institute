"""
Helpers partagés pour les leçons du cours de Mécanique Quantique I.

Chaque leçon est définie dans un fichier séparé et importe ces helpers
pour construire sa structure de blocs.

RÈGLES D'ÉCHAPPEMENT CRITIQUES (à respecter STRICTEMENT) :
- Source Python : `\\vec{F}` (2 backslashes) → DB : `\vec{F}` → MathJax rend ✓
- JAMAIS utiliser `\\\\vec{F}` (4 backslashes) → casse MathJax ✗
- Pour matplotlib : utiliser raw strings `r'...'` pour les labels LaTeX

Usage dans un fichier de leçon :

    from cours.quantum_modules.helpers import T, S, APP, MCQ, FB, TF

    LESSON = {
        "order": 0,
        "title": "Titre de la leçon",
        "slug": "titre-de-la-lecon",
        "minutes": 45,
        "blocks": [
            T("# Titre\n\nTexte avec $\\vec{F}$ et $$\\frac{a}{b}$$..."),
            S("Titre sandbox", "import matplotlib.pyplot as plt\n..."),
            APP("Titre exo", "Énoncé...", "Correction détaillée..."),
            MCQ("Titre QCM", "Question ?", [...], explanation="..."),
            FB("Titre FB", "Texte avec {{blank_1}}", {"blank_1": ["valeur"]}),
            TF("Titre TF", [{"statement": "...", "is_true": True}, ...]),
        ],
    }
"""


def T(content):
    """Bloc texte (Markdown + LaTeX)."""
    return {"type": "text", "content": content}


def S(title, code):
    """Bloc sandbox (code matplotlib qui sauvegarde dans plot.png)."""
    return {"type": "sandbox", "title": title, "code": code}


def APP(title, enonce, correction):
    """Exercice d'application corrigé avec correction dépliable."""
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
    """QCM. choices = [{"text":..., "correct":..., "feedback":...}, ...]."""
    out = {"type": "mcq", "title": title, "question": question,
           "choices": choices, "explanation": explanation}
    out.update(kw)
    return out


def FB(title, text_with_blanks, answers, explanation="", **kw):
    """Exercice à trous. answers = {"blank_1": ["val1", "val2"], ...}."""
    out = {"type": "fill_blank", "title": title,
           "text_with_blanks": text_with_blanks, "answers": answers,
           "explanation": explanation}
    out.update(kw)
    return out


def TF(title, statements, explanation=""):
    """Vrai/Faux. statements = [{"statement":..., "is_true":...}, ...]."""
    return {"type": "true_false", "title": title,
            "statements": statements, "explanation": explanation}
